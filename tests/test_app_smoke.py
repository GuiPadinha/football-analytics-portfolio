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


def _compare(label_a, label_b):
    at = _run("compare")
    at.selectbox(key="compare_pick_a").set_value(label_a).run()
    at.selectbox(key="compare_pick_b").set_value(label_b).run()
    return at


KANE = "Harry Kane (Tottenham Hotspur) · Premier League 2015/16"
VARDY = "Jamie Vardy (Leicester City) · Premier League 2015/16"
COUTINHO = "Philippe Coutinho (Liverpool) · Premier League 2015/16"
ZAHA = "Wilfried Zaha (Crystal Palace) · Premier League 2015/16"
EARPS_LABEL = "Mary Alexandra Earps (Manchester United W) · FA Women's Super League 2023/24"


def test_compare_gives_a_verdict_for_a_same_position_and_a_cross_position_pair():
    for pair in ((KANE, VARDY), (COUTINHO, ZAHA)):
        at = _compare(*pair)
        _assert_clean(at)
        assert "VERDICT" in _html(at)
    assert "Not a like-for-like swap" in _html(at)


def test_compare_refuses_a_keeper_against_an_outfielder_without_crashing():
    at = _compare(KANE, EARPS_LABEL)
    _assert_clean(at)
    assert any("share no stats" in w.value for w in at.warning)


def test_compare_prompts_until_two_different_players_are_picked():
    at = _run("compare")
    assert any("Pick two players" in i.value for i in at.info)
    at.selectbox(key="compare_pick_a").set_value(KANE).run()
    at.selectbox(key="compare_pick_b").set_value(KANE).run()
    assert any("two different players" in i.value for i in at.info)


def test_the_compare_button_on_a_player_page_prefills_player_a():
    at = _open_player(MAHREZ)
    next(b for b in at.button if "with another player" in b.label).click().run()
    _assert_clean(at)
    assert "Riyad Mahrez" in at.selectbox(key="compare_pick_a").value


def test_leaderboard_filters_by_game_and_name():
    at = _run("leaderboard")
    _assert_clean(at)
    total = len(at.dataframe[0].value)
    at.text_input(key="board_name").set_value("Mahrez").run()
    _assert_clean(at)
    assert 0 < len(at.dataframe[0].value) < total
    assert any("Riyad Mahrez" in str(name) for name in at.dataframe[0].value["Player"])
    at.text_input(key="board_name").set_value("zzzz-no-one").run()
    assert any("No players match" in w.value for w in at.warning)


def test_how_it_works_quotes_the_numbers_from_metrics_json():
    import json

    metrics = json.loads((REPO_ROOT / "metrics.json").read_text(encoding="utf-8"))
    at = _run("how_it_works")
    _assert_clean(at)
    text = " ".join(m.value for m in at.markdown)
    assert str(metrics["xg"]["logistic"]["test_roc_auc"]) in text
    assert f"{metrics['xg']['n_train_shots']:,} shots" in text


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
