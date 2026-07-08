"""Unit tests for the headline-metrics single source (src/metrics.py).

Two kinds of test here:

* **pure-compute** tests drive ``compute_xg_metrics`` / ``compute_similarity_metrics`` with
  tiny synthetic frames, so they stay offline and deterministic (same reason the manifest
  tests inject a fake loader — CI has no ``data/`` and no network).
* the **doc-lint** test is the actual point of Phase 3b: it reads the committed
  ``metrics.json`` and fails if a *current-state* doc (README/CLAUDE/MODULES/DATA) quotes a
  different number. Append-only history (PROGRESS, INITIATIVE log entries, ML_LEARNING_LOG,
  the archive) is intentionally NOT checked — an old dated entry is allowed to record the
  0.798 it reported at the time.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    METRICS_PATH,
    build_metrics,
    compute_generalisation_metrics,
    compute_similarity_metrics,
    compute_xg_metrics,
)
from src.models import ASSIST_TYPES
from src.similarity import PER90_FEATURE_COLUMNS

REPO_ROOT = Path(__file__).resolve().parent.parent


def _synth_shots(n, seed):
    """A synthetic shot table with a real distance->goal signal (so ROC-AUC > 0.5)."""
    rng = np.random.default_rng(seed)
    distance = rng.uniform(4, 35, n)
    goal_prob = 1 / (1 + np.exp((distance - 12) / 4))  # closer shots convert more often
    return pd.DataFrame(
        {
            "distance_to_goal": distance,
            "angle_to_goal": rng.uniform(0.1, 1.5, n),
            "game_state_score_diff": rng.integers(-2, 3, n),
            "is_header": rng.integers(0, 2, n).astype(bool),
            "is_first_time": rng.integers(0, 2, n).astype(bool),
            "under_pressure": rng.integers(0, 2, n).astype(bool),
            "is_penalty": False,
            "is_free_kick": False,
            "assist_type": rng.choice(ASSIST_TYPES, n),
            "is_goal": (rng.uniform(size=n) < goal_prob).astype(int),
        }
    )


def _synth_per90(groups, per_group, seed):
    """A synthetic per-90 table: `per_group` players in each named position group."""
    rng = np.random.default_rng(seed)
    rows = []
    for group in groups:
        for _ in range(per_group):
            row = {"position_group": group}
            row.update({col: rng.uniform(0, 5) for col in PER90_FEATURE_COLUMNS})
            rows.append(row)
    return pd.DataFrame(rows)


def test_compute_xg_metrics_structure_and_invariants():
    train, test = _synth_shots(200, seed=1), _synth_shots(80, seed=2)
    m = compute_xg_metrics(train, test, cv=5)

    assert m["n_train_shots"] == 200
    assert m["n_test_shots"] == 80
    # A DummyClassifier ranks no shot above another -> ROC-AUC is exactly 0.5 by construction.
    assert m["baseline_ladder_test_roc_auc"]["no_skill"] == 0.5
    # The "full" rung is the same fitted model as the headline logistic test score.
    assert m["baseline_ladder_test_roc_auc"]["full"] == m["logistic"]["test_roc_auc"]
    for rung in m["baseline_ladder_test_roc_auc"].values():
        assert 0.0 <= rung <= 1.0
    assert m["cv_in_distribution"]["folds"] == 5
    assert m["cv_in_distribution"]["roc_auc_std"] >= 0.0
    for score in m["logistic"].values():
        assert 0.0 <= score <= 1.0


def test_compute_generalisation_metrics_scores_each_tournament_separately():
    from types import SimpleNamespace

    train = _synth_shots(200, seed=10)
    tournament_a = _synth_shots(60, seed=11)
    tournament_a["competition_id"] = 55
    tournament_b = _synth_shots(30, seed=12)
    tournament_b["competition_id"] = 223
    generalisation_shots = pd.concat([tournament_a, tournament_b], ignore_index=True)

    datasets = [
        SimpleNamespace(comp_id=55, label="UEFA EURO 2024"),
        SimpleNamespace(comp_id=223, label="Copa América 2024"),
    ]
    result = compute_generalisation_metrics(train, generalisation_shots, datasets)

    assert set(result) == {"55", "223"}
    assert result["55"]["n_shots"] == 60
    assert result["223"]["n_shots"] == 30
    for row in result.values():
        assert 0.0 <= row["roc_auc"] <= 1.0


def test_build_metrics_omits_generalisation_section_by_default():
    # Backward compatible: existing callers that don't pass generalisation data get exactly
    # the pre-Phase-4c dict shape.
    train, test = _synth_shots(200, seed=4), _synth_shots(80, seed=5)
    per90 = _synth_per90(["Defender", "Midfielder", "Forward"], per_group=12, seed=6)
    metrics = build_metrics(train, test, per90)
    assert "xg_generalisation" not in metrics


def test_build_metrics_includes_generalisation_section_when_provided():
    from types import SimpleNamespace

    train, test = _synth_shots(200, seed=4), _synth_shots(80, seed=5)
    per90 = _synth_per90(["Defender", "Midfielder", "Forward"], per_group=12, seed=6)
    generalisation_shots = _synth_shots(50, seed=13)
    generalisation_shots["competition_id"] = 55
    datasets = [SimpleNamespace(comp_id=55, label="UEFA EURO 2024")]

    metrics = build_metrics(
        train, test, per90,
        generalisation_shots=generalisation_shots, generalisation_datasets=datasets,
    )

    assert json.loads(json.dumps(metrics)) == metrics
    assert metrics["xg_generalisation"]["55"]["label"] == "UEFA EURO 2024"


def test_compute_similarity_metrics_per_group():
    per90 = _synth_per90(["Defender", "Midfielder"], per_group=15, seed=3)
    groups = compute_similarity_metrics(
        per90, groups=["Defender", "Midfielder"], k_range=range(2, 5)
    )

    assert set(groups) == {"defender", "midfielder"}
    for stats in groups.values():
        assert stats["n_players"] == 15
        assert stats["best_k"] in range(2, 5)
        assert -1.0 <= stats["best_silhouette"] <= 1.0


def test_build_metrics_is_json_serialisable_and_pure():
    train, test = _synth_shots(200, seed=4), _synth_shots(80, seed=5)
    per90 = _synth_per90(["Defender", "Midfielder", "Forward"], per_group=12, seed=6)
    metrics = build_metrics(train, test, per90)

    # No numpy scalars leaking through -> round-trips through JSON unchanged.
    assert json.loads(json.dumps(metrics)) == metrics
    assert set(metrics["xg"]) >= {"logistic", "cv_in_distribution", "baseline_ladder_test_roc_auc"}
    assert set(metrics["similarity"]["groups"]) == {"defender", "midfielder", "forward"}


# --- Doc-lint: current-state docs must quote metrics.json, or the build goes red -------------

def _doc_text(rel_path):
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_current_state_docs_match_metrics_json():
    """Every headline number a *current-state* doc prints must equal the one in metrics.json.

    Add a row here when a doc starts quoting a new metric; that is the whole maintenance
    cost of keeping the docs honest.
    """
    if not METRICS_PATH.exists():
        pytest.skip("metrics.json not generated yet - run `python -m src.metrics`")

    m = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    xg = m["xg"]

    # (human-facing string, list of current-state docs that must contain it verbatim)
    expectations = [
        (f"{xg['logistic']['test_roc_auc']:.3f}", ["README.md", "CLAUDE.md", "docs/MODULES.md"]),
        (f"{xg['logistic']['train_roc_auc']:.3f}", ["README.md", "docs/MODULES.md"]),
        (f"{xg['logistic']['test_brier']:.3f}", ["README.md"]),
        (f"{xg['logistic']['train_brier']:.3f}", ["README.md"]),
        (f"{xg['cv_in_distribution']['roc_auc_mean']:.3f}", ["docs/MODULES.md"]),
        (f"{xg['cv_in_distribution']['roc_auc_std']:.3f}", ["docs/MODULES.md"]),
        (f"{xg['baseline_ladder_test_roc_auc']['geometry_only']:.3f}", ["docs/MODULES.md"]),
        (f"{xg['n_train_shots']:,}", ["README.md", "docs/DATA.md"]),
        (f"{xg['n_test_shots']:,}", ["README.md", "docs/DATA.md"]),
    ]

    failures = []
    for value, docs in expectations:
        for doc in docs:
            if value not in _doc_text(doc):
                failures.append(f"{doc} does not contain metrics.json value '{value}'")

    assert not failures, "Docs drifted from metrics.json:\n  " + "\n  ".join(failures)
