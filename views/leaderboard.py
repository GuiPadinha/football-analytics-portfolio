"""Leaderboard: everyone in one sortable table, for browsing and spotting outliers."""

import streamlit as st

from src.profile import build_leaderboard
from views.data import load_pool, load_xg_table, open_player

pool = load_pool()
board = build_leaderboard(pool, load_xg_table())

st.html('<div style="height:12px"></div><p class="fap-kicker">LEADERBOARD</p>'
        '<h1 class="fap-display fap-h1" style="font-size:clamp(40px,6vw,64px)">Everyone, in one table</h1>'
        '<p class="fap-sub">Click a column to sort and a row to open the player. Blank means not available, never guessed.</p>')

game_col, position_col, name_col = st.columns([1.3, 2, 2])
with game_col:
    game = st.segmented_control("Game", ["Men's", "Women's"], default=None, key="board_game")
with position_col:
    positions = sorted(board["Position"].unique())
    position = st.multiselect("Position", positions, default=positions, key="board_position")
with name_col:
    query = st.text_input("Name contains (press Enter)", key="board_name")

shown = board[board["Position"].isin(position)]
if game:
    shown = shown[shown["Game"] == game]
if query:
    shown = shown[shown["Player"].str.contains(query, case=False, regex=False)]
shown = shown.sort_values("Goals", ascending=False, na_position="last").reset_index(drop=True)

if shown.empty:
    st.warning("No players match these filters.")
    st.stop()
st.caption(f"{len(shown):,} of {len(board):,} players")

event = st.dataframe(
    shown[["Player", "Team", "League", "Position", "Minutes", "Goals", "Assists", "Goals − xG", "Value (€M)"]],
    hide_index=True, width="stretch", placeholder="", on_select="rerun", selection_mode="single-row",
    key=f"board_table_{game}_{'-'.join(position)}_{query}",
    column_config={
        "Minutes": st.column_config.NumberColumn(format="%d"),
        "Goals": st.column_config.NumberColumn(format="%d", help="Includes penalties. Blank for goalkeepers."),
        "Assists": st.column_config.NumberColumn(format="%d", help="Blank for goalkeepers."),
        "Goals − xG": st.column_config.NumberColumn(
            format="%+.1f",
            help="Goals minus the goals the shots were worth. Premier League 2015/16 only, the one competition with shot-by-shot data.",
        ),
        "Value (€M)": st.column_config.NumberColumn(
            format="€%.1fM", help="Transfermarkt, around the 2015/16 season. Men's leagues only; blank where there is no confident match.",
        ),
    },
)
if event and event.selection["rows"]:
    row = shown.iloc[event.selection["rows"][0]]
    open_player((row["player"], row["team"]))
    st.switch_page("views/players.py")
