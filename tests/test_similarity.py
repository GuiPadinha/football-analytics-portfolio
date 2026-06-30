"""Unit tests for minutes/position aggregation and clock parsing in the similarity module."""

import numpy as np
import pandas as pd
import pytest

from src.similarity import (
    _parse_clock,
    compute_minutes_played,
    compute_silhouette_scores,
    resolve_season_positions,
)


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


def test_resolve_season_positions_weights_by_minutes_not_match_count():
    # The Michail Antonio failure mode in miniature: a winger whose attacking
    # minutes are fragmented across three forward labels, plus four short defensive
    # cameos all sharing one label. A modal-per-match vote would pick Right Back
    # (4 matches) over any single forward label (1 match each) and call him a
    # defender; minutes-weighting at the group level must call him a forward.
    rows = (
        [{"player": "P", "team": "T", "position": "Right Wing", "minutes_played": 90},
         {"player": "P", "team": "T", "position": "Left Wing", "minutes_played": 90},
         {"player": "P", "team": "T", "position": "Center Forward", "minutes_played": 90}]
        + [{"player": "P", "team": "T", "position": "Right Back", "minutes_played": 20}
           for _ in range(4)]
    )
    result = resolve_season_positions(pd.DataFrame(rows))

    assert len(result) == 1
    row = result.iloc[0]
    # 270 forward minutes vs 80 defender minutes -> Forward, despite Right Back
    # being the single most *frequent* per-match label.
    assert row["position_group"] == "Forward"
    assert row["minutes_played"] == pytest.approx(350.0)


def test_resolve_season_positions_total_minutes_span_all_positions():
    # A genuine two-position player: total minutes must be the full season
    # presence (both positions summed), not just minutes in the winning group.
    rows = [
        {"player": "Q", "team": "T", "position": "Center Midfield", "minutes_played": 600},
        {"player": "Q", "team": "T", "position": "Center Back", "minutes_played": 300},
    ]
    result = resolve_season_positions(pd.DataFrame(rows)).iloc[0]
    assert result["position_group"] == "Midfielder"      # 600 > 300
    assert result["minutes_played"] == pytest.approx(900.0)


def test_compute_silhouette_scores_prefers_true_cluster_count():
    # Two tight, well-separated blobs: the silhouette score should peak at K=2,
    # the real cluster count — the property that lets it recommend a K where the
    # always-decreasing elbow inertia cannot.
    rng = np.random.default_rng(0)
    X = pd.DataFrame(
        np.vstack([rng.normal(0.0, 0.1, size=(30, 2)), rng.normal(5.0, 0.1, size=(30, 2))]),
        columns=["f1", "f2"],
    )
    scores = compute_silhouette_scores(X, k_range=range(2, 6))

    assert scores.idxmax() == 2
    assert scores.loc[2] > 0.8       # near-perfect separation scores close to 1
