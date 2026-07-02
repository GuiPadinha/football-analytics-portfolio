"""Unit tests for the data provenance manifest (src/manifest.py).

The match listing normally comes from the network (statsbombpy); every test here injects a
fake loader so the suite stays offline and deterministic — same reason CI can run it.
"""

import pandas as pd

from src.config import Dataset
from src.manifest import build_manifest, hash_file, hash_match_ids


def _fake_loader(match_ids_by_key):
    """Return a matches_loader that yields a match_id-only frame keyed by (comp, season)."""

    def loader(comp_id, season_id):
        return pd.DataFrame({"match_id": match_ids_by_key[(comp_id, season_id)]})

    return loader


def test_hash_match_ids_is_order_independent():
    # The *set* of matches is the fingerprint — the order a listing returns them must not matter.
    assert hash_match_ids([3, 1, 2]) == hash_match_ids([1, 2, 3])
    assert hash_match_ids([1, 2]) != hash_match_ids([1, 2, 3])


def test_hash_file_missing_returns_none(tmp_path):
    assert hash_file(tmp_path / "nope.parquet") is None


def test_hash_file_changes_with_content(tmp_path):
    path = tmp_path / "t.bin"
    path.write_bytes(b"aaaa")
    first = hash_file(path)
    path.write_bytes(b"bbbb")
    assert first != hash_file(path)


def test_build_manifest_pins_matches_and_reports_cache_coverage(tmp_path):
    ds = Dataset(9, 281, "league", "Fake FC", has_360=True)
    loader = _fake_loader({(9, 281): [100, 101, 102]})

    # Only one of the three matches is "cached" locally.
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "events_101.pkl").write_bytes(b"x")

    manifest = build_manifest([ds], matches_loader=loader, data_dir=tmp_path, cache_dir=cache_dir)

    entry = manifest["datasets"]["comp9_season281"]
    assert entry["n_matches"] == 3
    assert entry["n_cached_locally"] == 1
    assert entry["match_ids"] == [100, 101, 102]
    assert entry["has_360"] is True
    assert entry["match_set_hash"] == hash_match_ids([100, 101, 102])
    # No processed tables present in tmp_path → recorded as absent, not crashed.
    assert manifest["processed_tables"]["shots_train.parquet"]["exists"] is False


def test_build_manifest_hashes_present_processed_table(tmp_path):
    ds = Dataset(2, 27, "league", "Fake League", has_360=False)
    loader = _fake_loader({(2, 27): [1, 2]})
    (tmp_path / "shots_train.parquet").write_bytes(b"parquet-bytes")

    manifest = build_manifest([ds], matches_loader=loader, data_dir=tmp_path, cache_dir=tmp_path)

    train = manifest["processed_tables"]["shots_train.parquet"]
    assert train["exists"] is True
    assert train["sha256"] is not None
    assert train["bytes"] == len(b"parquet-bytes")
