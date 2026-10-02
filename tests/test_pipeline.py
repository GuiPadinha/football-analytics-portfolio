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
from src.similarity import PER90_TABLE_COLUMNS


def _fake_builder(calls, marker):
    """Return a stub matching `build_training_dataset`'s signature: records the call, returns a
    small distinguishable DataFrame instead of hitting the network."""

    def builder(datasets):
        calls.append(datasets)
        return _shots_frame(datasets, marker)

    return builder


def _shots_frame(datasets, marker):
    """A tiny shot table holding one row per dataset's competition — what a real cache of that
    config list looks like to the pipeline's staleness check."""
    return pd.DataFrame({
        "marker": [marker] * len(datasets),
        "competition_id": [ds.comp_id for ds in datasets],
    })


def test_build_shot_tables_reuses_existing_cache(tmp_path, monkeypatch):
    _shots_frame(config.TRAIN_SETS, "cached").to_parquet(tmp_path / "shots_train.parquet")
    _shots_frame(config.TEST_SETS, "cached").to_parquet(tmp_path / "shots_test.parquet")

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
    _shots_frame(config.TRAIN_SETS, "cached").to_parquet(tmp_path / "shots_train.parquet")
    _shots_frame(config.TEST_SETS, "cached").to_parquet(tmp_path / "shots_test.parquet")

    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    train, test = build_shot_tables(force=True, data_dir=tmp_path)

    assert len(calls) == 2
    assert train["marker"].iloc[0] == "rebuilt"
    assert test["marker"].iloc[0] == "rebuilt"


def test_build_generalisation_table_reuses_existing_cache(tmp_path, monkeypatch):
    _shots_frame(config.GENERALISATION_TEST_SETS, "cached").to_parquet(
        tmp_path / "shots_generalisation.parquet"
    )

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


def test_build_generalisation_table_rebuilds_when_config_gained_a_tournament(tmp_path, monkeypatch):
    # A cache built before the newest tournament was added to the config must not be reused —
    # this is exactly how a new held-out tournament could silently miss metrics.json.
    _shots_frame(config.GENERALISATION_TEST_SETS[:-1], "stale").to_parquet(
        tmp_path / "shots_generalisation.parquet"
    )
    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    shots = build_generalisation_table(force=False, data_dir=tmp_path)

    assert calls == [config.GENERALISATION_TEST_SETS]
    assert set(shots["marker"]) == {"rebuilt"}


def test_build_shot_tables_rebuilds_a_cache_without_competition_ids(tmp_path, monkeypatch):
    pd.DataFrame({"marker": ["legacy"]}).to_parquet(tmp_path / "shots_train.parquet")
    _shots_frame(config.TEST_SETS, "cached").to_parquet(tmp_path / "shots_test.parquet")
    calls = []
    monkeypatch.setattr("src.pipeline.build_training_dataset", _fake_builder(calls, "rebuilt"))

    train, test = build_shot_tables(force=False, data_dir=tmp_path)

    assert calls == [config.TRAIN_SETS]
    assert train["marker"].iloc[0] == "rebuilt"
    assert test["marker"].iloc[0] == "cached"


def _per90_frame(marker, columns=PER90_TABLE_COLUMNS):
    """A one-row per-90 table with the given columns; `player` carries the marker."""
    return pd.DataFrame({col: [marker] for col in columns})


def _fake_per90_builder(calls):
    """Stub for `build_player_per90_features`: records the call, returns a 'rebuilt' table."""

    def builder(comp_id, season_id):
        calls.append((comp_id, season_id))
        return _per90_frame("rebuilt")

    return builder


def test_build_similarity_table_reuses_existing_cache(tmp_path, monkeypatch):
    _per90_frame("cached").to_pickle(tmp_path / "player_per90_pl_2015_16.pkl")
    calls = []
    monkeypatch.setattr("src.pipeline.build_player_per90_features", _fake_per90_builder(calls))

    features = build_similarity_table(force=False, data_dir=tmp_path)

    assert calls == []
    assert features["player"].iloc[0] == "cached"


def test_build_similarity_table_missing_cache_triggers_build(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("src.pipeline.build_player_per90_features", _fake_per90_builder(calls))

    features = build_similarity_table(force=False, data_dir=tmp_path)

    assert len(calls) == 1
    assert features["player"].iloc[0] == "rebuilt"


def test_build_similarity_table_rebuilds_a_cache_with_stale_columns(tmp_path, monkeypatch):
    # The real case found 2026-10-02: a cache from before the raw season totals were added.
    stale_columns = [col for col in PER90_TABLE_COLUMNS if not col.endswith("_p90")][:4] + \
        [col for col in PER90_TABLE_COLUMNS if col.endswith("_p90")]
    _per90_frame("cached", stale_columns).to_pickle(tmp_path / "player_per90_pl_2015_16.pkl")
    calls = []
    monkeypatch.setattr("src.pipeline.build_player_per90_features", _fake_per90_builder(calls))

    features = build_similarity_table(force=False, data_dir=tmp_path)

    assert len(calls) == 1
    assert features["player"].iloc[0] == "rebuilt"
    assert list(features.columns) == PER90_TABLE_COLUMNS
