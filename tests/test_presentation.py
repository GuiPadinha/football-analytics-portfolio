"""Unit tests for src/presentation.py — the words the app puts around its numbers.

Two of these helpers exist because of shipped bugs ("91th" ordinals; a goalkeeper's goals-conceded
percentile reading as "elite"), so the edge cases below are the ones that actually bit.
"""

import pandas as pd
import pytest

from src.presentation import (
    SIGNATURE_STATS_BY_POSITION,
    STAT_LABELS,
    build_scouting_blurb,
    feature_columns_for,
    format_market_value,
    format_percentile,
    lookup_market_value,
    ordinal,
    percentile_tier,
    popular_name,
    style_intensity_label,
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


def test_style_intensity_label_words_and_signs():
    assert style_intensity_label(0.1) == "Typical (0.1σ)"
    assert style_intensity_label(-0.2) == "Typical (0.2σ)"
    assert style_intensity_label(0.5) == "Somewhat more (+0.5σ)"
    assert style_intensity_label(-1.0) == "Much less (-1.0σ)"
    assert style_intensity_label(1.8) == "Far more (+1.8σ)"


def test_style_intensity_label_rounds_before_thresholding():
    # Both display as 0.3σ, so both must get the same word.
    assert style_intensity_label(0.296) == style_intensity_label(0.304) == "Somewhat more (+0.3σ)"


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


def test_every_signature_stat_has_a_label_and_belongs_to_its_group():
    for group, stats in SIGNATURE_STATS_BY_POSITION.items():
        _, per90_columns, _ = feature_columns_for(group)
        for stat in stats:
            assert stat in STAT_LABELS
            assert stat in per90_columns


def test_build_scouting_blurb_names_best_stat_tier_and_value():
    high = pd.Series({"tackles_p90": 1.2, "interceptions_p90": 0.9})
    percentiles = pd.Series({"tackles_p90": 0.97, "interceptions_p90": 0.60})
    blurb = build_scouting_blurb(
        "Defender", high, "shots_p90", 4, percentiles, pd.Series({"market_value_eur": 850_000})
    )
    assert "**Tackles** and **Interceptions** defender" in blurb
    assert "light on **Shots**" in blurb
    assert "97th percentile (Elite)" in blurb
    assert "€850k" in blurb


def test_build_scouting_blurb_without_market_value():
    blurb = build_scouting_blurb(
        "Goalkeeper", pd.Series({"saves_p90": 1.0}), "punches_p90", 4,
        pd.Series({"saves_p90": 0.5}), None,
    )
    assert blurb.endswith("Market value not on record.")
    assert "50th percentile (Average)" in blurb


def test_ordinal_handles_the_teens_and_large_ranks():
    assert [ordinal(n) for n in (1, 2, 3, 11, 12, 13, 21, 112, 558)] == [
        "1st", "2nd", "3rd", "11th", "12th", "13th", "21st", "112th", "558th",
    ]


def test_popular_name_prefers_the_nickname_and_never_shortens():
    assert popular_name("Philippe Coutinho Correia", "Philippe Coutinho") == "Philippe Coutinho"
    assert popular_name("Harry Kane", None) == "Harry Kane"
    assert popular_name("Geum-Min Lee", float("nan")) == "Geum-Min Lee"
    assert popular_name("Kevin De Bruyne", "  ") == "Kevin De Bruyne"
