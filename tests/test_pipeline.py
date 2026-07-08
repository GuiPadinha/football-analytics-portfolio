"""Unit tests for the headless rebuild pipeline (src/pipeline.py).

Only the caching decision (rebuild-from-raw vs. reload-from-disk) is worth unit testing here —
it's the one piece of real logic `pipeline.py` adds; the rest is orchestration of already-tested
`src/` functions. Every network-touching builder (`build_training_dataset`,
`build_player_per90_features`) is monkeypatched so this suite stays offline, same reason as
`tests/test_manifest.py`.
"""

import pandas as pd

from src import config
from src.pipeline import build_generalisation_table, build_shot_tables, build_similarity_table


def _fake_builder(calls, marker):
    """Return a stub matching `build_training_dataset`'s signature: records the call, returns a
    small distinguishable DataFrame instead of hitting the network."""

    def builder(datasets):
        calls.append(datasets)
        return pd.DataFrame({"marker": [marker]})

    return builder


def test_build_shot_tables_reuses_existing_cache(tmp_path, monkeypatch):
    pd.DataFrame({"marker": ["cached"]}).to_parquet(tmp_path / "shots_train.parquet")
    pd.DataFrame({"marker": ["cached"]}).to_parquet(tmp_path / "shots_test.parquet")

    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    train, test = build_shot_tables(force=False, data_dir=tmp_path)

    assert calls == []  # raw builder never invoked — both caches already existed
    assert train["marker"].iloc[0] == "cached"
    assert test["marker"].iloc[0] == "cached"


def test_build_shot_tables_missing_cache_triggers_build(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    train, test = build_shot_tables(force=False, data_dir=tmp_path)

    assert len(calls) == 2  # neither cache existed — both TRAIN_SETS and TEST_SETS built
    assert train["marker"].iloc[0] == "rebuilt"
    assert test["marker"].iloc[0] == "rebuilt"


def test_build_shot_tables_force_ignores_existing_cache(tmp_path, monkeypatch):
    pd.DataFrame({"marker": ["cached"]}).to_parquet(tmp_path / "shots_train.parquet")
    pd.DataFrame({"marker": ["cached"]}).to_parquet(tmp_path / "shots_test.parquet")

    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    train, test = build_shot_tables(force=True, data_dir=tmp_path)

    assert len(calls) == 2
    assert train["marker"].iloc[0] == "rebuilt"
    assert test["marker"].iloc[0] == "rebuilt"


def test_build_generalisation_table_reuses_existing_cache(tmp_path, monkeypatch):
    pd.DataFrame({"marker": ["cached"]}).to_parquet(tmp_path / "shots_generalisation.parquet")

    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    shots = build_generalisation_table(force=False, data_dir=tmp_path)

    assert calls == []
    assert shots["marker"].iloc[0] == "cached"


def test_build_generalisation_table_missing_cache_triggers_build(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    shots = build_generalisation_table(force=False, data_dir=tmp_path)

    assert len(calls) == 1
    assert calls[0] == config.GENERALISATION_TEST_SETS
    assert shots["marker"].iloc[0] == "rebuilt"


def test_build_similarity_table_reuses_existing_cache(tmp_path, monkeypatch):
    pd.DataFrame({"marker": ["cached"]}).to_pickle(tmp_path / "player_per90_pl_2015_16.pkl")

    calls = []

    def fake_per90(comp_id, season_id):
        calls.append((comp_id, season_id))
        return pd.DataFrame({"marker": ["rebuilt"]})

    monkeypatch.setattr("src.pipeline.build_player_per90_features", fake_per90)

    features = build_similarity_table(force=False, data_dir=tmp_path)

    assert calls == []
    assert features["marker"].iloc[0] == "cached"


def test_build_similarity_table_missing_cache_triggers_build(tmp_path, monkeypatch):
    calls = []

    def fake_per90(comp_id, season_id):
        calls.append((comp_id, season_id))
        return pd.DataFrame({"marker": ["rebuilt"]})

    monkeypatch.setattr("src.pipeline.build_player_per90_features", fake_per90)

    features = build_similarity_table(force=False, data_dir=tmp_path)

    assert len(calls) == 1
    assert features["marker"].iloc[0] == "rebuilt"
