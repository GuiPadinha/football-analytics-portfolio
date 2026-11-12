"""Build a player: set a style with sliders and see who plays like it. A toy, and labelled so.

The one page where the numbers are typed in rather than measured: a semi-pro has no event data.
The matching itself is the real one (`profile.build_your_own` ranks with the same code as the
player pages' lookalikes), on StatsBomb's outfield pool, the one with both games on the same stats.
"""

from html import escape

import streamlit as st

from src.narrative import GAME_WORDS, GROUP_PLURALS
from src.presentation import STAT_LABELS, feature_columns_for, format_market_value
from src.profile import BUILD_GROUPS, build_your_own, find_player
from views import components as ui
from views.data import load_pool, open_player, player_options

pool = load_pool()
_, STATS, _ = feature_columns_for("Forward", "statsbomb")   # the same 11 stats for every outfield group
outfield = pool.per90[(pool.per90["provider"] == "statsbomb") & pool.per90["position_group"].isin(BUILD_GROUPS)]
_, key_by_label = player_options()
label_by_key = {key: label for label, key in key_by_label.items()}
start_labels = sorted(label_by_key[(row.player, row.team)] for row in outfield.itertuples())


def _slider_key(stat):
    return f"build_{stat}"


def _start_from_player():
    """Start-box callback: put the sliders and the position where the chosen player stands."""
    label = st.session_state.get("build_start")
    if not label:
        return
    row = find_player(pool, *key_by_label[label])
    standing = pool.percentiles[("statsbomb", row["position_group"])].loc[row.name]
    st.session_state["build_group"] = row["position_group"]
    for stat in STATS:
        st.session_state[_slider_key(stat)] = int(round(standing[stat] * 100))


def _reset():
    st.session_state["build_start"] = None
    for stat in STATS:
        st.session_state[_slider_key(stat)] = 50


for stat in STATS:
    st.session_state.setdefault(_slider_key(stat), 50)
st.session_state.setdefault("build_group", "Forward")

st.html('<div style="height:12px"></div>' + ui.page_header(
    "BUILD A PLAYER", "Who plays like you?",
    "A toy, and the one page where the numbers are made up: set a style with the sliders, and the app finds the "
    "real players closest to it, with the same matching as every player page.",
))

group_col, start_col, reset_col = st.columns([2.2, 3.4, 1], vertical_alignment="bottom")
with group_col:
    group = st.segmented_control("Position", BUILD_GROUPS, key="build_group", required=True)
with start_col:
    st.selectbox("Start from a real player (optional)", start_labels, index=None, key="build_start",
                 placeholder="e.g. Riyad Mahrez, then add tackles…", on_change=_start_from_player)
with reset_col:
    st.button("Reset", on_click=_reset, width="stretch")

st.caption("Each slider is a standing within the league: 50 is the median player in that position, "
           "90 means better than nine in ten of them.")
columns = st.columns(3)
for i, stat in enumerate(STATS):
    with columns[i % 3]:
        st.slider(STAT_LABELS[stat], 0, 100, key=_slider_key(stat), step=5)

start = st.session_state.get("build_start")
started_from = key_by_label[start] if start else None
standing = {stat: st.session_state[_slider_key(stat)] / 100 for stat in STATS}
lists = build_your_own(pool, group, standing, exclude=started_from)

closest = {game: matches[0] for game, matches in lists.items() if matches}
summary = (f"Among {GROUP_PLURALS[group]}, the closest real player is {closest['male'].name} "
           f"({closest['male'].team}, {closest['male'].competition}) in the men's game, and "
           f"{closest['female'].name} ({closest['female'].team}, {closest['female'].competition}) in the women's.")
if started_from:
    summary += f" {start.split(' (')[0]}'s own season is left off the lists."
st.html('<div style="height:12px"></div>' + ui.summary_panel(summary, heading="YOUR PLAYER"))

st.html(ui.section_title("Who plays like this?", "Closest real players, each judged against their own league"))
tabs = st.tabs([f"{GAME_WORDS[game].capitalize()} game" for game in ("male", "female")])
for tab, game in zip(tabs, ("male", "female")):
    with tab:
        color = ui.ORANGE if game == "male" else ui.BLUE
        widths = [0.5, 2.4, 2.8, 2.4, 1.5]
        header = st.columns(widths)
        for column, text in zip(header, ("#", "PLAYER", "CLUB AND LEAGUE", "HOW CLOSE", "VALUE")):
            column.html(f'<span class="fap-muted" style="letter-spacing:1px">{text}</span>')
        for rank, match in enumerate(lists[game], start=1):
            number, name, league, close, value = st.columns(widths, vertical_alignment="center")
            number.html(f'<span class="fap-display" style="font-size:24px;color:{ui.TEXT_FAINT}">{rank}</span>')
            with name:
                if st.button(match.name, key=f"build_look_{game}_{rank}", type="tertiary"):
                    open_player((match.player, match.team))
                    st.switch_page("views/players.py")
            league.html(
                f'<div style="color:{ui.TEXT_MUTED};font-size:14px;line-height:1.35">{escape(match.team)}<br>'
                f'<span class="fap-muted">{escape(match.competition)}</span></div>'
            )
            close.html(ui.closeness_bar(match.closeness, color))
            value.html(f'<div style="text-align:right;font-weight:600">{format_market_value(match.market_value_eur) or "n/a"}</div>')
st.caption("StatsBomb's full league seasons only (men's 2015/16, women's 2023/24), where both games are counted "
           "on the same stats. Bar length: how close each profile is, relative to the closest match.")
