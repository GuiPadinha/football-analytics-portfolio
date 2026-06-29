"""Unit tests for minutes/position aggregation and clock parsing in the similarity module."""

import pandas as pd
import pytest

from src.similarity import _parse_clock, compute_minutes_played


def test_parse_clock_with_stoppage_time():
    # StatsBomb's clock doesn't reset at half-time, so second-half stoppage reads e.g. 95:12.
    assert _parse_clock("95:12") == pytest.approx(95.2)


def test_parse_clock_zero():
    assert _parse_clock("00:00") == 0.0


def test_compute_minutes_played_sums_stints_and_picks_modal_position():
    lineups = {
        "Test FC": pd.DataFrame([{
            "player_name": "Test Player",
            "positions": [
                {"from": "00:00", "to": "60:00", "position": "Center Back"},   # 60 min
                {"from": "60:00", "to": None, "position": "Right Back"},        # 30 min (to full time)
            ],
        }])
    }
    result = compute_minutes_played(lineups, match_duration=90.0)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["player"] == "Test Player"
    assert row["team"] == "Test FC"
    assert row["minutes_played"] == pytest.approx(90.0)
    # Primary position is the one with the most minutes, not the last one played.
    assert row["position"] == "Center Back"
