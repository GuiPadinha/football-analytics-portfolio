"""src/warehouse_tables.py: reading the dbt marts as the app build's StatsBomb tables.

The real marts need the landed events (local only), so these tests build tiny stand-in marts in
an in-memory DuckDB: same names, same key columns. What they pin down is the contract with
`app_data.py`: the key columns go, the row order is pandas' (player, then team, code point by code
point), the seasons don't leak into each other, and a missing league or warehouse stops the build
with a message saying what to run.
"""

import duckdb
import pytest

from src.warehouse_tables import (
    GOALKEEPER_MART,
    OUTFIELD_MART,
    connect_warehouse,
    read_season_per90_tables,
    warehouse_db_path,
)


@pytest.fixture
def marts():
    """Two stand-in marts: two seasons, names whose order differs between collations."""
    con = duckdb.connect(":memory:")
    for mart in (OUTFIELD_MART, GOALKEEPER_MART):
        con.execute(
            f"create table {mart} (competition_id int, season_id int, competition varchar, "
            "player varchar, team varchar, minutes_played double)"
        )
    con.execute(
        f"insert into {OUTFIELD_MART} values "
        "(2, 27, 'PL', 'pa', 'B', 900), (2, 27, 'PL', 'Pérez', 'A', 950), "
        "(2, 27, 'PL', 'Pz', 'A', 1000), (2, 27, 'PL', 'Pa', 'B', 990), (2, 27, 'PL', 'Pa', 'A', 1100), "
        "(11, 27, 'La Liga', 'Other', 'C', 2000)"
    )
    con.execute(f"insert into {GOALKEEPER_MART} values (2, 27, 'PL', 'Keeper', 'A', 3000)")
    yield con
    con.close()


def test_rows_come_in_pandas_order_without_the_key_columns(marts):
    outfield, goalkeepers = read_season_per90_tables(marts, 2, 27)
    assert list(outfield.columns) == ["player", "team", "minutes_played"]
    # Python's sorted(): upper case before lower, an accented letter after every plain one.
    assert list(zip(outfield["player"], outfield["team"])) == [
        ("Pa", "A"), ("Pa", "B"), ("Pz", "A"), ("Pérez", "A"), ("pa", "B"),
    ]
    assert outfield.index.tolist() == list(range(5))
    assert goalkeepers["player"].tolist() == ["Keeper"]


def test_a_season_missing_from_the_warehouse_stops_the_build(marts):
    with pytest.raises(ValueError, match="src.landing --all"):
        read_season_per90_tables(marts, 11, 27)  # outfield rows exist, goalkeepers don't


def test_a_missing_warehouse_says_how_to_build_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="tools.warehouse --persist"):
        connect_warehouse(tmp_path / "nowhere.duckdb")


def test_the_path_follows_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("FAP_WAREHOUSE_DB", str(tmp_path / "w.duckdb"))
    assert warehouse_db_path() == tmp_path / "w.duckdb"
    monkeypatch.delenv("FAP_WAREHOUSE_DB")
    monkeypatch.setenv("FAP_CACHE_DIR", str(tmp_path))
    assert warehouse_db_path() == tmp_path / "warehouse.duckdb"
