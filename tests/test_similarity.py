"""Unit tests for minutes/position aggregation and clock parsing in the similarity module."""

import numpy as np
import pandas as pd
import pytest

from src.similarity import (
    _parse_clock,
    compute_minutes_played,
    compute_silhouette_scores,
    extract_goalkeeper_match_actions,
    extract_player_match_actions,
    find_similar_players,
    normalize_within_competition,
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


def _player_pool():
    # Two position groups so the "restricted to own group" behaviour is actually
    # exercised: a defender pool (all near each other) and one lone forward who
    # would otherwise look "similar" by raw distance if groups weren't respected.
    return pd.DataFrame([
        {"player": "Target", "team": "T", "position_group": "Defender", "f1": 0.0, "f2": 0.0},
        {"player": "Near", "team": "T", "position_group": "Defender", "f1": 0.1, "f2": 0.1},
        {"player": "Far", "team": "T", "position_group": "Defender", "f1": 5.0, "f2": 5.0},
        {"player": "WrongGroup", "team": "T", "position_group": "Forward", "f1": 0.05, "f2": 0.05},
    ])


def test_find_similar_players_excludes_self_and_restricts_to_position_group():
    result = find_similar_players(_player_pool(), ["f1", "f2"], player="Target", team="T", n=5)

    assert "Target" not in result["player"].values          # never recommends the player to themselves
    assert "WrongGroup" not in result["player"].values       # different position_group, excluded even though closer
    assert list(result["player"]) == ["Near", "Far"]         # ranked nearest-first within the group


def test_find_similar_players_respects_n():
    result = find_similar_players(_player_pool(), ["f1", "f2"], player="Target", team="T", n=1)
    assert len(result) == 1
    assert result.iloc[0]["player"] == "Near"


def test_find_similar_players_raises_for_unknown_player():
    with pytest.raises(ValueError):
        find_similar_players(_player_pool(), ["f1", "f2"], player="Nobody", team="T")


def test_find_similar_players_includes_competition_column_when_present():
    pool = _player_pool()
    pool["competition"] = ["Comp A", "Comp A", "Comp A", "Comp B"]
    result = find_similar_players(pool, ["f1", "f2"], player="Target", team="T", n=5)
    assert "competition" in result.columns
    assert result.set_index("player").loc["Near", "competition"] == "Comp A"


def test_find_similar_players_omits_competition_column_when_absent():
    # Single-dataset callers (notebooks/pipeline) carry no competition column at all -
    # must not KeyError trying to keep a column that was never there.
    result = find_similar_players(_player_pool(), ["f1", "f2"], player="Target", team="T", n=5)
    assert "competition" not in result.columns


def test_extract_goalkeeper_match_actions_counts_by_type():
    events = pd.DataFrame([
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Shot Faced"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Shot Saved"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Shot Faced"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Goal Conceded"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Collected"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Punch"},
        {"type": "Goal Keeper", "player": "Keeper A", "team": "T", "goalkeeper_type": "Keeper Sweeper"},
        # A different team's outfield event in the same match must not be counted as a GK action.
        {"type": "Pass", "player": "Midfielder B", "team": "T", "goalkeeper_type": np.nan},
    ])
    result = extract_goalkeeper_match_actions(events).set_index(["player", "team"])
    row = result.loc[("Keeper A", "T")]
    assert row["shots_faced"] == 2
    assert row["saves"] == 1
    assert row["goals_conceded"] == 1
    assert row["claims"] == 1
    assert row["punches"] == 1
    assert row["sweeper_actions"] == 1
    assert "Midfielder B" not in result.index.get_level_values("player")


def test_extract_goalkeeper_match_actions_handles_zero_gk_events():
    # Sparser version of the same sparse-column family as features.py's Barcelona 2020/21 fix:
    # if a match has zero "Goal Keeper" events at all, `goalkeeper_type` never appears as a
    # column in `events`, not just as a missing flag on an existing row.
    events = pd.DataFrame([
        {"type": "Pass", "player": "Midfielder B", "team": "T"},
    ])
    result = extract_goalkeeper_match_actions(events)
    assert len(result) == 0
    assert list(result.columns) == ["player", "team", "shots_faced", "saves", "goals_conceded", "claims", "punches", "sweeper_actions"]


def test_extract_player_match_actions_counts_clearances_and_blocks():
    # Neither sub-type needs a safe_column guard (unlike shot_body_part/goalkeeper_type):
    # both filter on the always-present `type` column, never touch an optional sub-field.
    # Uses "Pressure" (not "Pass") for the unrelated event — a bare Pass row would hit the
    # progressive-passes code path, which needs location/pass_end_location columns this
    # minimal frame doesn't carry, unrelated to what this test is actually checking.
    events = pd.DataFrame([
        {"type": "Clearance", "player": "Defender A", "team": "T"},
        {"type": "Clearance", "player": "Defender A", "team": "T"},
        {"type": "Block", "player": "Defender A", "team": "T"},
        {"type": "Pressure", "player": "Midfielder B", "team": "T"},
    ])
    result = extract_player_match_actions(events).set_index(["player", "team"])
    assert result.loc[("Defender A", "T"), "clearances"] == 2
    assert result.loc[("Defender A", "T"), "blocks"] == 1
    assert result.loc[("Midfielder B", "T"), "clearances"] == 0
    assert result.loc[("Midfielder B", "T"), "blocks"] == 0


