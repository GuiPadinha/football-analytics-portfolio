"""The redesign's look: one stylesheet, small HTML builders, and the native shot map.

Pages call these instead of writing markup, so the palette lives in one place and matches
`.streamlit/config.toml`. Every dynamic string goes through `html.escape`. The builders return
strings (tested without Streamlit in tests/test_components.py); pages pass them to `st.html`.

Colour carries one meaning throughout: orange is "above" (strengths, goals, the closest match) and
blue is "below" (weaknesses, misses), and each pair also differs in lightness so it survives
colour-blindness.
"""

from html import escape

import altair as alt
import pandas as pd

BACKGROUND = "#0F1419"
PANEL = "#182028"
PANEL_RAISED = "#1C2630"
BORDER = "#243039"
TEXT = "#E8ECEF"
TEXT_MUTED = "#B9C4CC"
TEXT_FAINT = "#8494A0"
ORANGE = "#F28C38"
ORANGE_LIGHT = "#F5A15C"
BLUE = "#4C9BE8"
BLUE_LIGHT = "#7DB5EE"
PITCH_LINE = "#4A5A66"
# Pitch x (of 120) the shot map's view starts at, unless a shot came from further out.
FINAL_THIRD_START = 100

STYLESHEET = f"""
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="st-"], .stApp {{ font-family: 'IBM Plex Sans', sans-serif; }}
.block-container {{ max-width: 1200px; padding-top: 2.5rem; }}
.fap-display {{ font-family: 'Barlow Condensed', sans-serif; font-weight: 700; letter-spacing: 0.2px; }}
.fap-kicker {{ margin: 0; font-size: 13px; letter-spacing: 1.8px; font-weight: 600; color: {ORANGE_LIGHT}; text-transform: uppercase; }}
.fap-kicker.blue {{ color: {BLUE_LIGHT}; }}
.fap-h1 {{ margin: 6px 0 4px; font-size: clamp(44px, 7vw, 76px); line-height: 0.98; color: {TEXT}; }}
.fap-h2 {{ margin: 0; font-size: clamp(30px, 4vw, 40px); color: {TEXT}; }}
.fap-sub {{ margin: 6px 0 0; color: #9AA7B2; font-size: 15px; }}
.fap-muted {{ color: {TEXT_FAINT}; font-size: 13px; }}
.fap-panel {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; padding: 22px 24px; }}
.fap-summary {{ background: {PANEL_RAISED}; border: 1px solid #2C3A45; border-radius: 16px; padding: 26px 30px; }}
.fap-summary p {{ margin: 8px 0 0; font-size: clamp(18px, 2.2vw, 23px); line-height: 1.5; font-weight: 500; color: {TEXT}; }}
.fap-head {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 20px; }}
.fap-value {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; padding: 16px 22px; min-width: 210px; }}
.fap-value .figure {{ font-size: 44px; line-height: 1.1; }}
.fap-bar-row {{ margin-bottom: 16px; }}
.fap-bar-row .line {{ display: flex; justify-content: space-between; gap: 12px; font-size: 15px; color: {TEXT}; }}
.fap-track {{ height: 10px; background: {BORDER}; border-radius: 5px; overflow: hidden; margin: 6px 0 4px; }}
.fap-fill {{ height: 10px; border-radius: 5px; }}
.fap-tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1px; background: {BORDER}; border: 1px solid {BORDER}; border-radius: 14px; overflow: hidden; }}
.fap-tiles > div {{ background: {PANEL}; padding: 18px 24px; }}
.fap-tiles .figure {{ font-size: 52px; line-height: 1.05; }}
.fap-grid2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }}
.fap-card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; padding: 26px; display: flex; flex-direction: column; gap: 10px; height: 100%; box-sizing: border-box; }}
.fap-card .figure {{ font-size: clamp(40px, 5vw, 60px); line-height: 1; }}
.fap-card h3 {{ margin: 0; font-size: 21px; font-weight: 600; line-height: 1.3; color: {TEXT}; }}
.fap-card p.body {{ margin: 0; color: {TEXT_MUTED}; font-size: 15.5px; line-height: 1.55; }}
.fap-pill {{ background: #3A2A18; color: #FFC48F; font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: 999px; }}
.fap-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1px; background: {BORDER}; border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
.fap-strip > div {{ background: #131A21; padding: 20px 22px; }}
.fap-strip .figure {{ font-size: 38px; }}
.fap-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }}
.fap-steps > div {{ border-top: 2px solid #33424E; padding-top: 16px; }}
.fap-steps h4 {{ margin: 4px 0 6px; font-size: 18px; font-weight: 600; color: {TEXT}; }}
.fap-steps p {{ margin: 0; color: {TEXT_MUTED}; font-size: 15px; line-height: 1.55; }}
.fap-verdict {{ background: {PANEL_RAISED}; border: 1px solid #2C3A45; border-radius: 16px; padding: 26px 30px; }}
.fap-versus {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(120px, 190px) minmax(0, 1fr); gap: 14px; align-items: center; padding: 9px 0; border-bottom: 1px solid #1F2A33; font-size: 15px; }}
.fap-versus .label {{ text-align: center; color: {TEXT_MUTED}; }}
.fap-versus .side {{ display: flex; align-items: center; gap: 10px; }}
.fap-versus .side.a {{ justify-content: flex-end; }}
.fap-versus .bar {{ width: 70%; display: flex; }}
.fap-versus .side.a .bar {{ justify-content: flex-end; }}
.fap-versus .bar > div {{ height: 14px; border-radius: 4px; }}
@media (max-width: 640px) {{ .fap-versus {{ grid-template-columns: 1fr; text-align: center; }} .fap-versus .side.a {{ justify-content: center; }} }}
"""


