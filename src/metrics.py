"""Single source of truth for the framework's headline metrics.

The numbers a reader first sees — xG test ROC-AUC 0.765, the CV spread, the baseline
ladder, the per-group silhouette peaks — were hand-typed into README/CLAUDE/MODULES/DATA
and drifted (see the S3→penalty-fix 0.798→0.765 correction that took four separate doc
edits to chase down). This module *computes* them from the same code and data the models
use and writes them to ``metrics.json`` at the repo root. Docs then quote that file, and a
doc-lint test (``tests/test_metrics.py``) fails if a current-state doc diverges from it —
so drift on a headline number becomes a red build, not a slow rot.

Two layers, deliberately split so the unit tests never need the network or the (gitignored)
``data/`` tables:

* **pure compute** — ``compute_xg_metrics`` / ``compute_similarity_metrics`` / ``build_metrics``
  take in-memory frames and return a plain dict. Tested with tiny synthetic frames.
* **IO wrapper** — ``write_metrics`` loads the processed parquet tables + builds the per-90
  similarity table, then writes ``metrics.json``. This is the build step:

      python -m src.metrics

``metrics.json`` is committed (it lives at the repo root, outside the gitignored ``data/``),
so CI and the doc-lint test read it without touching data or the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.models import (
    build_feature_matrix,
    build_logistic_pipeline,
    cross_validate_model,
    evaluate_model,
    train_baseline_classifier,
    train_logistic_regression,
)
from src.similarity import (
    build_player_per90_features,
    compute_silhouette_scores,
    scale_features,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "metrics.json"
DATA_DIR = REPO_ROOT / "data"

# The geometry-only rung of the baseline ladder: a logistic model on shot geometry alone.
# ~80% of the full model's discrimination is already here — the honest "how much do the
# fancier features actually add" reference (notebook 02, Phase 2).
GEOMETRY_FEATURES = ["distance_to_goal", "angle_to_goal"]

# Order the similarity groups the way the docs list them (Defender / Mid / Forward).
POSITION_GROUP_ORDER = ["Defender", "Midfielder", "Forward"]

# K sweep for the silhouette peak, matching src.similarity.compute_silhouette_scores' default.
SILHOUETTE_K_RANGE = range(2, 11)

# Similarity minutes floor (matches build_player_per90_features' default) — kept explicit so it
# lands in the manifest as the recorded provenance of the "300 players" pool.
SIMILARITY_MIN_MINUTES = 900


def _r(value, ndigits=3):
    """Round to a JSON-clean Python float (numpy scalars serialise badly otherwise)."""
    return round(float(value), ndigits)


def compute_xg_metrics(shots_train, shots_test, cv=5):
    """Compute the Module A headline numbers from the processed shot tables.

    Pure: takes the two shot frames (as loaded from ``shots_{train,test}.parquet``) and
    returns a JSON-serialisable dict. Reproduces exactly what notebook 02 reports —
    the fitted-once train/test logistic scores, the in-distribution CV spread, and the
    no-skill → geometry-only → full baseline ladder — so the file can't silently disagree
    with the notebook narrative.

    Args:
        shots_train (pandas.DataFrame): engineered training shots (league).
        shots_test (pandas.DataFrame): engineered held-out shots (EURO 2024, OOD).
        cv (int): folds for the in-distribution CV estimate.

    Returns:
        dict: shot counts, logistic train/test ROC-AUC + Brier, CV mean/std, and the
            baseline ladder (no-skill, geometry-only, full) — all on the test set.
    """
    X_train, y_train = build_feature_matrix(shots_train)
    X_test, y_test = build_feature_matrix(shots_test)

    model = train_logistic_regression(X_train, y_train)
    train_eval = evaluate_model(model, X_train, y_train)
    test_eval = evaluate_model(model, X_test, y_test)

    # Baseline ladder, all scored on the same held-out test set.
    no_skill = train_baseline_classifier(X_train, y_train)
    no_skill_eval = evaluate_model(no_skill, X_test, y_test)

    geometry = train_logistic_regression(
        X_train[GEOMETRY_FEATURES], y_train, numeric_features=GEOMETRY_FEATURES
    )
    geometry_eval = evaluate_model(geometry, X_test[GEOMETRY_FEATURES], y_test)

    cv_auc = cross_validate_model(build_logistic_pipeline(), X_train, y_train, cv=cv)["roc_auc"]

    return {
        "n_train_shots": int(len(y_train)),
        "n_test_shots": int(len(y_test)),
        "train_goal_rate": _r(y_train.mean()),
        "logistic": {
            "train_roc_auc": _r(train_eval["roc_auc"]),
            "test_roc_auc": _r(test_eval["roc_auc"]),
            "train_brier": _r(train_eval["brier_score"]),
            "test_brier": _r(test_eval["brier_score"]),
        },
        "cv_in_distribution": {
            "folds": cv,
            "roc_auc_mean": _r(cv_auc.mean()),
            "roc_auc_std": _r(cv_auc.std()),
        },
        "baseline_ladder_test_roc_auc": {
            "no_skill": _r(no_skill_eval["roc_auc"]),
            "geometry_only": _r(geometry_eval["roc_auc"]),
            "full": _r(test_eval["roc_auc"]),
        },
    }


def compute_similarity_metrics(per90_features, groups=POSITION_GROUP_ORDER, k_range=SILHOUETTE_K_RANGE):
    """Compute the Module B per-group silhouette peaks from a per-90 feature table.

    Pure: takes the output of ``build_player_per90_features`` and returns a dict. For each
    position group it scales the per-90 features and sweeps K, recording the peak silhouette
    and the K that achieved it — the ~0.25 "soft continuum" finding that justified keeping
    K=4 against the metric's preference for a coarser K=2.

    Args:
        per90_features (pandas.DataFrame): per-player per-90 table with a ``position_group``
            column, as returned by ``build_player_per90_features``.
        groups (list[str]): position groups to profile, in doc order.
        k_range (range): K values to sweep for the silhouette peak.

    Returns:
        dict: per group, the player count, best K, and peak silhouette score.
    """
    out = {}
    for group in groups:
        group_features = per90_features[per90_features["position_group"] == group]
        X_scaled, _ = scale_features(group_features)
        scores = compute_silhouette_scores(X_scaled, k_range=k_range)
        out[group.lower()] = {
            "n_players": int(len(group_features)),
            "best_k": int(scores.idxmax()),
            "best_silhouette": _r(scores.max()),
        }
    return out


def build_metrics(shots_train, shots_test, per90_features, similarity_set=None):
    """Assemble the full metrics dict from in-memory frames (pure, no IO)."""
    similarity_set = similarity_set if similarity_set is not None else config.SIMILARITY_SET
    return {
        "note": "Headline metrics - single source. Regenerate with `python -m src.metrics`.",
        "xg": compute_xg_metrics(shots_train, shots_test),
        "similarity": {
            "competition": similarity_set.label,
            "comp_id": similarity_set.comp_id,
            "season_id": similarity_set.season_id,
            "min_minutes": SIMILARITY_MIN_MINUTES,
            "kmeans_k_used": 4,
            "groups": compute_similarity_metrics(per90_features),
        },
    }


def write_metrics(path=METRICS_PATH, data_dir=DATA_DIR, similarity_set=None):
    """Build the metrics for the in-use datasets and write ``metrics.json`` (sorted JSON).

    Loads the processed parquet tables and rebuilds the per-90 similarity table (the latter
    reads the cached event data for the similarity competition — the slow part), so this needs
    ``data/`` present. Deterministic and timestamp-free like the manifest: an unchanged model
    regenerates byte-for-byte, so only a real metric move produces a diff.
    """
    similarity_set = similarity_set if similarity_set is not None else config.SIMILARITY_SET
    data_dir = Path(data_dir)

    shots_train = pd.read_parquet(data_dir / "shots_train.parquet")
    shots_test = pd.read_parquet(data_dir / "shots_test.parquet")
    per90_features = build_player_per90_features(
        similarity_set.comp_id, similarity_set.season_id, min_minutes=SIMILARITY_MIN_MINUTES
    )

    metrics = build_metrics(shots_train, shots_test, per90_features, similarity_set=similarity_set)

    path = Path(path)
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    written = write_metrics()
    xg = written["xg"]
    print(f"Wrote {METRICS_PATH}")
    print(
        f"  xG: test ROC-AUC {xg['logistic']['test_roc_auc']} "
        f"(train {xg['logistic']['train_roc_auc']}), "
        f"CV {xg['cv_in_distribution']['roc_auc_mean']} +/- {xg['cv_in_distribution']['roc_auc_std']}, "
        f"ladder {xg['baseline_ladder_test_roc_auc']}"
    )
    print(f"  similarity groups: {written['similarity']['groups']}")
