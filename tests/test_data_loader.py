"""Unit tests for the sparse-column accessors in src/data_loader.py.

Shared by features.py and similarity.py: statsbombpy omits a column entirely from a match's
events DataFrame if zero events in that match have it set, so a plain `df[column]` access risks
a KeyError on an otherwise ordinary match. Moved here from similarity.py (Phase 4 data expansion)
once features.py needed the same guard on a real new-competition failure — see test_features.py's
`test_extract_shot_features_handles_missing_sparse_flag_columns`.

Also covers `resolve_cache_dir`, the `FAP_CACHE_DIR` override for where the per-match cache lives.
"""

from pathlib import Path

import pandas as pd

from src import data_loader
from src.data_loader import DEFAULT_CACHE_DIR, resolve_cache_dir, safe_bool_column, safe_column


def test_safe_bool_column_present_reads_normally():
    df = pd.DataFrame({"flag": [True, False, True]})
    result = safe_bool_column(df, "flag")
    assert result.tolist() == [True, False, True]


def test_safe_bool_column_missing_returns_all_false():
    df = pd.DataFrame({"other": [1, 2, 3]})
    result = safe_bool_column(df, "flag")
    assert result.tolist() == [False, False, False]
    assert len(result) == len(df)


def test_safe_column_present_reads_normally():
    df = pd.DataFrame({"outcome": ["Complete", "Incomplete"]})
    result = safe_column(df, "outcome")
    assert result.tolist() == ["Complete", "Incomplete"]


def test_safe_column_missing_returns_all_default():
    df = pd.DataFrame({"other": [1, 2]})
    result = safe_column(df, "outcome", default="Missing")
    assert result.tolist() == ["Missing", "Missing"]

def test_cache_dir_defaults_to_data_cache_without_the_env_var():
    assert resolve_cache_dir({}) == DEFAULT_CACHE_DIR


def test_cache_dir_env_var_overrides_the_default():
    assert resolve_cache_dir({"FAP_CACHE_DIR": "D:/elsewhere/cache"}) == Path("D:/elsewhere/cache")


def test_cache_dir_ignores_a_blank_env_var():
    assert resolve_cache_dir({"FAP_CACHE_DIR": "  "}) == DEFAULT_CACHE_DIR


def test_disk_cache_downloads_once_and_announces_the_folder_once(tmp_path, monkeypatch, capsys):
    from src import data_loader

    monkeypatch.setattr(data_loader, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(data_loader, "_download_notice_shown", False)
    calls = []

    def producer():
        calls.append(1)
        return {"events": len(calls)}

    first = data_loader._disk_cached("events", 1, producer)
    again = data_loader._disk_cached("events", 1, producer)  # served from disk
    data_loader._disk_cached("events", 2, producer)  # a second download, no second notice

    assert first == again == {"events": 1}
    assert len(calls) == 2
    assert capsys.readouterr().out.count(str(tmp_path)) == 1