def test_extract_player_match_actions_handles_zero_clearances_and_blocks():
    events = pd.DataFrame([{"type": "Pressure", "player": "Midfielder B", "team": "T"}])
    result = extract_player_match_actions(events)
    assert result.loc[0, "clearances"] == 0
    assert result.loc[0, "blocks"] == 0


def test_extract_player_match_actions_goals_include_penalties_but_np_goals_do_not():
    # The whole point of the display-only `goals` column: it counts penalties, while the
    # modelling `non_penalty_goals` column strips them. A penalty-heavy scorer must show up
    # in `goals` but not be rewarded for it in the clustering feature.
    events = pd.DataFrame([
        {"type": "Shot", "player": "Striker A", "team": "T", "shot_outcome": "Goal", "shot_type": "Open Play"},
        {"type": "Shot", "player": "Striker A", "team": "T", "shot_outcome": "Goal", "shot_type": "Penalty"},
        {"type": "Shot", "player": "Striker A", "team": "T", "shot_outcome": "Saved", "shot_type": "Open Play"},
    ])
    result = extract_player_match_actions(events).set_index(["player", "team"])
    assert result.loc[("Striker A", "T"), "goals"] == 2  # open-play + penalty
    assert result.loc[("Striker A", "T"), "non_penalty_goals"] == 1  # penalty excluded


def test_normalize_within_competition_z_scores_relative_to_own_league():
    # Two leagues with very different baselines: League A's players cluster around a rate of
    # 10, League B's around 100 — a raw comparison would say every League B player "presses
    # more" than every League A player, purely from the league-level baseline, not style. After
    # league normalisation, a player's z-score should reflect standing *within their own
    # league* only, so the "high" League A player and the "high" League B player land at the
    # same relative position.
    features = pd.DataFrame({
        "competition": ["A", "A", "A", "B", "B", "B"],
        "pressures_p90": [8.0, 10.0, 12.0, 80.0, 100.0, 120.0],
    })
    z = normalize_within_competition(features, ["pressures_p90"])

    assert list(z.columns) == ["pressures_p90_lz"]
    # Same relative position (highest in a 3-player group, symmetric spacing) -> identical
    # z-score regardless of the two leagues' very different raw baselines (10 vs 100).
    assert z.loc[2, "pressures_p90_lz"] == pytest.approx(z.loc[5, "pressures_p90_lz"])
    assert z.loc[0, "pressures_p90_lz"] == pytest.approx(z.loc[3, "pressures_p90_lz"])
    # Each league's own z-scores are mean 0 (a raw pooled z-score would not be, since League B's
    # mean is ~10x League A's).
    assert z.loc[[0, 1, 2], "pressures_p90_lz"].mean() == pytest.approx(0.0, abs=1e-9)
    assert z.loc[[3, 4, 5], "pressures_p90_lz"].mean() == pytest.approx(0.0, abs=1e-9)


def test_normalize_within_competition_fills_zero_for_degenerate_groups():
    # A competition with a single player (std is undefined, 0/0) and one with zero variance
    # (every player identical on this stat) both produce a NaN z-score before the guard - "no
    # relative signal available" is filled with 0.0 (neutral) rather than propagating NaN into
    # clustering/distance, which would silently corrupt every downstream computation touching
    # that player.
    features = pd.DataFrame({
        "competition": ["Solo", "Tied", "Tied"],
        "tackles_p90": [5.0, 3.0, 3.0],
    })
    z = normalize_within_competition(features, ["tackles_p90"])

    assert (z["tackles_p90_lz"] == 0.0).all()
    assert z["tackles_p90_lz"].notna().all()


def test_normalize_within_competition_groups_by_position_group_too_when_asked():
    # Called with an extra group column (e.g. position_group), normalisation happens within
    # each (competition, position_group) pair independently - a defender's rate is never
    # compared to a forward's when computing the league baseline.
    features = pd.DataFrame({
        "competition": ["A", "A", "A", "A"],
        "position_group": ["Defender", "Defender", "Forward", "Forward"],
        "shots_p90": [1.0, 3.0, 10.0, 30.0],
    })
    z = normalize_within_competition(features, ["shots_p90"], group_columns=("competition", "position_group"))

    # Defenders (1.0, 3.0) and forwards (10.0, 30.0) are each their own 2-player group -> the
    # lower player in each group gets the same (negative) z-score, unaffected by the other
    # group's much larger raw values.
    assert z.loc[0, "shots_p90_lz"] == pytest.approx(z.loc[2, "shots_p90_lz"])
    assert z.loc[1, "shots_p90_lz"] == pytest.approx(z.loc[3, "shots_p90_lz"])


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
