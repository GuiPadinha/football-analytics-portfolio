"""Headless rebuild: ingestion -> features -> models -> outputs -> manifest/metrics.

The notebooks (02, 03) are deliberately kept as the teaching surface (see CLAUDE.md's
learning mandate) — this module is their non-interactive twin, chaining the same
`src/` functions into one script so the whole processed-data + output-PNG rebuild can
run without a Jupyter kernel (CI, a pre-release check, or a fresh clone). It doesn't
replace the notebooks' narrative; it's the reproducibility path alongside them.

Usage:
    python -m src.pipeline                # rebuild, reusing existing data/ caches
    python -m src.pipeline --force        # rebuild the processed tables from the per-match cache
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
    evaluate_by_competition,
    evaluate_model,
    get_calibration_curve,
    get_feature_importance,
    train_gradient_boosting,
    train_logistic_regression,
)
from src.similarity import (
    CLUSTER_K,
    OUTFIELD_GROUPS,
    PER90_FEATURE_COLUMNS,
    PER90_TABLE_COLUMNS,
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
    plot_xg_generalisation_bar,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUTS_DIR = REPO_ROOT / "outputs"

ELBOW_K_RANGE = range(2, 9)

# One example player per position group for the radar-chart deliverable (notebook 03, S7).
RADAR_EXAMPLES = [
    ("Midfielder", "N''Golo Kanté", "Leicester City"),
    ("Defender", "Aaron Cresswell", "West Ham United"),
    ("Forward", "Harry Kane", "Tottenham Hotspur"),
]


def _cache_matches_datasets(path, datasets):
    """True if the shot table at `path` exists and holds exactly `datasets`' competitions.

    "The file exists" used to be the whole cache key, so adding a dataset to a config list (a new
    held-out tournament in `GENERALISATION_TEST_SETS`, say) silently reused the old table and the
    new tournament never reached metrics.json. Comparing the cached table's `competition_id`s
    against the config catches that without anyone remembering `--force`. Competition id is
    enough for the lists this guards (none mixes two seasons of one competition); a season swap
    within one competition would still need `--force`.

    Args:
        path (Path): a cached shots parquet (with a `competition_id` column).
        datasets (list[config.Dataset]): the config list it is supposed to contain.

    Returns:
        bool: False when missing, when the column is absent, or when the competitions differ.
    """
    if not path.exists():
        return False
    cached = pd.read_parquet(path)
    if "competition_id" not in cached.columns:
        return False
    cached_ids = set(cached["competition_id"].unique())
    expected_ids = {ds.comp_id for ds in datasets}
    if cached_ids != expected_ids:
        print(
            f"      {path.name} holds competitions {sorted(cached_ids)}, config expects "
            f"{sorted(expected_ids)} — rebuilding"
        )
        return False
    return True


def build_shot_tables(force=False, data_dir=DATA_DIR):
    """Rebuild (or load) the processed xG shot tables.

    Mirrors notebook 02's REBUILD cell: pulls and engineers from raw StatsBomb data
    only when a parquet cache is missing, stale (its competitions no longer match the config
    list, see `_cache_matches_datasets`) or `force=True`; otherwise reloads instantly from
    `data/shots_{train,test}.parquet`.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: (shots_train, shots_test).
    """
    data_dir = Path(data_dir)
    train_path = data_dir / "shots_train.parquet"
    test_path = data_dir / "shots_test.parquet"

    if force or not _cache_matches_datasets(train_path, config.TRAIN_SETS):
        build_training_dataset(config.TRAIN_SETS).to_parquet(train_path)
    if force or not _cache_matches_datasets(test_path, config.TEST_SETS):
        build_training_dataset(config.TEST_SETS).to_parquet(test_path)

    return pd.read_parquet(train_path), pd.read_parquet(test_path)


def build_generalisation_table(force=False, data_dir=DATA_DIR):
    """Rebuild (or load) the combined held-out shot table for Phase 4c's per-tournament check.

    Mirrors `build_shot_tables`'s cache-or-build pattern, one level up: a single combined
    table across every dataset in `config.GENERALISATION_TEST_SETS`, later split back out
    per-competition by `models.evaluate_by_competition` (via `metrics.write_metrics`).

    Returns:
        pandas.DataFrame: combined shots across `config.GENERALISATION_TEST_SETS`.
    """
    data_dir = Path(data_dir)
    path = data_dir / "shots_generalisation.parquet"

    if force or not _cache_matches_datasets(path, config.GENERALISATION_TEST_SETS):
        build_training_dataset(config.GENERALISATION_TEST_SETS).to_parquet(path)
    return pd.read_parquet(path)


def _cache_has_columns(path, columns):
    """True if the pickled table at `path` exists and has exactly `columns`, in order.

    The similarity table's version of `_cache_matches_datasets`: its risk is a feature change,
    not a config list change. "The file exists" was the whole key here too, so a copy cached
    before the raw season totals were added (2026-07-06) was still being reused in October.
    Notebook 03 and the README PNGs read this cache while metrics.json rebuilds features
    directly, so a stale copy would let them disagree without anything failing.

    Args:
        path (Path): a cached per-90 pickle.
        columns (list[str]): the columns the current builder returns.

    Returns:
        bool: False when missing or when the columns differ.
    """
    if not path.exists():
        return False
    cached_columns = list(pd.read_pickle(path).columns)
    if cached_columns != list(columns):
        print(f"      {path.name} columns no longer match the feature builder — rebuilding")
        return False
    return True


def build_similarity_table(force=False, data_dir=DATA_DIR):
    """Rebuild (or load) the per-90 similarity feature table for `config.SIMILARITY_SET`.

    Rebuilt when the cache is missing, when its columns differ from `PER90_TABLE_COLUMNS` (see
    `_cache_has_columns`), or when `force=True`.

    Returns:
        pandas.DataFrame: output of `build_player_per90_features`.
    """
    path = Path(data_dir) / "player_per90_pl_2015_16.pkl"
    if force or not _cache_has_columns(path, PER90_TABLE_COLUMNS):
        features = build_player_per90_features(
            config.SIMILARITY_SET.comp_id, config.SIMILARITY_SET.season_id
        )
        features.to_pickle(path)
    return pd.read_pickle(path)


def run_xg_pipeline(shots_train, shots_test, generalisation_shots=None, outputs_dir=OUTPUTS_DIR):
    """Train the Module A models and regenerate every xG output PNG (notebook 02).

    Args:
        shots_train (pandas.DataFrame): engineered training shots (league).
        shots_test (pandas.DataFrame): engineered held-out EURO 2024 shots.
        generalisation_shots (pandas.DataFrame, optional): combined output of
            `build_generalisation_table` (Phase 4c) — if given, also writes
            `xg_generalisation_by_tournament.png`, the per-tournament ROC-AUC breakdown.
        outputs_dir (Path): directory to write PNGs to.

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

    if generalisation_shots is not None:
        breakdown = evaluate_by_competition(model, generalisation_shots, config.GENERALISATION_TEST_SETS)
        generalisation_df = pd.DataFrame(breakdown.values())
        ax = plot_xg_generalisation_bar(generalisation_df)
        ax.set_title("xG generalisation - held-out ROC-AUC by tournament (Phase 4c)")
        ax.figure.savefig(
            outputs_dir / "xg_generalisation_by_tournament.png", dpi=150, bbox_inches="tight"
        )
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
    for position_group in OUTFIELD_GROUPS:
        subset = per90_features[per90_features["position_group"] == position_group].reset_index(drop=True)
        X_scaled, _ = scale_features(subset)
        groups[position_group] = {"data": subset, "X_scaled": X_scaled}

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, position_group in zip(axes, OUTFIELD_GROUPS):
        inertias = compute_elbow_scores(groups[position_group]["X_scaled"], k_range=ELBOW_K_RANGE)
        plot_elbow_curve(
            inertias, chosen_k=CLUSTER_K, ax=ax,
            title=f"{position_group} (n={len(groups[position_group]['data'])})",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "similarity_elbow_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, position_group in zip(axes, OUTFIELD_GROUPS):
        silhouettes = compute_silhouette_scores(groups[position_group]["X_scaled"], k_range=ELBOW_K_RANGE)
        plot_silhouette_curve(
            silhouettes, ax=ax, title=f"{position_group} (n={len(groups[position_group]['data'])})",
        )
    fig.tight_layout()
    fig.savefig(outputs_dir / "similarity_silhouette_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    for position_group in OUTFIELD_GROUPS:
        g = groups[position_group]
        _, labels = fit_kmeans(g["X_scaled"], n_clusters=CLUSTER_K)
        g["labels"] = labels
        g["data"]["cluster"] = labels

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, position_group in zip(axes, OUTFIELD_GROUPS):
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
    print("[1/6] Building xG shot tables...")
    shots_train, shots_test = build_shot_tables(force=force, data_dir=data_dir)
    print(f"      train: {len(shots_train)} shots, test: {len(shots_test)} shots")

    print("[2/6] Building Phase 4c generalisation shot table...")
    generalisation_shots = build_generalisation_table(force=force, data_dir=data_dir)
    n_tournaments = len(config.GENERALISATION_TEST_SETS)
    print(f"      {len(generalisation_shots)} shots across {n_tournaments} held-out tournaments")

    print("[3/6] Building similarity per-90 table...")
    per90_features = build_similarity_table(force=force, data_dir=data_dir)
    print(f"      {len(per90_features)} players")

    if skip_plots:
        print("[4/6] Skipped (--skip-plots)")
        print("[5/6] Skipped (--skip-plots)")
    else:
        print("[4/6] Training xG models + writing output PNGs...")
        run_xg_pipeline(shots_train, shots_test, generalisation_shots=generalisation_shots, outputs_dir=outputs_dir)
        print("[5/6] Clustering + writing similarity PNGs...")
        run_similarity_pipeline(per90_features, outputs_dir=outputs_dir)

    print("[6/6] Writing data/manifest.json and metrics.json...")
    write_manifest()
    write_metrics(data_dir=data_dir, per90_features=per90_features)
    print("Done.")


def main():
    """CLI entry point: `python -m src.pipeline [--force] [--skip-plots]`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Rebuild the processed tables from the per-match cache instead of reusing them "
        "(downloads only matches the cache doesn't have yet).",
    )
    parser.add_argument(
        "--skip-plots", action="store_true",
        help="Rebuild data + manifest/metrics only; skip model training and PNG regeneration.",
    )
    args = parser.parse_args()
    run(force=args.force, skip_plots=args.skip_plots)


if __name__ == "__main__":
    main()
