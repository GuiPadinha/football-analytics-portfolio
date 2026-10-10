"""Smoke tests for the app via Streamlit's headless AppTest harness.

Runs the real `app.py` (top navigation, file-based pages under `views/`) against the committed
`app_data/` and fails on any exception, on every page and for each kind of player: a star with
xG, an outfield player without xG, a goalkeeper, and a women's-league player with no price. It
checks that pages render and say the right things, not what they look like: visual checks need a
real browser (docs/ML_TOOLING.md).
"""

from pathlib import Path

import pandas as pd
import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(REPO_ROOT / "app.py")
TIMEOUT_SECS = 180
PAGES = ["home", "players", "compare", "leaderboard", "how_it_works"]

MAHREZ = ("Riyad Mahrez", "Leicester City")
MESSI = ("Lionel Andrés Messi Cuccittini", "Barcelona")  # outside the xG set: no shots
EARPS = ("Mary Alexandra Earps", "Manchester United W")


def _run(page=None):
    at = streamlit_testing.AppTest.from_file(APP_PATH, default_timeout=TIMEOUT_SECS)
    at.run()
    if page:
        at.switch_page(f"views/{page}.py").run()
    return at


def _assert_clean(at):
    assert not at.exception, [e.message for e in at.exception]


def _open_player(key):
    at = _run("players")
    at.session_state["selected_player"] = key
    at.run()
    _assert_clean(at)
    return at


def _html(at):
    return " ".join(element.proto.body for element in at.get("html"))


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_exceptions(page):
    _assert_clean(_run(None if page == "home" else page))


def test_player_page_without_a_selection_offers_starting_points():
    at = _run("players")
    _assert_clean(at)
    assert len(at.button) >= 4


@pytest.mark.parametrize("key", [MAHREZ, MESSI, EARPS])
def test_player_page_renders_each_kind_of_player(key):
    at = _open_player(key)
    html = _html(at)
    assert "THE SHORT VERSION" in html
    assert "What kind of player is this?" in html


def test_a_star_with_xg_shows_finishing_and_a_native_shot_map():
    at = _open_player(MAHREZ)
    assert "Are the goals real?" in _html(at)
    assert len(at.get("vega_lite_chart")) == 1


def test_an_outfield_player_without_xg_says_why_instead_of_faking_it():
    at = _open_player(MESSI)
    html = _html(at)
    assert "only available for the Premier League 2015/16" in html
    assert not at.get("vega_lite_chart")


def test_a_goalkeeper_gets_saves_not_goals():
    html = _html(_open_player(EARPS))
    assert "How good is the shot-stopping?" in html
    assert "Are the goals real?" not in html
    assert "Not on record" in html


def test_clicking_a_lookalike_jumps_to_that_player():
    at = _open_player(MAHREZ)
    button = next(b for b in at.button if b.key.startswith("look_male_1_"))
    button.click().run()
    _assert_clean(at)
    assert at.session_state["selected_player"] != MAHREZ
    assert "THE SHORT VERSION" in _html(at)


def test_the_home_search_opens_the_players_page():
    at = _run()
    at.selectbox(key="home_search").set_value("Riyad Mahrez (Leicester City) · Premier League 2015/16").run()
    _assert_clean(at)
    assert at.session_state["selected_player"] == MAHREZ


def test_every_search_label_is_unique():
    from views.data import player_options  # noqa: F401  (imports Streamlit caching only)

    per90 = pd.read_parquet(REPO_ROOT / "app_data" / "player_per90.parquet")
    labels, key_by_label = _labels(per90)
    assert len(labels) == len(per90) == len(key_by_label)


def _labels(per90):
    from src.profile import display_name

    key_by_label = {
        f"{display_name(row)} ({row['team']}) · {row['competition']}": (row["player"], row["team"])
        for _, row in per90.iterrows()
    }
    return sorted(key_by_label), key_by_label
