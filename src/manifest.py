"""Data provenance manifest for the Player Evaluation Framework.

Pins exactly which StatsBomb open-data matches each dataset resolves to, plus content
hashes of the processed flat tables the models consume. Purpose: reproducibility and
drift detection.

StatsBomb open data is immutable *per match*, but the *set* of matches in a
competition/season can still change under us — late-added fixtures, corrections, or a
statsbombpy upgrade that reshapes a schema. A committed manifest turns "the data changed"
from a silent surprise into a diffable event: re-run `python -m src.manifest`, and any
delta in match ids, counts, or table hashes shows up in version control.

The manifest is deliberately a pure function of (the match listing + the processed tables +
the installed statsbombpy version) — no wall-clock timestamp — so an unchanged dataset
regenerates byte-for-byte and only real drift produces a diff. Git records the "when".

Run as a build step (needs network for the match listing):

    python -m src.manifest

writes ``data/manifest.json`` (tracked via a ``.gitignore`` exception).
"""

from __future__ import annotations

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from src import config
from src.data_loader import CACHE_DIR, load_matches

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "manifest.json"

# The processed flat tables the models actually consume (built in notebook 02, plus the Phase 4c
# generalisation table from `pipeline.build_generalisation_table`). Hashing them catches a silent
# change in the feature pipeline, not just in the upstream raw data.
PROCESSED_TABLES = ("shots_train.parquet", "shots_test.parquet", "shots_generalisation.parquet")

# 16 hex chars (64 bits) is plenty to detect drift by eye; the full digest adds noise.
_HASH_LEN = 16


def hash_match_ids(match_ids):
    """Return a stable short fingerprint of a set of match ids.

    Sorted before hashing so the fingerprint is order-independent — the *set* of matches is
    what matters, not the order a listing happened to return them in.
    """
    joined = ",".join(str(m) for m in sorted(int(m) for m in match_ids))
    return hashlib.sha256(joined.encode()).hexdigest()[:_HASH_LEN]


def hash_file(path):
    """Return the short sha256 of a file's bytes, or None if the file is absent."""
    path = Path(path)
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:_HASH_LEN]


def _statsbombpy_version():
    """Return the installed statsbombpy version string, or 'unknown' if it can't be read.

    A dependency bump is provenance that matters (schemas move between releases) but changes
    rarely, so it belongs in the manifest without adding per-run noise.
    """
    try:
        return version("statsbombpy")
    except PackageNotFoundError:  # pragma: no cover - only if run outside the pinned env
        return "unknown"


def _dataset_entry(dataset, matches_loader, cache_dir):
    """Build the manifest entry for one dataset: identity, match-set pin, local cache coverage."""
    matches = matches_loader(dataset.comp_id, dataset.season_id)
    match_ids = sorted(int(m) for m in matches["match_id"].tolist())
    n_cached = sum((Path(cache_dir) / f"events_{mid}.pkl").exists() for mid in match_ids)
    return {
        "label": dataset.label,
        "comp_id": dataset.comp_id,
        "season_id": dataset.season_id,
        "context": dataset.context,
        "has_360": dataset.has_360,
        "n_matches": len(match_ids),
        "n_cached_locally": n_cached,
        "match_set_hash": hash_match_ids(match_ids),
        "match_ids": match_ids,
    }


def build_manifest(datasets, matches_loader=load_matches, data_dir=None, cache_dir=CACHE_DIR):
    """Assemble the provenance manifest dict for the given datasets.

    Args:
        datasets: iterable of ``config.Dataset``.
        matches_loader: callable ``(comp_id, season_id) -> DataFrame`` with a ``match_id``
            column. Injected so tests can run without touching the network.
        data_dir: directory holding the processed parquet tables (defaults to repo ``data/``).
        cache_dir: per-match pickle cache dir, used to report local coverage.

    Returns:
        A JSON-serialisable dict; keyed by a stable ``comp{c}_season{s}`` slug per dataset.
    """
    data_dir = Path(data_dir) if data_dir is not None else (REPO_ROOT / "data")

    datasets_section = {
        f"comp{ds.comp_id}_season{ds.season_id}": _dataset_entry(ds, matches_loader, cache_dir)
        for ds in datasets
    }

    processed_tables = {}
    for name in PROCESSED_TABLES:
        path = data_dir / name
        entry = {"exists": path.exists(), "sha256": hash_file(path)}
        if path.exists():
            entry["bytes"] = path.stat().st_size
        processed_tables[name] = entry

    return {
        "note": "Data provenance pin — regenerate with `python -m src.manifest`.",
        "tooling": {"statsbombpy": _statsbombpy_version()},
        "datasets": datasets_section,
        "processed_tables": processed_tables,
    }


def write_manifest(path=MANIFEST_PATH, datasets=None):
    """Build the manifest for the in-use datasets and write it to ``path`` as sorted JSON."""
    if datasets is None:
        in_use = config.TRAIN_SETS + config.TEST_SETS
        # GENERALISATION_TEST_SETS overlaps TEST_SETS (both include EURO_2024) — add only the
        # Phase 4c tournaments not already pinned above, so each dataset gets one manifest entry.
        datasets = in_use + [ds for ds in config.GENERALISATION_TEST_SETS if ds not in in_use]
    else:
        in_use = datasets
    manifest = build_manifest(datasets)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    written = write_manifest()
    total_matches = sum(d["n_matches"] for d in written["datasets"].values())
    total_cached = sum(d["n_cached_locally"] for d in written["datasets"].values())
    print(
        f"Wrote {MANIFEST_PATH} — {len(written['datasets'])} datasets, "
        f"{total_matches} matches pinned ({total_cached} cached locally)."
    )
