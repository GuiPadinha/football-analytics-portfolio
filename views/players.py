"""Players: one player's page, as three questions (style, are the goals real, who plays like this)."""

from html import escape

import streamlit as st

from src.narrative import GAME_WORDS, GROUP_PLURALS
from src.presentation import format_market_value
from src.profile import build_player_profile
from views import components as ui
from views.data import label_of, load_pool, open_player, player_options, popular_picks

LOW_NOTE = {
    False: "Not weaknesses as such: a winger who carries the ball is rarely the one who tackles.",
    True: "Not flaws as such: a low count can mean a defence that rarely needed the keeper.",
}

pool = load_pool()
labels, key_by_label = player_options()


def _remember_choice():
    """Search-box callback: the box is the source of truth until a jump button overrides it."""
    st.session_state["selected_player"] = key_by_label.get(st.session_state.get("player_search"))


# A jump (a lookalike's name, a Home card) sets `selected_player` and reruns. Pushing it into the
# search box before the box is drawn makes the box show who the page is about.
selected = st.session_state.get("selected_player")
if selected and key_by_label.get(st.session_state.get("player_search")) != tuple(selected):
    st.session_state["player_search"] = label_of(selected)

st.selectbox(
    "Search a player", labels, index=None, key="player_search", on_change=_remember_choice,
    label_visibility="collapsed", placeholder="Search a player: start typing a name…",
)
selected = st.session_state.get("selected_player")

if not selected:
    st.html(ui.section_title("Pick a player", "Search above, or start with one of the most valuable names in the data."))
    columns = st.columns(len(popular_picks()))
    for column, key in zip(columns, popular_picks()):
        with column:
            if st.button(label_of(key).split(" (")[0], key=f"pick_{key}", width="stretch"):
                open_player(key)
                st.rerun()
    st.stop()

profile = build_player_profile(pool, *selected)
group_plural = GROUP_PLURALS[profile.position_group]
is_keeper = profile.position_group == "Goalkeeper"

# --- header -----------------------------------------------------------------------------------
if is_keeper:
    facts = f"{profile.competition} · {profile.minutes:,.0f} minutes · {profile.saves.shots_on_target} shots on target faced"
else:
    facts = f"{profile.competition} · {profile.minutes:,.0f} minutes · {profile.goals} goals · {profile.assists} assists"
if profile.market_value_eur is not None:
    value_card = ui.value_card(
        format_market_value(profile.market_value_eur),
        f"Transfermarkt, as of {profile.market_value_as_of}",
    )
else:
    reason = (
        "Transfermarkt has no women's football" if profile.gender == "female"
        else "No single Transfermarkt profile at this club that season"
    )
    value_card = ui.value_card("Not on record", reason)
st.html(
    '<div style="height:20px"></div>'
    + ui.page_header(f"{profile.position_group} · {profile.team}", profile.name, facts, value_card)
    + '<div style="height:26px"></div>' + ui.summary_panel(profile.short_version)
)

# --- 1 · style --------------------------------------------------------------------------------
st.html(ui.section_title(
    "1 · What kind of player is this?",
    f"Per 90 minutes, ranked against {profile.group_size:,} {group_plural}, each judged against their own league",
))
more, less = st.columns(2)
with more:
    st.html(ui.bar_card("Does more than most", profile.strengths, empty="No stat is in this player's top quarter."))
with less:
    st.html(
        ui.bar_card("Does less than most", profile.weaknesses, ui.BLUE, ui.BLUE_LIGHT, empty="No stat is in this player's bottom quarter.")
        + f'<p class="fap-muted" style="margin:10px 2px 0">{escape(LOW_NOTE[is_keeper])}</p>'
    )

# --- 2 · goals / saves ------------------------------------------------------------------------
if is_keeper:
    saves = profile.saves
    st.html(
        ui.section_title("2 · How good is the shot-stopping?", "Shots on target only, penalties included")
        + '<div style="height:16px"></div>'
        + ui.tiles([
            ("Save %", f"{saves.save_pct:.0%}", True),
            ("Saves", f"{round(saves.save_pct * saves.shots_on_target)}", False),
            ("Shots on target faced", f"{saves.shots_on_target}", False),
        ])
        + f'<p style="font-size:18px;line-height:1.55;margin:18px 0 0;max-width:900px">{escape(profile.output_text)}</p>'
        + '<p class="fap-muted" style="margin-top:8px">A keeper\'s save % depends on how hard the shots were, and there is no '
          "shot-quality model for goalkeepers here yet: read it as a rate, not a verdict.</p>"
    )
