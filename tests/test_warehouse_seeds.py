"""The dbt seeds repeat two Python constants as CSV; these tests keep the copies identical."""

import csv
from pathlib import Path

from src import config
from src.similarity import POSITION_GROUPS

SEEDS = Path(__file__).resolve().parent.parent / "warehouse" / "seeds"


def _rows(name):
    with open(SEEDS / name, encoding="utf-8", newline="") as seed_file:
        return list(csv.DictReader(seed_file))


def test_position_groups_seed_equals_the_python_mapping():
    seed = {row["position"]: row["position_group"] for row in _rows("position_groups.csv")}
    assert seed == POSITION_GROUPS


def test_competitions_seed_equals_the_app_statsbomb_leagues():
    seed = [
        (int(row["competition_id"]), int(row["season_id"]), row["competition"], row["gender"])
        for row in _rows("competitions.csv")
    ]
    expected = [
        (dataset.comp_id, dataset.season_id, dataset.label, dataset.gender)
        for dataset in config.SIMILARITY_SETS
    ]
    assert seed == expected
