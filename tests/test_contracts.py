"""Tests for the cross-module data contracts documented in docs/ARCHITECTURE.md.

`features.py` and `similarity.py` produce DataFrames whose column names `models.py`/
`metrics.py` hard-assume, with nothing but convention enforcing the match — a renamed
column would surface as a silent KeyError at run time, not at import time. These tests
pin the contract so a mismatch fails in CI instead of on someone's laptop mid-demo.
"""

import numpy as np
import pandas as pd

from src.features import extract_shot_features
from src.models import ASSIST_TYPES, BOOLEAN_FEATURES, NUMERIC_FEATURES
from src.similarity import ACTION_COLUMNS, PER90_FEATURE_COLUMNS


def test_extract_shot_features_output_covers_every_model_input_column():
    # Every column build_feature_matrix reads from a shots table must actually be
    # produced by extract_shot_features, or model training breaks downstream with
    # a bare KeyError instead of a clear contract violation.
    events = pd.DataFrame([
        {"id": "s1", "type": "Shot", "period": 1, "location": [108.0, 40.0], "team": "A", "minute": 10,
         "shot_outcome": "Goal", "shot_type": "Open Play", "shot_body_part": "Right Foot",
         "shot_key_pass_id": np.nan, "shot_statsbomb_xg": 0.3},
    ])
    shots = extract_shot_features(events)

    required = set(NUMERIC_FEATURES) | set(BOOLEAN_FEATURES) | {"assist_type", "is_goal"}
    assert required.issubset(shots.columns)


def test_assist_types_constant_matches_classify_assist_categories():
    # models.ASSIST_TYPES is a fixed category list used to build one-hot columns
    # in the same order for every train/test split; it must stay in sync with
    # every category _classify_assist can actually produce.
    from src.features import _classify_assist

    produced = {
        _classify_assist(None),
        _classify_assist({"pass_cross": True}),
        _classify_assist({"pass_through_ball": True}),
        _classify_assist({"pass_cut_back": True}),
        _classify_assist({}),
    }
    assert produced.issubset(set(ASSIST_TYPES))


def test_per90_feature_columns_derived_from_action_columns():
    # PER90_FEATURE_COLUMNS is the single list clustering/metrics key off (see
    # ARCHITECTURE.md's Data Contracts section) — it must stay a pure function of
    # ACTION_COLUMNS, not a second hand-maintained list that can drift from it.
    assert PER90_FEATURE_COLUMNS == [f"{col}_p90" for col in ACTION_COLUMNS]
