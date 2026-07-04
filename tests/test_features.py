"""Unit tests for xG feature engineering geometry and assist classification.

The assist-classification tests are deliberate regression tests for the truthy-NaN bug hit
twice in this project (StatsBomb flag columns hold True/NaN, and bool(nan) is True in Python).
"""

import numpy as np
import pandas as pd
import pytest

from src.features import _classify_assist, _shot_angle, _shot_distance, extract_shot_features


def test_shot_distance_central():
    # 12 yards out, dead centre (x=108, y=40): straight-line distance to goal centre is 12.
    assert _shot_distance(108.0, 40.0) == pytest.approx(12.0)


def test_shot_angle_central_known_geometry():
    # From (108, 40) the posts at (120, 44)/(120, 36) subtend arccos(0.8) = 36.8699 degrees.
    assert _shot_angle(108.0, 40.0) == pytest.approx(36.8699, abs=1e-3)


def test_shot_angle_tight_is_near_zero():
    # On the goal line but outside the post (y=50): both post vectors point the same way,
    # so the subtended angle collapses to ~0 — a near-impossible shooting angle.
    assert _shot_angle(120.0, 50.0) == pytest.approx(0.0, abs=1e-6)


def test_classify_assist_none_when_no_pass():
    assert _classify_assist(None) == "None"


def test_classify_assist_cross():
    assert _classify_assist({"pass_cross": True}) == "Cross"


def test_classify_assist_through_ball():
    assert _classify_assist({"pass_through_ball": True}) == "Through Ball"


def test_classify_assist_nan_is_standard_pass():
    # Regression: pass_cross holds True/NaN. bool(nan) is True, so a naive truthy check
    # would misread this as a Cross. It must classify as a Standard Pass.
    assert _classify_assist({"pass_cross": float("nan")}) == "Standard Pass"


def test_classify_assist_empty_is_standard_pass():
    assert _classify_assist({}) == "Standard Pass"


def test_extract_shot_features_handles_missing_sparse_flag_columns():
    # Regression: statsbombpy omits shot_first_time/under_pressure entirely from a match's
    # events if zero shots in that match have them set — hit for real on Barcelona 2020/21
    # (Phase 4 data expansion), where extract_shot_features crashed with a bare KeyError before
    # this fix. Note: no "shot_first_time" or "under_pressure" key in this event at all.
    events = pd.DataFrame([
        {"id": "s1", "type": "Shot", "period": 1, "location": [108.0, 40.0], "team": "A", "minute": 10,
         "shot_outcome": "Goal", "shot_type": "Open Play", "shot_body_part": "Right Foot",
         "shot_key_pass_id": np.nan, "shot_statsbomb_xg": 0.3},
    ])
    result = extract_shot_features(events)
    assert len(result) == 1
    assert bool(result.iloc[0]["is_first_time"]) is False
    assert bool(result.iloc[0]["under_pressure"]) is False


def test_game_state_score_diff_reflects_score_before_not_after_the_shot():
    # A shot that itself is a goal must NOT have that goal counted in its own
    # game_state_score_diff (the feature describes the state the shooter faced
    # when deciding to shoot, not the outcome). The next shot from the same team
    # should then see the lead.
    events = pd.DataFrame([
        {"id": "s1", "type": "Shot", "period": 1, "location": [108.0, 40.0], "team": "A", "minute": 10,
         "shot_outcome": "Goal", "shot_type": "Open Play", "shot_body_part": "Right Foot",
         "shot_key_pass_id": np.nan, "shot_statsbomb_xg": 0.3},
        {"id": "s2", "type": "Shot", "period": 1, "location": [100.0, 40.0], "team": "A", "minute": 20,
         "shot_outcome": "Saved", "shot_type": "Open Play", "shot_body_part": "Right Foot",
         "shot_key_pass_id": np.nan, "shot_statsbomb_xg": 0.1},
    ])
    result = extract_shot_features(events)
    assert result.iloc[0]["game_state_score_diff"] == 0  # before its own goal is credited
    assert result.iloc[1]["game_state_score_diff"] == 1  # now leading by the first goal


def test_extract_shot_features_handles_a_match_with_zero_shots():
    # A sparser version of the sparse-column family than the missing-flag case above: if a match
    # has literally no Shot events, shot-only fields (shot_body_part, shot_type, shot_outcome,
    # shot_key_pass_id) never appear in `events` at all, not just a missing flag on an existing
    # shot. Rare in real matches but not impossible across thousands of them (Phase 4 volume), and
    # it's exactly the "all shots filtered out" shape the period-5/null-location guards can also
    # produce internally — same failure mode, so worth covering directly.
    events = pd.DataFrame([
        {"id": "p1", "type": "Pass", "period": 1, "location": [60.0, 40.0], "team": "A", "minute": 5},
        {"id": "p2", "type": "Pass", "period": 1, "location": [55.0, 38.0], "team": "B", "minute": 6},
    ])
    result = extract_shot_features(events)
    assert len(result) == 0
    assert "is_goal" in result.columns


def test_extract_shot_features_drops_shootout_and_null_location():
    events = pd.DataFrame([
        # A normal in-game shot (kept).
        {"id": "s1", "type": "Shot", "period": 2, "location": [108.0, 40.0], "team": "A", "minute": 50,
         "shot_outcome": "Goal", "shot_type": "Open Play", "shot_body_part": "Right Foot",
         "shot_first_time": True, "under_pressure": np.nan, "shot_key_pass_id": np.nan,
         "shot_statsbomb_xg": 0.3},
        # A penalty-shootout attempt (period 5) — must be dropped.
        {"id": "s2", "type": "Shot", "period": 5, "location": [108.0, 40.0], "team": "A", "minute": 120,
         "shot_outcome": "Goal", "shot_type": "Penalty", "shot_body_part": "Right Foot",
         "shot_first_time": np.nan, "under_pressure": np.nan, "shot_key_pass_id": np.nan,
         "shot_statsbomb_xg": 0.76},
        # A shot logged without a location — must be dropped, not crash the unpacking.
        {"id": "s3", "type": "Shot", "period": 1, "location": np.nan, "team": "A", "minute": 10,
         "shot_outcome": "Saved", "shot_type": "Open Play", "shot_body_part": "Head",
         "shot_first_time": np.nan, "under_pressure": np.nan, "shot_key_pass_id": np.nan,
         "shot_statsbomb_xg": 0.05},
    ])
    result = extract_shot_features(events)
    assert len(result) == 1  # only the normal in-game shot survives
    assert bool(result.iloc[0]["is_goal"]) is True
    assert result.iloc[0]["distance_to_goal"] == pytest.approx(12.0)
