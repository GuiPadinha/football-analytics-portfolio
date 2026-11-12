"""Compare: any two outfielders (or any two goalkeepers), a verdict first, then side by side."""

import streamlit as st

from src.profile import build_compare_view, price_line
from views import components as ui
from views.data import label_of, link_params, linked_player, load_pool, player_options, read_link

pool = load_pool()
labels, key_by_label = player_options()

# A link to a comparison ("?player_a=Harry Kane&player_b=Jamie Vardy") fills the two boxes. As on
# the Players page it is followed once, and the address then mirrors the boxes.
link = read_link("_a") + read_link("_b")
if any(link) and link != st.session_state.get("compare_link"):
    st.session_state["compare_link"] = link
    for side, wanted in (("a", link[:3]), ("b", link[3:])):
        key = linked_player(wanted)
        if key:
            st.session_state[f"compare_pick_{side}"] = label_of(key)

st.html('<div style="height:12px"></div>' + ui.page_header(
    "COMPARE", "Two players, one verdict",
    "Any two outfield players, whatever their position, or any two goalkeepers, from the same data provider.",
))
pick_a, pick_b = st.columns(2)
with pick_a:
    label_a = st.selectbox("Player A", labels, index=None, key="compare_pick_a", placeholder="Search player A…")
with pick_b:
    label_b = st.selectbox("Player B", labels, index=None, key="compare_pick_b", placeholder="Search player B…")

address = {}
for side, label in (("a", label_a), ("b", label_b)):
    if label:
        address.update(link_params(key_by_label[label], suffix=f"_{side}"))
st.query_params.from_dict(address)
st.session_state["compare_link"] = read_link("_a") + read_link("_b")

if not (label_a and label_b):
    st.info("Pick two players above to compare them.")
    st.stop()
if label_a == label_b:
    st.info("Pick two different players to compare.")
    st.stop()

try:
    view = build_compare_view(pool, key_by_label[label_a], key_by_label[label_b])
except ValueError as refusal:  # keeper vs outfielder, or two providers: the message is page-ready
    st.warning(str(refusal))
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
if not keepers and a.finishing is None and b.finishing is None:
    # Two "n/a" panels side by side said nothing twice: one sentence instead.
    st.html(
        '<div class="fap-panel"><p style="margin:0;font-size:17px;line-height:1.55">No shot data for either player: '
        "goals against chances is only available for the Premier League 2015/16, the one competition with "
        "shot-by-shot data behind the model.</p></div>"
    )
    st.stop()
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