def stylesheet_html():
    """The page-wide stylesheet, as a `<style>` element for `st.html`."""
    return f"<style>{STYLESHEET}</style>"


def page_header(kicker, title, sub, aside_html=""):
    """A page's top block: kicker, big name, a line of facts, and an optional right-hand card."""
    return (
        '<div class="fap-head"><div>'
        f'<p class="fap-kicker">{escape(kicker)}</p>'
        f'<h1 class="fap-display fap-h1">{escape(title)}</h1>'
        f'<p class="fap-sub">{escape(sub)}</p></div>{aside_html}</div>'
    )


def value_card(figure, caption, label="MARKET VALUE"):
    """The right-hand card of a player's header: a price, or why there isn't one."""
    return (
        '<div class="fap-value">'
        f'<div class="fap-muted" style="letter-spacing:1px">{escape(label)}</div>'
        f'<div class="fap-display figure" style="color:{TEXT}">{escape(figure)}</div>'
        f'<div class="fap-muted">{escape(caption)}</div></div>'
    )


def summary_panel(text, heading="THE SHORT VERSION"):
    """The highlighted paragraph at the top of a page."""
    return (
        f'<section class="fap-summary" aria-label="Summary"><p class="fap-kicker">{escape(heading)}</p>'
        f"<p>{escape(text)}</p></section>"
    )


def section_title(title, sub=""):
    """A numbered section heading with an optional one-line subtitle."""
    sub_html = f'<p class="fap-sub">{escape(sub)}</p>' if sub else ""
    return f'<div style="margin-top:40px"><h2 class="fap-display fap-h2">{escape(title)}</h2>{sub_html}</div>'


def bar_card(title, bars, color=ORANGE, light=ORANGE_LIGHT, empty="Nothing stands out here."):
    """A card of labelled bars: one row per `profile.StatBar` (label, rank, width, detail)."""
    rows = "".join(
        '<div class="fap-bar-row"><div class="line">'
        f'<span>{escape(bar.label)}</span><span style="color:{light};font-weight:600">{escape(bar.rank)}</span></div>'
        f'<div class="fap-track"><div class="fap-fill" style="width:{bar.width:.0f}%;background:{color}"></div></div>'
        f'<div class="fap-muted">{escape(bar.detail)}</div></div>'
        for bar in bars
    ) or f'<p class="fap-muted">{escape(empty)}</p>'
    return f'<div class="fap-panel"><h3 style="margin:0 0 16px;font-size:18px;font-weight:600">{escape(title)}</h3>{rows}</div>'


def tiles(items):
    """A row of big figures: `(label, figure, highlight)` per tile."""
    cells = "".join(
        f'<div><div style="color:#9AA7B2;font-size:14px">{escape(label)}</div>'
        f'<div class="fap-display figure" style="color:{ORANGE if highlight else TEXT}">{escape(figure)}</div></div>'
        for label, figure, highlight in items
    )
    return f'<div class="fap-tiles">{cells}</div>'


