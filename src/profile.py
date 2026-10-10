"""What the redesigned pages show, built from the app's tables: pure functions, no Streamlit.

`app.py`'s views stay thin because everything that decides *what to say about a player* lives here
and in `narrative.py`, where it is tested against the real tables (tests/test_profile.py). A page
asks for a `PlayerProfile` (the three questions: what kind of player, are the goals real, who plays
like this) or a `CompareView` (a verdict plus a side-by-side) and only lays them out.

Percentiles rank league standing, not pooled raw rates (`similarity.league_adjusted_percentiles`);
the numbers shown next to them stay raw per-90 rates and season totals.
"""

from dataclasses import dataclass

import pandas as pd

from src.config import GENDER_BY_COMPETITION
from src.narrative import (
    CHEAPER_RATIO,
    CompareSide,
    Finishing,
    Lookalike,
    Saves,
    bottom_share,
    build_compare_verdict,
    build_short_version,
    describe_finishing,
    describe_saves,
    finishing_from_shots,
    format_rate,
    top_share,
)
from src.presentation import STAT_LABELS, feature_columns_for, format_market_value, popular_name
from src.similarity import league_adjusted_percentiles, pair_closeness, rank_matches

# A stat is listed as something he does more (less) than most from the 75th (25th) league-adjusted
# percentile, five and four of them at most, as in the approved mockup.
STRONG_PERCENTILE = 0.75
WEAK_PERCENTILE = 0.25
MAX_STRENGTHS = 5
MAX_WEAKNESSES = 4
LOOKALIKES_PER_GAME = 5


@dataclass(frozen=True)
class StatBar:
    """One row of "does more / less than most".

    Attributes:
        label (str): the stat's name.
        rank (str): "Top 4%" or "Bottom 17%".
        width (float): bar length, 0-100: the league-adjusted percentile.
        detail (str): the raw rate and the season total ("3.6 per 90 · 123 this season").
    """

    label: str
    rank: str
    width: float
    detail: str


@dataclass(frozen=True)
class Match:
    """One entry of a lookalike list.

    Attributes:
        player (str): the table's player name (the key, with `team`).
        team (str): the club.
        name (str): the popular name to show.
        competition (str): the league and season.
        distance (float): distance in the lookalike space (smaller = closer).
        closeness (float): 0-1, the closest match of either game's list over this distance.
        market_value_eur (float or None): Transfermarkt value, if matched.
        cheaper (bool): valued at `narrative.CHEAPER_RATIO` of the profiled player's value or less.
    """

    player: str
    team: str
    name: str
    competition: str
    distance: float
    closeness: float
    market_value_eur: float | None
    cheaper: bool


@dataclass(frozen=True)
class PlayerProfile:
    """Everything a player's page shows.

    Attributes:
        player, team (str): the table key.
        name (str): popular name.
        position_group, competition, gender (str): where he plays.
        minutes (float): minutes played in the pool's season.
        short_version (str): the opening paragraph (`narrative.build_short_version`).
        strengths, weaknesses (list[StatBar]): the style section's two columns.
        goals, assists (int or None): season totals; `None` for goalkeepers.
        penalty_goals (int): goals from the spot.
        finishing (Finishing or None): outfield players with logged shots.
        output_text (str or None): the section-2 sentence: `narrative.describe_finishing` for outfield
            players with xG, `narrative.describe_saves` for goalkeepers.
        shots (pandas.DataFrame): the player's shots with `predicted_xg` (empty without xG).
        saves (Saves or None): goalkeepers.
        market_value_eur (float or None), tm_name (str or None), market_value_as_of (str or None).
        lookalikes (dict[str, list[Match]]): "male" / "female" lists, closest first.
        group_size (int): players in his position group.
    """

    player: str
    team: str
    name: str
    position_group: str
    competition: str
    gender: str
    minutes: float
    short_version: str
    strengths: list[StatBar]
    weaknesses: list[StatBar]
    goals: int | None
    assists: int | None
    penalty_goals: int
    finishing: Finishing | None
    output_text: str | None
    shots: pd.DataFrame
    saves: Saves | None
    market_value_eur: float | None
    tm_name: str | None
    market_value_as_of: str | None
    lookalikes: dict[str, list[Match]]
    group_size: int


@dataclass(frozen=True)
class Pool:
    """The app's tables, prepared once (and cached by the app) for every page.

    Attributes:
        per90 (pandas.DataFrame): the player table with a `gender` column, index 0..n-1.
        percentiles (dict[str, pandas.DataFrame]): per position group, league-adjusted
            percentiles indexed like `per90`.
        shots (pandas.DataFrame): shots with `predicted_xg` (Premier League 2015/16).
        market_values (pandas.DataFrame): `player, team, tm_name, market_value_eur,
            market_value_as_of`, indexed by (player, team).
    """

    per90: pd.DataFrame
    percentiles: dict[str, pd.DataFrame]
    shots: pd.DataFrame
    market_values: pd.DataFrame


