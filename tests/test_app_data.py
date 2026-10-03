"""Plain facts about the committed app data (`app_data/*.parquet`).

These tables are exactly what the live app shows, and they are committed, so CI checks them
directly. Each test pins a property a real bug broke (all found 2026-10-02): one club under two
names gave Ligue 1 21 teams and split players' seasons in two; goalkeeper save % was divided by
the wrong count (median 38% instead of ~70%); and name-only market-value matching attached other
people's valuations, from years away, to famous players.
"""

from pathlib import Path

import pandas as pd
import pytest

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"

# The real number of clubs in each competition's season.
TEAMS_PER_COMPETITION = {
    "Premier League 2015/16": 20,
    "La Liga 2015/16 (full season)": 20,
    "Serie A 2015/16": 20,
    "Ligue 1 2015/16": 20,
    "Frauen Bundesliga 2023/24": 12,
    "FA Women's Super League 2023/24": 12,
}


@pytest.fixture(scope="module")
def per90():
    return pd.read_parquet(APP_DATA_DIR / "player_per90.parquet")


@pytest.fixture(scope="module")
def market_value():
    return pd.read_parquet(APP_DATA_DIR / "market_value.parquet")


def test_each_competition_has_its_real_number_of_teams(per90):
    assert per90.groupby("competition")["team"].nunique().to_dict() == TEAMS_PER_COMPETITION


def test_each_player_appears_once_per_team(per90):
    # A mid-season transfer legitimately gives two rows (one per club); one club twice does not.
    assert not per90.duplicated(["competition", "player", "team"]).any()


def test_goalkeeper_numbers_are_realistic(per90):
    keepers = per90[per90["position_group"] == "Goalkeeper"]
    on_target = keepers["saves"] + keepers["goals_conceded"]
    # Top-flight keepers save roughly 55-85% of on-target shots; judge only regular starters.
    assert keepers.loc[on_target >= 30, "save_pct"].between(0.5, 0.9).all()
    # A keeper's shots are the ones on target only (saves + goals conceded), never every shot.
    assert "shots_faced" not in per90.columns


def test_market_values_are_unique_mens_only_and_from_around_the_season(per90, market_value):
    assert not market_value.duplicated(["player", "team"]).any()
    competitions = market_value.merge(
        per90[["player", "team", "competition"]], on=["player", "team"], how="left"
    )["competition"]
    assert competitions.notna().all()
    assert not competitions.str.contains("Women|Frauen").any()
    # The club check only keeps players valued around 2015/16, so the nearest valuation is too.
    as_of = pd.to_datetime(market_value["market_value_as_of"])
    assert as_of.between("2015-01-01", "2017-01-01").all()