def strip(items):
    """The slim stats strip under the Home hero: `(figure, caption)` per cell."""
    cells = "".join(
        f'<div><div class="fap-display figure">{escape(figure)}</div>'
        f'<div style="color:#9AA7B2;font-size:14px">{escape(caption)}</div></div>'
        for figure, caption in items
    )
    return f'<div class="fap-strip" aria-label="What is in the data">{cells}</div>'


def finding_card(finding):
    """One Home card from a `findings.Finding` dict. Its link is a Streamlit button, drawn by the page."""
    blue = finding["tone"] == "down"
    accent = BLUE if blue else ORANGE
    return (
        f'<article class="fap-card"><p class="fap-kicker{" blue" if blue else ""}">{escape(finding["kicker"])}</p>'
        f'<div class="fap-display figure" style="color:{accent}">{escape(finding["figure"])}</div>'
        f'<h3>{escape(finding["headline"])}</h3><p class="body">{escape(finding["body"])}</p></article>'
    )


def steps(items):
    """The "how it works" row: `(number and name, question, text)` per step."""
    cells = "".join(
        f'<div><div class="fap-display" style="font-size:22px;color:{ORANGE_LIGHT}">{escape(name)}</div>'
        f"<h4>{escape(question)}</h4><p>{escape(text)}</p></div>"
        for name, question, text in items
    )
    return f'<div class="fap-steps">{cells}</div>'


def closeness_bar(fraction, color=ORANGE):
    """A thin bar for "how close": 0-1, the closest match being 1."""
    return (
        f'<div class="fap-track" role="img" aria-label="{fraction:.0%} as close as the closest match" '
        f'style="margin:14px 0"><div class="fap-fill" style="width:{fraction * 100:.0f}%;background:{color}"></div></div>'
    )


def compare_card(name, sub, value, color):
    """One side's header on Compare: the colour that runs through its bars, name, facts and price."""
    return (
        f'<div class="fap-panel" style="border-top:4px solid {color};display:flex;flex-wrap:wrap;justify-content:space-between;gap:14px">'
        f'<div><div class="fap-display" style="font-size:42px;line-height:1">{escape(name)}</div>'
        f'<div class="fap-sub">{escape(sub)}</div></div>'
        f'<div style="text-align:right"><div class="fap-display" style="font-size:38px;line-height:1">{escape(value)}</div>'
        '<div class="fap-muted">market value</div></div></div>'
    )


def result_panel(figure, text, color):
    """A big figure with its sentence: one side's finishing (or saves) on Compare."""
    return (
        f'<div class="fap-panel"><div class="fap-display" style="font-size:40px;color:{color}">{escape(figure)}</div>'
        f'<p style="margin:6px 0 0;font-size:16px;line-height:1.5">{escape(text)}</p></div>'
    )


def score_bars(rows, low=0.5, high=0.85, color=ORANGE):
    """Horizontal bars for scores between `low` and `high`, in the site's own bar style.

    Used for the shot model's ROC-AUC per tournament, where 0.5 is a coin flip: the bar starts
    there, so its length is the skill above chance. Drawn as HTML rather than a Vega chart because
    a Vega chart with long category labels rendered shifted off-screen in Streamlit (2026-10-10).

    Args:
        rows (list[tuple[str, float, str]]): `(label, score, note)`, drawn in the order given.
        low, high (float): the scores at the empty and the full bar.
    """
    body = "".join(
        '<div class="fap-bar-row"><div class="line">'
        f'<span>{escape(label)}</span><span style="font-weight:600">{score:.3f}</span></div>'
        f'<div class="fap-track"><div class="fap-fill" style="width:{max(0.0, min(1.0, (score - low) / (high - low))) * 100:.0f}%;'
        f'background:{color}"></div></div><div class="fap-muted">{escape(note)}</div></div>'
        for label, score, note in rows
    )
    return f'<div class="fap-panel">{body}</div>'


def pill(text):
    """The small "Cheaper" tag."""
    return f'<span class="fap-pill">{escape(text)}</span>'


