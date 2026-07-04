"""Property-based sanity checks against the real cached shot tables.

Deliberately the one exception to the rest of the suite's "network-free, synthetic data only"
rule (see docs/ARCHITECTURE.md's pure-compute/IO-wrapper split): everything else in tests/
builds tiny in-memory frames so CI never needs data/. These checks instead read the actual
processed Parquet tables to catch a class of bug synthetic data can't — a real StatsBomb schema
change, a unit-conversion slip, or a feature-engineering regression that produces well-typed but
nonsensical values (e.g. a shot 400 yards from goal). Skipped automatically wherever data/ hasn't
been pulled (CI, a fresh clone) rather than failing for an environment reason.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.models import BOOLEAN_FEATURES, NUMERIC_FEATURES

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SHOT_TABLES = ["shots_train.parquet", "shots_test.parquet"]

# StatsBomb's pitch is 120x80; the farthest any point can be from the goal centre (120, 40) is
# the opposite corner, sqrt(120^2 + 40^2) ~= 126.5 — 130 leaves a small margin, not a loophole.
MAX_PLAUSIBLE_DISTANCE = 130
MIN_PLAUSIBLE_GOAL_RATE = 0.03
MAX_PLAUSIBLE_GOAL_RATE = 0.25


def _load_shots(filename):
    path = DATA_DIR / filename
    if not path.exists():
        pytest.skip(f"{path} not present locally (data/ is gitignored) — skipping data sanity check")
    return pd.read_parquet(path)


@pytest.mark.parametrize("filename", SHOT_TABLES)
def test_shot_geometry_within_pitch_bounds(filename):
    shots = _load_shots(filename)
    assert shots["distance_to_goal"].between(0, MAX_PLAUSIBLE_DISTANCE).all()
    assert shots["angle_to_goal"].between(0, 180).all()


@pytest.mark.parametrize("filename", SHOT_TABLES)
def test_shot_features_have_no_missing_values(filename):
    shots = _load_shots(filename)
    feature_columns = NUMERIC_FEATURES + BOOLEAN_FEATURES + ["assist_type", "is_goal"]
    assert not shots[feature_columns].isna().any().any()


@pytest.mark.parametrize("filename", SHOT_TABLES)
def test_goal_rate_within_plausible_range(filename):
    # A coarse drift check: this project's actual rates are ~10% (league train) and ~8-10%
    # (tournament test); the wide band is meant to catch a gross error (a broken filter letting
    # non-shots through, an inverted is_goal flag), not to police the exact conversion rate.
    shots = _load_shots(filename)
    goal_rate = shots["is_goal"].mean()
    assert MIN_PLAUSIBLE_GOAL_RATE < goal_rate < MAX_PLAUSIBLE_GOAL_RATE
