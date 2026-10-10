"""Tests for src/profile.py and src/findings.py against the committed app tables.

The pages are thin layouts over these view models, so what a reader sees is pinned here on real
players: a star with xG, a keeper, a women's-league player without a price, and the refusals.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.findings import FINDINGS_PATH, MIN_SHOTS_FOR_FINISHING_CARD
from src.profile import (
    LOOKALIKES_PER_GAME,
    build_compare_view,
    build_leaderboard,
    build_player_profile,
    find_player,
    market_value_of,
    prepare_pool,
)

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"
MAHREZ = ("Riyad Mahrez", "Leicester City")
EARPS = ("Mary Alexandra Earps", "Manchester United W")
PAJOR = ("Ewa Pajor", "VfL Wolfsburg WFC")


@pytest.fixture(scope="module")
def pool():
    read = lambda name: pd.read_parquet(APP_DATA_DIR / f"{name}.parquet")  # noqa: E731
    return prepare_pool(read("player_per90"), read("shots_with_xg"), read("market_value"))


def test_prepare_pool_adds_each_players_game_and_ranks_every_group(pool):
    assert set(pool.per90["gender"]) == {"male", "female"}
    assert set(pool.percentiles) == {"Defender", "Midfielder", "Forward", "Goalkeeper"}
    forwards = pool.per90["position_group"] == "Forward"
    assert pool.percentiles["Forward"].index.equals(pool.per90.index[forwards])
    assert pool.percentiles["Forward"].max().max() == 1.0


def test_a_star_with_xg_gets_every_section(pool):
    profile = build_player_profile(pool, *MAHREZ)
    assert profile.name == "Riyad Mahrez"
    assert profile.finishing.goals == 17 and profile.finishing.expected_goals == pytest.approx(12.5, abs=0.1)
    assert len(profile.shots) == 87
    assert profile.strengths and profile.weaknesses
    assert all(bar.rank.startswith("Top ") for bar in profile.strengths)
    assert all(bar.rank.startswith("Bottom ") for bar in profile.weaknesses)
    assert [bar.width for bar in profile.strengths] == sorted((bar.width for bar in profile.strengths), reverse=True)
    assert profile.short_version.startswith("A scorer and dribbler")
    assert profile.market_value_eur == 20_000_000


def test_lookalike_lists_are_per_game_ordered_and_flag_cheaper_players(pool):
    profile = build_player_profile(pool, *MAHREZ)
    for gender, matches in profile.lookalikes.items():
        assert len(matches) == LOOKALIKES_PER_GAME
        assert [m.distance for m in matches] == sorted(m.distance for m in matches)
        assert all(pool.per90[(pool.per90.player == m.player) & (pool.per90.team == m.team)].gender.iloc[0] == gender
                   for m in matches)
    assert all(0 < m.closeness <= 1 for ms in profile.lookalikes.values() for m in ms)
    assert any(m.closeness == 1.0 for ms in profile.lookalikes.values() for m in ms)
    cheaper = {m.name for m in profile.lookalikes["male"] if m.cheaper}
    assert {"José Luis Morales", "Ousmane Dembélé"} <= cheaper
    assert all(m.market_value_eur is None for m in profile.lookalikes["female"])


def test_a_keeper_gets_saves_instead_of_finishing(pool):
    profile = build_player_profile(pool, *EARPS)
    assert profile.finishing is None and profile.goals is None and profile.shots.empty
    assert profile.saves.save_pct == pytest.approx(0.67, abs=0.01)
    assert "Saved 67% of 90 shots on target" in profile.short_version
    assert profile.market_value_eur is None


def test_a_womens_player_has_no_price_and_closes_on_the_closest_matches(pool):
    profile = build_player_profile(pool, *PAJOR)
    assert profile.market_value_eur is None and profile.finishing is None
    assert profile.short_version.endswith("in the men's game, Karim Benzema.")


def test_unknown_players_are_refused(pool):
    with pytest.raises(ValueError):
        find_player(pool, "Nobody", "Nowhere")
    with pytest.raises(ValueError):
        build_player_profile(pool, "Nobody", "Nowhere")
    assert market_value_of(pool, "Nobody", "Nowhere") == (None, None, None)


def test_compare_view_has_a_verdict_and_one_row_per_stat(pool):
    view = build_compare_view(pool, ("Philippe Coutinho Correia", "Liverpool"), ("Wilfried Zaha", "Crystal Palace"))
    assert view.verdict.startswith("Not a like-for-like swap")
    assert len(view.rows) == 11
    assert all(max(row.a_width, row.b_width) == 100.0 for row in view.rows if row.a_text != "0")
    assert view.a.finishing is not None and view.b.output_text is not None


def test_compare_leader_flips_for_goals_conceded(pool):
    keepers = pool.per90[pool.per90.position_group == "Goalkeeper"]
    ordered = keepers.sort_values("goals_conceded_p90")
    one, two = ordered.iloc[0], ordered.iloc[-1]
    view = build_compare_view(pool, (one.player, one.team), (two.player, two.team))
    conceded = next(row for row in view.rows if row.label == "Goals Conceded")
    assert conceded.leader == "a"                                     # fewer conceded wins
    assert view.a.save_pct is not None


def test_compare_refuses_a_keeper_against_an_outfielder(pool):
    with pytest.raises(ValueError, match="share no stats"):
        build_compare_view(pool, EARPS, MAHREZ)


def test_findings_file_matches_the_tables(pool):
    findings = {f["kind"]: f for f in json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))}
    assert list(findings) == ["overperformer", "underperformer", "price", "cross_game"]
    xg = pd.read_parquet(APP_DATA_DIR / "player_xg_table.parquet")
    regulars = xg[xg["shots"] >= MIN_SHOTS_FOR_FINISHING_CARD]
    for kind, pick in (("overperformer", regulars["xg_diff"].idxmax()), ("underperformer", regulars["xg_diff"].idxmin())):
        assert findings[kind]["player"] == regulars.loc[pick, "player"]
        assert abs(float(findings[kind]["figure"].replace("−", "-").split()[0])) == pytest.approx(abs(regulars.loc[pick, "xg_diff"]), abs=0.05)
    man = find_player(pool, findings["cross_game"]["player"], findings["cross_game"]["team"])
    assert man["gender"] == "male"
    assert f"{len(pool.per90):,} players" in findings["cross_game"]["body"]
    assert 0.5 < float(findings["price"]["figure"].rstrip("%")) / 100 <= 1.0


def test_leaderboard_has_one_row_per_player_and_blanks_what_does_not_apply(pool):
    xg = pd.read_parquet(APP_DATA_DIR / "player_xg_table.parquet")
    board = build_leaderboard(pool, xg)
    assert len(board) == len(pool.per90) and not board.duplicated(["player", "team"]).any()
    keepers = board[board["Position"] == "Goalkeeper"]
    assert keepers["Goals"].isna().all() and keepers["Assists"].isna().all()
    assert board.loc[board["Game"] == "Women's", "Value (€M)"].isna().all()
    # Only shooters with enough minutes to be in the pool (900+) get a row.
    assert board["Goals − xG"].notna().sum() == len(xg.merge(pool.per90[["player", "team"]]))
    assert board.loc[board["player"] == "Riyad Mahrez", "Value (€M)"].iloc[0] == 20.0
    assert set(board["Game"]) == {"Men's", "Women's"}