def versus_rows(rows, name_a, name_b):
    """Compare's side-by-side: one row per `profile.CompareRow`, A's bar growing left, B's right."""
    def side(css, text, width, color, bold):
        weight = 600 if bold else 400
        number = f'<span style="font-weight:{weight}">{escape(text)}</span>'
        bar = f'<div class="bar"><div style="width:{width:.0f}%;background:{color}"></div></div>'
        return f'<div class="side {css}">{number}{bar}</div>' if css == "a" else f'<div class="side {css}">{bar}{number}</div>'

    legend = (
        '<div style="display:flex;gap:20px;flex-wrap:wrap;color:#B9C4CC;font-size:14px;margin-bottom:6px">'
        f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:{BLUE};margin-right:8px"></span>{escape(name_a)}</span>'
        f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:{ORANGE};margin-right:8px"></span>{escape(name_b)}</span></div>'
    )
    body = "".join(
        '<div class="fap-versus">'
        + side("a", row.a_text, row.a_width, BLUE, row.leader == "a")
        + f'<span class="label">{escape(row.label)}</span>'
        + side("b", row.b_text, row.b_width, ORANGE, row.leader == "b")
        + "</div>"
        for row in rows
    )
    return f'<div class="fap-panel">{legend}{body}</div>'


def shot_map(shots):
    """A half-pitch shot map: every shot sized by its chance of scoring, goals in orange.

    Native Altair, so it scales with the page and shows a tooltip, instead of the old Matplotlib
    image. StatsBomb pitch coordinates (120 x 80, attacking toward x = 120) are drawn with the goal
    at the top.

    Args:
        shots (pandas.DataFrame): `x`, `y`, `predicted_xg`, `is_goal`, `minute`, `shot_body_part`.

    Returns:
        altair.LayerChart
    """
    data = pd.DataFrame({
        "side": shots["y"], "depth": shots["x"], "xg": shots["predicted_xg"],
        "Outcome": shots["is_goal"].map({True: "Goal", False: "No goal"}),
        "Minute": shots["minute"], "Body part": shots["shot_body_part"],
        "Chance of scoring": (shots["predicted_xg"] * 100).round(0).astype(int).astype(str) + "%",
    })
    # Crop to where this player shoots from, in steps of 5, so the map isn't mostly empty grass.
    bottom = float(min(FINAL_THIRD_START, 5 * (shots["x"].min() // 5)))
    # (left, right, bottom, top) in pitch coordinates: the pitch, the penalty area, the six-yard box.
    lines = pd.DataFrame(
        [(0, 80, bottom, 120), (18, 62, 102, 120), (30, 50, 114, 120)],
        columns=["left", "right", "bottom", "top"],
    )
    x_scale = alt.Scale(domain=[-2, 82], nice=False)
    y_scale = alt.Scale(domain=[bottom - 1, 122], nice=False)
    pitch = alt.Chart(lines).mark_rect(fill=None, stroke=PITCH_LINE, strokeWidth=1.5).encode(
        x=alt.X("left:Q", scale=x_scale, axis=None), x2="right:Q",
        y=alt.Y("bottom:Q", scale=y_scale, axis=None), y2="top:Q",
    )
    goal = alt.Chart(pd.DataFrame({"left": [36], "right": [44], "bottom": [120], "top": [121.5]})).mark_rect(
        fill=None, stroke=TEXT_FAINT, strokeWidth=2
    ).encode(x=alt.X("left:Q", scale=x_scale, axis=None), x2="right:Q",
             y=alt.Y("bottom:Q", scale=y_scale, axis=None), y2="top:Q")
    points = alt.Chart(data).mark_circle(stroke=BACKGROUND, strokeWidth=0.8).encode(
        x=alt.X("side:Q", scale=x_scale, axis=None),
        y=alt.Y("depth:Q", scale=y_scale, axis=None),
        size=alt.Size("xg:Q", scale=alt.Scale(domain=[0, 1], range=[40, 900]), legend=None),
        color=alt.Color("Outcome:N", scale=alt.Scale(domain=["Goal", "No goal"], range=[ORANGE, BLUE]),
                        legend=alt.Legend(title=None, orient="bottom")),
        opacity=alt.condition(alt.datum.Outcome == "Goal", alt.value(1.0), alt.value(0.55)),
        tooltip=["Outcome", "Chance of scoring", "Minute", "Body part"],
    )
    return (pitch + goal + points).properties(height=360).configure_view(stroke=None)
