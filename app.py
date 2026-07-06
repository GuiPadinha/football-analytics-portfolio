"""Player Evaluation Framework — Streamlit product layer (Phase 8).

Thin presentation shell over `src/`: every panel is powered by an already-tested backend
function (see docs/PRODUCT_SPEC.md's Component -> Backend Map). Reads precomputed artifacts
from `app_data/` only — no live StatsBomb pulls, no live model training (see PRODUCT_SPEC.md's
Data Flow section for why: a hosted demo has to respond to a click, not an ~8-minute pull).

The similarity pool spans every competition in `config.SIMILARITY_SETS` (Phase 4b, 2026-07-05)
— PL/La Liga/Serie A/Ligue 1 2015/16 plus Frauen Bundesliga/FA WSL 2023/24, see src/app_data.py.
The xG "Finishing" panel still only has data for Premier League 2015/16 + Bayer Leverkusen
2023/24 (Module A's own training set, unchanged) — most players in the wider similarity pool
will hit that panel's "no logged shots" fallback, which is expected, not a bug.

Run locally: streamlit run app.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from cycler import cycler

from src.similarity import (
    ACTION_COLUMNS,
    PER90_FEATURE_COLUMNS,
    compute_silhouette_scores,
    find_similar_players,
    scale_features,
)
from src.visualisation import (
    plot_player_radar,
    plot_shot_map,
    plot_silhouette_curve,
    plot_similar_players_bar,
)

REPO_ROOT = Path(__file__).resolve().parent
APP_DATA_DIR = REPO_ROOT / "app_data"

# Dark teal/gray base + orange primary / blue secondary (2026-07-05 theme pass) — kept as
# named constants rather than repeated literals so the app + its charts read as one palette
# instead of Streamlit's theme and matplotlib's defaults visibly disagreeing.
DARK_BG = "#12181a"
DARK_PANEL = "#1c2b2e"
GRID_LINE = "#33454a"
TEXT_LIGHT = "#e6e6e6"
ACCENT_ORANGE = "#e8752f"
ACCENT_BLUE = "#1a78cf"

# Applied once at import time — this is its own process (a `streamlit run` script), so mutating
# rcParams here can't bleed into the notebooks/pipeline.py's own matplotlib usage, which stays on
# the light/paper-friendly default look on purpose (see visualisation.py's docstring notes).
plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": DARK_PANEL,
    "axes.edgecolor": TEXT_LIGHT,
    "axes.labelcolor": TEXT_LIGHT,
    "axes.prop_cycle": cycler(color=[ACCENT_ORANGE, ACCENT_BLUE, "#8fd19e", TEXT_LIGHT]),
    "text.color": TEXT_LIGHT,
    "xtick.color": TEXT_LIGHT,
    "ytick.color": TEXT_LIGHT,
    "legend.facecolor": DARK_PANEL,
    "legend.edgecolor": TEXT_LIGHT,
    "legend.labelcolor": TEXT_LIGHT,
    "grid.color": GRID_LINE,
})

# "Best fit" stat per position group (2026-07-05, requested: signature stats that match the
# role, not a one-size-fits-all list) — a deliberately small, curated subset of ACTION_COLUMNS
# per group, not a ranking of "the best 3 stats" in some absolute sense. Updated 2026-07-05 to
# surface assists (Midfielder/Forward) and clearances (Defender) — previously only visible
# buried in the "All per-90 stats" expander below.
SIGNATURE_STATS_BY_POSITION = {
    "Defender": ["tackles_p90", "interceptions_p90", "clearances_p90"],
    "Midfielder": ["key_passes_p90", "assists_p90", "progressive_passes_p90"],
    "Forward": ["non_penalty_goals_p90", "assists_p90", "shots_p90"],
}

STAT_LABELS = {col: col.replace("_p90", "").replace("_", " ").title() for col in PER90_FEATURE_COLUMNS}

st.set_page_config(page_title="Player Evaluation Framework", layout="wide")


@st.cache_data
def load_artifacts():
    """Load the three precomputed app_data/ tables plus the repo's metrics.json.

    Cached by Streamlit so the (small) Parquet reads happen once per server process, not once
    per user interaction — every widget change reruns this script top to bottom.
    """
    per90 = pd.read_parquet(APP_DATA_DIR / "player_per90.parquet")
    xg_table = pd.read_parquet(APP_DATA_DIR / "player_xg_table.parquet")
    shots = pd.read_parquet(APP_DATA_DIR / "shots_with_xg.parquet")
    with open(REPO_ROOT / "metrics.json") as metrics_file:
        metrics = json.load(metrics_file)
    return per90, xg_table, shots, metrics


@st.cache_data
def cached_silhouette_scores(position_group_df):
    """Silhouette score per K for one position group — cheap enough (<=300 rows) to compute
    live rather than shipping a fourth precomputed artifact just for the methodology expander.
    """
    X_scaled, _ = scale_features(position_group_df)
    return compute_silhouette_scores(X_scaled)


def render_leaderboard(pool, xg_table):
    """Render the all-players leaderboard: one sortable table over the current filter pool.

    Deliberately different from the player-explorer page (one player at a time): this is the
    "browse everyone, spot the outliers" view Guilherme asked for — e.g. a penalty-inflated
    centre-back tops the Goals column even though `non_penalty_goals` (the modelling stat) is
    modest. Goals here is the real total incl. penalties (see similarity.DISPLAY_COUNT_COLUMNS).

    xG / G-xG are left-joined from the flagship xG table and blank for anyone outside Module A's
    training set (PL 2015/16 + Leverkusen) — most of the wider similarity pool — rather than
    faked, matching the single-player panel's honesty about that gap.

    Args:
        pool (pandas.DataFrame): the per-90 table already narrowed by the sidebar
            position/competition filters (the app's `searchable`).
        xg_table (pandas.DataFrame): flagship player xG table (`total_xg`, `xg_diff` per player).
    """
    st.title("Player leaderboard")
    st.caption(
        f"{len(pool):,} players across {pool['competition'].nunique()} competitions "
        "(narrow with the sidebar position/competition filters). Click any column header to "
        "sort — Goals *includes* penalties, so penalty-takers rise; the modelling stats use "
        "non-penalty goals instead."
    )

    board = pool[[
        "player", "team", "competition", "position_group",
        "minutes_played", "goals", "non_penalty_goals", "assists",
    ]].merge(
        xg_table[["player", "team", "total_xg", "xg_diff"]],
        on=["player", "team"], how="left",
    )
    board = board.rename(columns={
        "player": "Player", "team": "Team", "competition": "Competition",
        "position_group": "Position", "minutes_played": "Minutes",
        "goals": "Goals", "non_penalty_goals": "Non-pen goals", "assists": "Assists",
        "total_xg": "xG", "xg_diff": "G-xG",
    }).sort_values("Goals", ascending=False)

    st.dataframe(
        board,
        hide_index=True,
        width="stretch",
        column_config={
            "Minutes": st.column_config.NumberColumn(format="%d"),
            "Goals": st.column_config.NumberColumn(format="%d"),
            "Non-pen goals": st.column_config.NumberColumn(format="%d"),
            "Assists": st.column_config.NumberColumn(format="%d"),
            "xG": st.column_config.NumberColumn(format="%.1f", help="Flagship xG set only"),
            "G-xG": st.column_config.NumberColumn(
                format="%+.1f",
                help="Goals minus xG. Positive = outscoring chance quality (expect regression); "
                "negative = under-converting good chances (possible buy-low). Flagship set only.",
            ),
        },
    )
    st.caption(
        "xG and G-xG are blank for players outside the xG training set (Premier League 2015/16 + "
        "Bayer Leverkusen 2023/24) — the similarity pool is wider than the xG model's, so most "
        "rows have no xG, shown blank rather than faked."
    )


per90, xg_table, shots, metrics = load_artifacts()

st.sidebar.title("Player Evaluation Framework")
st.sidebar.caption(
    f"{per90['competition'].nunique()} competitions · StatsBomb open data (2015/16-2023/24)"
)

view = st.sidebar.radio(
    "View", ["Player explorer", "Leaderboard"],
    help="Player explorer: one player's radar, similar players and finishing. "
    "Leaderboard: browse and sort every player in the current filters.",
)

position_filter = st.sidebar.selectbox(
    "Filter by position (optional)", ["All"] + sorted(per90["position_group"].unique())
)
competition_filter = st.sidebar.selectbox(
    "Filter by competition (optional)", ["All"] + sorted(per90["competition"].unique())
)
searchable = per90
if position_filter != "All":
    searchable = searchable[searchable["position_group"] == position_filter]
if competition_filter != "All":
    searchable = searchable[searchable["competition"] == competition_filter]

# Leaderboard is a whole-pool table, not a per-player drill-down: render it here (after the
# shared filters, before any player-explorer-only widget) and stop, so the search box / radar
# controls below never render in this view.
if view == "Leaderboard":
    if searchable.empty:
        st.warning("No players match the current filters.")
        st.stop()
    render_leaderboard(searchable, xg_table)
    st.stop()

radar_axes = st.sidebar.multiselect(
    "Radar axes", PER90_FEATURE_COLUMNS, default=list(PER90_FEATURE_COLUMNS)
)

# Typing search: a free-text query narrows the match list once committed (Enter, or clicking
# away — st.text_input shows its own "Press Enter to apply" hint while a keystroke is pending;
# it does NOT rerun on every character the way an earlier version of this comment claimed,
# caught 2026-07-06 by actually driving the app with Playwright rather than assuming), and the
# selectbox right below always shows the current matches with the top one pre-selected. This
# is still a deliberately different interaction from a plain combobox (click to open, then type
# inside it) — the text box is the obvious first thing to type into, matching "typing search"
# as asked, not a searchable-but-still-dropdown-shaped control.
search_query = st.text_input("Search for a player", placeholder="Type a name, then press Enter...")
if search_query:
    matches = searchable[searchable["player"].str.contains(search_query, case=False, regex=False, na=False)]
else:
    matches = searchable
matches = matches.sort_values("player")

if matches.empty:
    st.warning(f'No players match "{search_query}" with the current filters.' if search_query else "No players match the current filters.")
    st.stop()

player_by_label = {
    f"{player} ({team}) · {competition}": (player, team, position_group, competition)
    for player, team, position_group, competition in zip(
        matches["player"], matches["team"], matches["position_group"], matches["competition"]
    )
}
labels = sorted(player_by_label)
picked_label = st.selectbox(
    f"{len(labels)} match{'es' if len(labels) != 1 else ''}",
    labels,
    # Keyed on every filter/query that can change the option set, so the widget always resets
    # to the (fresh) top suggestion instead of Streamlit trying to preserve a prior selection
    # that may no longer be a valid option (the exact crash this shape avoids — see
    # ML_TOOLING.md's selectbox-with-changing-options gotcha).
    key=f"player_pick_{position_filter}_{competition_filter}_{search_query}",
)
player_name, team_name, position_group, competition_name = player_by_label[picked_label]
group_df = per90[per90["position_group"] == position_group].reset_index(drop=True)

st.title(f"{player_name} · {team_name} · {position_group}")
st.caption(competition_name)

st.subheader(f"Signature stats for a {position_group.lower()}")
signature_cols = SIGNATURE_STATS_BY_POSITION[position_group]
player_row_full = group_df[(group_df["player"] == player_name) & (group_df["team"] == team_name)].iloc[0]
percentiles = group_df[PER90_FEATURE_COLUMNS].rank(pct=True).loc[player_row_full.name]

metric_cols = st.columns(len(signature_cols))
for col, stat in zip(metric_cols, signature_cols):
    raw_col = stat.replace("_p90", "")
    total = int(round(player_row_full[raw_col]))
    rate = player_row_full[stat]
    pct = percentiles[stat] * 100
    col.metric(
        STAT_LABELS[stat], f"{total:,}",
        help=f"{rate:.2f} per 90 · {pct:.0f}th percentile among {position_group.lower()}s",
    )
st.caption(
    "Season totals (not personalised to this player's strengths — a fixed set per position "
    f"group). Hover a card for the per-90 rate and percentile vs. {len(group_df)} "
    f"{position_group.lower()}s across {group_df['competition'].nunique()} competitions."
)

with st.expander(f"All per-90 stats ({len(PER90_FEATURE_COLUMNS)} metrics, vs. {position_group.lower()} peers)"):
    stat_table = pd.DataFrame({
        "Stat": [STAT_LABELS[c] for c in PER90_FEATURE_COLUMNS],
        "Total": [int(round(player_row_full[c])) for c in ACTION_COLUMNS],
        "Per 90": [player_row_full[c] for c in PER90_FEATURE_COLUMNS],
        "Percentile (numeric)": [percentiles[c] * 100 for c in PER90_FEATURE_COLUMNS],
    }).sort_values("Percentile (numeric)", ascending=False)
    stat_table["Percentile"] = stat_table["Percentile (numeric)"].map(lambda p: f"{p:.0f}th")
    st.dataframe(
        stat_table.drop(columns="Percentile (numeric)"), hide_index=True, width="stretch"
    )
    st.caption(
        "Percentile within this player's position group (n="
        f"{len(group_df)}). No pass-completion % yet, since that needs a new feature (passes "
        "attempted, not just completed) from raw events, not just a different chart. Flagged as "
        "a follow-up, not faked here. Clearances are StatsBomb's general Clearance event count, "
        "not a 'last-ditch/goal-line' sub-type — StatsBomb's schema doesn't distinguish those, "
        "so this is the closest available proxy."
    )

col_radar, col_similar = st.columns(2)

with col_radar:
    st.subheader(f"Radar vs. {position_group.lower()} peers")
    if radar_axes:
        fig, ax = plt.subplots(figsize=(6, 6))
        plot_player_radar(
            player_row_full, population=group_df, feature_columns=radar_axes, ax=ax,
            circle_facecolor=DARK_PANEL, circle_edgecolor=GRID_LINE, radar_facecolor=ACCENT_BLUE,
        )
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("Pick at least one radar axis in the sidebar.")

with col_similar:
    st.subheader(f"Players like {player_name}")
    similar = find_similar_players(
        per90, PER90_FEATURE_COLUMNS, player=player_name, team=team_name, n=5
    )
    fig, ax = plt.subplots(figsize=(7, 0.7 * len(similar) + 1))
    plot_similar_players_bar(similar, accent_color=ACCENT_ORANGE, grid_color=GRID_LINE, ax=ax)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        "Distance = Euclidean, standardised per-90 features, same position group only — now "
        "searched across the whole multi-competition pool, so a match can come from a different "
        "league. No cross-league normalisation yet (see \"Under the hood\" below), so treat a "
        "cross-league match as a coarser signal than a same-league one."
    )
    with st.expander("Table view"):
        st.dataframe(
            similar[["player", "team", "competition", "distance"]].rename(
                columns={
                    "player": "Player", "team": "Team",
                    "competition": "Competition", "distance": "Distance (standardised)",
                }
            ),
            hide_index=True,
            width="stretch",
        )

st.subheader("Finishing — is the output real?")
xg_row = xg_table[(xg_table["player"] == player_name) & (xg_table["team"] == team_name)]

if xg_row.empty:
    st.info(
        f"{player_name} ({competition_name}) has no logged shots in the xG training set "
        "(Premier League 2015/16 + Bayer Leverkusen 2023/24). The similarity pool is wider than "
        "the xG training set (see \"Under the hood\" below), so this is expected for most "
        "players outside those two competitions, not a bug."
    )
else:
    row = xg_row.iloc[0]
    xg_metric_cols = st.columns(3)
    xg_metric_cols[0].metric("Goals", int(row["goals"]))
    xg_metric_cols[1].metric("Expected goals (xG)", f"{row['total_xg']:.1f}")
    xg_metric_cols[2].metric(
        "Difference",
        f"{row['xg_diff']:+.1f}",
        help="Positive: scoring more than the chances deserved (partly luck, expect regression). "
        "Negative: creating good chances but not converting (possible buy-low).",
    )

    player_shots = shots[
        (shots["player"] == player_name) & (shots["team"] == team_name)
    ].reset_index(drop=True)
    if len(player_shots):
        fig, ax = plt.subplots(figsize=(9, 6))
        plot_shot_map(player_shots, player_shots["predicted_xg"].values, ax=ax)
        st.pyplot(fig)
        plt.close(fig)

with st.expander("Under the hood (methodology)"):
    st.markdown(
        f"""
- **xG model:** logistic regression, test ROC-AUC **{metrics['xg']['logistic']['test_roc_auc']}**,
  test Brier **{metrics['xg']['logistic']['test_brier']}**
  (train: Leverkusen 2023/24 + PL 2015/16, test: EURO 2024 — a deliberate league-to-tournament
  distribution shift, see [docs/MODULES.md](docs/MODULES.md)).
- **Baseline ladder (test ROC-AUC):** no-skill {metrics['xg']['baseline_ladder_test_roc_auc']['no_skill']}
  → geometry-only {metrics['xg']['baseline_ladder_test_roc_auc']['geometry_only']}
  → full model {metrics['xg']['baseline_ladder_test_roc_auc']['full']}.
- **Similarity model:** K-means, K={metrics['similarity']['kmeans_k_used']} per position group,
  min. {metrics['similarity']['min_minutes']} minutes played, pool spans
  {per90['competition'].nunique()} competitions: {", ".join(sorted(per90["competition"].unique()))}.
- **Data recency ceiling:** StatsBomb's *free* open data has no recent men's top-flight season —
  2015/16 is the newest full men's league available (PL/La Liga/Serie A/Ligue 1 alike); the
  women's leagues above (2023/24) are the newest full-season data this project has anywhere.
  A live/current-season pool isn't possible on this data source without a paid licence.
- **No cross-league normalisation yet** — per-90 rates are compared directly across leagues of
  different competitiveness/style. A cross-league "similar player" match is a coarser signal
  than a same-league one until that's designed (see ROADMAP.md Phase 4b).
        """
    )
    st.caption(
        f"Silhouette score by K — {position_group} (peaks low, ~0.25: play-styles within a "
        "position are a soft continuum, not crisp blobs; K=4 is kept deliberately above the "
        "metric's preferred K=2 for archetype granularity)."
    )
    silhouettes = cached_silhouette_scores(group_df)
    fig, ax = plt.subplots(figsize=(6, 4))
    plot_silhouette_curve(silhouettes, ax=ax)
    st.pyplot(fig)
    plt.close(fig)