def prepare_pool(per90, shots, market_value):
    """Add each player's game and rank every position group once.

    Args:
        per90 (pandas.DataFrame): `app_data/player_per90.parquet`.
        shots (pandas.DataFrame): `app_data/shots_with_xg.parquet`.
        market_value (pandas.DataFrame): `app_data/market_value.parquet`.

    Returns:
        Pool
    """
    per90 = per90.assign(gender=per90["competition"].map(GENDER_BY_COMPETITION)).reset_index(drop=True)
    percentiles = {
        group: league_adjusted_percentiles(part, feature_columns_for(group)[1])
        for group, part in per90.groupby("position_group")
    }
    return Pool(per90, percentiles, shots, market_value.set_index(["player", "team"]))


def find_player(pool, player, team):
    """The player's row, or `ValueError` if the pool doesn't have him."""
    hit = pool.per90[(pool.per90["player"] == player) & (pool.per90["team"] == team)]
    if hit.empty:
        raise ValueError(f"No player found matching player={player!r}, team={team!r}")
    return hit.iloc[0]


def market_value_of(pool, player, team):
    """`(value in euros, Transfermarkt name, as-of date)` for a player, or `(None, None, None)`."""
    if (player, team) not in pool.market_values.index:
        return None, None, None
    row = pool.market_values.loc[(player, team)]
    return float(row["market_value_eur"]), row["tm_name"], row["market_value_as_of"]


def display_name(row):
    """The popular name for a `per90` row."""
    return popular_name(row["player"], row["nickname"])


def _stat_bars(row, percentiles, group_size):
    """Strength and weakness rows for one player, best / worst first."""
    def detail(stat):
        if stat == "save_pct":
            saves, faced = int(round(row["saves"])), int(round(row["saves"] + row["goals_conceded"]))
            return f"{saves} saves from {faced} shots on target"
        total = int(round(row[stat.replace("_p90", "")]))
        return f"{format_rate(row[stat])} per 90 · {total:,} this season"

    ranked = percentiles.sort_values(ascending=False, kind="stable")
    strong = ranked[ranked >= STRONG_PERCENTILE].head(MAX_STRENGTHS)
    weak = ranked[ranked <= WEAK_PERCENTILE].tail(MAX_WEAKNESSES)[::-1]
    strengths = [
        StatBar(STAT_LABELS[stat], f"Top {top_share(pct, group_size)}%", pct * 100, detail(stat))
        for stat, pct in strong.items()
    ]
    weaknesses = [
        StatBar(STAT_LABELS[stat], f"Bottom {bottom_share(pct)}%", pct * 100, detail(stat))
        for stat, pct in weak.items()
    ]
    return strengths, weaknesses


def _lookalikes(pool, row, value_eur):
    """Both games' top lists for one player, from one ranking of his position group."""
    _, _, lz_columns = feature_columns_for(row["position_group"])
    ranked = rank_matches(pool.per90, lz_columns, row["player"], row["team"])
    lists = {gender: ranked[ranked["gender"] == gender].head(LOOKALIKES_PER_GAME) for gender in ("male", "female")}
    nearest = min(part["distance"].iloc[0] for part in lists.values() if len(part))
    result = {}
    for gender, part in lists.items():
        matches = []
        for _, other in part.iterrows():
            other_value, _, _ = market_value_of(pool, other["player"], other["team"])
            matches.append(Match(
                player=other["player"], team=other["team"], name=display_name(other),
                competition=other["competition"], distance=float(other["distance"]),
                closeness=float(nearest / other["distance"]) if other["distance"] else 1.0,
                market_value_eur=other_value,
                cheaper=other_value is not None and value_eur is not None
                and other_value <= CHEAPER_RATIO * value_eur,
            ))
        result[gender] = matches
    return result


