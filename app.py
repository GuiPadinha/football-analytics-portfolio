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

Goalkeepers (2026-07-13) are wired in with their own feature set (saves, shots faced, goals
conceded, claims, punches, sweeper actions, save %) — none of the outfield `PER90_FEATURE_COLUMNS`
apply to them, so several spots below branch on `position_group == "Goalkeeper"` rather than
assuming exactly the three outfield groups. As of a same-day follow-up pass, goalkeepers are
K-means clustered (K=4, same silhouette-informed-but-archetype-driven call as the outfield
groups) and share the Style archetype panel with them — see `src/app_data.py`'s
`_cluster_position_groups`.

Cross-league similarity normalisation (also this pass): clustering and "players like X" both run
on `similarity.normalize_within_competition`'s league-adjusted (`_lz`-suffixed) features, not the
raw per-90 rates — a player's standing is compared to their *own competition's* peers before ever
being compared across leagues. Radar axes, percentiles, and signature stats stay on the raw,
literal per-90 rates on purpose — those are "how good is this player, in real units" displays,
not a similarity computation, so a fan reads an actual rate, not a z-score.

Run locally: streamlit run app.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap

from src.similarity import (
    ACTION_COLUMNS,
    GK_ACTION_COLUMNS,
    GK_PER90_FEATURE_COLUMNS,
    GK_PER90_LEAGUE_Z_COLUMNS,
    PER90_FEATURE_COLUMNS,
    PER90_LEAGUE_Z_COLUMNS,
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
    manually (see `render_leaderboard`'s None-cell fix for why it can't use that helper
    directly): `DIVERGING_CMAP` sampled at `value`'s position between `-span` and `+span`.
    """
    normalized = 0.5 if span == 0 else (value + span) / (2 * span)
    r, g, b, a = DIVERGING_CMAP(min(max(normalized, 0.0), 1.0))
    return f"background-color: rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, {a:.2f})"

# Brand identity (2026-07-13 visual pass) — one icon/slogan pair reused everywhere (browser tab,
# sidebar, every page header) so the app reads as one product rather than a stack of bare
# st.title() calls with no shared identity.
BRAND_ICON = "⚽"
SLOGAN = "Scout by data, not by reputation."

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
# Goalkeeper (2026-07-13) draws from GK_ACTION_COLUMNS instead — a keeper's outfield rates
# (tackles, key passes, ...) are meaninglessly near zero, see src/similarity.py's
# build_goalkeeper_per90_features docstring. save_pct is shown separately (a ratio, not a
# per-90 rate with its own raw-total counterpart the way these three are), same pattern as the
# penalty breakdown below the outfield signature stats.
SIGNATURE_STATS_BY_POSITION = {
    "Defender": ["tackles_p90", "interceptions_p90", "clearances_p90"],
    "Midfielder": ["key_passes_p90", "assists_p90", "progressive_passes_p90"],
    "Forward": ["non_penalty_goals_p90", "assists_p90", "shots_p90"],
    "Goalkeeper": ["saves_p90", "goals_conceded_p90", "claims_p90"],
}

STAT_LABELS = {
    col: col.replace("_p90", "").replace("_", " ").title()
    for col in PER90_FEATURE_COLUMNS + GK_PER90_FEATURE_COLUMNS
}
STAT_LABELS["save_pct"] = "Save %"
# Cluster profiling (Style archetype panel) reads the league-normalised `_lz` columns, not the
# raw `_p90` ones (see the module docstring) — same clean label either way, so a reader sees
# "Tackles" whether the underlying number is a per-90 rate or a league z-score.
STAT_LABELS.update({f"{col}_lz": label for col, label in list(STAT_LABELS.items())})


def percentile_tier(goodness_pct):
    """Plain-language read of a 0-100 goodness percentile (`similarity.goodness_percentiles`).

    A bare "72nd percentile" still asks the reader to supply their own judgment of what counts
    as good — and for the app's one lower-is-better stat (a goalkeeper's goals conceded), the
    raw percentile actively read backwards before `goodness_percentiles` fixed the direction.
    These bands are the FBref/StatsBomb scouting-report convention, so the number never has to
    carry the "is this good?" call by itself. Every caller here already passes a
    goodness-adjusted percentile, never a raw one.
    """
    if goodness_pct >= 95:
        return "Elite"
    if goodness_pct >= 80:
        return "Very good"
    if goodness_pct >= 60:
        return "Good"
    if goodness_pct >= 40:
        return "Average"
    if goodness_pct >= 20:
        return "Below average"
    return "Poor"


def format_percentile(goodness_pct):
    """"72nd", not "72th" — every percentile display in the app goes through this so the ordinal
    suffix is never wrong (11th/12th/13th are the exception to 1st/2nd/3rd, handled by the
    `10 <= n % 100 <= 20` guard below).
    """
    n = round(goodness_pct)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def style_intensity_label(z):
    """Plain-language read of one cluster-vs-population z-score (`similarity.profile_clusters`)
    for the Style archetype panel's bar chart — same "lead with the word, not the Greek letter"
    fix as `percentile_tier`, prompted by exactly that feedback: "+1.4σ" reads as jargon, "Much
    more (+1.4σ)" reads as English with the number kept for whoever wants it. Unlike a
    percentile, a z-score here has no good/bad direction (see the panel's own "not a ranking"
    caption) — the word describes *how unusual*, not *how good*.
    """
    # Round before thresholding, not after: two bars that both display "0.3σ" must always get the
    # same word, even if their unrounded values (e.g. 0.296 and 0.304) sit on opposite sides of a
    # threshold — a mismatch there would look like a bug, not a rounding artifact.
    rounded = round(z, 1)
    magnitude = abs(rounded)
    if magnitude < 0.3:
        return f"Typical ({magnitude:.1f}σ)"
    strength = "far" if magnitude >= 1.5 else "much" if magnitude >= 0.8 else "somewhat"
    direction = "more" if rounded > 0 else "less"
    return f"{strength.capitalize()} {direction} ({rounded:+.1f}σ)"

st.set_page_config(page_title="Player Evaluation Framework", page_icon=BRAND_ICON, layout="wide")


@st.cache_data
def load_artifacts():
    """Load the precomputed app_data/ tables plus the repo's metrics.json.

    Cached by Streamlit so the (small) Parquet reads happen once per server process, not once
    per user interaction — every widget change reruns this script top to bottom.

    `market_value.parquet` is loaded defensively (empty frame if missing) rather than assumed
    present: `app_data.build_app_artifacts(with_market_value=False)` is a real, supported way to
    run an otherwise-offline build (see that function's docstring), so a market-value-less
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


def format_market_value(eur):
    """Human-readable market value string ("€30.0M" / "€850k"), or "" for a missing value.

    Shared by every market-value display in the app (player page, "players like X" table,
    Leaderboard, Compare players) so the same number always reads the same way.
    """
    if pd.isna(eur):
        return ""
    if eur >= 1_000_000:
        return f"€{eur / 1_000_000:.1f}M"
    return f"€{eur / 1_000:.0f}k"


def lookup_market_value(market_value, player, team):
    """Return the matched market-value row for one (player, team), or `None` if unresolved."""
    match = market_value[(market_value["player"] == player) & (market_value["team"] == team)]
    return match.iloc[0] if len(match) else None


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

    xG / G-xG are left-joined from the flagship xG table and blank for anyone outside Module A's
    training set (PL 2015/16 + Leverkusen) — most of the wider similarity pool — rather than
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
        "- **xG / G-xG** — only populated for the xG model's own training set (Premier League "
        "2015/16 + Bayer Leverkusen 2023/24); blank elsewhere, not faked. Sort G-xG ascending for "
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

    # Blank xG/G-xG cells (2026-07-13, fixed this pass): `column_config.NumberColumn` renders a
    # missing *numeric* cell as the literal text "None" no matter what a Styler's `na_rep` or its
    # own `format=` says — confirmed as a real, still-open Streamlit limitation (GitHub issue
    # #7360: "Allow configuration of missing value placeholder in st.dataframe"), not something
    # three previous fix attempts (nullable Float64, Styler na_rep, dropping column_config's
    # `format=`) got wrong — see docs/ML_TOOLING.md for that full account. The only real fix is
    # at the data layer: xG/G-xG become hand-formatted **text** columns (blank string for
    # missing, not NaN) instead of numeric ones, so there is no null numeric cell for the grid to
    # special-case. The diverging background colour is computed manually (`_diverging_css`) from
    # the still-numeric `xg_diff` values *before* they're overwritten by the display strings, so
    # the colour survives the dtype change even though `Styler.background_gradient` itself needs
    # numeric input and can no longer be used directly on the (now text) G-xG column.
    #
    # Known trade-off, stated plainly: Streamlit's interactive "click a header to sort" now sorts
    # these two columns lexically (text), not numerically — e.g. "+10.5" sorts before "+4.2".
    # There is no column_config option to declare "sort column A, display column B" in this
    # Streamlit version, so a perfectly numeric click-sort and a blank-for-missing cell are not
    # simultaneously achievable here; the default row order (sorted by Goals, below) is
    # unaffected, and this is a materially smaller issue than every blank cell reading "None".
    gxg_raw = board["G-xG"]
    if gxg_raw.notna().any():
        gxg_span = gxg_raw.abs().max() or 1.0
        gxg_colors = gxg_raw.map(lambda v: "" if pd.isna(v) else _diverging_css(v, gxg_span))
    else:
        gxg_colors = None

    board["xG"] = board["xG"].map(lambda v: "" if pd.isna(v) else f"{v:.1f}")
    board["G-xG"] = gxg_raw.map(lambda v: "" if pd.isna(v) else f"{v:+.1f}")
    # Same "hand-format to text, never a null numeric cell" fix as xG/G-xG above — market value
    # is blank just as often (men's competitions only, and only where name-matching resolved).
    board["Market value"] = board["Market value"].map(format_market_value)

    board_style = board.style
    if gxg_colors is not None:
        board_style = board_style.apply(lambda _: gxg_colors, subset=["G-xG"])

    st.dataframe(
        board_style,
        hide_index=True,
        width="stretch",
        column_config={
            "Minutes": st.column_config.NumberColumn(format="%d"),
            "Goals": st.column_config.NumberColumn(format="%d"),
            "Non-pen goals": st.column_config.NumberColumn(format="%d"),
            "Assists": st.column_config.NumberColumn(format="%d"),
            "xG": st.column_config.TextColumn(help="Flagship xG set only"),
            "G-xG": st.column_config.TextColumn(
                help="Goals minus xG. Positive = outscoring chance quality (expect regression); "
                "negative = under-converting good chances (possible buy-low). Flagship set only.",
            ),
            "Market value": st.column_config.TextColumn(
                help="Transfermarkt valuation, roughly as of this season (see \"About & Roadmap\" "
                "for the matching caveats). Men's competitions only; blank where unmatched.",
            ),
        },
    )
    st.caption(
        "xG and G-xG are blank for players outside the xG training set (Premier League 2015/16 + "
        "Bayer Leverkusen 2023/24) — the similarity pool is wider than the xG model's, so most "
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
        if position_group == "Goalkeeper":
            feature_columns = GK_PER90_FEATURE_COLUMNS
        else:
            feature_columns = PER90_FEATURE_COLUMNS
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
        help="The trained xG model is checked against 4 held-out tournaments it never saw during "
        "training, not just one — see Methodology below for the per-tournament breakdown.",
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
            "6. If the player has logged shots in the xG training set (Premier League 2015/16 + "
            "Bayer Leverkusen 2023/24), see their **Finishing** panel: goals vs. expected goals, "
            "plus a shot map."
        )

    st.subheader("Data used")
    st.markdown(
        "All open data — **StatsBomb** event data, **SkillCorner** tracking data, and (new) "
        "**Transfermarkt** market values via a maintained open mirror. No paid licence, nothing "
        "scraped live; the app only reads precomputed tables built by `python -m src.pipeline` / "
        "`python -m src.app_data`.\n\n"
        "- **Similarity pool, 6 competitions:** Premier League, La Liga, Serie A, Ligue 1 (all "
        "2015/16), Frauen-Bundesliga and the FA Women's Super League (both 2023/24) — the newest "
        "full season StatsBomb's free tier has for each league.\n"
        "- **xG training set:** Premier League 2015/16 + Bayer Leverkusen 2023/24 — a different "
        "league and country from the test set below, on purpose.\n"
        "- **xG generalisation tests, 4 tournaments never trained on:** UEFA EURO 2024 (the "
        "headline test), FIFA World Cup 2022, Africa Cup of Nations 2023, Copa América 2024.\n"
        "- **Market value:** Transfermarkt valuations for the four men's competitions above (that "
        "mirror has no women's-football coverage at all), matched to a StatsBomb player by name — "
        "there's no shared ID between the two sources, so an unresolved or ambiguous name is left "
        "blank rather than guessed (see \"What's already shipped, and what's next\" below).\n"
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
        "tackles, progressive passes, and more (a different set for goalkeepers: saves, shots "
        "faced, claims) — are first **league-normalised** (each stat expressed as standard "
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
        "**Done:** the full similarity + xG pipeline across 6 competitions, a leaderboard view "
        "with name/position filters, clickable similar-player drill-down, penalty-aware goal "
        "totals, goalkeepers wired in with their own feature set (saves, shots faced, goals "
        "conceded, claims, save %) and K-means clustered into style archetypes like the outfield "
        "groups, league-normalised similarity (each stat compared to the player's own competition "
        "before it's compared across leagues), a **side-by-side player comparison view**, "
        "**Transfermarkt market value** matched onto \"players like X\" and the Leaderboard, and "
        "this app deployed live.\n\n"
        "**Open, small:** the league normalisation is a relative (z-score) adjustment, not a true "
        "competitiveness rating — there's no external league-strength data behind it, so it "
        "assumes each league's stat distribution is roughly comparable in shape, not that the "
        "leagues are equally strong. Market-value matching is name-based (no shared player ID "
        "exists between StatsBomb and Transfermarkt) — a real match can be missed (left blank, "
        "never guessed) when two different real players share a name and broad position; women's-"
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
        "[INITIATIVE.md](https://github.com/GuiPadinha/football-analytics-portfolio/blob/main/docs/INITIATIVE.md) · "
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
            "EURO 2024 is the *floor* of the four, not a fluke — the model holds up as well or "
            "better on every other tournament it's been checked against."
        )

        st.markdown(
            f"""
**Similarity model.** K-means, K={metrics['similarity']['kmeans_k_used']} clusters per position
group, minimum {metrics['similarity']['min_minutes']} minutes played to qualify — for the three
outfield groups (Defender/Midfielder/Forward), on the notebook/pipeline's single-competition (PL
2015/16) scope. Silhouette score (cluster tightness, −1 to 1) peaks low at K=2 for every one of
them (~0.22–0.26) — reported honestly rather than hidden: play styles within a position are a
soft continuum, not sharply separated blobs. K=4 is used anyway, for archetype granularity,
against the metric's own preference. Goalkeepers now get the same treatment on the app's wider
6-competition pool (124 keepers): silhouette also peaks at K=2 (~0.22) and K=4 is kept for the
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


per90, xg_table, shots, market_value, metrics = load_artifacts()

# "Similar player" row-click drill-down (2026-07-09 backlog item): clicking a row in the
# "Players like X" table (near the bottom of this script) stashes a (player, team) pair in
# session_state and calls st.rerun(). This block is what that rerun lands on — it runs before
# any widget below is created, which is the only point Streamlit allows a script to set a
# widget's value programmatically (by pre-seeding st.session_state[key] ahead of the matching
# st.xxx(key=...) call). Resets position/competition filters and the search box so the target
# player can't be hidden by whatever the user had filtered/typed before the click.
if "jump_to_player" in st.session_state:
    jump_player, jump_team = st.session_state.pop("jump_to_player")
    jump_match = per90[(per90["player"] == jump_player) & (per90["team"] == jump_team)]
    if not jump_match.empty:
        st.session_state["view_radio"] = "Player explorer"
        st.session_state["position_filter"] = "All"
        st.session_state["competition_filter"] = "All"
        jump_competition = jump_match.iloc[0]["competition"]
        st.session_state["player_pick_All_All"] = f"{jump_player} ({jump_team}) · {jump_competition}"

# Brand header (2026-07-13 visual pass): icon + name + slogan, then a few live quick-facts so the
# sidebar carries more than just filter widgets — the same "what's this app made of" numbers as
# the About & Roadmap page's headline tiles, computed live rather than hardcoded so they can't
# drift from the data the way a copy-pasted number in a doc can.
st.sidebar.markdown(f"## {BRAND_ICON} Player Evaluation Framework")
st.sidebar.caption(f"*{SLOGAN}*")
st.sidebar.divider()

n_goalkeepers = int((per90["position_group"] == "Goalkeeper").sum())
sidebar_metric_cols = st.sidebar.columns(2)
sidebar_metric_cols[0].metric("Players", f"{len(per90):,}")
sidebar_metric_cols[1].metric("Competitions", per90["competition"].nunique())
st.sidebar.caption(
    f"StatsBomb open data, 2015/16-2023/24 · includes {n_goalkeepers} goalkeepers · "
    f"{metrics['xg']['n_train_shots']:,} shots power the xG model"
)
st.sidebar.divider()

view = st.sidebar.radio(
    "View", ["Player explorer", "Leaderboard", "Compare players", "About & Roadmap"],
    help="Player explorer: one player's radar, similar players and finishing. "
    "Leaderboard: browse and sort every player in the current filters. "
    "Compare players: two players side by side. "
    "About & Roadmap: what this is, how to use it, what's built, and what's next.",
    key="view_radio",
)
if view != "About & Roadmap":
    st.sidebar.caption("New here? Start with **About & Roadmap** for the full story.")
st.sidebar.divider()
st.sidebar.caption("[Source on GitHub](https://github.com/GuiPadinha/football-analytics-portfolio)")

# "About & Roadmap" is a static informational page, not a player/filter view — branch and stop
# here, before the position/competition filter widgets below, so its sidebar stays uncluttered
# (2026-07-13, pitch-prep pass: promoted from an always-visible main-pane banner into its own
# tab, per feedback that it deserved a dedicated place rather than repeating on every view).
if view == "About & Roadmap":
    render_about_and_roadmap(per90, metrics)
    st.stop()

position_filter = st.sidebar.selectbox(
    "Filter by position (optional)", ["All"] + sorted(per90["position_group"].unique()),
    key="position_filter",
)
competition_filter = st.sidebar.selectbox(
    "Filter by competition (optional)", ["All"] + sorted(per90["competition"].unique()),
    key="competition_filter",
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
    render_leaderboard(searchable, xg_table, market_value)
    st.stop()

# Compare players is its own two-player pane, not filtered by the sidebar's position/competition
# selectors (a comparison is meaningful across positions/competitions too, unlike the shared
# per-90 feature space "players like X"/clustering need) — it reads the full, unfiltered `per90`.
if view == "Compare players":
    render_compare_players(per90, xg_table, market_value)
    st.stop()

render_page_header("Player explorer")
st.markdown(
    "One player at a time: pick anyone below to see their **signature stats**, a **radar** "
    "against their position-group peers, a ranked **\"Players like X\"** shortlist you can click "
    "through (a recursive drill-down, not a static list), and — for players inside the xG "
    "training set — a **Finishing** panel comparing goals to expected goals.\n\n"
    "Narrow the pool with the sidebar's position/competition filters, then start typing a name "
    "below — the list filters live as you type."
)

if searchable.empty:
    st.warning("No players match the current filters.")
    st.stop()

# Live-filtering search (2026-07-14 pass, replacing a two-widget text_input + selectbox combo):
# driving the *running* app with Playwright showed that combo felt broken — st.text_input only
# reruns the script on Enter/blur, so typing produced no visible change (the match count and the
# selectbox below both sat frozen on the old query) even though the box looked like a live search
# field. st.selectbox's own dropdown already does instant client-side type-to-filter, no server
# roundtrip needed to narrow the list — the same interaction VS Code's Quick Open or GitHub's
# file finder use — so one widget now does the whole job.
#
# This does revisit a shape PRODUCT_SPEC.md records as explicitly rejected once already
# (2026-07-05, round 1: a bare selectbox "read as a dropdown-first interaction, not a search
# box," which is why round 2 replaced it with the text_input + selectbox combo this pass just
# removed). Two things are different this time, not just a straight revert: (a) today's complaint
# was specifically about live-as-you-type behaviour, which a selectbox's built-in filtering
# actually delivers and text_input never did; (b) `index=None` below means the box starts empty
# with placeholder text, never pre-filled with a value the way round 1's did — round 1 always
# showed some already-selected player, which is a large part of what made it read as "a dropdown
# with a choice already made" rather than "an empty box waiting for input." Confirmed with the
# user before making this change, given the documented history.
player_by_label = {
    f"{player} ({team}) · {competition}": (player, team, position_group, competition)
    for player, team, position_group, competition in zip(
        searchable["player"], searchable["team"], searchable["position_group"], searchable["competition"]
    )
}
labels = sorted(player_by_label)
picked_label = st.selectbox(
    f"Search for a player ({len(labels):,} in the current filters)",
    labels, index=None, placeholder="Start typing a name...",
    # Keyed on the sidebar filters that change the option set (position/competition), so the
    # widget always resets to a fresh default instead of Streamlit trying to preserve a prior
    # selection that may no longer be a valid option (ML_TOOLING.md's selectbox-with-changing-
    # options gotcha). No query in the key anymore — there's no separate query state to track.
    key=f"player_pick_{position_filter}_{competition_filter}",
)
if picked_label is None:
    st.info("Search for a player above to see their profile.")
    st.stop()
player_name, team_name, position_group, competition_name = player_by_label[picked_label]
group_df = per90[per90["position_group"] == position_group].reset_index(drop=True)

# Goalkeepers use a completely disjoint feature set from the three outfield groups (see the
# module docstring) — everything below that used to hardcode PER90_FEATURE_COLUMNS/ACTION_COLUMNS
# now branches on position_group instead.
if position_group == "Goalkeeper":
    position_action_columns = GK_ACTION_COLUMNS
    position_feature_columns = GK_PER90_FEATURE_COLUMNS
    position_feature_columns_lz = GK_PER90_LEAGUE_Z_COLUMNS
else:
    position_action_columns = ACTION_COLUMNS
    position_feature_columns = PER90_FEATURE_COLUMNS
    position_feature_columns_lz = PER90_LEAGUE_Z_COLUMNS

# Radar axes (moved here 2026-07-13, was a fixed-options sidebar widget declared before the
# player was even picked — worked only because all three outfield groups shared one feature
# set). Options now depend on position_group, so this has to render after it's known; `key`
# scoped to position_group so switching between an outfield player and a goalkeeper resets the
# widget to a fresh default instead of Streamlit trying to carry over a selection that may not
# exist in the new options list (same crash class as the player-picker's own key, see
# ML_TOOLING.md).
radar_axes = st.sidebar.multiselect(
    "Radar axes", position_feature_columns, default=list(position_feature_columns),
    key=f"radar_axes_{position_group}",
)

render_page_header(f"{player_name} · {team_name} · {position_group}")
st.caption(competition_name)

st.subheader(f"Signature stats for a {position_group.lower()}")
signature_cols = SIGNATURE_STATS_BY_POSITION[position_group]
player_row_full = group_df[(group_df["player"] == player_name) & (group_df["team"] == team_name)].iloc[0]
# goodness_percentiles flips goals_conceded_p90 so a bigger number always means "better than
# peers" — shared by the signature-stat cards below and the "All per-90 stats" percentile chart
# further down the page, both of which read from this one `percentiles` variable.
percentiles = goodness_percentiles(group_df[position_feature_columns].rank(pct=True).loc[player_row_full.name])

metric_cols = st.columns(len(signature_cols))
for col, stat in zip(metric_cols, signature_cols):
    raw_col = stat.replace("_p90", "")
    total = int(round(player_row_full[raw_col]))
    rate = player_row_full[stat]
    pct = percentiles[stat] * 100
    col.metric(
        STAT_LABELS[stat], f"{total:,}",
        help=f"{rate:.2f} per 90 · {format_percentile(pct)} percentile among "
        f"{position_group.lower()}s ({percentile_tier(pct)})",
    )
st.caption(
    "Season totals (not personalised to this player's strengths — a fixed set per position "
    f"group). Hover a card for the per-90 rate and percentile vs. {len(group_df)} "
    f"{position_group.lower()}s across {group_df['competition'].nunique()} competitions." + (
        " Goals Conceded's percentile is flipped so fewer conceded reads as higher, not lower."
        if position_group == "Goalkeeper" else ""
    )
)

# Penalty breakdown (2026-07-09 backlog item): signature stats show non_penalty_goals only, so a
# penalty-taker's card understates their real total. `goals` (incl. penalties) already ships in
# app_data/player_per90.parquet — display-only, computed by src/similarity.py, never fed to
# clustering/xG (see DISPLAY_COUNT_COLUMNS). Skipped for zero-goal players to avoid a "0 goals, 0
# from penalties" line cluttering every non-scorer's page. Goalkeepers have no "goals" column at
# all (NaN post-concat, see app_data.py) — `save_pct` is their equivalent extra headline number.
if position_group == "Goalkeeper":
    shots_faced = int(round(player_row_full["shots_faced"]))
    saves = int(round(player_row_full["saves"]))
    st.caption(f"**Save %: {player_row_full['save_pct']:.0%}** ({saves}/{shots_faced} shots faced)")
elif pd.notna(player_row_full.get("goals")):
    total_goals = int(round(player_row_full["goals"]))
    non_penalty_goals = int(round(player_row_full["non_penalty_goals"]))
    penalty_goals = total_goals - non_penalty_goals
    if total_goals > 0:
        penalty_note = f" ({penalty_goals} from penalties)" if penalty_goals > 0 else ""
        st.caption(f"**Goals (incl. penalties): {total_goals}**{penalty_note}")

# Market value (Phase 9): a Transfermarkt valuation, matched by name (see src/market_value.py)
# and only ever resolved for the four men's competitions in MARKET_VALUE_AS_OF_DATES - that
# mirror has no women's-football coverage at all (verified against the real data, not assumed),
# so Frauen Bundesliga/FA WSL players fall into the same "not resolved" caption as any player a
# name match genuinely failed for, rather than a separate, more alarming-sounding message.
player_market_value = lookup_market_value(market_value, player_name, team_name)
if player_market_value is not None:
    st.caption(
        f"**Market value: {format_market_value(player_market_value['market_value_eur'])}** "
        f"(Transfermarkt, as of {player_market_value['market_value_as_of']} — matched to "
        f"\"{player_market_value['tm_name']}\")"
    )
else:
    st.caption(
        "Market value: not available (no confident Transfermarkt name match, or a "
        "competition outside its coverage — see \"About & Roadmap\")."
    )

# Style archetype (2026-07-13 visual/feature pass, extended to goalkeepers + league-normalised
# in a same-day follow-up): app_data.py's build step computes a K=4 style-archetype `cluster`
# label per player — outfield and goalkeeper alike, on league-normalised features (see the module
# docstring) — but nothing in the app surfaced it until this pass. No new model here:
# `profile_clusters` (src/similarity.py, already used to name clusters in the notebooks) is a
# pure z-score readout of stats the clustering already ran on.
st.subheader("Style archetype")
cluster_id = int(player_row_full["cluster"])
cluster_profile = cached_cluster_profile(group_df, position_feature_columns_lz)
cluster_z = cluster_profile.loc[cluster_id]
cluster_peers = group_df[
    (group_df["cluster"] == cluster_id)
    & ~((group_df["player"] == player_name) & (group_df["team"] == team_name))
]
high_traits = cluster_z.sort_values(ascending=False).head(2)
low_col = cluster_z.sort_values().index[0]
# Headline sentence is plain language only (2026-07-14 pass, dropped the inline "(+1.4σ)"
# parentheticals) — feedback was that leading with a Greek letter made a genuinely simple idea
# ("this group does more of X, less of Y") read as jargon. The exact numbers still exist, just
# one click away in the expander below, for whoever wants them.
high_text = " and ".join(f"**{STAT_LABELS[c]}**" for c in high_traits.index)
st.markdown(
    f"One of **{cluster_profile.shape[0]}** style clusters found among {position_group.lower()}s "
    "in this pool (K-means on league-normalised per-90 stats — the grouping came from the "
    f"numbers alone, no role label was given to the model). This cluster does noticeably more "
    f"{high_text} and noticeably less **{STAT_LABELS[low_col]}** than other "
    f"{position_group.lower()}s — a style shared with **{len(cluster_peers)}** other players "
    "in the current pool."
)
with st.expander("See the full style breakdown"):
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(cluster_z) + 1))
    plot_diverging_bar(
        labels=[STAT_LABELS[c] for c in cluster_z.index], values=cluster_z.values, reference=0,
        label_format=style_intensity_label,
        above_color=ACCENT_ORANGE, below_color=ACCENT_BLUE, grid_color=GRID_LINE,
        xlabel="Cluster average vs. position-group average", ax=ax,
    )
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        "Each stat first expressed relative to its own competition's peers (so a Bundesliga "
        "cluster isn't just describing 'more actions than a WSL team'), then this cluster's "
        "average measured in standard deviations (σ) from the whole position group's average — "
        "the same z-score reading the project notebooks use to name clusters (e.g. high "
        "Tackles/Interceptions + low Clearances reads as a ball-winning full-back). **Not a "
        "ranking** — a low value here is a different style, not a worse one (unlike the "
        "percentile chart further down the page, which is a ranking)."
    )
if len(cluster_peers):
    with st.expander(f"Browse this archetype ({len(cluster_peers)} other players)"):
        archetype_board = cluster_peers.sort_values("minutes_played", ascending=False).head(8)
        st.caption(
            f"Top {len(archetype_board)} by minutes played, of {len(cluster_peers)} total "
            "sharing this cluster. Click a row to jump to that player."
        )
        # Same click-to-jump mechanism as the "Players like X" table below (see its comment
        # for why the key must be scoped to the current player/team, not fixed).
        archetype_selection = st.dataframe(
            archetype_board[["player", "team", "competition", "minutes_played"]].rename(
                columns={
                    "player": "Player", "team": "Team",
                    "competition": "Competition", "minutes_played": "Minutes",
                }
            ),
            hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
            key=f"archetype_table_{player_name}_{team_name}",
        )
        archetype_rows = archetype_selection.selection["rows"] if archetype_selection else []
        if archetype_rows:
            picked = archetype_board.iloc[archetype_rows[0]]
            st.session_state["jump_to_player"] = (picked["player"], picked["team"])
            st.rerun()

with st.expander(
    f"All per-90 stats ({len(position_feature_columns)} metrics, vs. {position_group.lower()} peers)"
):
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(position_feature_columns) + 1))
    plot_diverging_bar(
        labels=[STAT_LABELS[c] for c in position_feature_columns],
        values=[percentiles[c] * 100 for c in position_feature_columns],
        # label_format carries the tier word, not just the ordinal number — a bare "72nd" still
        # asks the reader to judge whether that's good; "72nd (Good)" doesn't (see
        # percentile_tier's own docstring for why this app leads with the word).
        reference=50, label_format=lambda v: f"{format_percentile(v)} ({percentile_tier(v)})",
        above_color=ACCENT_ORANGE, below_color=ACCENT_BLUE, grid_color=GRID_LINE,
        xlabel=f"Percentile within position group (n={len(group_df)}) — higher is always better",
        ax=ax,
    )
    st.pyplot(fig)
    plt.close(fig)
    if position_group == "Goalkeeper":
        st.caption(
            "Counts are from StatsBomb's `Goal Keeper` event sub-types (Shot Faced, Shot Saved, "
            "Goal Conceded, Collected, Punch, Keeper Sweeper) — save % isn't shown here since "
            "it's already above, as a ratio rather than a per-90 rate. Goals Conceded's "
            "percentile is flipped so fewer conceded reads as higher, not lower."
        )
    else:
        st.caption(
            "No pass-completion % yet, since that needs a new feature (passes attempted, not "
            "just completed) from raw events, not just a different chart. Flagged as a "
            "follow-up, not faked here. Clearances are StatsBomb's general Clearance event "
            "count, not a 'last-ditch/goal-line' sub-type — StatsBomb's schema doesn't "
            "distinguish those, so this is the closest available proxy."
        )
    with st.expander("Table view", expanded=False):
        stat_table = pd.DataFrame({
            "Stat": [STAT_LABELS[c] for c in position_feature_columns],
            "Total": [int(round(player_row_full[c])) for c in position_action_columns],
            "Per 90": [player_row_full[c] for c in position_feature_columns],
            "Percentile (numeric)": [percentiles[c] * 100 for c in position_feature_columns],
        }).sort_values("Percentile (numeric)", ascending=False)
        stat_table["Percentile"] = stat_table["Percentile (numeric)"].map(
            lambda p: f"{format_percentile(p)} ({percentile_tier(p)})"
        )
        st.dataframe(
            stat_table.drop(columns="Percentile (numeric)"), hide_index=True, width="stretch"
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
        per90, position_feature_columns_lz, player=player_name, team=team_name, n=5
    ).reset_index(drop=True)
    # Left merge preserves `similar`'s row order (needed below: `selection.rows` positions index
    # back into this same frame via `similar.iloc[...]`) - "similar profile, cheaper" is Module
    # B's original market-value pitch (see DATA.md), so this is exactly where it belongs.
    similar = similar.merge(
        market_value[["player", "team", "market_value_eur"]], on=["player", "team"], how="left"
    )
    fig, ax = plt.subplots(figsize=(7, 0.7 * len(similar) + 1))
    plot_similar_players_bar(similar, accent_color=ACCENT_ORANGE, grid_color=GRID_LINE, ax=ax)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        "Distance = Euclidean, standardised per-90 features — league-normalised (each stat "
        "expressed as standard deviations above/below this player's own competition's average) "
        "before comparing, so a cross-league match is judged on relative standing, not a raw "
        "rate compared across leagues of different competitiveness. Still an approximation, not "
        "a true competitiveness adjustment — see \"About & Roadmap\" in the sidebar."
    )
    with st.expander("Table view — click a row to jump to that player", expanded=False):
        # `similar` was reset_index(drop=True) above so its positions line up 1:1 with the
        # rendered rows Streamlit reports in `selection.rows`. A click sets `jump_to_player` and
        # reruns; the block at the very top of the script (before any widget is created) turns
        # that into a pre-seeded selectbox value — see its comment for why a rerun is needed
        # instead of just overwriting `player_name` in place.
        #
        # `key` is scoped to the current player/team, not a fixed string: `st.dataframe`
        # selection state persists in session_state by key across reruns, so a fixed key would
        # leave "row 0 selected" true after landing on the new page, since it renders a table
        # under the very same key — immediately re-triggering another jump, and cascading into
        # an infinite chain through each player's own most-similar match. Caught by actually
        # driving the click via Playwright, not by reasoning about it in the abstract: the app
        # visibly kept jumping player-to-player instead of settling on one page.
        similar_display = similar[["player", "team", "competition", "distance"]].rename(
            columns={
                "player": "Player", "team": "Team",
                "competition": "Competition", "distance": "Distance (standardised)",
            }
        )
        similar_display["Market value"] = similar["market_value_eur"].map(format_market_value)
        selection_event = st.dataframe(
            similar_display,
            hide_index=True,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
            key=f"similar_table_{player_name}_{team_name}",
        )
        selected_rows = selection_event.selection["rows"] if selection_event else []
        if selected_rows:
            picked = similar.iloc[selected_rows[0]]
            st.session_state["jump_to_player"] = (picked["player"], picked["team"])
            st.rerun()

st.subheader("Finishing — is the output real?")
xg_row = xg_table[(xg_table["player"] == player_name) & (xg_table["team"] == team_name)]

if xg_row.empty:
    if position_group == "Goalkeeper":
        st.info(f"{player_name} has no logged shots — goalkeepers don't take them.")
    else:
        st.info(
            f"{player_name} ({competition_name}) has no logged shots in the xG training set "
            "(Premier League 2015/16 + Bayer Leverkusen 2023/24). The similarity pool is wider "
            "than the xG training set (see \"About & Roadmap\" in the sidebar), so this is "
            "expected for most players outside those two competitions, not a bug."
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
    # Slimmed 2026-07-13 (pitch-prep pass): this used to repeat the whole headline-metrics
    # writeup on every single player's page. That's now one place — the "About & Roadmap" view's
    # "Methodology" expander — so this stays scoped to what's genuinely specific to *this*
    # player's page: how tightly their own position group's players cluster.
    st.caption(
        "Full methodology, credibility numbers and roadmap: see **About & Roadmap** in the "
        "sidebar. Below: how tightly this specific position group's players cluster."
    )
    st.caption(
        f"Silhouette score by K — {position_group} (league-normalised features; peaks low, "
        "~0.2-0.25 for every group including goalkeepers: play-styles within a position are a "
        "soft continuum, not crisp blobs; K=4 is kept deliberately above the metric's preferred "
        "K=2 for archetype granularity)."
    )
    silhouettes = cached_silhouette_scores(group_df, position_feature_columns_lz)
    fig, ax = plt.subplots(figsize=(6, 4))
    plot_silhouette_curve(silhouettes, ax=ax)
    st.pyplot(fig)
    plt.close(fig)
