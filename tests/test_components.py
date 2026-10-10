"""Tests for views/components.py: the HTML builders escape what they are given, and the shot map
crops to where the shots are."""

import pandas as pd

from src.profile import CompareRow, StatBar
from views import components as ui


def test_builders_escape_dynamic_text():
    bar = StatBar("<script>x</script>", "Top 1%", 99.0, "a & b")
    html = ui.bar_card("<b>Title</b>", [bar])
    assert "<script>" not in html and "<b>Title" not in html
    assert "&lt;script&gt;" in html and "a &amp; b" in html
    assert "&lt;i&gt;" in ui.summary_panel("<i>hi</i>")
    assert "&amp;" in ui.page_header("A & B", "C & D", "E & F")


def test_an_empty_bar_card_says_so():
    assert "Nothing stands out" in ui.bar_card("More", [])


def test_versus_rows_bold_only_the_leader_and_name_both_sides():
    rows = [CompareRow("Shots", "4.75", "1.15", 100.0, 24.2, "a")]
    html = ui.versus_rows(rows, "Coutinho", "Zaha")
    assert "Coutinho" in html and "Zaha" in html and "font-weight:600\">4.75" in html
    assert "font-weight:400\">1.15" in html


def _shots(xs):
    return pd.DataFrame({
        "x": xs, "y": [40.0] * len(xs), "predicted_xg": [0.1] * len(xs), "is_goal": [False] * len(xs),
        "minute": [10] * len(xs), "shot_body_part": ["Right Foot"] * len(xs),
    })


def test_shot_map_crops_to_the_shots_but_never_cuts_one_off():
    near = ui.shot_map(_shots([108.0, 112.0])).to_dict()
    far = ui.shot_map(_shots([108.0, 72.0])).to_dict()
    near_domain = near["layer"][0]["encoding"]["y"]["scale"]["domain"]
    far_domain = far["layer"][0]["encoding"]["y"]["scale"]["domain"]
    assert near_domain[0] > far_domain[0]
    assert far_domain[0] < 72
    assert near_domain[0] <= 108


def test_score_bars_start_at_the_coin_flip_and_clamp():
    html = ui.score_bars([("A & B", 0.675, "n"), ("floor", 0.4, "n"), ("ceiling", 0.99, "n")])
    assert "width:50%" in html            # halfway between 0.5 and 0.85
    assert "width:0%" in html and "width:100%" in html
    assert "A &amp; B" in html and "0.675" in html