elif profile.finishing is not None:
    finishing = profile.finishing
    gap = finishing.goals - finishing.expected_goals
    st.html(
        ui.section_title("2 · Are the goals real?", f"{len(profile.shots)} shots, each rated by its chance of going in")
        + '<div style="height:16px"></div>'
        + ui.tiles([
            ("Goals", f"{finishing.goals}", False),
            ("Goals the chances were worth", f"{finishing.expected_goals:.1f}", False),
            ("Above expectation", f"{gap:+.1f}".replace("-", "−"), gap > 0),
        ])
        + f'<p style="font-size:18px;line-height:1.55;margin:18px 0 0;max-width:900px">{escape(profile.output_text)}</p>'
    )
    st.altair_chart(ui.shot_map(profile.shots), width="stretch")
    st.caption("Every shot, sized by its chance of scoring. Orange circles are goals.")
else:
    st.html(
        ui.section_title("2 · Are the goals real?")
        + f'<div class="fap-panel" style="margin-top:14px"><p style="margin:0;font-size:17px;line-height:1.55">'
          f"{profile.goals} goals and {profile.assists} assists this season"
          f"{f' ({profile.penalty_goals} from penalties)' if profile.penalty_goals else ''}. "
          "Goals against chances is only available for the Premier League 2015/16, the one competition with "
          "shot-by-shot data behind the model.</p></div>"
    )

# --- 3 · lookalikes ---------------------------------------------------------------------------
own, other = profile.gender, ("female" if profile.gender == "male" else "male")
st.html(ui.section_title("3 · Who plays like this player?", "Closest statistical matches, each judged against their own league"))
tabs = st.tabs([f"{GAME_WORDS[own].capitalize()} game", f"{GAME_WORDS[other].capitalize()} game"])
for tab, game in zip(tabs, (own, other)):
    with tab:
        matches = profile.lookalikes[game]
        color = ui.ORANGE if game == "male" else ui.BLUE
        widths = [0.5, 2.4, 2.8, 2.4, 1.5]
        header = st.columns(widths)
        for column, text in zip(header, ("#", "PLAYER", "CLUB AND LEAGUE", "HOW CLOSE", "VALUE")):
            column.html(f'<span class="fap-muted" style="letter-spacing:1px">{text}</span>')
        for rank, match in enumerate(matches, start=1):
            number, name, league, close, value = st.columns(widths, vertical_alignment="center")
            number.html(f'<span class="fap-display" style="font-size:24px;color:{ui.TEXT_FAINT}">{rank}</span>')
            with name:
                if st.button(match.name, key=f"look_{game}_{rank}_{match.player}_{match.team}", type="tertiary"):
                    open_player((match.player, match.team))
                    st.rerun()
            league.html(
                f'<div style="color:{ui.TEXT_MUTED};font-size:14px;line-height:1.35">{escape(match.team)}<br>'
                f'<span class="fap-muted">{escape(match.competition)}</span></div>'
            )
            close.html(ui.closeness_bar(match.closeness, color))
            value.html(
                f'<div style="text-align:right"><div style="font-weight:600">{format_market_value(match.market_value_eur) or "n/a"}</div>'
                f'{ui.pill("Cheaper") if match.cheaper else ""}</div>'
            )
        if game == "male":
            st.caption(
                "Bar length: how close each profile is, relative to the closest match in either game. Valuations are "
                "Transfermarkt's, around the 2015/16 season. A similar style is not the same level: league, age and "
                "contract move a price, so treat a cheaper match as a lead to check."
            )
        else:
            st.caption("No market values exist for women's football in this data.")

if st.button(f"Compare {profile.name} with another player", type="primary"):
    st.session_state["compare_pick_a"] = label_of(selected)
    st.session_state.pop("compare_pick_b", None)
    st.switch_page("views/compare.py")
st.page_link("views/how_it_works.py", label="How these numbers are made →")
