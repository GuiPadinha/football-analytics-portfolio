"""Read the dbt marts (warehouse/) as the app build's StatsBomb player tables.

Since 2026-11-15 the app's StatsBomb per-90 tables come out of the dbt warehouse, not out of
pandas: `app_data.py` reads `player_per90_outfield` and `player_per90_goalkeepers` from the
persisted DuckDB file that `python -m tools.warehouse --persist` builds. What stays in Python is
what needs a model or a fit: league normalisation, K-means, the xG model, Wyscout (no dbt models).

The marts were built to be drop-in: same columns, same dtypes, same values as
`similarity.build_season_per90_tables` (the dbt parity tests hold them equal), and here the same
row order, because K-means' result depends on the order of its rows. `tests/test_warehouse_tables`
checks the shape of what this returns; the full equality against pandas is checked locally, where
the event cache exists (docs/PROGRESS.md, 2026-11-15).
"""

import os
from pathlib import Path

from src.data_loader import resolve_cache_dir

# The persisted warehouse, as tools/warehouse.py --persist writes it: next to the event cache,
# outside any synced folder.
WAREHOUSE_DB_ENV_VAR = "FAP_WAREHOUSE_DB"
OUTFIELD_MART = "player_per90_outfield"
GOALKEEPER_MART = "player_per90_goalkeepers"
# The marts' key columns: the build tags each table with the dataset's own label instead.
MART_KEY_COLUMNS = ["competition_id", "season_id", "competition"]


def warehouse_db_path():
    """Where the persisted warehouse is: `$FAP_WAREHOUSE_DB`, else `<cache dir>/warehouse.duckdb`.

    Same rule as tools/warehouse.py, so the file that command writes is the file read here.
    """
    override = os.environ.get(WAREHOUSE_DB_ENV_VAR, "").strip()
    return Path(override) if override else resolve_cache_dir() / "warehouse.duckdb"


def mart_query(mart, competition_id, season_id):
    """The SQL for one season of one mart, in `build_season_per90_tables`' row order.

    pandas builds the season table from a `groupby(["player", "team"])`, which sorts by player,
    then team, comparing strings code point by code point. DuckDB's default collation compares
    the same way (checked 2026-11-15: "Pa" < "Pz" < "Pérez" < "pa" in both), so a plain
    `order by` puts an accented name where Python does. A `default_collation` setting would
    break that; this project never sets one.

    Args:
        mart (str): `OUTFIELD_MART` or `GOALKEEPER_MART`.
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.

    Returns:
        tuple[str, list]: the query and its parameters.
    """
    query = (
        f"select * from {mart} where competition_id = ? and season_id = ? "
        "order by player, team"
    )
    return query, [competition_id, season_id]


def read_season_per90_tables(connection, competition_id, season_id):
    """One season's (outfield, goalkeepers) tables from the marts, shaped like pandas' own.

    Args:
        connection (duckdb.DuckDBPyConnection): an open connection to the warehouse.
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: as `similarity.build_season_per90_tables`.

    Raises:
        ValueError: the warehouse has no rows for this season (not landed, or not built), so the
            build stops instead of shipping an app without a league.
    """
    tables = []
    for mart in (OUTFIELD_MART, GOALKEEPER_MART):
        query, params = mart_query(mart, competition_id, season_id)
        table = connection.execute(query, params).df().drop(columns=MART_KEY_COLUMNS)
        if table.empty:
            raise ValueError(
                f"{mart} has no rows for competition {competition_id}, season {season_id}: land it "
                "(python -m src.landing --all) and rebuild (python -m tools.warehouse --persist)."
            )
        tables.append(table)
    return tables[0], tables[1]


SHOT_FEATURES_MODEL = "int_shot_features"
# The columns of `features.extract_shot_features`' output, in its order, before the two that
# `features.build_training_dataset` adds.
SHOT_FEATURE_COLUMNS = [
    "match_id", "player", "team", "minute", "x", "y", "distance_to_goal", "angle_to_goal",
    "shot_body_part", "is_header", "is_first_time", "under_pressure", "is_penalty",
    "is_free_kick", "assist_type", "game_state_score_diff", "shot_statsbomb_xg", "is_goal",
]


def read_training_shots(connection, datasets, match_ids_by_dataset):
    """The xG model's shot table from `int_shot_features`, shaped like `build_training_dataset`'s.

    Row order matters: grouped cross-validation and the solver see rows in order. pandas walks
    the matches in the StatsBomb API's order, then each match's events in order, so the caller
    passes that match order (Python owns it: it comes from the cache's match lists) and this
    sorts by it, then by event position.

    Args:
        connection (duckdb.DuckDBPyConnection): an open connection to the warehouse.
        datasets (list[config.Dataset]): the competitions/seasons wanted, in pandas' order.
        match_ids_by_dataset (list[list[int]]): each dataset's match ids in API order.

    Returns:
        pandas.DataFrame: as `features.build_training_dataset(datasets)`.

    Raises:
        ValueError: a dataset has no shots in the warehouse, or its match set differs from
            the cache's (not landed, or landed from a different cache).
    """
    frames = []
    for dataset, match_ids in zip(datasets, match_ids_by_dataset):
        table = connection.execute(
            f"select * from {SHOT_FEATURES_MODEL} where competition_id = ? and season_id = ?",
            [dataset.comp_id, dataset.season_id],
        ).df()
        if table.empty:
            raise ValueError(
                f"{SHOT_FEATURES_MODEL} has no shots for {dataset.label}: land it "
                "(python -m src.landing --all) and rebuild (python -m tools.warehouse --persist)."
            )
        position = {match_id: i for i, match_id in enumerate(match_ids)}
        unknown = set(table["match_id"]) - set(position)
        if unknown:
            raise ValueError(f"{dataset.label}: warehouse has matches the cache doesn't: {sorted(unknown)[:5]}")
        table["_position"] = table["match_id"].map(position)
        table = table.sort_values(["_position", "event_index"], kind="stable")
        table = table[SHOT_FEATURE_COLUMNS].reset_index(drop=True)
        # A sum over a window is a 128-bit integer in DuckDB, which pandas hands back as float.
        table["game_state_score_diff"] = table["game_state_score_diff"].astype("int64")
        table["league_context"] = dataset.context
        table["competition_id"] = dataset.comp_id
        frames.append(table)
    import pandas as pd

    return pd.concat(frames, ignore_index=True)


def connect_warehouse(db_path=None):
    """Open the persisted warehouse read-only, with a clear message when it isn't built.

    duckdb is imported here, not at the top: it is a build dependency (requirements-dev.txt),
    never one of the app's.
    """
    import duckdb

    db_path = Path(db_path) if db_path else warehouse_db_path()
    if not db_path.exists():
        raise FileNotFoundError(
            f"No warehouse at {db_path}. Build it first: python -m tools.warehouse --persist "
            "(or rebuild from pandas: python -m src.app_data --from-pandas)."
        )
    return duckdb.connect(str(db_path), read_only=True)
