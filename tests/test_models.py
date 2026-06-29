"""Unit tests for the xG feature matrix assembly."""

import pandas as pd

from src.models import build_feature_matrix


def _one_shot(**overrides):
    shot = {
        "distance_to_goal": 10.0, "angle_to_goal": 40.0, "game_state_score_diff": 0,
        "is_header": False, "is_first_time": False, "under_pressure": False,
        "is_penalty": False, "is_free_kick": False,
        "assist_type": "Cross", "is_goal": False,
    }
    shot.update(overrides)
    return shot


def test_build_feature_matrix_drops_none_reference_category():
    # "None" (unassisted) is the dropped reference category — its dummy must NOT appear,
    # so every assist_* coefficient reads as "vs. an unassisted shot" (the S4 collinearity fix).
    X, _ = build_feature_matrix(pd.DataFrame([_one_shot(assist_type="None")]))
    assert "assist_None" not in X.columns
    assert "assist_Cross" in X.columns
    assert "assist_Through Ball" in X.columns


def test_build_feature_matrix_booleans_become_ints_and_target_aligns():
    X, y = build_feature_matrix(pd.DataFrame([
        _one_shot(is_penalty=True, is_goal=True),
        _one_shot(is_penalty=False, is_goal=False),
    ]))
    assert list(X["is_penalty"]) == [1, 0]
    assert list(y) == [1, 0]
    # Even when only one assist category is present in the data, all expected dummy
    # columns exist (reindexed) so train/test matrices line up.
    assert "assist_Cut Back" in X.columns
