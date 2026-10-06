"""Text/number presentation helpers for the Streamlit app — pure functions, no Streamlit.

Everything here turns an already-computed number (a percentile, a cluster z-score, a market
value) into the words a scout or fan actually reads. Kept out of `app.py` so it can be unit
tested directly (`tests/test_presentation.py`): these functions decide what the app *says*, and
two of them have already shipped real bugs ("91th"; a leaky goalkeeper reading as "elite").
`visualisation.py` is the chart half of the same presentation layer.
"""

import pandas as pd

from src.similarity import (
    ACTION_COLUMNS,
    GK_ACTION_COLUMNS,
    GK_PER90_FEATURE_COLUMNS,
    GK_PER90_LEAGUE_Z_COLUMNS,
    PER90_FEATURE_COLUMNS,
    PER90_LEAGUE_Z_COLUMNS,
)

# Three role-relevant headline stats per position group: a deliberately small, curated subset,
# not a ranking of "the best 3 stats" in any absolute sense. Goalkeepers draw from their own
# feature set (a keeper's tackles/key passes are meaninglessly near zero); save % is shown
# separately, since it's a ratio rather than a per-90 rate with a raw-total counterpart.
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
# StatsBomb flags a pass that set up a goal as an assist and *not* as a shot assist, so this count
# excludes assists (checked 2026-10-02: the two flags never overlap). The usual "key passes" figure
# includes them; the label says so, so 123 for Özil isn't read as his full chance creation.
STAT_LABELS["key_passes_p90"] = "Key Passes (excl. Assists)"
# Cluster profiling reads the league-normalised `_lz` columns, not the raw `_p90` ones — same
# clean label either way, so a reader sees "Tackles" whichever number sits underneath.
STAT_LABELS.update({f"{col}_lz": label for col, label in list(STAT_LABELS.items())})


def feature_columns_for(position_group):
    """The column sets one position group is described by: `(raw totals, per-90 rates,
    league-normalised rates)`.

    Goalkeepers use a feature set disjoint from the three outfield groups, so every view that
    handles "any position" branches here instead of hard-coding the outfield columns.

    Args:
        position_group (str): "Defender", "Midfielder", "Forward" or "Goalkeeper".

    Returns:
        tuple[list[str], list[str], list[str]]: action, `_p90` and `_lz` columns, index-aligned.
    """
    if position_group == "Goalkeeper":
        return GK_ACTION_COLUMNS, GK_PER90_FEATURE_COLUMNS, GK_PER90_LEAGUE_Z_COLUMNS
    return ACTION_COLUMNS, PER90_FEATURE_COLUMNS, PER90_LEAGUE_Z_COLUMNS


def percentile_tier(goodness_pct):
    """Plain-language read of a 0-100 goodness percentile (`similarity.goodness_percentiles`).

    A bare "72nd percentile" still asks the reader to supply their own judgment of what counts
    as good. These bands are the FBref/StatsBomb scouting-report convention, so the number never
    has to carry the "is this good?" call by itself. Callers must pass a goodness-adjusted
    percentile (direction already flipped for lower-is-better stats), never a raw one.
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


def ordinal(n):
    """"72nd", not "72th": 11th/12th/13th are the exception to 1st/2nd/3rd, handled by the
    `10 <= n % 100 <= 20` guard below. Shared by percentiles and Compare's "5th-closest match".
    """
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_percentile(goodness_pct):
    """A 0-100 percentile as an ordinal ("72nd"). Every percentile display in the app goes
    through this, so the suffix is never wrong."""
    return ordinal(round(goodness_pct))


def popular_name(player, nickname):
    """The name a fan knows: StatsBomb's `nickname` ("Koke", "Philippe Coutinho") when it has
    one, else the full name, which for most players is already the popular one ("Harry Kane").

    Never cut down to a surname. The last word is wrong too often: it would make "Geum-Min Lee"'s
    given name her surname and turn "Kevin De Bruyne" into "Bruyne".
    """
    return nickname if isinstance(nickname, str) and nickname.strip() else player


def style_intensity_label(z):
    """Plain-language read of one cluster-vs-population z-score (`similarity.profile_clusters`):
    "Much more (+1.4σ)" instead of a bare "+1.4σ" — the word first, the number kept for whoever
    wants it. Unlike a percentile, a style z-score has no good/bad direction: the word describes
    *how unusual*, not *how good*.
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


def format_market_value(eur):
    """Human-readable market value ("€30.0M" / "€850k"), or "" for a missing value — shared by
    every market-value caption so the same number always reads the same way."""
    if pd.isna(eur):
        return ""
    if eur >= 1_000_000:
        return f"€{eur / 1_000_000:.1f}M"
    return f"€{eur / 1_000:.0f}k"


def lookup_market_value(market_value, player, team):
    """The matched market-value row for one (player, team), or `None` if unresolved."""
    match = market_value[(market_value["player"] == player) & (market_value["team"] == team)]
    return match.iloc[0] if len(match) else None


def build_scouting_blurb(position_group, high_traits, low_stat_col, n_clusters, percentiles, market_value_row):
    """One-paragraph scouting-report summary for the top of a player's page.

    Stitches three panels the page already renders lower down — the Style archetype read, the
    single best percentile stat, and market value — into prose. A fixed template over numbers
    those panels already display, deliberately not an LLM summary: it can't say anything the
    rest of the page doesn't.

    Args:
        position_group (str): the player's position group label.
        high_traits (pandas.Series): top cluster z-scores, index=feature column (the same series
            the Style archetype panel's headline sentence uses).
        low_stat_col (str): the feature column with the lowest cluster z-score.
        n_clusters (int): how many style clusters exist for this position group.
        percentiles (pandas.Series): this player's goodness-adjusted percentiles
            (`similarity.goodness_percentiles`), 0-1, index=feature column.
        market_value_row (pandas.Series or None): output of `lookup_market_value`.

    Returns:
        str: a Markdown-formatted paragraph.
    """
    style_text = " and ".join(f"**{STAT_LABELS[c]}**" for c in high_traits.index)
    best_stat = percentiles.idxmax()
    best_pct = percentiles[best_stat] * 100
    sentences = [
        # style_text already bolds each trait; wrapping it again produced nested `****` markup.
        f"A {style_text} {position_group.lower()}, light on **{STAT_LABELS[low_stat_col]}** — "
        f"one of {n_clusters} style clusters found among {position_group.lower()}s in this pool.",
        f"Stands out most for **{STAT_LABELS[best_stat]}**, ranking in the "
        f"**{format_percentile(best_pct)} percentile ({percentile_tier(best_pct)})** among "
        f"{position_group.lower()}s.",
    ]
    if market_value_row is not None:
        sentences.append(
            f"Valued at **{format_market_value(market_value_row['market_value_eur'])}** (Transfermarkt)."
        )
    else:
        sentences.append("Market value not on record.")
    return " ".join(sentences)
