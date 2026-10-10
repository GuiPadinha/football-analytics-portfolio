"""TEMPORARY (redesign 1b): the pre-redesign Compare, Leaderboard and About views, moved here
verbatim so the live app keeps them until stages C and D replace them. Deleted by stage D.

Original docstring: Player Evaluation Framework — Streamlit product layer (Phase 8).

Thin presentation shell over `src/`: every panel is powered by an already-tested backend
function (see docs/PRODUCT_SPEC.md's Component -> Backend Map), and the words around the numbers
come from `src/presentation.py`. Reads precomputed artifacts from `app_data/` only — no live
StatsBomb pulls, no live model training: a hosted demo has to respond to a click, not a pull.

Things worth knowing before editing a view:
- The similarity pool spans every competition in `config.SIMILARITY_SETS` (see src/app_data.py),
  but the xG "Finishing" panel only has data for Premier League 2015/16 (the one competition in
  both the xG training set and this pool), so most players hit its "no logged shots" fallback.
- Goalkeepers have their own, disjoint feature set (`presentation.feature_columns_for`), so views
  branch on position group rather than assuming the three outfield groups.
- Clustering and "players like X" run on league-normalised (`_lz`) features; radar axes,
  percentiles and signature stats deliberately stay on raw per-90 rates, so a fan reads a real
  rate, not a z-score.

Run locally: streamlit run app.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap

from src.presentation import (
    SIGNATURE_STATS_BY_POSITION,
    STAT_LABELS,
    build_scouting_blurb,
    feature_columns_for,
    format_market_value,
    format_percentile,
    lookup_market_value,
    percentile_tier,
    style_intensity_label,
)
from src.similarity import (
    compute_silhouette_scores,
    find_similar_players,
    goodness_percentiles,
    profile_clusters,
)
from src.visualisation import (
    plot_diverging_bar,
    plot_player_radar,
    plot_player_radar_comparison,
    plot_shot_map,
    plot_silhouette_curve,
    plot_similar_players_bar,
    plot_xg_generalisation_bar,
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

# Diverging colormap for table cell backgrounds (Leaderboard's G-xG column) — same blue/orange
# poles + a neutral (dark panel) midpoint as plot_diverging_bar's bar colours, so "which side of
# a baseline" reads the same way whether it's a bar chart or a table cell (2026-07-13 pass; see
# the dataviz skill's colour-formula doc: two hues that read as opposite + a neutral midpoint,
# never a hue *at* the midpoint).
DIVERGING_CMAP = LinearSegmentedColormap.from_list(
    "app_diverging", [ACCENT_BLUE, DARK_PANEL, ACCENT_ORANGE]
)


def _diverging_css(value, span):
    """CSS `background-color` for one G-xG cell, replicating `Styler.background_gradient`
    manually so a missing cell gets no colour at all (the built-in helper paints NaN black):
    `DIVERGING_CMAP` sampled at `value`'s position between `-span` and `+span`.
    """
    normalized = 0.5 if span == 0 else (value + span) / (2 * span)
    r, g, b, a = DIVERGING_CMAP(min(max(normalized, 0.0), 1.0))
    return f"background-color: rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, {a:.2f})"

# Brand identity (2026-07-13 visual pass) — one icon/slogan pair reused everywhere (browser tab,
# sidebar, every page header) so the app reads as one product rather than a stack of bare
# st.title() calls with no shared identity.
BRAND_ICON = "⚽"
SLOGAN = "Scout by data, not by reputation."

MIN_RADAR_AXES = 3

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



@st.cache_data
def load_artifacts():
    """Load the precomputed app_data/ tables plus the repo's metrics.json.

    Cached by Streamlit so the (small) Parquet reads happen once per server process, not once
    per user interaction — every widget change reruns this script top to bottom.

    `market_value.parquet` is loaded defensively (empty frame if missing) rather than assumed
    present: `app_data.build_app_artifacts(with_market_value=False)` is a supported way to build
    without Transfermarkt (see that function's docstring), so a market-value-less
    `app_data/` is a legitimate state, not a broken one — every market-value UI element already
    treats "no row for this player" as "not resolved," so an entirely empty table just means
    everyone falls into that same, already-handled branch.
    """
    per90 = pd.read_parquet(APP_DATA_DIR / "player_per90.parquet")
    xg_table = pd.read_parquet(APP_DATA_DIR / "player_xg_table.parquet")
    shots = pd.read_parquet(APP_DATA_DIR / "shots_with_xg.parquet")
    market_value_path = APP_DATA_DIR / "market_value.parquet"
    if market_value_path.exists():
        market_value = pd.read_parquet(market_value_path)
    else:
        market_value = pd.DataFrame(
            columns=["player", "team", "tm_name", "market_value_eur", "market_value_as_of"]
        )
    with open(REPO_ROOT / "metrics.json") as metrics_file:
        metrics = json.load(metrics_file)
    return per90, xg_table, shots, market_value, metrics


@st.cache_data
def cached_silhouette_scores(position_group_df, feature_columns):
    """Silhouette score per K for one position group — cheap enough (<=300 rows) to compute
    live rather than shipping a fourth precomputed artifact just for the methodology expander.

    `feature_columns` should be the same league-normalised (`_lz`) columns
    `src/app_data.py`'s `_cluster_position_groups` actually clustered on, so this curve matches
    the real K decision rather than a different (raw, pooled-across-leagues) feature space —
    those columns are already standardised (mean ~0, std ~1 within each competition), so this
    skips `scale_features`'s own global rescale rather than re-scaling an already-scaled matrix.
    """
    return compute_silhouette_scores(position_group_df[feature_columns])


@st.cache_data
def cached_cluster_profile(position_group_df, feature_columns):
    """Per-cluster feature z-scores for one position group (2026-07-13 style-archetype panel).

    `_cluster_position_groups` (src/app_data.py) computes a K=4 style-archetype `cluster` label
    per player — outfield and, as of a same-day follow-up pass, goalkeepers too — when app_data/
    is built. This wraps the existing `profile_clusters` (no new modelling, just a z-score
    readout the notebook already uses to name clusters like "ball-winning destroyer") so a
    player's page can show *why* their cluster is what it is, not just a bare cluster number.
    `feature_columns` is the league-normalised `_lz` set (the actual clustering space, see the
    module docstring), so a cluster's "high Tackles" reading is standard deviations above this
    cluster's peers' *own leagues'* average, not the raw multi-league pool's. Cached per position
    group, same reasoning as `cached_silhouette_scores` above — cheap, but no reason to recompute
    per rerun.
    """
    return profile_clusters(position_group_df, feature_columns, position_group_df["cluster"].values)


def render_page_header(title):
    """Shared header chrome: a big page title on the left, a small brand badge (icon + slogan) in
    the top-right corner — so every view (Leaderboard, Player explorer, a player's own page) reads
    as one product rather than a bare `st.title()` with no shared identity (2026-07-13 visual pass).
    """
    header_left, header_right = st.columns([5, 1])
    with header_left:
        st.title(title)
    with header_right:
        st.caption(f"{BRAND_ICON} *{SLOGAN}*")


def render_leaderboard(pool, xg_table, market_value):
    """Render the all-players leaderboard: one sortable table over the current filter pool.

    Deliberately different from the player-explorer page (one player at a time): this is the
    "browse everyone, spot the outliers" view Guilherme asked for — e.g. a penalty-inflated
    centre-back tops the Goals column even though `non_penalty_goals` (the modelling stat) is
    modest. Goals here is the real total incl. penalties (see similarity.DISPLAY_COUNT_COLUMNS).

    xG / G-xG are left-joined from the flagship xG table and blank for anyone outside Premier
    League 2015/16 — most of the wider similarity pool — rather than
    faked, matching the single-player panel's honesty about that gap. Market value (Phase 9) is
    left-joined the same way, blank for anyone Transfermarkt matching couldn't resolve (unmatched
    name, or a women's-league player — that data source only covers men's football, see
    src/market_value.py) — never faked either.

    Args:
        pool (pandas.DataFrame): the per-90 table already narrowed by the sidebar
            position/competition filters (the app's `searchable`).
        xg_table (pandas.DataFrame): flagship player xG table (`total_xg`, `xg_diff` per player).
        market_value (pandas.DataFrame): output of `market_value.build_market_value_table`.
    """
    render_page_header("Player leaderboard")
    st.markdown(
        "Every player in the current filters, one sortable table — the **\"browse and spot "
        "outliers\"** view, as opposed to the Player explorer's one-player-at-a-time deep dive. "
        f"**{len(pool):,} players** across **{pool['competition'].nunique()} competitions** right "
        "now; narrow further below by name or position, or click any column header to sort (click "
        "again to reverse)."
    )
    st.markdown(
        "**What to look for:**\n"
        "- **Goals vs. Non-pen goals** — Goals *includes* penalties, Non-pen goals is what the "
        "models actually use. Sort by Goals to find the outliers where the gap is biggest (a "
        "penalty-taking defender, a striker whose real output is lower than the headline number).\n"
        "- **xG / G-xG** — only populated for Premier League 2015/16 players (the one competition "
        "in both the xG training set and this pool); blank elsewhere, not faked. Sort G-xG ascending for "
        "the biggest \"creating chances, not converting\" candidates; descending for the biggest "
        "likely finishing spikes.\n"
        "- **Position** — includes Goalkeeper now; their Goals/Assists columns are blank here "
        "(different feature set, see their own Player explorer page for saves/save %).\n"
        "- **Market value** — a Transfermarkt valuation, men's competitions only; blank where "
        "name-matching couldn't confidently resolve a player (see \"About & Roadmap\")."
    )

    # In-page filters (2026-07-13, requested on top of the sidebar's position/competition
    # filters): a name search plus a position multiselect scoped to this view only, so browsing
    # the whole table doesn't require leaving it to touch the sidebar.
    filter_name_col, filter_position_col = st.columns([2, 1])
    with filter_name_col:
        # Feeds a multi-row table rather than a single pick, so it can't be swapped for the
        # live-filtering selectbox pattern the two player-picker search boxes use (see Player
        # explorer's own comment) — a table has no single "pick one" widget to become. Streamlit's
        # text_input still only reruns on Enter/blur, so the placeholder says so plainly instead
        # of implying a live filter it can't deliver.
        name_query = st.text_input(
            "Filter by player name", placeholder="Type a name, then press Enter...",
            key="leaderboard_name_filter",
        )
    with filter_position_col:
        position_options = sorted(pool["position_group"].unique())
        position_pick = st.multiselect(
            "Filter by position", position_options, default=position_options,
            key="leaderboard_position_filter",
        )

    filtered = pool[pool["position_group"].isin(position_pick)] if position_pick else pool.iloc[0:0]
    if name_query:
        filtered = filtered[filtered["player"].str.contains(name_query, case=False, regex=False, na=False)]
    if filtered.empty:
        st.warning("No players match the name/position filters above.")
        return
    if len(filtered) != len(pool):
        st.caption(f"Showing {len(filtered):,} of {len(pool):,} players after the filters above.")

    board = filtered[[
        "player", "team", "competition", "position_group",
        "minutes_played", "goals", "non_penalty_goals", "assists",
    ]].merge(
        xg_table[["player", "team", "total_xg", "xg_diff"]],
        on=["player", "team"], how="left",
    ).merge(
        market_value[["player", "team", "market_value_eur"]],
        on=["player", "team"], how="left",
    )
    board = board.rename(columns={
        "player": "Player", "team": "Team", "competition": "Competition",
        "position_group": "Position", "minutes_played": "Minutes",
        "goals": "Goals", "non_penalty_goals": "Non-pen goals", "assists": "Assists",
        "total_xg": "xG", "xg_diff": "G-xG", "market_value_eur": "Market value",
    }).sort_values("Goals", ascending=False)

    # Missing values stay genuinely missing (NaN) in numeric columns: `placeholder=""` below
    # renders them as blank cells, so every column keeps a *numeric* click-to-sort. Blanks are
    # expected here — xG/G-xG exist only for the xG training set, Goals/Assists don't apply to
    # goalkeepers, market value only resolves for men's competitions. (Between 2026-07-13 and
    # 2026-10-01 these were hand-formatted text columns to dodge Streamlit's literal "None"
    # rendering, on the mistaken belief no config fix existed; see docs/ML_TOOLING.md.)
    # G-xG's diverging background is still computed by hand (`_diverging_css`) so missing cells
    # get no colour at all; `Styler.background_gradient` would paint them black.
    # Millions, so the column can stay numeric and sort correctly (a formatted "€9.0M" string
    # sorts after "€10.0M" lexically); the player page keeps the finer "€850k" wording.
    board["Market value"] = board["Market value"] / 1_000_000
    gxg_raw = board["G-xG"]
    board_style = board.style
    if gxg_raw.notna().any():
        gxg_span = gxg_raw.abs().max() or 1.0
        gxg_colors = gxg_raw.map(lambda v: "" if pd.isna(v) else _diverging_css(v, gxg_span))
        board_style = board_style.apply(lambda _: gxg_colors, subset=["G-xG"])

    st.dataframe(
        board_style,
        hide_index=True,
        width="stretch",
        placeholder="",
        column_config={
            "Minutes": st.column_config.NumberColumn(format="%d"),
            "Goals": st.column_config.NumberColumn(
                format="%d", help="Includes penalties. Blank for goalkeepers."
            ),
            "Non-pen goals": st.column_config.NumberColumn(format="%d", help="Blank for goalkeepers."),
            "Assists": st.column_config.NumberColumn(format="%d", help="Blank for goalkeepers."),
            "xG": st.column_config.NumberColumn(format="%.1f", help="Flagship xG set only"),
            "G-xG": st.column_config.NumberColumn(
                format="%+.1f",
                help="Goals minus xG. Positive = outscoring chance quality (expect regression); "
                "negative = under-converting good chances (possible buy-low). Flagship set only.",
            ),
            "Market value": st.column_config.NumberColumn(
                format="€%.1fM",
                help="Transfermarkt valuation in € millions, roughly as of this season (see "
                "\"About & Roadmap\" for the matching caveats). Men's competitions only; blank "
                "where unmatched.",
            ),
        },
    )
    st.caption(
        "xG and G-xG are blank for players outside Premier League 2015/16 (the one competition in "
        "both the xG training set and this pool) — the similarity pool is wider, so most "
        "rows have no xG, shown blank rather than faked. Goalkeepers show blank Goals/Assists too "
        "— those columns come from the outfield feature set, which doesn't cover them; see a "
        "goalkeeper's own page (Player explorer) for their saves/goals-conceded/save % instead."
    )


def render_compare_players(per90, xg_table, market_value):
    """Render the "Compare players" view (Phase 9): two players side by side.

    Deliberately not filtered by the sidebar's position/competition selectors (see the view's own
    dispatch comment near the top of the script) — two independent search+pick widgets pull from
    the *whole* `per90` pool, since a side-by-side comparison is a reasonable thing to want across
    positions or competitions too (e.g. "is this expensive winger really worth more than that
    cheap forward"), unlike "players like X"/clustering, which only make sense within one shared
    feature space. The radar/percentile/signature-stat comparison below only renders when both
    picks share a position group, for the same reason — market value and Finishing still compare
    directly either way.
    """
    render_page_header("Compare players")
    st.markdown(
        "Pick any two players — same position group or not — for a side-by-side read: market "
        "value, and (when they share a position group, so the same stats apply) signature stats, "
        "an overlaid radar, and a percentile comparison."
    )

    # One live-filtering selectbox per side (2026-07-14, same fix and reasoning as the Player
    # explorer's search box — see its own comment: a text_input + selectbox combo doesn't
    # actually filter until Enter/blur, which felt broken under an actual Playwright drive of the
    # running app). Starts unselected (`index=None`) rather than defaulting to the alphabetically
    # -first player on both sides at once — the old two-widget version did that, which meant a
    # fresh "Compare players" load immediately showed the same player against themselves and the
    # "pick two different players" warning below, before anyone had touched anything.
    label_map = {
        f"{p} ({t}) · {c}": (p, t)
        for p, t, c in zip(per90["player"], per90["team"], per90["competition"])
    }
    option_labels = sorted(label_map)

    pick_cols = st.columns(2)
    picks = []
    for col, side_label, key in zip(pick_cols, ["Player A", "Player B"], ["a", "b"]):
        with col:
            st.markdown(f"**{side_label}**")
            picked_label = st.selectbox(
                f"Search for {side_label} ({len(option_labels):,} players)",
                option_labels, index=None, placeholder="Start typing a name...",
                key=f"compare_pick_{key}",
            )
            picks.append(label_map[picked_label] if picked_label else None)

    if picks[0] is None or picks[1] is None:
        st.info("Search for two players above to compare them.")
        return
    (name_a, team_a), (name_b, team_b) = picks
    if (name_a, team_a) == (name_b, team_b):
        st.info("Pick two different players to compare.")
        return

    row_a = per90[(per90["player"] == name_a) & (per90["team"] == team_a)].iloc[0]
    row_b = per90[(per90["player"] == name_b) & (per90["team"] == team_b)].iloc[0]

    st.divider()
    header_a, header_b = st.columns(2)
    header_a.subheader(f"{name_a} · {row_a['team']} · {row_a['position_group']}")
    header_a.caption(row_a["competition"])
    header_b.subheader(f"{name_b} · {row_b['team']} · {row_b['position_group']}")
    header_b.caption(row_b["competition"])

    # Market value side by side — Module B's original "similar profile, cheaper" pitch (see
    # DATA.md's market-value note); this view is the most direct place to answer it.
    mv_a = lookup_market_value(market_value, name_a, team_a)
    mv_b = lookup_market_value(market_value, name_b, team_b)
    mv_cols = st.columns(2)
    for col, mv in zip(mv_cols, [mv_a, mv_b]):
        if mv is not None:
            col.metric(
                "Market value", format_market_value(mv["market_value_eur"]),
                help=f"Transfermarkt, as of {mv['market_value_as_of']} — matched to \"{mv['tm_name']}\".",
            )
        else:
            col.metric("Market value", "—", help="Not available — see \"About & Roadmap\".")
    if mv_a is not None and mv_b is not None and mv_a["market_value_eur"] != mv_b["market_value_eur"]:
        diff = mv_a["market_value_eur"] - mv_b["market_value_eur"]
        cheaper, pricier, amount = (name_b, name_a, diff) if diff > 0 else (name_a, name_b, -diff)
        st.caption(f"{cheaper} is valued {format_market_value(amount)} less than {pricier}.")

    same_group = row_a["position_group"] == row_b["position_group"]
    if not same_group:
        st.info(
            f"{name_a} is a {row_a['position_group'].lower()}, {name_b} is a "
            f"{row_b['position_group'].lower()} — different feature sets, so a stat-by-stat radar "
            "comparison isn't meaningful here. Finishing below still compares directly."
        )
    else:
        position_group = row_a["position_group"]
        _, feature_columns, _ = feature_columns_for(position_group)
        signature_cols = SIGNATURE_STATS_BY_POSITION[position_group]
        group_df = per90[per90["position_group"] == position_group].reset_index(drop=True)
        row_a_full = group_df[(group_df["player"] == name_a) & (group_df["team"] == team_a)].iloc[0]
        row_b_full = group_df[(group_df["player"] == name_b) & (group_df["team"] == team_b)].iloc[0]

        st.subheader("Signature stats")
        stat_cols = st.columns(len(signature_cols))
        for col, stat in zip(stat_cols, signature_cols):
            raw_col = stat.replace("_p90", "")
            col.metric(
                STAT_LABELS[stat],
                f"{int(round(row_a_full[raw_col]))} vs {int(round(row_b_full[raw_col]))}",
                help=f"Per 90: {name_a} {row_a_full[stat]:.2f} · {name_b} {row_b_full[stat]:.2f}",
            )

        st.subheader(f"Radar vs. {position_group.lower()} peers")
        fig, ax = plt.subplots(figsize=(7, 7))
        plot_player_radar_comparison(
            row_a_full, row_b_full, population=group_df, feature_columns=feature_columns, ax=ax,
            circle_facecolor=DARK_PANEL, circle_edgecolor=GRID_LINE,
            player_a_color=ACCENT_BLUE, player_b_color=ACCENT_ORANGE,
            player_a_label=name_a, player_b_label=name_b,
        )
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("Percentile within position group")
        # goodness_percentiles flips goals_conceded_p90 (the one stat here where a *smaller* raw
        # number is the better outcome) so a bigger percentile always means "better than peers,"
        # never just "bigger raw number" — see similarity.py's own docstring for why that flip
        # exists. The tier word is the actual "is this good?" answer; the ordinal number alone
        # doesn't carry it (see the percentile-perception discussion this pass grew out of).
        percentiles = goodness_percentiles(group_df[feature_columns].rank(pct=True))
        pct_a = percentiles.loc[row_a_full.name]
        pct_b = percentiles.loc[row_b_full.name]
        pct_table = pd.DataFrame({
            "Stat": [STAT_LABELS[c] for c in feature_columns],
            name_a: [
                f"{format_percentile(pct_a[c] * 100)} ({percentile_tier(pct_a[c] * 100)})"
                for c in feature_columns
            ],
            name_b: [
                f"{format_percentile(pct_b[c] * 100)} ({percentile_tier(pct_b[c] * 100)})"
                for c in feature_columns
            ],
        })
        st.dataframe(pct_table, hide_index=True, width="stretch")
        st.caption(
            f"Percentile among {len(group_df)} {position_group.lower()}s in the current pool — "
            "raw per-90 rates, not league-normalised (see \"About & Roadmap\"). Higher is always "
            "better here" + (
                ", including Goals Conceded — fewer goals conceded is flipped to read as a "
                "higher percentile, not a lower one."
                if position_group == "Goalkeeper" else "."
            )
        )

    st.subheader("Finishing — is the output real?")
    fin_cols = st.columns(2)
    for col, name, team in zip(fin_cols, [name_a, name_b], [team_a, team_b]):
        xg_row = xg_table[(xg_table["player"] == name) & (xg_table["team"] == team)]
        with col:
            st.markdown(f"**{name}**")
            if xg_row.empty:
                st.caption("No logged shots in the xG training set.")
            else:
                row = xg_row.iloc[0]
                xg_metric_cols = st.columns(3)
                xg_metric_cols[0].metric("Goals", int(row["goals"]))
                xg_metric_cols[1].metric("xG", f"{row['total_xg']:.1f}")
                xg_metric_cols[2].metric("G-xG", f"{row['xg_diff']:+.1f}")


def render_about_and_roadmap(per90, metrics):
    """Render the "About & Roadmap" view: framework explanation, how to use, what's built, what's
    next, and — behind a collapsed expander — the full methodology justification for the model
    numbers.

    Headline stats here are deliberately whole-number counts (shots, players, tournaments) rather
    than decimal model-evaluation scores (ROC-AUC, Brier, silhouette) — 2026-07-13 pitch-prep ask:
    the at-a-glance numbers should be things Guilherme can say confidently without notes, while the
    decimal statistics (which need methodology context to defend under questioning) live only in
    the "Methodology" expander below, explained alongside how they were computed, not bare.
    """
    n_generalisation_shots = sum(v["n_shots"] for v in metrics["xg_generalisation"].values())
    n_tournaments = len(metrics["xg_generalisation"])
    peaks = [group["best_silhouette"] for group in metrics["similarity"]["groups"].values()]
    n_goalkeepers = int((per90["position_group"] == "Goalkeeper").sum())

    st.title(f"{BRAND_ICON} Player Evaluation Framework")
    st.caption(f"*{SLOGAN}*")
    st.markdown(
        "A recruitment-led player evaluation tool over StatsBomb open data — two independent ML "
        "models, nothing scraped live, everything reproducible via `python -m src.pipeline`. "
        "**Two questions, one screen:**"
    )
    col_scouting, col_valuation = st.columns(2)
    with col_scouting:
        st.markdown("**🔍 Who plays like this player?** *(scouting lens)*")
        st.caption(
            "K-means clustering on standardised per-90 stats, per position group. Ranks every "
            "other player by how close their statistical profile is — click a match to jump "
            "straight into their own page."
        )
    with col_valuation:
        st.markdown("**📊 Is their output real, or luck?** *(valuation lens)*")
        st.caption(
            "Logistic regression scores every shot's quality from its geometry and context. "
            "Goals minus expected goals (xG) separates a genuine step up from a hot streak likely "
            "to regress — or a player creating good chances but unlucky not to convert them."
        )

    st.subheader("What's been built")
    built_cols = st.columns(4)
    built_cols[0].metric("Competitions", f"{per90['competition'].nunique()}")
    built_cols[1].metric("Players in the pool", f"{len(per90):,}")
    built_cols[2].metric(
        "Shots evaluated", f"{metrics['xg']['n_train_shots'] + n_generalisation_shots:,}",
        help=f"{metrics['xg']['n_train_shots']:,} used to train the xG model, plus "
        f"{n_generalisation_shots:,} more held out for testing — never trained on — across "
        f"{n_tournaments} different tournaments. See Methodology below for how each one scored.",
    )
    built_cols[3].metric(
        "Tournaments tested on", f"{n_tournaments}",
        help=f"The trained xG model is checked against {n_tournaments} held-out tournaments it never "
        "saw during training (men's and women's), not just one — see Methodology below for the "
        "per-tournament breakdown.",
    )
    st.caption(
        "Also: a live deployed app (no local setup needed), a reproducible one-command pipeline, "
        "continuous integration on every change, and a data-provenance manifest. Full numeric "
        "justification for every claim on this page is in **Methodology** below."
    )

    st.subheader("How the two lenses combine")
    st.markdown(
        "> A club's striker is leaving and the analyst needs a replacement on a smaller budget.\n"
        ">\n"
        "> 1. **Similarity:** input the departing striker → get a shortlist of statistically "
        "similar forwards.\n"
        "> 2. **Valuation:** for each name on that shortlist, check goals minus xG. One scored a "
        "lot last season but is well over his xG — a likely finishing spike, due to regress. "
        "Another scored less but is under his xG — creating good chances, unlucky not to convert.\n"
        "> 3. **Shortlist:** the second player is the better-value target — similar playing style, "
        "output suppressed by variance rather than inflated by it.\n"
        ">\n"
        "> Similarity narrows the field by *style*; xG corrects for *luck*. Neither answers the "
        "question alone."
    )

    with st.expander("How to use this app", expanded=True):
        st.markdown(
            "1. **Pick a view** in the sidebar — *Player explorer* (one player, deep dive), "
            "*Leaderboard* (browse/sort everyone in the current filters), or *Compare players* "
            "(two players side by side).\n"
            "2. **Narrow with the sidebar filters** — position group and competition are both "
            "optional (Player explorer/Leaderboard only; Compare players searches the whole pool).\n"
            "3. **Start typing a player's name** — the list filters live as you type, no need to "
            "press Enter.\n"
            "4. On a player's page: their **radar** (pick which stats form the spokes), "
            "**signature stats** for their position, **market value** (men's competitions only), "
            "and the ranked **\"Players like X\"** list.\n"
            "5. **Click a row** in the \"players like X\" table to jump straight to that player — "
            "a recursive drill-down, not a static list.\n"
            "6. For a Premier League 2015/16 player (the one competition in both the xG training "
            "set and this pool), see their **Finishing** panel: goals vs. expected goals, "
            "plus a shot map."
        )

    st.subheader("Data used")
    st.markdown(
        "All open data — **StatsBomb** event data, **SkillCorner** tracking data, and (new) "
        "**Transfermarkt** market values via a maintained open mirror. No paid licence, nothing "
        "scraped live; the app only reads precomputed tables built by `python -m src.pipeline` / "
        "`python -m src.app_data`.\n\n"
        f"- **Similarity pool, {per90['competition'].nunique()} competitions:** Premier League, "
        "La Liga, Serie A, Ligue 1 (all 2015/16); Frauen-Bundesliga, FA Women's Super League, "
        "Liga F, Serie A Women (all 2023/24) and NWSL 2023 — every full league season StatsBomb's "
        "free tier has.\n"
        "- **xG training set:** Premier League 2015/16 + Bayer Leverkusen 2023/24 — a different "
        "league and country from the test set below, on purpose.\n"
        "- **xG generalisation tests, 6 tournaments never trained on:** UEFA EURO 2024 (the "
        "headline test), FIFA World Cup 2022, Africa Cup of Nations 2023, Copa América 2024, and "
        "two women's tournaments — FIFA Women's World Cup 2023 and UEFA Women's EURO 2025.\n"
        "- **Market value:** Transfermarkt valuations for the four men's competitions above (that "
        "mirror has no women's-football coverage at all), matched to a StatsBomb player by name "
        "(StatsBomb's own popular name for him, e.g. \"Koke\", or his full name) and then by club "
        "— there's no shared ID between the two sources, so a player who can't be pinned to "
        "exactly one Transfermarkt profile at his club is left blank rather than guessed (see "
        "\"What's already shipped, and what's next\" below).\n"
        "- **SkillCorner tracking data (A-League):** a standalone physical-metrics demo (distance, "
        "high-speed running, sprints per 90) — no player overlap with the datasets above yet, so "
        "it doesn't feed either model.\n\n"
        "Full dataset-by-dataset detail, including honest caveats about what each competition "
        "actually contains: "
        "[DATA.md](https://github.com/GuiPadinha/football-analytics-portfolio/blob/main/docs/DATA.md)."
    )

    st.subheader("How each model works")
    st.markdown(
        "**Similarity (scouting lens).** Every player's per-90 stats — shots, key passes, "
        "tackles, progressive passes, and more (a different set for goalkeepers: saves, goals "
        "conceded, claims, punches, sweeper actions) — are first **league-normalised** (each stat expressed as standard "
        "deviations above/below that player's own competition's average, so a Bundesliga rate "
        "isn't compared raw to a WSL one), then split by position group and grouped with "
        "**K-means clustering** — outfield players and goalkeepers alike. \"Players like X\" "
        "doesn't actually use the cluster label: it ranks every other player in the same group by "
        "raw **Euclidean distance** in that same league-normalised space, a continuous measure "
        "rather than a same-cluster/different-cluster cutoff. **PCA** compresses the same features "
        "to 2D for the cluster scatterplot in the project notebooks.\n\n"
        "**Valuation (luck-vs-skill lens).** A **logistic regression** scores every shot from its "
        "geometry (distance and angle to goal), how it was struck (header vs. foot, first-time, "
        "under pressure), how it was created (cross, through-ball, cut-back, or unassisted), and "
        "the game state (score difference, penalty, free-kick). It's trained once on league data, "
        "then scored — never retrained — against tournaments it has never seen, to check the "
        "ranking still holds outside its training league."
    )

    st.subheader("What's already shipped, and what's next")
    st.markdown(
        f"**Done:** the full similarity + xG pipeline across {per90['competition'].nunique()} "
        "competitions, a leaderboard view "
        "with name/position filters, clickable similar-player drill-down, penalty-aware goal "
        "totals, goalkeepers wired in with their own feature set (saves, goals conceded, claims, "
        "punches, sweeper actions, plus save %) and K-means clustered into style archetypes like the outfield "
        "groups, league-normalised similarity (each stat compared to the player's own competition "
        "before it's compared across leagues), a **side-by-side player comparison view**, "
        "**Transfermarkt market value** matched onto \"players like X\" and the Leaderboard, and "
        "this app deployed live.\n\n"
        "**Open, small:** the league normalisation is a relative (z-score) adjustment, not a true "
        "competitiveness rating — there's no external league-strength data behind it, so it "
        "assumes each league's stat distribution is roughly comparable in shape, not that the "
        "leagues are equally strong. Market-value matching is name-based (no shared player ID "
        "exists between StatsBomb and Transfermarkt), and a match is kept only if Transfermarkt "
        "also places the player at the same club that season. A real match can be missed (left "
        "blank, never guessed), e.g. a loanee valued at his parent club; women's-"
        "league players have no market value at all, since the Transfermarkt mirror used here only "
        "covers men's football.\n\n"
        "**Bigger modelling upgrades:** uncertainty ranges on the xG number instead of one point "
        "estimate; a smarter distance metric for similarity (today's treats correlated stats — "
        "e.g. tackles and interceptions — as independent, which double-counts overlapping skill); "
        "shot context from player-tracking freeze-frames (360°-context xG, building on the same "
        "kind of tracking data already demoed for physical metrics).\n\n"
        "**A third lens, not started:** a **\"performance under pressure\"** module — do players "
        "who perform well in high-stakes league moments (title races, relegation battles, derbies) "
        "also perform well in tournaments? There's a real 51-player overlap between one league "
        "training squad and a EURO 2024 squad to test this against, but it needs external "
        "match-importance data StatsBomb doesn't provide (league-table position, rivalry context), "
        "and has to be framed as a correlation check, not a causal one — tournament squads are "
        "themselves selection-biased."
    )
    st.caption(
        "Full phase-by-phase detail: "
        "[ROADMAP.md](https://github.com/GuiPadinha/football-analytics-portfolio/blob/main/docs/ROADMAP.md)"
    )

    with st.expander("Methodology — the numbers, and how we got them"):
        st.markdown(
            f"""
**xG model.** Logistic regression, trained on **{metrics['xg']['n_train_shots']:,} shots**
(Bayer Leverkusen 2023/24 + Premier League 2015/16), a {metrics['xg']['train_goal_rate']:.0%} goal
rate in training. Tested on **UEFA EURO 2024** — a tournament the model never trained on, a
deliberate league-to-tournament distribution shift.

**ROC-AUC** measures how often the model correctly ranks a more dangerous shot above a less
dangerous one (1.0 = always correct, 0.5 = a coin flip). On the held-out EURO 2024 shots:
**{metrics['xg']['logistic']['test_roc_auc']}** — and a baseline ladder shows the model earns that
number rather than getting there for free: guessing the training goal rate for every shot scores
{metrics['xg']['baseline_ladder_test_roc_auc']['no_skill']} (no skill); shot geometry alone
(distance + angle to goal) already reaches {metrics['xg']['baseline_ladder_test_roc_auc']['geometry_only']};
the full model (adds body part, assist type, game state) reaches
{metrics['xg']['baseline_ladder_test_roc_auc']['full']}.

**Generalisation check (Phase 4c):** the same trained model, never retrained, scored against
{n_tournaments} held-out tournaments totalling **{n_generalisation_shots:,} shots** it never saw:
            """
        )
        gen_table = pd.DataFrame(metrics["xg_generalisation"].values()).sort_values(
            "roc_auc", ascending=False
        )
        st.dataframe(
            gen_table[["label", "n_shots", "roc_auc", "brier_score"]].rename(columns={
                "label": "Tournament", "n_shots": "Shots", "roc_auc": "ROC-AUC",
                "brier_score": "Brier score",
            }),
            hide_index=True, width="stretch",
        )
        fig, ax = plt.subplots(figsize=(7, 0.6 * len(gen_table) + 1.5))
        plot_xg_generalisation_bar(
            gen_table, accent_color=ACCENT_ORANGE, grid_color=GRID_LINE, ax=ax
        )
        st.pyplot(fig)
        plt.close(fig)
        st.caption(
            f"The ranking holds on every tournament checked (ROC-AUC {gen_table['roc_auc'].min():.2f}"
            f"–{gen_table['roc_auc'].max():.2f}), including two women's tournaments — a men's-trained "
            "model meeting a second distribution shift. A higher Brier score mostly tracks a higher "
            "goal rate, not a bias (see MODULES.md for goals vs. expected goals per tournament)."
        )

        st.markdown(
            f"""
**Similarity model.** K-means, K={metrics['similarity']['kmeans_k_used']} clusters per position
group, minimum {metrics['similarity']['min_minutes']} minutes played to qualify — for the three
outfield groups (Defender/Midfielder/Forward), on the notebook/pipeline's single-competition (PL
2015/16) scope. Silhouette score (cluster tightness, −1 to 1) peaks low at K=2 for every one of
them ({min(peaks):.2f}–{max(peaks):.2f}) — reported honestly rather than hidden: play styles within a position are a
soft continuum, not sharply separated blobs. K=4 is used anyway, for archetype granularity,
against the metric's own preference. Goalkeepers now get the same treatment on the app's wider
multi-league pool ({n_goalkeepers} keepers): silhouette also peaks low, and K=4 is kept for the
same archetype-granularity reason.

**Known limitations, stated plainly:** cross-league normalisation is a *relative*, data-only fix
(each stat expressed as standard deviations above/below the player's own competition's average),
not an external competitiveness rating — there is no scraped league-strength index in this
project's data, so it assumes each league's stat distribution has a broadly similar shape, not
that the leagues are equally strong. StatsBomb's free data also has no recent men's top-flight
season (2015/16 is the newest full men's league available; 2023/24 women's leagues are the newest
full-season data anywhere in this project).
            """
        )
