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


def test_land_dataset_writes_once_and_reports_missing(tmp_path):
    cache, raw = tmp_path / "cache", tmp_path / "raw"
    cache.mkdir()
    (cache / "events_7.pkl").write_bytes(pickle.dumps(_events()))
    dataset = {"comp_id": 2, "season_id": 27, "match_ids": [7, 8]}

    assert landing.land_dataset(dataset, raw, cache) == {"landed": 1, "skipped": 0, "missing": 1}
    target = raw / "events" / "competition_id=2" / "season_id=27" / "match_7.parquet"
    assert pq.read_table(target).num_rows == 3
    # A second run rewrites nothing: a played match never changes.
    assert landing.land_dataset(dataset, raw, cache) == {"landed": 0, "skipped": 1, "missing": 1}
