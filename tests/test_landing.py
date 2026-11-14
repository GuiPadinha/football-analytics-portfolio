"""The raw layer: one match's pickled events become a Parquet file dbt can read."""

import json
import pickle

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src import landing


def _events():
    """Three events with the awkward column kinds: True/NaN flags, lists, dicts, all-empty."""
    return pd.DataFrame({
        "id": ["a", "b", "c"],
        "index": [1, 2, 3],
        "match_id": [7, 7, 7],
        "type": ["Pass", "Shot", "Half End"],
        "player_id": [10.0, 11.0, np.nan],
        "location": [[60.0, 40.0], [100, 30.5], np.nan],
        "under_pressure": [True, np.nan, np.nan],
        "shot_freeze_frame": [np.nan, [{"location": [1.0, 2.0], "teammate": False}], np.nan],
        "pass_height": ["Ground Pass", np.nan, np.nan],
        "never_set": [np.nan, np.nan, np.nan],
    })


def test_contract_columns_are_always_present_and_typed():
    table = landing.events_to_table(_events())
    for name, arrow_type in landing.CONTRACT_COLUMNS.items():
        assert table.schema.field(name).type == arrow_type, name
    # A flag no event of the match had is still a column, all null.
    assert table["pass_cut_back"].null_count == 3


def test_values_survive_the_conversion():
    table = landing.events_to_table(_events())
    assert table["player_id"].to_pylist() == [10, 11, None]
    assert table["location"].to_pylist() == [[60.0, 40.0], [100.0, 30.5], None]
    assert table["under_pressure"].to_pylist() == [True, None, None]
    assert table["pass_height"].to_pylist() == ["Ground Pass", None, None]


def test_nested_columns_become_json_and_empty_ones_are_dropped():
    table = landing.events_to_table(_events())
    assert table.schema.field("shot_freeze_frame").type == pa.string()
    assert json.loads(table["shot_freeze_frame"][1].as_py())[0]["teammate"] is False
    assert "never_set" not in table.column_names


def _lineups():
    """Two teams; one player changes position, one never comes on."""
    return {
        "Home": pd.DataFrame([
            {"player_id": 1, "player_name": "Starter", "player_nickname": "Star", "positions": [
                {"position": "Right Wing", "from": "00:00", "to": "60:30"},
                {"position": "Right Back", "from": "60:30", "to": None},
            ]},
            {"player_id": 2, "player_name": "Unused", "player_nickname": None, "positions": []},
        ]),
        "Away": pd.DataFrame([
            {"player_id": 3, "player_name": "Keeper", "player_nickname": None, "positions": [
                {"position": "Goalkeeper", "from": "00:00", "to": None},
            ]},
        ]),
    }


def test_lineups_become_one_row_per_stint():
    table = landing.lineups_to_table(_lineups(), match_id=7)
    assert table.schema == landing.LINEUP_SCHEMA
    rows = table.to_pylist()
    assert [(row["player_name"], row["stint_index"], row["position"]) for row in rows] == [
        ("Starter", 0, "Right Wing"), ("Starter", 1, "Right Back"), ("Keeper", 0, "Goalkeeper"),
    ]
    assert rows[1]["from_clock"] == "60:30" and rows[1]["to_clock"] is None
    assert {row["match_id"] for row in rows} == {7}


def test_land_dataset_writes_once_and_reports_missing(tmp_path):
    cache, raw = tmp_path / "cache", tmp_path / "raw"
    cache.mkdir()
    (cache / "events_7.pkl").write_bytes(pickle.dumps(_events()))
    (cache / "lineups_7.pkl").write_bytes(pickle.dumps(_lineups()))
    # Match 9 has events but no lineups: it is missing, and nothing is written for it.
    (cache / "events_9.pkl").write_bytes(pickle.dumps(_events()))
    dataset = {"comp_id": 2, "season_id": 27, "match_ids": [7, 8, 9]}

    assert landing.land_dataset(dataset, raw, cache) == {"landed": 1, "skipped": 0, "missing": 2}
    season = "competition_id=2/season_id=27"
    assert pq.read_table(raw / "events" / season / "match_7.parquet").num_rows == 3
    assert pq.read_table(raw / "lineups" / season / "match_7.parquet").num_rows == 3
    assert not (raw / "events" / season / "match_9.parquet").exists()
    # A second run rewrites nothing: a played match never changes.
    assert landing.land_dataset(dataset, raw, cache) == {"landed": 0, "skipped": 1, "missing": 2}


def test_land_matches_fetches_only_when_the_file_is_missing(tmp_path):
    calls = []

    def fetch(competition_id, season_id):
        calls.append((competition_id, season_id))
        return pd.DataFrame([{
            "match_id": 7, "match_date": "2015-08-08", "match_week": 1, "home_team": "Home",
            "away_team": "Away", "home_score": 1, "away_score": 0, "referee": "not landed",
        }])

    dataset = {"comp_id": 2, "season_id": 27, "match_ids": [7]}
    assert landing.land_matches(dataset, tmp_path, fetch=fetch) is True
    assert landing.land_matches(dataset, tmp_path, fetch=fetch) is False
    assert calls == [(2, 27)]
    target = tmp_path / "matches" / "competition_id=2" / "season_id=27" / "matches.parquet"
    # The file itself: read_table would add the folder names as columns.
    assert pq.ParquetFile(target).schema_arrow.names == landing.MATCH_COLUMNS