def build_player_profile(pool, player, team):
    """Assemble one player's page: stats, finishing or saves, price, lookalikes, and the
    short version that sums them up.

    Args:
        pool (Pool): from `prepare_pool`.
        player (str): the table's player name.
        team (str): his club.

    Returns:
        PlayerProfile

    Raises:
        ValueError: unknown player.
    """
    row = find_player(pool, player, team)
    group = row["position_group"]
    group_rows = pool.per90[pool.per90["position_group"] == group]
    group_size = len(group_rows)
    percentiles = pool.percentiles[group].loc[row.name]
    value_eur, tm_name, as_of = market_value_of(pool, player, team)
    lookalikes = _lookalikes(pool, row, value_eur)
    strengths, weaknesses = _stat_bars(row, percentiles, group_size)

    finishing = saves = output_text = None
    shots = pool.shots[0:0]
    if group == "Goalkeeper":
        saves = Saves(float(row["save_pct"]), int(round(row["saves"] + row["goals_conceded"])),
                      float(percentiles["save_pct"]))
        output_text = describe_saves(saves, group_size)
    else:
        shots = pool.shots[(pool.shots["player"] == player) & (pool.shots["team"] == team)].reset_index(drop=True)
        if len(shots):
            finishing = finishing_from_shots(shots["predicted_xg"].values, shots["is_goal"].sum())
            output_text = describe_finishing(finishing)

    gender = row["gender"]
    same_game = [Lookalike(m.name, m.market_value_eur) for m in lookalikes[gender]]
    other_game = "female" if gender == "male" else "male"
    other_closest = (
        Lookalike(lookalikes[other_game][0].name, lookalikes[other_game][0].market_value_eur)
        if lookalikes[other_game] else None
    )
    short_version = build_short_version(
        group, percentiles, group_size, finishing=finishing, saves=saves, market_value_eur=value_eur,
        lookalikes=same_game, other_game_closest=other_closest, other_game=other_game,
    )

    is_keeper = group == "Goalkeeper"
    goals = None if is_keeper else int(round(row["goals"]))
    return PlayerProfile(
        player=player, team=team, name=display_name(row), position_group=group,
        competition=row["competition"], gender=gender, minutes=float(row["minutes_played"]),
        short_version=short_version, strengths=strengths, weaknesses=weaknesses,
        goals=goals, assists=None if is_keeper else int(round(row["assists"])),
        penalty_goals=0 if is_keeper else goals - int(round(row["non_penalty_goals"])),
        finishing=finishing, output_text=output_text, shots=shots, saves=saves,
        market_value_eur=value_eur, tm_name=tm_name, market_value_as_of=as_of,
        lookalikes=lookalikes, group_size=group_size,
    )


@dataclass(frozen=True)
class ComparePlayer:
    """One side of Compare: the header card and the finishing block."""

    player: str
    team: str
    name: str
    position_group: str
    competition: str
    minutes: float
    market_value_eur: float | None
    finishing: Finishing | None
    finishing_text: str | None
    save_pct: float | None


@dataclass(frozen=True)
class CompareRow:
    """One stat of the side-by-side. Widths are 0-100, each stat scaled to the larger of the two."""

    label: str
    a_text: str
    b_text: str
    a_width: float
    b_width: float
    leader: str | None


@dataclass(frozen=True)
class CompareView:
    """A verdict plus the side-by-side for two players."""

    a: ComparePlayer
    b: ComparePlayer
    verdict: str
    rows: list[CompareRow]


def _compare_player(pool, row):
    value, _, _ = market_value_of(pool, row["player"], row["team"])
    shots = pool.shots[(pool.shots["player"] == row["player"]) & (pool.shots["team"] == row["team"])]
    finishing = finishing_from_shots(shots["predicted_xg"].values, shots["is_goal"].sum()) if len(shots) else None
    return ComparePlayer(
        player=row["player"], team=row["team"], name=display_name(row),
        position_group=row["position_group"], competition=row["competition"],
        minutes=float(row["minutes_played"]), market_value_eur=value, finishing=finishing,
        finishing_text=describe_finishing(finishing) if finishing else None,
        save_pct=float(row["save_pct"]) if row["position_group"] == "Goalkeeper" else None,
    )


def build_compare_view(pool, key_a, key_b):
    """The Compare page for two players: any two outfielders, or any two goalkeepers.

    Args:
        pool (Pool): from `prepare_pool`.
        key_a, key_b (tuple[str, str]): `(player, team)`.

    Returns:
        CompareView

    Raises:
        ValueError: unknown player, or a goalkeeper against an outfielder (no stats in common).
    """
    row_a, row_b = find_player(pool, *key_a), find_player(pool, *key_b)
    closeness = pair_closeness(pool.per90, key_a, key_b)
    a, b = _compare_player(pool, row_a), _compare_player(pool, row_b)
    _, columns, _ = feature_columns_for(row_a["position_group"])
    sides = [
        CompareSide(p.name, row[columns].astype(float), p.market_value_eur, p.save_pct)
        for p, row in ((a, row_a), (b, row_b))
    ]
    rows = []
    for stat in columns:
        rate_a, rate_b = float(row_a[stat]), float(row_b[stat])
        top = max(rate_a, rate_b) or 1.0
        lower_is_better = stat == "goals_conceded_p90"
        leader = None
        if rate_a != rate_b:
            leader = "a" if (rate_a < rate_b) == lower_is_better else "b"
        rows.append(CompareRow(
            STAT_LABELS[stat], format_rate(rate_a), format_rate(rate_b), rate_a / top * 100, rate_b / top * 100, leader,
        ))
    return CompareView(a, b, build_compare_verdict(sides[0], sides[1], closeness), rows)


def price_line(value_eur):
    """A value as the pages show it, or "Not on record" when there is none."""
    return format_market_value(value_eur) or "Not on record"
