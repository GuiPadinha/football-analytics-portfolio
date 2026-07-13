"""Build step for the Streamlit app (Phase 8): precomputes the flat artifacts app.py reads.

The app never pulls StatsBomb or trains a model live (see docs/PRODUCT_SPEC.md's Data Flow
section) — it only reads small, committed Parquet tables from `app_data/`. This module is
the offline step that produces them, reusing the same `src/` functions as notebooks/pipeline.py
rather than reimplementing feature engineering or clustering for the app.

The similarity pool spans every dataset in `config.SIMILARITY_SETS` (Phase 4b, 2026-07-05) —
widened from the original single-competition (Premier League 2015/16) v1. The xG "flagship"
ranking/shot map still scopes to `config.SIMILARITY_SET` (PL 2015/16 alone): Module A's own
TRAIN_SETS were deliberately *not* expanded (see ML_LEARNING_LOG.md — more league volume didn't
close the tournament generalisation gap), so a player from one of the newly-added similarity
competitions simply has no xG data in the app; that's an expected gap, not a bug, and the app
already handles it (see app.py's "no logged shots" fallback).

Goalkeepers (2026-07-13) are built via their own feature set (`build_goalkeeper_per90_features`)
across the same `config.SIMILARITY_SETS` pool, then concatenated onto the outfield table — see
`_build_combined_gk_table`.

Usage:
    python -m src.app_data
"""

from pathlib import Path

import pandas as pd

from src import config
from src.models import build_feature_matrix, build_player_xg_table, train_logistic_regression
from src.pipeline import CLUSTER_K, POSITION_GROUPS, build_shot_tables
from src.similarity import (
    build_goalkeeper_per90_features,
    build_player_per90_features,
    fit_kmeans,
    scale_features,
)

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"


def _build_combined_similarity_table(datasets=config.SIMILARITY_SETS):
    """Build and concatenate per-90 features across every dataset in the app's similarity pool.

    Each dataset contributes its own season's minutes/actions (per-90 rates don't carry across
    competitions) — this just tags provenance and stacks the results; clustering happens
    afterward in `_add_cluster_labels`, across the *combined* pool per position group, so
    "players like X" can surface a cross-league match, not just same-league ones.

    Args:
        datasets (list[config.Dataset]): competitions/seasons to include.

    Returns:
        pandas.DataFrame: concatenated output of `build_player_per90_features`, one extra
            `competition` column (the dataset's `label`) identifying each row's source.
    """
    frames = []
    for dataset in datasets:
        features = build_player_per90_features(dataset.comp_id, dataset.season_id)
        features["competition"] = dataset.label
        frames.append(features)
    return pd.concat(frames, ignore_index=True)


def _build_combined_gk_table(datasets=config.SIMILARITY_SETS):
    """Build and concatenate goalkeeper per-90 features across the app's similarity pool.

    Mirrors `_build_combined_similarity_table`, but via `build_goalkeeper_per90_features` (own
    feature set — saves, shots faced, goals conceded, claims, punches, sweeper actions, save % —
    since a keeper's outfield-action rates are meaninglessly near zero, see that function's
    docstring). No clustering/K-means pass for goalkeepers (2026-07-13, app wiring): unlike the
    three outfield groups, there's no silhouette-informed K decided for goalkeepers yet, and
    `find_similar_players` doesn't need cluster labels anyway (it ranks by raw distance within a
    position group) — the resulting `cluster` column is simply absent/NaN for these rows once
    concatenated with the outfield table, which nothing in `app.py` reads.

    Args:
        datasets (list[config.Dataset]): competitions/seasons to include — same pool as the
            outfield table, so a keeper's "similar goalkeeper" match can also cross leagues.

    Returns:
        pandas.DataFrame: concatenated output of `build_goalkeeper_per90_features`, with the
            same `competition` provenance column the outfield table carries.
    """
    frames = []
    for dataset in datasets:
        features = build_goalkeeper_per90_features(dataset.comp_id, dataset.season_id)
        features["competition"] = dataset.label
        frames.append(features)
    return pd.concat(frames, ignore_index=True)


