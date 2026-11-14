"""Land the cached StatsBomb data as Parquet, the raw layer the dbt warehouse reads.

    python -m src.landing                      # the app's shot competition (PL 2015/16)
    python -m src.landing comp55_season282     # any dataset key of data/manifest.json
    python -m src.landing --all

The per-match cache is pickled pandas (`data_loader`), which only Python can read. dbt works in
SQL, so each match is rewritten once as one Parquet file:

    $FAP_CACHE_DIR/raw/events/competition_id=2/season_id=27/match_3753972.parquet
    $FAP_CACHE_DIR/raw/lineups/competition_id=2/season_id=27/match_3753972.parquet
    $FAP_CACHE_DIR/raw/matches/competition_id=2/season_id=27/matches.parquet

One file per match on purpose: a match never changes once played, so a new match is a new file
and nothing already landed is rewritten. That is what the warehouse's incremental model relies
on. The competition and season live in the folder names (Hive partitioning), which DuckDB turns
back into columns.

Lineups are flattened to one row per stint (a player's spell in one position), which is the
grain minutes are computed at. The match sheet (home and away team names) is the one thing not
in the cache: it is one small request per competition, made only when its file is missing.
Events and lineups are never downloaded here: a match missing from the cache is reported.
"""

import io
import json
import pickle
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data_loader import CACHE_DIR, load_matches
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
    "pass_shot_assist": pa.bool_(),
    "pass_goal_assist": pa.bool_(),
    "pass_outcome": pa.string(),
    "pass_end_location": pa.list_(pa.float64()),
    "dribble_outcome": pa.string(),
    "duel_type": pa.string(),
    "goalkeeper_type": pa.string(),
}

LINEUP_SCHEMA = pa.schema([
    ("match_id", pa.int64()),
    ("team", pa.string()),
    ("player_id", pa.int64()),
    ("player_name", pa.string()),
    ("player_nickname", pa.string()),
    ("stint_index", pa.int64()),
    ("position", pa.string()),
    ("from_clock", pa.string()),
    ("to_clock", pa.string()),
])

MATCH_COLUMNS = [
    "match_id", "match_date", "match_week", "home_team", "away_team", "home_score", "away_score",
]


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


def lineups_to_table(lineups, match_id):
    """Flatten one match's lineups to one row per stint.

    Args:
        lineups (dict[str, pandas.DataFrame]): `data_loader.load_lineups`' output, a table per
            team whose `positions` cell is a list of stints (position, from, to).
        match_id (int): written on every row; the lineups themselves don't carry it.

    Returns:
        pyarrow.Table: `LINEUP_SCHEMA`. `stint_index` is the stint's place in the player's
            list, kept because the first position listed wins a tie on minutes. A squad
            player who never came on has no stints and so no rows.
    """
    rows = []
    for team, lineup in lineups.items():
        for player in lineup.to_dict(orient="records"):
            for stint_index, stint in enumerate(player["positions"]):
                rows.append({
                    "match_id": match_id,
                    "team": team,
                    "player_id": player["player_id"],
                    "player_name": player["player_name"],
                    "player_nickname": player.get("player_nickname"),
                    "stint_index": stint_index,
                    "position": stint["position"],
                    "from_clock": stint["from"],
                    "to_clock": stint["to"],
                })
    return pa.Table.from_pylist(rows, schema=LINEUP_SCHEMA)


def match_path(raw_dir, comp_id, season_id, match_id, kind="events"):
    """Where one match's events or lineups land: Hive-style folders, one file per match."""
    return (
        Path(raw_dir) / kind / f"competition_id={comp_id}" / f"season_id={season_id}"
        / f"match_{match_id}.parquet"
    )


def _write_parquet(table, target):
    """Write a table to `target` in one move, so a reader never sees half a file."""
    buffer = io.BytesIO()
    pq.write_table(table, buffer, compression="zstd")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomically(target, buffer.getvalue())


def land_matches(dataset, raw_dir=RAW_DIR, force=False, fetch=load_matches):
    """Land one competition's match sheet (who played whom); download it only if missing.

    Args:
        dataset (dict): one entry of `data/manifest.json`'s `datasets`.
        raw_dir (str | Path): root of the raw layer.
        force (bool): fetch and rewrite even if the file exists.
        fetch (callable): `(competition_id, season_id) -> DataFrame`, swappable in tests.

    Returns:
        bool: True if the file was written, False if it was already there.
    """
    target = (
        Path(raw_dir) / "matches" / f"competition_id={dataset['comp_id']}"
        / f"season_id={dataset['season_id']}" / "matches.parquet"
    )
    if target.exists() and not force:
        return False
    matches = fetch(dataset["comp_id"], dataset["season_id"])[MATCH_COLUMNS]
    _write_parquet(pa.Table.from_pandas(matches, preserve_index=False), target)
    return True


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
            A match counts once: landed if its events or its lineups were written, missing if
            either pickle is absent.
    """
    counts = {"landed": 0, "skipped": 0, "missing": 0}
    for match_id in dataset["match_ids"]:
        targets = {
            kind: match_path(raw_dir, dataset["comp_id"], dataset["season_id"], match_id, kind)
            for kind in ("events", "lineups")
        }
        todo = [kind for kind, target in targets.items() if force or not target.exists()]
        if not todo:
            counts["skipped"] += 1
            continue
        sources = {kind: Path(cache_dir) / f"{kind}_{match_id}.pkl" for kind in todo}
        if not all(source.exists() for source in sources.values()):
            counts["missing"] += 1
            continue
        for kind, source in sources.items():
            with open(source, "rb") as cache_file:
                cached = pickle.load(cache_file)
            if kind == "events":
                if not isinstance(cached, pd.DataFrame) or cached.empty:
                    raise ValueError(f"events_{match_id}.pkl holds no events")
                table = events_to_table(cached)
            else:
                table = lineups_to_table(cached, match_id)
            _write_parquet(table, targets[kind])
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
        land_matches(datasets[key], force=force)
        counts = land_dataset(datasets[key], force=force)
        missing += counts["missing"]
        print(f"{key} ({datasets[key]['label']}): {counts['landed']} landed, "
              f"{counts['skipped']} already there, {counts['missing']} not in the cache")
    print(f"Raw layer: {RAW_DIR}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
