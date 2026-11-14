"""Land the cached StatsBomb events as Parquet, the raw layer the dbt warehouse reads.

    python -m src.landing                      # the app's shot competition (PL 2015/16)
    python -m src.landing comp55_season282     # any dataset key of data/manifest.json
    python -m src.landing --all

The per-match cache is pickled pandas (`data_loader`), which only Python can read. dbt works in
SQL, so each match is rewritten once as one Parquet file:

    $FAP_CACHE_DIR/raw/events/competition_id=2/season_id=27/match_3753972.parquet

One file per match on purpose: a match never changes once played, so a new match is a new file
and nothing already landed is rewritten. That is what the warehouse's incremental model relies
on. The competition and season live in the folder names (Hive partitioning), which DuckDB turns
back into columns.

Nothing is downloaded here: a match missing from the cache is reported, not fetched.
"""

import io
import json
import pickle
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data_loader import CACHE_DIR
from src.net import write_atomically

REPO = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO / "data" / "manifest.json"
RAW_DIR = CACHE_DIR / "raw"
DEFAULT_DATASET_KEYS = ["comp2_season27"]

# statsbombpy drops a column from a match where no event has it set (a match with no cut-back
# has no `pass_cut_back`). The staging models select these columns by name, so every landed
# file carries them, typed, null where the match had none. Everything else is landed as found.
CONTRACT_COLUMNS = {
    "id": pa.string(),
    "index": pa.int64(),
    "match_id": pa.int64(),
    "period": pa.int64(),
    "minute": pa.int64(),
    "second": pa.int64(),
    "timestamp": pa.string(),
    "type": pa.string(),
    "team": pa.string(),
    "team_id": pa.int64(),
    "player": pa.string(),
    "player_id": pa.int64(),
    "position": pa.string(),
    "possession": pa.int64(),
    "play_pattern": pa.string(),
    "location": pa.list_(pa.float64()),
    "under_pressure": pa.bool_(),
    "shot_outcome": pa.string(),
    "shot_type": pa.string(),
    "shot_body_part": pa.string(),
    "shot_technique": pa.string(),
    "shot_first_time": pa.bool_(),
    "shot_statsbomb_xg": pa.float64(),
    "shot_key_pass_id": pa.string(),
    "pass_cross": pa.bool_(),
    "pass_through_ball": pa.bool_(),
    "pass_cut_back": pa.bool_(),
}


def _is_missing(value):
    """True for None and NaN, the two ways pandas marks an empty cell in an object column."""
    return value is None or (isinstance(value, float) and value != value)


def _is_number(value):
    """True for ints and floats but not booleans (`True` is an int in Python)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _arrow_column(series):
    """Turn one pandas column into an Arrow array, or None when the column is entirely empty.

    Object columns are where pickle and Parquet disagree: pandas lets one column hold True/NaN,
    strings, lists or dicts. The rule here is by content: all booleans → bool, all strings →
    string, lists of numbers (locations) → list of floats, anything else (freeze frames,
    tactics, related event ids) → a JSON string, which DuckDB can still unpack. An entirely
    empty column is dropped rather than written with a made-up type; the reader fills it back
    as nulls (`union_by_name`).
    """
    if series.dtype != object:
        return None if series.isna().all() else pa.array(series, from_pandas=True)
    values = [None if _is_missing(value) else value for value in series]
    present = [value for value in values if value is not None]
    if not present:
        return None
    if all(isinstance(value, bool) for value in present):
        return pa.array(values, pa.bool_())
    if all(isinstance(value, str) for value in present):
        return pa.array(values, pa.string())
    if all(isinstance(value, list) and all(_is_number(item) for item in value) for value in present):
        return pa.array(values, pa.list_(pa.float64()))
    return pa.array(
        [None if value is None else json.dumps(value, default=str) for value in values], pa.string()
    )


def events_to_table(events):
    """Convert one match's event DataFrame to an Arrow table with the contract columns typed.

    Args:
        events (pandas.DataFrame): one match as `data_loader.load_events` returns it.

    Returns:
        pyarrow.Table: one row per event, in the DataFrame's row order. Contract columns are
            always present with their fixed type; the remaining columns keep whatever the match
            had, and all-empty ones are left out.
    """
    arrays, names = [], []
    for name, arrow_type in CONTRACT_COLUMNS.items():
        if name in events.columns:
            array = _arrow_column(events[name])
            array = pa.nulls(len(events), arrow_type) if array is None else array.cast(arrow_type)
        else:
            array = pa.nulls(len(events), arrow_type)
        arrays.append(array)
        names.append(name)
    for name in events.columns:
        if name in CONTRACT_COLUMNS:
            continue
        array = _arrow_column(events[name])
        if array is not None:
            arrays.append(array)
            names.append(name)
    return pa.table(arrays, names=names)


def match_path(raw_dir, comp_id, season_id, match_id):
    """Where one match's events land: Hive-style folders, one file per match."""
    return (
        Path(raw_dir) / "events" / f"competition_id={comp_id}" / f"season_id={season_id}"
        / f"match_{match_id}.parquet"
    )


def land_dataset(dataset, raw_dir=RAW_DIR, cache_dir=CACHE_DIR, force=False):
    """Land every cached match of one manifest dataset; skip those already landed.

    Args:
        dataset (dict): one entry of `data/manifest.json`'s `datasets` (comp_id, season_id,
            match_ids).
        raw_dir (str | Path): root of the raw layer.
        cache_dir (str | Path): the per-match pickle cache.
        force (bool): rewrite files that already exist (after a change to this module).

    Returns:
        dict: counts of matches `landed`, `skipped` (already there) and `missing` (not cached).
    """
    counts = {"landed": 0, "skipped": 0, "missing": 0}
    for match_id in dataset["match_ids"]:
        target = match_path(raw_dir, dataset["comp_id"], dataset["season_id"], match_id)
        if target.exists() and not force:
            counts["skipped"] += 1
            continue
        source = Path(cache_dir) / f"events_{match_id}.pkl"
        if not source.exists():
            counts["missing"] += 1
            continue
        with open(source, "rb") as cache_file:
            events = pickle.load(cache_file)
        if not isinstance(events, pd.DataFrame) or events.empty:
            counts["missing"] += 1
            continue
        buffer = io.BytesIO()
        pq.write_table(events_to_table(events), buffer, compression="zstd")
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomically(target, buffer.getvalue())
        counts["landed"] += 1
    return counts


def main(argv=None):
    """Command line: land the named manifest datasets (default: the app's shot competition)."""
    argv = sys.argv[1:] if argv is None else argv
    force = "--force" in argv
    datasets = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["datasets"]
    keys = [arg for arg in argv if not arg.startswith("--")]
    if "--all" in argv:
        keys = list(datasets)
    keys = keys or DEFAULT_DATASET_KEYS
    unknown = [key for key in keys if key not in datasets]
    if unknown:
        print(f"Not in data/manifest.json: {', '.join(unknown)}. Known: {', '.join(datasets)}")
        return 2
    missing = 0
    for key in keys:
        counts = land_dataset(datasets[key], force=force)
        missing += counts["missing"]
        print(f"{key} ({datasets[key]['label']}): {counts['landed']} landed, "
              f"{counts['skipped']} already there, {counts['missing']} not in the cache")
    print(f"Raw layer: {RAW_DIR}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
