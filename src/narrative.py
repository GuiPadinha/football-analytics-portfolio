"""Rule-based sentences for the app's redesign: a player's "short version" and Compare's verdict.

The redesign leads with conclusions ("A dribbler and scorer: top 1% of midfielders for both")
instead of tables of numbers. Each sentence is a fixed rule over numbers the page also shows,
with its thresholds as named constants calibrated on the real pool (ML_LEARNING_LOG.md,
2026-10-06), so every claim traces back to a number. Deliberately not an LLM: it could phrase
more freely, but it could also claim something the data doesn't say, and nothing here could
test for that.

Pure functions, no Streamlit (tests/test_narrative.py). The inputs come from `similarity.py`
(league-adjusted percentiles, lookalike rankings, `pair_closeness`) and the app's precomputed
tables. Players are named by their popular name (`presentation.popular_name`), never by
pronoun: the pool mixes men's and women's football, and a name is always right.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.presentation import format_market_value, ordinal


@dataclass(frozen=True)
class StatWords:
    """How the text talks about one stat.

    Attributes:
        role (str or None): what a standout in it makes a player ("dribbler"). None: the stat
            never names a style.
        activity (str or None): what one player leads another on ("dribbling"). None: never a
            lead.
        unit (str): what one per-90 number counts ("dribbles").
    """

    role: str | None
    activity: str | None
    unit: str


STAT_WORDS = {
    "non_penalty_goals_p90": StatWords("scorer", "scoring", "non-penalty goals"),
    "shots_p90": StatWords("shooter", "shooting", "shots"),
    "key_passes_p90": StatWords("chance creator", "chance creation", "key passes"),
    "assists_p90": StatWords("provider", "assists", "assists"),
    "progressive_passes_p90": StatWords("progressive passer", "forward passing", "progressive passes"),
    "dribbles_completed_p90": StatWords("dribbler", "dribbling", "dribbles"),
    "pressures_p90": StatWords("presser", "pressing", "pressures"),
    "interceptions_p90": StatWords("interceptor", "interceptions", "interceptions"),
    "tackles_p90": StatWords("tackler", "tackling", "tackles"),
    "clearances_p90": StatWords("box defender", "clearances", "clearances"),
    "blocks_p90": StatWords("blocker", "blocks", "blocks"),
    "saves_p90": StatWords("busy shot-stopper", "saves", "saves"),
    # Goals conceded mostly measure the defence in front of the keeper, and fewer is better, so
    # they never name a style or a lead.
    "goals_conceded_p90": StatWords(None, None, "goals conceded"),
    "claims_p90": StatWords("cross-claimer", "claiming crosses", "claims"),
    "punches_p90": StatWords("puncher", "punching", "punches"),
    "sweeper_actions_p90": StatWords("sweeper-keeper", "sweeping", "sweeper actions"),
}

GROUP_PLURALS = {
    "Defender": "defenders",
    "Midfielder": "midfielders",
    "Forward": "forwards",
    "Goalkeeper": "goalkeepers",
    "Outfield": "outfielders",
}
GAME_WORDS = {"male": "men's", "female": "women's"}

# A standout is a top-10% stat, league-adjusted, within the position group. Measured on
# 2026-10-06: about 40% of outfielders and 65% of keepers have none, so "no standout" is an
# ordinary answer the text has to handle well, not an edge case.
STANDOUT_PERCENTILE = 0.90
MAX_NAMED_STANDOUTS = 2

# How rare a season must be, for an average finisher on the same chances, before the text says
# more than "about par": rarer than 1 in 5 earns "luck alone could explain it", rarer than 1 in
# 20 earns "likely skill" (or "more than bad luck"). On PL 2015/16's 163 players with 2+ xG
# (2026-10-06): 5 pass 1 in 20 above and 21 more pass 1 in 5; 2 and 12 below. Agüero is 1 in 22,
# Mahrez 1 in 14, Kane 1 in 6. Luck alone would put several of ~160 players past 1 in 20 each
# way, so even the strongest wording says "likely", never "proven".
RARE_SEASON = 0.05
UNUSUAL_SEASON = 0.20
# Under one expected goal, "about par" is true and says nothing.
MIN_EXPECTED_GOALS_TO_JUDGE = 1.0

# "Cheaper" means half the value or less: the price sentence says "half", so change both together.
# Measured on 2026-10-06, 75% of valued men have at least one top-5 lookalike that cheap. Values
# are heavy-tailed, and a similar style is not the same level (league, age and contract all move
# a price), which the page says next to the list.
CHEAPER_RATIO = 0.5

# Compare's closeness bands, on the rank `similarity.pair_closeness` returns. Top 5 is the player
# page's lookalike list, so "like-for-like" means "would be on that list". Calibrated 2026-10-06:
# Mahrez-Dembélé rank 3 and Kane-Vardy 4 are like-for-like, Coutinho-Zaha 894 is not a swap.
LIKE_FOR_LIKE_RANK = 5
SIMILAR_RANK = 25
# A stat is one player's lead only if the two differ by at least half a league standard
# deviation *and* the leader's raw per-90 rate is at least 20% higher. The standing gap is the
# fair comparison across leagues; the raw rate is what the reader sees. Without the second rule,
# 2026-10-06 produced "leads on shooting: 2.5 shots per 90, to 2.5" (Dembélé over Mahrez: the
# same rate, a different standing in a different league).
LEAD_GAP = 0.5
MIN_LEAD_RATIO = 1.2
MAX_LEADS = 2
# Two values within 20% of each other read as "about the same".
SAME_VALUE_RATIO = 0.8
# A keepers' save % gap worth a sentence: 3 points, about one save in 33 shots on target.
SAVE_PCT_GAP = 0.03

FRACTION_WORDS = {
    2: "half", 3: "a third", 4: "a quarter", 5: "a fifth", 6: "a sixth",
    7: "a seventh", 8: "an eighth", 9: "a ninth", 10: "a tenth",
}
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


@dataclass(frozen=True)
class Finishing:
    """One season's finishing against what an average finisher would do with the same shots.

    Attributes:
        goals (int): goals scored, penalties included (as in the app's xG table).
        expected_goals (float): the shots' summed xG.
        p_at_least (float): chance an average finisher scores `goals` or more from these shots.
        p_at_most (float): chance an average finisher scores `goals` or fewer.
    """

    goals: int
    expected_goals: float
    p_at_least: float
    p_at_most: float


@dataclass(frozen=True)
class Saves:
    """A keeper's season of shot-stopping, as the short version needs it.

    Attributes:
        save_pct (float): saves over shots on target, 0-1.
        shots_on_target (int): saves plus goals conceded.
        percentile (float): league-adjusted percentile of `save_pct` among goalkeepers.
    """

    save_pct: float
    shots_on_target: int
    percentile: float


@dataclass(frozen=True)
class Lookalike:
    """One entry of a player's same-game lookalike list, as the price sentence needs it."""

    name: str
    market_value_eur: float | None


@dataclass(frozen=True)
class CompareSide:
    """One player in Compare, as the verdict needs them.

    Attributes:
        name (str): popular name.
        per90 (pandas.Series): raw per-90 rates, index = the `_p90` columns.
        market_value_eur (float or None): Transfermarkt value, if matched.
        save_pct (float or None): keepers only.
    """

    name: str
    per90: pd.Series
    market_value_eur: float | None = None
    save_pct: float | None = None


def top_share(percentile, group_size):
    """The N in "top N%": the player and everyone ranked above them, as a share of the group,
    rounded up. The 5th best of 422 is in the top 2%, not the top 1%.

    Args:
        percentile (float): `rank(pct=True)` output in (0, 1], 1.0 = best in the group.
        group_size (int): players in the group.
    """
    share = 1 - percentile + 1 / group_size
    return max(1, math.ceil(round(share * 100, 6)))


def bottom_share(percentile):
    """The N in "bottom N%": the player and everyone ranked below them, rounded up."""
    return max(1, math.ceil(round(percentile * 100, 6)))


def describe_style(position_group, percentiles, group_size):
    """The short version's first sentence: what kind of player this is, from standout stats.

    Up to two top-10% stats become role nouns ("A dribbler and scorer: top 1% of midfielders
    for both"); any further ones are counted, not listed. With none, it names the best stat and
    its rank instead of inventing a strength.

    Args:
        position_group (str): "Defender", "Midfielder", "Forward" or "Goalkeeper".
        percentiles (pandas.Series): this player's `similarity.league_adjusted_percentiles` row.
        group_size (int): players in the position group.

    Returns:
        str: one sentence.
    """
    group = GROUP_PLURALS[position_group]
    nameable = [stat for stat in percentiles.index if stat in STAT_WORDS and STAT_WORDS[stat].role]
    ranked = percentiles[nameable].sort_values(ascending=False, kind="stable")
    standouts = ranked[ranked >= STANDOUT_PERCENTILE]
    if ranked.iloc[0] < 0.5:
        # "The best is punches, top 73%" reads as praise and isn't. Every stat here is a volume, so
        # all-below-median is a style in itself: a keeper behind a defence that rarely needs one.
        if position_group == "Goalkeeper":
            units = _join([STAT_WORDS[stat].unit for stat in nameable])
            return f"A quiet keeper: below the median on {units}."
        return f"A low-volume {position_group.lower()}: below the median on every stat."
    if standouts.empty:
        best = ranked.index[0]
        return (
            f"No standout stat: the best is {STAT_WORDS[best].unit}, "
            f"top {top_share(ranked.iloc[0], group_size)}% of {group}."
        )

    named = standouts.head(MAX_NAMED_STANDOUTS)
    identity = _with_article(" and ".join(STAT_WORDS[stat].role for stat in named.index))
    shares = [top_share(pct, group_size) for pct in named]
    if len(shares) == 1:
        ranks = f"top {shares[0]}% of {group}"
    elif shares[0] == shares[1]:
        ranks = f"top {shares[0]}% of {group} for both"
    else:
        ranks = f"top {shares[0]}% and top {shares[1]}% of {group}"
    extra = len(standouts) - len(named)
    more = ""
    if extra:
        cutoff = round((1 - STANDOUT_PERCENTILE) * 100)
        more = f", plus {_count_word(extra)} more {_plural(extra, 'stat')} in the top {cutoff}%"
    return f"{identity}: {ranks}{more}."


def goals_distribution(shot_xg):
    """P(goals = k) for k = 0..len(shot_xg), if each shot went in with probability equal to its
    xG, independently: the Poisson-binomial distribution, built one shot at a time.

    This is the luck an *average* finisher would see on exactly these chances, which a fixed
    "±3 goals" rule ignores: +3 is unremarkable on 120 shots and rare on 20. It's exact rather
    than a normal approximation, which overstates small samples (2026-10-06: Townsend's 4 goals
    from 1.1 xG read as 2.8 SD; the exact tail is 1 in 44, about 1.9 SD). Two simplifications
    are left to Phase 5a/5b: the xG is in-sample (the model saw these shots, which moves
    goals - xG by 0.02 on average), and shots aren't fully independent (a rebound exists only
    because the first shot missed).

    Args:
        shot_xg (array-like): one xG per shot.

    Returns:
        numpy.ndarray: probabilities for 0..n goals, summing to 1.
    """
    pmf = np.array([1.0])
    for p in shot_xg:
        pmf = np.convolve(pmf, [1 - p, p])
    return pmf


def finishing_from_shots(shot_xg, goals):
    """A `Finishing` from one player's per-shot xG and their goal count."""
    pmf = goals_distribution(shot_xg)
    goals = int(goals)
    return Finishing(
        goals=goals,
        expected_goals=float(np.sum(shot_xg)),
        p_at_least=float(pmf[goals:].sum()),
        p_at_most=float(pmf[: goals + 1].sum()),
    )


def describe_finishing(finishing):
    """The short version's finishing sentence: are the goals real, or luck?

    Reads the exact tail odds as "about one season in N" for an average finisher on the same
    chances, which a fan can weigh without knowing what a standard deviation is.

    Args:
        finishing (Finishing): this player's season.

    Returns:
        str: one or two sentences.
    """
    goals, worth = finishing.goals, f"{finishing.expected_goals:.1f}"
    head = f"{'No' if goals == 0 else goals} {_plural(goals, 'goal')} from chances worth {worth}"
    if finishing.expected_goals < MIN_EXPECTED_GOALS_TO_JUDGE:
        return f"{head}: too few chances to judge the finishing."
    if goals > finishing.expected_goals and finishing.p_at_least <= UNUSUAL_SEASON:
        odds = (
            "An average finisher scores that many from the same chances "
            f"{_season_odds(finishing.p_at_least)}"
        )
        if finishing.p_at_least <= RARE_SEASON:
            return f"{head}. {odds}: some of it is likely skill, but don't pay for all of it."
        return f"{head}. {odds}, so luck alone could explain it: judge on the {worth}, not the {goals}."
    if goals < finishing.expected_goals and finishing.p_at_most <= UNUSUAL_SEASON:
        how_few = "none" if goals == 0 else "that few"
        odds = (
            f"An average finisher scores {how_few} from the same chances "
            f"{_season_odds(finishing.p_at_most)}"
        )
        if finishing.p_at_most <= RARE_SEASON:
            return f"{head}. {odds}: more than bad luck usually explains."
        return f"{head}. {odds}, likely bad luck: if the chances keep coming, the goals usually follow."
    return f"{head}: about what an average finisher would score."


def describe_saves(saves, group_size):
    """A keeper's second sentence, in place of finishing: save % and where it ranks.

    The shot count is stated because save % is noisy (on 40 shots on target, one save moves it
    2.5 points). There's no shot-quality model for keepers yet, which would need post-shot xG,
    so the sentence ranks the rate and stops there.

    Args:
        saves (Saves): this keeper's season.
        group_size (int): goalkeepers in the pool.

    Returns:
        str: one sentence.
    """
    if saves.percentile >= 0.5:
        rank = f"top {top_share(saves.percentile, group_size)}%"
    else:
        rank = f"bottom {bottom_share(saves.percentile)}%"
    return (
        f"Saved {saves.save_pct:.0%} of {saves.shots_on_target} shots on target: "
        f"{rank} of goalkeepers."
    )


def describe_price(market_value_eur, lookalikes):
    """The short version's last sentence: who plays like this player, for less.

    Args:
        market_value_eur (float or None): the player's Transfermarkt value.
        lookalikes (list[Lookalike]): the player's same-game lookalike list, closest first.

    Returns:
        str or None: None when there's nothing to price: no value for the player or for any
            lookalike. That's always the case in women's football, which the source lacks.
    """
    if _missing(market_value_eur):
        return None
    valued = [look for look in lookalikes if not _missing(look.market_value_eur)]
    if not valued:
        return None

    closest = f"{_count_word(len(lookalikes))} closest"
    cheaper = sorted(
        (look for look in valued if look.market_value_eur <= CHEAPER_RATIO * market_value_eur),
        key=lambda look: look.market_value_eur,
    )
    if cheaper:
        named = _join([f"{look.name} ({format_market_value(look.market_value_eur)})" for look in cheaper[:2]])
        subject = "A similar profile costs" if len(cheaper) == 1 else "Similar profiles cost"
        rest = len(cheaper) - 2
        more = f", plus {_count_word(rest)} more of the {closest}" if rest > 0 else ""
        return f"{subject} half as much or less: {named}{more}."
    if all(look.market_value_eur > market_value_eur for look in valued):
        low = format_market_value(min(look.market_value_eur for look in valued))
        high = format_market_value(max(look.market_value_eur for look in valued))
        span = low if low == high else f"{low} to {high}"
        if len(valued) < len(lookalikes):
            scope = "every close match with a value"
        elif len(valued) == 1:
            scope = "the closest match"
        elif len(valued) == 2:
            scope = "both closest matches"
        else:
            scope = f"all {closest} matches"
        return f"Cheaper than {scope} ({span})."
    return f"None of the {closest} matches costs half as much."


def describe_closest(lookalikes, other_game_closest=None, other_game=None):
    """The last sentence when there's no price to talk about: the closest match in each game.

    Women's football has no market values in this data, so without this a WSL player's short
    version would stop after one sentence. The cross-game match is the pool's most surprising
    fact (Benzema's closest match plays for Wolfsburg), so it earns the slot.

    Args:
        lookalikes (list[Lookalike]): same-game lookalike list, closest first.
        other_game_closest (Lookalike or None): the closest match in the other game.
        other_game (str or None): that game, "male" or "female".

    Returns:
        str or None
    """
    if not lookalikes:
        return None
    if other_game_closest is None:
        return f"Closest match: {lookalikes[0].name}."
    return (
        f"Closest match: {lookalikes[0].name}; in the {GAME_WORDS[other_game]} game, "
        f"{other_game_closest.name}."
    )


def build_short_version(position_group, percentiles, group_size, finishing=None, saves=None,
                        market_value_eur=None, lookalikes=(), other_game_closest=None,
                        other_game=None):
    """The player page's opening paragraph: style, then finishing (or saves), then price.

    Each part comes from its own rule above and drops out when its data doesn't exist (no xG
    outside PL 2015/16, no market values in women's football). Without a price, the closest
    match in each game takes the last slot, so the paragraph runs two to three sentences.

    Args:
        position_group (str): the player's position group.
        percentiles (pandas.Series): `similarity.league_adjusted_percentiles` row.
        group_size (int): players in the position group.
        finishing (Finishing or None): outfielders with xG.
        saves (Saves or None): goalkeepers.
        market_value_eur (float or None): the player's Transfermarkt value.
        lookalikes (list[Lookalike]): same-game lookalike list, closest first.
        other_game_closest (Lookalike or None): the closest match in the other game.
        other_game (str or None): that game, "male" or "female".

    Returns:
        str
    """
    sentences = [describe_style(position_group, percentiles, group_size)]
    if saves is not None:
        sentences.append(describe_saves(saves, group_size))
    elif finishing is not None:
        sentences.append(describe_finishing(finishing))
    last = describe_price(market_value_eur, lookalikes) or describe_closest(
        lookalikes, other_game_closest, other_game
    )
    if last:
        sentences.append(last)
    return " ".join(sentences)


def closeness_band(rank):
    """"like-for-like", "similar" or "different", from a `pair_closeness` rank."""
    if rank <= LIKE_FOR_LIKE_RANK:
        return "like-for-like"
    if rank <= SIMILAR_RANK:
        return "similar"
    return "different"


def describe_price_gap(a, b, band):
    """Compare's price sentence: what the cheaper player saves, read against how alike they are.

    Args:
        a (CompareSide): first player.
        b (CompareSide): second player.
        band (str): `closeness_band` of the pair.

    Returns:
        str or None: None unless both have a value.
    """
    if _missing(a.market_value_eur) or _missing(b.market_value_eur):
        return None
    cheap, dear = sorted((a, b), key=lambda side: side.market_value_eur)
    if cheap.market_value_eur >= SAME_VALUE_RATIO * dear.market_value_eur:
        return (
            f"Both are valued about the same ({format_market_value(a.market_value_eur)} and "
            f"{format_market_value(b.market_value_eur)})."
        )
    values = (
        f"({format_market_value(cheap.market_value_eur)} against "
        f"{format_market_value(dear.market_value_eur)})"
    )
    tail = {
        "like-for-like": "for a close profile",
        "similar": "for a partly different profile",
        "different": "but does a different job",
    }[band]
    return f"{cheap.name} costs {_how_much_less(cheap.market_value_eur, dear.market_value_eur)} {values}, {tail}."


def build_compare_verdict(a, b, closeness):
    """Compare's verdict: are the two interchangeable, who does what, and what the price gap buys.

    Args:
        a (CompareSide): first player.
        b (CompareSide): second player.
        closeness (similarity.PairCloseness): this pair's closeness.

    Returns:
        str: two to five sentences.
    """
    target, match = (a, b) if closeness.from_a else (b, a)
    band = closeness_band(closeness.rank)
    place = "closest match" if closeness.rank == 1 else f"{ordinal(closeness.rank)}-closest match"
    pool = (
        f"{closeness.list_size:,} {GAME_WORDS[closeness.list_gender]} "
        f"{GROUP_PLURALS[closeness.list_position]}"
    )
    opening = {
        "like-for-like": f"A like-for-like pair: {match.name} is {target.name}'s {place} among {pool}.",
        "similar": f"Similar, with real differences: {match.name} is {target.name}'s {place} among {pool}.",
        "different": f"Not a like-for-like swap: {match.name} is only {target.name}'s {place} among {pool}.",
    }[band]

    sentences = [opening]
    leads_a, leads_b = _leads(a, b, closeness)
    if leads_a:
        sentences.append(_lead_sentence(a, b, leads_a))
    if leads_b:
        sentences.append(_lead_sentence(b, a, leads_b))
    if not leads_a and not leads_b:
        sentences.append("No stat separates them by much.")
    for extra in (_save_pct_sentence(a, b), describe_price_gap(a, b, band)):
        if extra:
            sentences.append(extra)
    return " ".join(sentences)


def _leads(a, b, closeness):
    """Each side's biggest leads: stats where it stands at least `LEAD_GAP` league standard
    deviations higher and its raw rate is at least `MIN_LEAD_RATIO` times the other's."""
    gap = closeness.standing_a - closeness.standing_b

    def visibly_ahead(leader, other, stat):
        return leader.per90[stat] > 0 and leader.per90[stat] >= MIN_LEAD_RATIO * other.per90[stat]

    leadable = [
        stat for stat in gap.index
        if stat in STAT_WORDS and STAT_WORDS[stat].activity and abs(gap[stat]) >= LEAD_GAP
        and (visibly_ahead(a, b, stat) if gap[stat] > 0 else visibly_ahead(b, a, stat))
    ]
    gap = gap[leadable]
    leads_a = gap[gap > 0].sort_values(ascending=False, kind="stable").head(MAX_LEADS)
    leads_b = (-gap[gap < 0]).sort_values(ascending=False, kind="stable").head(MAX_LEADS)
    return list(leads_a.index), list(leads_b.index)


def _lead_sentence(leader, other, stats):
    """"X leads on shooting and forward passing: 4.8 shots and 11.2 progressive passes per 90,
    to Y's 1.2 and 3.8." """
    activities = _join([STAT_WORDS[stat].activity for stat in stats])
    leader_rates = _join([f"{format_rate(leader.per90[stat])} {STAT_WORDS[stat].unit}" for stat in stats])
    other_rates = _join([format_rate(other.per90[stat]) for stat in stats])
    return f"{leader.name} leads on {activities}: {leader_rates} per 90, to {other.name}'s {other_rates}."


def _save_pct_sentence(a, b):
    """Keepers only: who saved the bigger share of shots on target, when the gap matters."""
    if _missing(a.save_pct) or _missing(b.save_pct):
        return None
    if abs(a.save_pct - b.save_pct) < SAVE_PCT_GAP:
        return f"Both saved about the same share of shots on target ({a.save_pct:.0%} and {b.save_pct:.0%})."
    better, worse = (a, b) if a.save_pct > b.save_pct else (b, a)
    return (
        f"{better.name} saved a bigger share of shots on target: "
        f"{better.save_pct:.0%} to {worse.save_pct:.0%}."
    )


def _how_much_less(cheap, dear):
    """"a quarter as much" when the ratio sits near a simple fraction, else the gap in euros."""
    ratio = cheap / dear
    n = round(1 / ratio)
    if n in FRACTION_WORDS and abs(ratio * n - 1) <= 0.15:
        return f"{FRACTION_WORDS[n]} as much"
    if ratio < 1 / max(FRACTION_WORDS):
        return "less than a tenth as much"
    return f"{format_market_value(dear - cheap)} less"


def _season_odds(p):
    """"about one season in 22" from a tail probability."""
    one_in = 1 / p
    if one_in > 1000:
        return "less than one season in 1,000"
    return f"about one season in {round(one_in):,}"


def format_rate(value):
    """A per-90 rate as text: one decimal from 1 up, two below (0.34 goals), plain 0 for none."""
    if value == 0:
        return "0"
    return f"{value:.1f}" if abs(value) >= 1 else f"{value:.2f}"


def _count_word(n):
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else f"{n:,}"


def _plural(n, word):
    return word if n == 1 else f"{word}s"


def _with_article(text):
    return f"{'An' if text[0].lower() in 'aeiou' else 'A'} {text}"


def _join(items):
    """"a", "a and b", "a, b and c"."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _missing(value):
    return value is None or pd.isna(value)
