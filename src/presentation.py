"""Text/number presentation helpers for the Streamlit app — pure functions, no Streamlit.

Everything here turns an already-computed number (a percentile, a cluster z-score, a market
value) into the words a scout or fan actually reads. Kept out of `app.py` so it can be unit
tested directly (`tests/test_presentation.py`): these functions decide what the app *says*, and
two of them have already shipped real bugs ("91th"; a leaky goalkeeper reading as "elite").
`visualisation.py` is the chart half of the same presentation layer.
"""

import pandas as pd

from src.similarity import (
    GK_PER90_FEATURE_COLUMNS,
    PER90_FEATURE_COLUMNS,
)
from src.similarity import feature_columns_for as similarity_feature_columns_for

STAT_LABELS = {
    col: col.replace("_p90", "").replace("_", " ").title()
    for col in PER90_FEATURE_COLUMNS + GK_PER90_FEATURE_COLUMNS
}
STAT_LABELS["save_pct"] = "Save %"
STAT_LABELS["non_penalty_goals_p90"] = "Non-Penalty Goals"
# StatsBomb flags a pass that set up a goal as an assist and *not* as a shot assist, so this count
# excludes assists (checked 2026-10-02: the two flags never overlap). The usual "key passes" figure
# includes them; the label says so, so 123 for Özil isn't read as his full chance creation.
STAT_LABELS["key_passes_p90"] = "Key Passes (excl. Assists)"
# Cluster profiling reads the league-normalised `_lz` columns, not the raw `_p90` ones — same
# clean label either way, so a reader sees "Tackles" whichever number sits underneath.
STAT_LABELS.update({f"{col}_lz": label for col, label in list(STAT_LABELS.items())})


def feature_columns_for(position_group, provider="statsbomb"):
    """The column sets one position group is described by: `(raw totals, per-90 rates,
    league-normalised rates)`. See `similarity.feature_columns_for`, which this re-exports so the
    views keep one import for their presentation needs.
    """
    return similarity_feature_columns_for(position_group, provider)


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


