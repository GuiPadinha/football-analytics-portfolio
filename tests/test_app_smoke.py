"""Smoke tests for app.py via Streamlit's headless AppTest harness.

Runs the real script against the committed `app_data/` artifacts and fails on any exception, in
every view and for both feature sets (outfield + goalkeeper). This is the harness earlier
sessions ran by hand before each change; committing it means CI catches a broken page before
the deployed app does. It checks that pages render, not what they look like — visual checks
still need a real browser (see docs/ML_TOOLING.md).
"""

from pathlib import Path

import pandas as pd
import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(REPO_ROOT / "app.py")
TIMEOUT_SECS = 120


def _label(per90, player, team):
    row = per90[(per90["player"] == player) & (per90["team"] == team)].iloc[0]
    return f"{row['player']} ({row['team']}) · {row['competition']}"


@pytest.fixture(scope="module")
def per90():
    return pd.read_parquet(REPO_ROOT / "app_data" / "player_per90.parquet")


def _run(view=None):
    at = streamlit_testing.AppTest.from_file(APP_PATH, default_timeout=TIMEOUT_SECS)
    at.run()
    if view is not None:
        at.sidebar.radio(key="view_radio").set_value(view).run()
    return at


def _assert_clean(at):
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("view", [None, "Leaderboard", "Compare players", "About & Roadmap"])
def test_every_view_renders_without_exceptions(view):
    _assert_clean(_run(view))


@pytest.mark.parametrize(
    "player, team",
    [
        ("Harry Kane", "Tottenham Hotspur"),  # in the xG training set: Finishing panel + shot map
        ("Lionel Andrés Messi Cuccittini", "Barcelona"),  # outside it: "no logged shots" fallback
    ],
)
def test_player_explorer_renders_an_outfield_player(per90, player, team):
    at = _run()
    at.selectbox(key="player_pick_All_All").set_value(_label(per90, player, team)).run()
    _assert_clean(at)
    assert any(player in h.value for h in at.title)


def test_player_explorer_renders_a_goalkeeper(per90):
    keeper = per90[per90["position_group"] == "Goalkeeper"].iloc[0]
    at = _run()
    at.selectbox(key="player_pick_All_All").set_value(
        _label(per90, keeper["player"], keeper["team"])
    ).run()
    _assert_clean(at)
    assert any("Save %" in c.value for c in at.caption)


def test_similar_player_jump_lands_on_the_target_page(per90):
    at = _run()
    at.session_state["jump_to_player"] = ("Jamie Vardy", "Leicester City")
    at.run()
    _assert_clean(at)
    assert any("Jamie Vardy" in h.value for h in at.title)


def test_compare_players_same_and_cross_position(per90):
    at = _run("Compare players")
    at.selectbox(key="compare_pick_a").set_value(
        _label(per90, "Harry Kane", "Tottenham Hotspur")
    ).run()
    at.selectbox(key="compare_pick_b").set_value(
        _label(per90, "Jamie Vardy", "Leicester City")
    ).run()
    _assert_clean(at)

    keeper = per90[per90["position_group"] == "Goalkeeper"].iloc[0]
    at.selectbox(key="compare_pick_b").set_value(
        _label(per90, keeper["player"], keeper["team"])
    ).run()
    _assert_clean(at)