def _add_cluster_labels(per90_features):
    """Attach a style-archetype `cluster` label per position group (K=4, matching the notebook's
    silhouette-informed but archetype-driven choice — see ML_LEARNING_LOG.md's Module B entry).

    Args:
        per90_features (pandas.DataFrame): output of `build_player_per90_features` (or
            `_build_combined_similarity_table` — same shape, just possibly multi-competition).

    Returns:
        pandas.DataFrame: same rows, with a new `cluster` column, position groups concatenated
            back together in their original relative order.
    """
    labelled_groups = []
    for position_group in POSITION_GROUPS:
        subset = per90_features[per90_features["position_group"] == position_group].reset_index(drop=True)
        X_scaled, _ = scale_features(subset)
        _, labels = fit_kmeans(X_scaled, n_clusters=CLUSTER_K)
        subset["cluster"] = labels
        labelled_groups.append(subset)
    return pd.concat(labelled_groups, ignore_index=True)


def build_app_artifacts(app_data_dir=APP_DATA_DIR):
    """Write the three artifacts the app reads: per-90 features, player xG table, shots+xG.

    Args:
        app_data_dir (str | Path): destination directory, created if missing.

    Returns:
        dict: row counts per artifact, as a cheap sanity-check summary for the caller.
    """
    app_data_dir = Path(app_data_dir)
    app_data_dir.mkdir(parents=True, exist_ok=True)

    shots_train, _ = build_shot_tables()
    outfield_per90 = _add_cluster_labels(_build_combined_similarity_table())
    gk_per90 = _build_combined_gk_table()
    # Concatenated, not two separate artifacts: lets goalkeepers show up for free in every
    # position-group-driven UI element already keyed off `per90["position_group"].unique()`
    # (the sidebar filter, the leaderboard) without a parallel code path. `pd.concat` aligns
    # columns automatically — outfield-only columns (goals, tackles_p90, ...) are NaN on
    # goalkeeper rows and vice versa, which app.py already handles by always scoping stat
    # lookups to the current position group's own rows, never a global column.
    per90_features = pd.concat([outfield_per90, gk_per90], ignore_index=True)

    X_train, y_train = build_feature_matrix(shots_train)
    model = train_logistic_regression(X_train, y_train)

    # The xG ranking + shot map deliberately stay scoped to config.SIMILARITY_SET (PL 2015/16)
    # alone, not the wider config.SIMILARITY_SETS pool above — Module A's TRAIN_SETS were never
    # expanded (see ML_LEARNING_LOG.md), so there is no xG model output for the other similarity
    # competitions' players. app.py's "no logged shots" fallback covers that gap in the UI.
    flagship_shots = shots_train[
        shots_train["competition_id"] == config.SIMILARITY_SET.comp_id
    ].reset_index(drop=True)
    X_flagship, _ = build_feature_matrix(flagship_shots)
    flagship_shots["predicted_xg"] = model.predict_proba(X_flagship)[:, 1]

    xg_table = build_player_xg_table(flagship_shots, flagship_shots["predicted_xg"].values).reset_index()

    per90_features.to_parquet(app_data_dir / "player_per90.parquet")
    xg_table.to_parquet(app_data_dir / "player_xg_table.parquet")
    flagship_shots.to_parquet(app_data_dir / "shots_with_xg.parquet")

    return {
        "players": len(per90_features),
        "xg_table_rows": len(xg_table),
        "shots": len(flagship_shots),
    }


def main():
    """CLI entry point: `python -m src.app_data`."""
    result = build_app_artifacts()
    print(
        f"Wrote app_data/: {result['players']} players, "
        f"{result['xg_table_rows']} xG-table rows, {result['shots']} shots."
    )


if __name__ == "__main__":
    main()
