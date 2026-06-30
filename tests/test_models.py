"""Unit tests for the xG feature matrix assembly and the Phase 2 model helpers."""

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.models import (
    ASSIST_TYPES,
    build_feature_matrix,
    build_logistic_pipeline,
    cross_validate_model,
    get_coefficients,
    train_baseline_classifier,
    train_logistic_regression,
)


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


def _synthetic_shots(n=60, seed=0):
    """Build a small synthetic shot table with real signal (closer shots score more),
    enough for the model helpers to fit without hitting a single-class fold."""
    rng = np.random.default_rng(seed)
    distance = rng.uniform(2, 35, n)
    goal_prob = 1 / (1 + np.exp(0.25 * (distance - 12)))  # closer to goal -> more likely
    return pd.DataFrame({
        "distance_to_goal": distance,
        "angle_to_goal": rng.uniform(5, 90, n),
        "game_state_score_diff": rng.integers(-2, 3, n),
        "is_header": rng.uniform(size=n) < 0.2,
        "is_first_time": rng.uniform(size=n) < 0.3,
        "under_pressure": rng.uniform(size=n) < 0.4,
        "is_penalty": False,
        "is_free_kick": rng.uniform(size=n) < 0.1,
        "assist_type": rng.choice(ASSIST_TYPES, n),
        "is_goal": rng.uniform(size=n) < goal_prob,
    })


def test_train_logistic_returns_fitted_pipeline_with_valid_probs():
    # The Phase 2 model is a scaler+logistic Pipeline, not a bare LogisticRegression,
    # but it must still behave like one (predict_proba in [0, 1]).
    X, y = build_feature_matrix(_synthetic_shots())
    model = train_logistic_regression(X, y)
    assert isinstance(model, Pipeline)
    proba = model.predict_proba(X)[:, 1]
    assert proba.min() >= 0.0 and proba.max() <= 1.0


def test_get_coefficients_returns_all_features_with_clean_names():
    # The ColumnTransformer reorders columns and prefixes names (scale__/remainder__);
    # get_coefficients must recover one clean-named coefficient per model column.
    X, y = build_feature_matrix(_synthetic_shots())
    coefficients = get_coefficients(train_logistic_regression(X, y))
    assert set(coefficients.index) == set(X.columns)
    assert not any("__" in name for name in coefficients.index)


def test_baseline_predicts_constant_base_rate():
    # The no-skill floor predicts the training goal rate for every shot (ROC-AUC 0.5).
    X, y = build_feature_matrix(_synthetic_shots())
    proba = train_baseline_classifier(X, y).predict_proba(X)[:, 1]
    assert np.allclose(proba, y.mean())


def test_cross_validate_returns_per_fold_scores():
    X, y = build_feature_matrix(_synthetic_shots())
    scores = cross_validate_model(build_logistic_pipeline(), X, y, cv=3)
    assert set(scores) == {"roc_auc", "neg_brier_score"}
    assert len(scores["roc_auc"]) == 3


def test_logistic_accepts_numeric_feature_subset():
    # The geometry-only baseline path: scaling must target only the columns present,
    # or the ColumnTransformer would KeyError on the absent game_state_score_diff.
    X, y = build_feature_matrix(_synthetic_shots())
    geometry = ["distance_to_goal", "angle_to_goal"]
    model = train_logistic_regression(X[geometry], y, numeric_features=geometry)
    assert model.predict_proba(X[geometry]).shape == (len(X), 2)
