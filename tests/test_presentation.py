"""Unit tests for src/presentation.py — the words the app puts around its numbers.

Two of these helpers exist because of shipped bugs ("91th" ordinals; a goalkeeper's goals-conceded
percentile reading as "elite"), so the edge cases below are the ones that actually bit.
"""

import pandas as pd
import pytest

from src.presentation import (
    STAT_LABELS,
    feature_columns_for,
    format_market_value,
    format_percentile,
    lookup_market_value,
    ordinal,
    percentile_tier,
    popular_name,
)
from src.similarity import (
    ACTION_COLUMNS,
    GK_ACTION_COLUMNS,
    GK_PER90_FEATURE_COLUMNS,
    PER90_FEATURE_COLUMNS,
)


@pytest.mark.parametrize(
    "pct, tier",
    [(100, "Elite"), (95, "Elite"), (94.9, "Very good"), (80, "Very good"), (60, "Good"),
     (59.9, "Average"), (40, "Average"), (20, "Below average"), (19.9, "Poor"), (0, "Poor")],
)
def test_percentile_tier_band_edges(pct, tier):
    assert percentile_tier(pct) == tier


@pytest.mark.parametrize(
    "pct, text",
    [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (12, "12th"), (13, "13th"),
     (21, "21st"), (22, "22nd"), (23, "23rd"), (91, "91st"), (100, "100th"), (101, "101st"),
     (111, "111th"), (112, "112th"), (71.6, "72nd")],
)
def test_format_percentile_ordinal_suffixes(pct, text):
    assert format_percentile(pct) == text


def test_format_market_value():
    assert format_market_value(30_000_000) == "€30.0M"
    assert format_market_value(1_000_000) == "€1.0M"
    assert format_market_value(850_000) == "€850k"
    assert format_market_value(float("nan")) == ""
    assert format_market_value(None) == ""


def test_lookup_market_value_matches_player_and_team():
    table = pd.DataFrame({
        "player": ["A", "A"], "team": ["X", "Y"], "market_value_eur": [1.0, 2.0],
    })
    assert lookup_market_value(table, "A", "Y")["market_value_eur"] == 2.0
    assert lookup_market_value(table, "A", "Z") is None


def test_feature_columns_for_goalkeepers_vs_outfield():
    assert feature_columns_for("Goalkeeper")[:2] == (GK_ACTION_COLUMNS, GK_PER90_FEATURE_COLUMNS)
    for group in ("Defender", "Midfielder", "Forward"):
        assert feature_columns_for(group)[:2] == (ACTION_COLUMNS, PER90_FEATURE_COLUMNS)


def test_ordinal_handles_the_teens_and_large_ranks():
    assert [ordinal(n) for n in (1, 2, 3, 11, 12, 13, 21, 112, 558)] == [
        "1st", "2nd", "3rd", "11th", "12th", "13th", "21st", "112th", "558th",
    ]


def test_popular_name_prefers_the_nickname_and_never_shortens():
    assert popular_name("Philippe Coutinho Correia", "Philippe Coutinho") == "Philippe Coutinho"
    assert popular_name("Harry Kane", None) == "Harry Kane"
    assert popular_name("Geum-Min Lee", float("nan")) == "Geum-Min Lee"
    assert popular_name("Kevin De Bruyne", "  ") == "Kevin De Bruyne"


@pytest.mark.parametrize("provider", ["statsbomb", "wyscout"])
@pytest.mark.parametrize("group", ["Defender", "Midfielder", "Forward", "Goalkeeper"])
def test_every_stat_a_page_shows_has_a_label(group, provider):
    # profile.py and views/build.py index STAT_LABELS[stat] directly: a missing label is a crash.
    _, per90, league_adjusted = feature_columns_for(group, provider)
    assert [c for c in per90 + league_adjusted if c not in STAT_LABELS] == []
