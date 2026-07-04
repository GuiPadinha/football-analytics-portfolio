"""Build step for the Streamlit app (Phase 8): precomputes the flat artifacts app.py reads.

The app never pulls StatsBomb or trains a model live (see docs/PRODUCT_SPEC.md's Data Flow
section) — it only reads small, committed Parquet tables from `app_data/`. This module is
the offline step that produces them, reusing the same `src/` functions as notebooks/pipeline.py
rather than reimplementing feature engineering or clustering for the app.

Scoped to the one dataset that's actually fully cached end-to-end today (Premier League
2015/16, `config.SIMILARITY_SET`) — the sidebar's competition/season selectors in the spec
mockup are aspirational for a future multi-dataset pass, not v1.

Usage:
    python -m src.app_data
"""

from pathlib import Path

import pandas as pd

from src import config
from src.models import build_feature_matrix, build_player_xg_table, train_logistic_regression
from src.pipeline import CLUSTER_K, POSITION_GROUPS, build_shot_tables, build_similarity_table
from src.similarity import fit_kmeans, scale_features

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"


def _add_cluster_labels(per90_features):
    """Attach a style-archetype `cluster` label per position group (K=4, matching the notebook's
    silhouette-informed but archetype-driven choice — see ML_LEARNING_LOG.md's Module B entry).

    Args:
        per90_features (pandas.DataFrame): output of `build_player_per90_features`.

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
    per90_features = _add_cluster_labels(build_similarity_table())

    X_train, y_train = build_feature_matrix(shots_train)
    model = train_logistic_regression(X_train, y_train)

    # The xG ranking + shot map both scope to config.SIMILARITY_SET's players only (Premier
    # League 2015/16) — the same player universe as the similarity table, so "players like X"
    # and "is X's output real" always refer to the same person, not two different pools.
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
