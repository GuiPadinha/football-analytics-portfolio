"""Unit tests for the sparse-column accessors in src/data_loader.py.

Shared by features.py and similarity.py: statsbombpy omits a column entirely from a match's
events DataFrame if zero events in that match have it set, so a plain `df[column]` access risks
a KeyError on an otherwise ordinary match. Moved here from similarity.py (Phase 4 data expansion)
once features.py needed the same guard on a real new-competition failure — see test_features.py's
`test_extract_shot_features_handles_missing_sparse_flag_columns`.
"""

import pandas as pd

from src.data_loader import safe_bool_column, safe_column


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
