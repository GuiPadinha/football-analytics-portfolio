"""Home: what the data says first, the method last."""

import streamlit as st

from views import components as ui
from views.data import load_findings, load_metrics, load_pool, open_player, player_options

pool = load_pool()
metrics = load_metrics()
labels, key_by_label = player_options()
per90 = pool.per90
games = per90.drop_duplicates("competition").groupby("gender").size().to_dict()

st.html(
    '<p class="fap-kicker" style="margin-top:28px">RECRUITMENT ANALYTICS · '
    f'{per90["competition"].nunique()} LEAGUES · {len(per90):,} PLAYERS</p>'
    '<h1 class="fap-display fap-h1" style="max-width:900px">Scout by data,<br>not by reputation.</h1>'
    '<p style="font-size:20px;line-height:1.5;color:#B9C4CC;max-width:760px;margin:14px 0 8px">'
    "Pick a player and get three answers: what kind of player this is, whether the goals are real, "
    "and who plays like this for less.</p>"
)
choice = st.selectbox(
    "Search a player", labels, index=None, key="home_search", label_visibility="collapsed",
    placeholder="Search a player, e.g. Riyad Mahrez",
)
if choice:
    open_player(key_by_label[choice])
    st.switch_page("views/players.py")

st.html('<div style="height:28px"></div>' + ui.strip([
    (f"{len(per90):,}", "players, goalkeepers included"),
    (str(per90["competition"].nunique()),
     f"leagues: {games.get('male', 0)} men's, {games.get('female', 0)} women's"),
    (f"{len(pool.market_values):,}", "Transfermarkt valuations"),
    (str(len(metrics["xg_generalisation"])), "tournaments the shot model was tested on, never trained on"),
]))

st.html(ui.section_title("What the data says", "Finishing from the Premier League 2015/16 · lookalikes across every league"))
findings = load_findings()
for left, right in ((0, 1), (2, 3)):
    columns = st.columns(2)
    for column, index in zip(columns, (left, right)):
        finding = findings[index]
        with column:
            st.html(ui.finding_card(finding))
            if st.button(finding["link_label"], key=f"finding_{finding['kind']}", type="tertiary"):
                if finding["player"]:
                    open_player((finding["player"], finding["team"]))
                st.switch_page("views/players.py")

st.html(ui.section_title("How it works") + '<div style="height:18px"></div>' + ui.steps([
    ("01 · STYLE", "What kind of player is this?",
     "Every action per 90 minutes, ranked against players in the same position, each judged against their own league."),
    ("02 · FINISHING", "Are the goals real?",
     "Each shot gets a chance of scoring from where and how it was taken. Goals above that are finishing, or luck."),
    ("03 · PRICE", "Who plays like this, for less?",
     "The closest statistical matches in the men's and the women's game, next to their Transfermarkt value."),
]))
st.page_link("views/how_it_works.py", label="Methodology and model accuracy →")
st.html('<p class="fap-muted" style="margin-top:36px">StatsBomb open data · Transfermarkt valuations via an open mirror · '
        '<a href="https://github.com/GuiPadinha/football-analytics-portfolio" style="color:#F5A15C">Source on GitHub</a></p>')
