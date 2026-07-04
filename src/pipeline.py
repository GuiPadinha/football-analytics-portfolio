"""Headless rebuild: ingestion -> features -> models -> outputs -> manifest/metrics.

The notebooks (02, 03) are deliberately kept as the teaching surface (see CLAUDE.md's
learning mandate) — this module is their non-interactive twin, chaining the same
`src/` functions into one script so the whole processed-data + output-PNG rebuild can
run without a Jupyter kernel (CI, a pre-release check, or a fresh clone). It doesn't
replace the notebooks' narrative; it's the reproducibility path alongside them.

Usage:
    python -m src.pipeline                # rebuild, reusing existing data/ caches
    python -m src.pipeline --force        # ignore caches, re-pull from StatsBomb
    python -m src.pipeline --skip-plots   # data + manifest/metrics only, no PNGs

Order matters: the shot tables and per-90 table must exist before `metrics.json` can
be (re)computed from them, so `write_manifest`/`write_metrics` run last.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.features import build_training_dataset
from src.manifest import write_manifest
from src.metrics import write_metrics
from src.models import (
    build_feature_matrix,
    build_player_xg_table,
    evaluate_model,
    get_calibration_curve,
    get_feature_importance,
    train_gradient_boosting,
    train_logistic_regression,
)
from src.similarity import (
    PER90_FEATURE_COLUMNS,
    build_player_per90_features,
    compute_elbow_scores,
    compute_silhouette_scores,
    fit_kmeans,
    run_pca,
    scale_features,
)
from src.visualisation import (
    plot_calibration_curve,
    plot_elbow_curve,
    plot_pca_clusters,
    plot_player_radar,
    plot_player_xg_ranking,
    plot_shot_map,
    plot_silhouette_curve,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUTS_DIR = REPO_ROOT / "outputs"

# Position groups in doc order (Defender / Midfielder / Forward) and the K kept
# deliberately against the silhouette metric's preferred K=2 (Phase 2, notebook 03 —
# archetype granularity beats the metric's blob-separation preference).
POSITION_GROUPS = ["Defender", "Midfielder", "Forward"]
CLUSTER_K = 4
ELBOW_K_RANGE = range(2, 9)

# One example player per position group for the radar-chart deliverable (notebook 03, S7).
RADAR_EXAMPLES = [
    ("Midfielder", "N''Golo Kanté", "Leicester City"),
    ("Defender", "Aaron Cresswell", "West Ham United"),
    ("Forward", "Harry Kane", "Tottenham Hotspur"),
]


def build_shot_tables(force=False, data_dir=DATA_DIR):
    """Rebuild (or load) the processed xG shot tables.

    Mirrors notebook 02's REBUILD cell: pulls and engineers from raw StatsBomb data
    only when a parquet cache is missing or `force=True`; otherwise reloads instantly
    from `data/shots_{train,test}.parquet`.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: (shots_train, shots_test).
    """
    data_dir = Path(data_dir)
    train_path = data_dir / "shots_train.parquet"
    test_path = data_dir / "shots_test.parquet"

    if force or not train_path.exists():
        build_training_dataset(config.TRAIN_SETS).to_parquet(train_path)
    if force or not test_path.exists():
        build_training_dataset(config.TEST_SETS).to_parquet(test_path)

    return pd.read_parquet(train_path), pd.read_parquet(test_path)


def build_similarity_table(force=False, data_dir=DATA_DIR):
    """Rebuild (or load) the per-90 similarity feature table for `config.SIMILARITY_SET`.

    Returns:
        pandas.DataFrame: output of `build_player_per90_features`.
    """
    path = Path(data_dir) / "player_per90_pl_2015_16.pkl"
    if force or not path.exists():
        features = build_player_per90_features(
            config.SIMILARITY_SET.comp_id, config.SIMILARITY_SET.season_id
        )
        features.to_pickle(path)
    return pd.read_pickle(path)


def run_xg_pipeline(shots_train, shots_test, outputs_dir=OUTPUTS_DIR):
    """Train the Module A models and regenerate every xG output PNG (notebook 02).

    Returns:
        dict: the fitted logistic model's held-out ROC-AUC, as a cheap sanity check
            for callers (the authoritative numbers live in `metrics.json`).
    """
    outputs_dir = Path(outputs_dir)
    X_train, y_train = build_feature_matrix(shots_train)
    X_test, y_test = build_feature_matrix(shots_test)

    model = train_logistic_regression(X_train, y_train)
    train_eval = evaluate_model(model, X_train, y_train)
    test_eval = evaluate_model(model, X_test, y_test)

    mean_pred_train, obs_freq_train = get_calibration_curve(y_train, train_eval["predicted_xg"])
    mean_pred_test, obs_freq_test = get_calibration_curve(y_test, test_eval["predicted_xg"])
    ax = plot_calibration_curve(mean_pred_train, obs_freq_train, label="League (train)")
    plot_calibration_curve(mean_pred_test, obs_freq_test, ax=ax, label="Tournament (test)")
    ax.set_title("Calibration - league vs tournament")
    ax.figure.savefig(outputs_dir / "calibration_curve.png", dpi=150, bbox_inches="tight")
    plt.close(ax.figure)

    ax = plot_shot_map(
        shots_test, test_eval["predicted_xg"], title="Euro 2024 - all shots, sized by predicted xG"
    )
    ax.figure.savefig(outputs_dir / "euro2024_shot_map.png", dpi=150, bbox_inches="tight")
    plt.close(ax.figure)

    gbm = train_gradient_boosting(X_train, y_train)
    importance = get_feature_importance(gbm, X_train.columns)
    fig, ax = plt.subplots(figsize=(7, 5))
    importance.sort_values().plot.barh(ax=ax, color="steelblue")
    ax.set_xlabel("Feature importance")
    ax.set_title("What drives predicted shot quality?")
    fig.savefig(outputs_dir / "feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    pl_shots = shots_train[
        shots_train["competition_id"] == config.PL_2015_16.comp_id
    ].reset_index(drop=True)
    X_pl, _ = build_feature_matrix(pl_shots)
    pl_predicted_xg = model.predict_proba(X_pl)[:, 1]
    pl_ranking = build_player_xg_table(pl_shots, pl_predicted_xg)
    pl_ranking = pl_ranking[pl_ranking["shots"] >= 20]
    ax = plot_player_xg_ranking(
        pl_ranking, n=10, title="PL 2015/16 - biggest xG over/underperformers (min. 20 shots)"
    )
    ax.figure.savefig(outputs_dir / "pl_2015_16_xg_ranking.png", dpi=150, bbox_inches="tight")
    plt.close(ax.figure)

    return {"logistic_test_roc_auc": test_eval["roc_auc"]}


def run_similarity_pipeline(per90_features, outputs_dir=OUTPUTS_DIR):
    """Cluster each position group and regenerate every Module B output PNG (notebook 03)."""
    outputs_dir = Path(outputs_dir)
    groups = {}
    for position_group in POSITION_GROUPS:
        subset = per90_features[per90_features["position_group"] == position_group].reset_index(drop=True)
        X_scaled, _ = scale_features(subset)
        groups[position_group] = {"data": subset, "X_scaled": X_scaled}

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, position_group in zip(axes, POSITION_GROUPS):
        inertias = compute_elbow_scores(groups[position_group]["X_scaled"], k_range=ELBOW_K_RANGE)
        plot_elbow_curve(
            inertias, chosen_k=CLUSTER_K, ax=ax,
            title=f"{position_group} (n={len(groups[position_group]['data'])})",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "similarity_elbow_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, position_group in zip(axes, POSITION_GROUPS):
        silhouettes = compute_silhouette_scores(groups[position_group]["X_scaled"], k_range=ELBOW_K_RANGE)
        plot_silhouette_curve(
            silhouettes, ax=ax, title=f"{position_group} (n={len(groups[position_group]['data'])})",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "similarity_silhouette_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    for position_group in POSITION_GROUPS:
        g = groups[position_group]
        _, labels = fit_kmeans(g["X_scaled"], n_clusters=CLUSTER_K)
        g["labels"] = labels
        g["data"]["cluster"] = labels

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, position_group in zip(axes, POSITION_GROUPS):
        g = groups[position_group]
        components, pca = run_pca(g["X_scaled"])
        plot_pca_clusters(
            components, g["labels"], ax=ax,
            title=f"{position_group}\n(explained var: {pca.explained_variance_ratio_.sum():.0%})",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "similarity_pca_clusters.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    for ax, (position_group, player, team) in zip(axes, RADAR_EXAMPLES):
        data = groups[position_group]["data"]
        row = data[(data["player"] == player) & (data["team"] == team)].iloc[0]
        plot_player_radar(
            row, population=data, feature_columns=PER90_FEATURE_COLUMNS, ax=ax,
            title=f"{player}\n{position_group} - {team}",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "player_radar_examples.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def run(force=False, skip_plots=False, data_dir=DATA_DIR, outputs_dir=OUTPUTS_DIR):
    """Run the full headless rebuild: data -> models -> outputs -> manifest -> metrics.json."""
    print("[1/5] Building xG shot tables...")
    shots_train, shots_test = build_shot_tables(force=force, data_dir=data_dir)
    print(f"      train: {len(shots_train)} shots, test: {len(shots_test)} shots")

    print("[2/5] Building similarity per-90 table...")
    per90_features = build_similarity_table(force=force, data_dir=data_dir)
    print(f"      {len(per90_features)} players")

    if skip_plots:
        print("[3/5] Skipped (--skip-plots)")
        print("[4/5] Skipped (--skip-plots)")
    else:
        print("[3/5] Training xG models + writing output PNGs...")
        run_xg_pipeline(shots_train, shots_test, outputs_dir=outputs_dir)
        print("[4/5] Clustering + writing similarity PNGs...")
        run_similarity_pipeline(per90_features, outputs_dir=outputs_dir)

    print("[5/5] Writing data/manifest.json and metrics.json...")
    write_manifest()
    write_metrics()
    print("Done.")


def main():
    """CLI entry point: `python -m src.pipeline [--force] [--skip-plots]`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Ignore existing data/ caches and re-pull/re-engineer from raw StatsBomb data.",
    )
    parser.add_argument(
        "--skip-plots", action="store_true",
        help="Rebuild data + manifest/metrics only; skip model training and PNG regeneration.",
    )
    args = parser.parse_args()
    run(force=args.force, skip_plots=args.skip_plots)


if __name__ == "__main__":
    main()
