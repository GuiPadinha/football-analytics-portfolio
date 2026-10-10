"""Compare: any two outfielders (or any two goalkeepers), a verdict first, then side by side."""

import streamlit as st

from src.profile import build_compare_view, price_line
from views import components as ui
from views.data import load_pool, player_options

pool = load_pool()
labels, key_by_label = player_options()

st.html('<div style="height:12px"></div>' + ui.page_header(
    "COMPARE", "Two players, one verdict",
    "Any two outfield players, whatever their position, or any two goalkeepers.",
))
pick_a, pick_b = st.columns(2)
with pick_a:
    label_a = st.selectbox("Player A", labels, index=None, key="compare_pick_a", placeholder="Search player A…")
with pick_b:
    label_b = st.selectbox("Player B", labels, index=None, key="compare_pick_b", placeholder="Search player B…")

if not (label_a and label_b):
    st.info("Pick two players above to compare them.")
    st.stop()
if label_a == label_b:
    st.info("Pick two different players to compare.")
    st.stop()

try:
    view = build_compare_view(pool, key_by_label[label_a], key_by_label[label_b])
except ValueError:
    st.warning("A goalkeeper and an outfield player share no stats, so there is nothing to compare. Pick two of the same kind.")
    st.stop()

a, b = view.a, view.b
cards_a, cards_b = st.columns(2)
for column, side, color in ((cards_a, a, ui.BLUE), (cards_b, b, ui.ORANGE)):
    with column:
        st.html(ui.compare_card(
            side.name, f"{side.team} · {side.position_group} · {side.minutes:,.0f} min", price_line(side.market_value_eur), color,
        ))
st.html('<div style="height:18px"></div>' + ui.summary_panel(view.verdict, heading="VERDICT"))

st.html(ui.section_title("Side by side, per 90 minutes") + '<div style="height:12px"></div>' + ui.versus_rows(view.rows, a.name, b.name))
if a.position_group != b.position_group:
    st.caption("Different positions, so each stat is read against every outfield player in the player's own league.")

keepers = a.position_group == "Goalkeeper"
st.html(ui.section_title("How good is the shot-stopping?" if keepers else "Are their goals real?") + '<div style="height:12px"></div>')
result_a, result_b = st.columns(2)
for column, side, color in ((result_a, a, ui.BLUE), (result_b, b, ui.ORANGE)):
    with column:
        if keepers:
            st.html(ui.result_panel(f"{side.save_pct:.0%}", f"{side.name} saved {side.save_pct:.0%} of shots on target.", color))
        elif side.finishing is not None:
            gap = side.finishing.goals - side.finishing.expected_goals
            st.html(ui.result_panel(f"{gap:+.1f}".replace("-", "−"), f"{side.name}: {side.output_text}", color))
        else:
            st.html(ui.result_panel("n/a", f"No shot data for {side.name}: goals against chances is only available for the Premier League 2015/16.", color))
