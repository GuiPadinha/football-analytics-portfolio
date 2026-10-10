"""The findings on the app's Home page, computed from the data instead of typed by hand.

The approved mockup had four cards. Hand-typed numbers drift the moment the pool changes (the
mockup still said six leagues and 1,638 players), so each card here is a rule over the tables:
the biggest finishing gaps, how often a valued man has a half-price lookalike, and the closest
man-woman pair. `python -m src.findings` writes `app_data/findings.json` from the committed
tables in seconds, so the app reads a small file instead of ranking ~600 players on page load.
`src.app_data` calls it at the end of a rebuild, and tests/test_findings.py checks the file
against the tables.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.narrative import CHEAPER_RATIO, describe_finishing, finishing_from_shots
from src.presentation import feature_columns_for, format_market_value
from src.profile import display_name, market_value_of, prepare_pool
from src.similarity import rank_matches

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app_data"
FINDINGS_PATH = APP_DATA_DIR / "findings.json"

# Finishing cards compare players with at least this many shots: 20 shots is where one season of
# goals starts to mean something (the exact-odds text says how much).
MIN_SHOTS_FOR_FINISHING_CARD = 20
# The price card's population: men whose value is high enough for "half price" to be real money,
# and a lookalike list short enough to be a real shortlist.
MIN_VALUE_FOR_PRICE_CARD_EUR = 10_000_000
PRICE_CARD_LIST_SIZE = 3
OUTFIELD = ("Forward", "Midfielder", "Defender")


@dataclass(frozen=True)
class Finding:
    """One card on the Home page.

    Attributes:
        kind (str): "overperformer", "underperformer", "price" or "cross_game".
        kicker (str): the small label above the figure.
        figure (str): the big number or pair.
        headline (str): one line saying what the figure is.
        body (str): one or two sentences of context, including the caveat.
        link_label (str): the link text.
        player, team (str or None): the player page the link opens; `None` for the Players page.
        tone (str): "up" (orange), "down" (blue) or "neutral" (orange): the card's accent.
    """

    kind: str
    kicker: str
    figure: str
    headline: str
    body: str
    link_label: str
    player: str | None
    team: str | None
    tone: str


def _finishing_findings(pool, xg_table):
    """The biggest over- and under-performer against their chances, among regular shooters."""
    shooters = xg_table[xg_table["shots"] >= MIN_SHOTS_FOR_FINISHING_CARD].merge(
        pool.per90[["player", "team", "nickname", "competition"]], on=["player", "team"]
    )
    cards = []
    for kind, row in (("overperformer", shooters.loc[shooters["xg_diff"].idxmax()]),
                      ("underperformer", shooters.loc[shooters["xg_diff"].idxmin()])):
        shots = pool.shots[(pool.shots["player"] == row["player"]) & (pool.shots["team"] == row["team"])]
        finishing = finishing_from_shots(shots["predicted_xg"].values, shots["is_goal"].sum())
        name = display_name(row)
        over = kind == "overperformer"
        cards.append(Finding(
            kind=kind,
            kicker="SCORING ABOVE HIS CHANCES" if over else "SCORING BELOW HIS CHANCES",
            figure=f"{'+' if over else '−'}{abs(row['xg_diff']):.1f} goals",
            headline=f"{name} scored {finishing.goals} from chances worth {finishing.expected_goals:.1f}",
            body=(f"The biggest gap in the Premier League among players with {MIN_SHOTS_FOR_FINISHING_CARD}+ "
                  f"shots. {describe_finishing(finishing).split('. ', 1)[1]}"),
            link_label=f"Open {name}'s profile →", player=row["player"], team=row["team"],
            tone="up" if over else "down",
        ))
    return cards


def _price_finding(pool):
    """How often a valued man has a lookalike at half his value or less."""
    per90 = pool.per90
    valued_men = [
        row for _, row in per90[(per90["gender"] == "male") & per90["position_group"].isin(OUTFIELD)].iterrows()
        if (market_value_of(pool, row["player"], row["team"])[0] or 0) >= MIN_VALUE_FOR_PRICE_CARD_EUR
    ]
    with_cheaper = 0
    for row in valued_men:
        value = market_value_of(pool, row["player"], row["team"])[0]
        ranked = rank_matches(per90, feature_columns_for(row["position_group"])[2], row["player"], row["team"])
        closest = ranked[ranked["gender"] == "male"].head(PRICE_CARD_LIST_SIZE)
        values = [market_value_of(pool, p, t)[0] for p, t in zip(closest["player"], closest["team"])]
        with_cheaper += any(v is not None and v <= CHEAPER_RATIO * value for v in values)
    share = with_cheaper / len(valued_men)
    return Finding(
        kind="price", kicker="SAME STYLE, SMALLER PRICE", figure=f"{share:.0%}",
        headline=(f"of men valued at {format_market_value(MIN_VALUE_FOR_PRICE_CARD_EUR)}+ have a top-"
                  f"{PRICE_CARD_LIST_SIZE} lookalike at half the price or less"),
        body=(f"{with_cheaper} of {len(valued_men)} outfield players. Style is cheap to find. What the price "
              "adds is level, age and contract, so treat a cheaper lookalike as a lead to check."),
        link_label="Find a player's lookalikes →", player=None, team=None, tone="up",
    )


def _cross_game_finding(pool):
    """The most valuable man whose closest woman has him as her closest man."""
    per90 = pool.per90
    best = None
    for group in OUTFIELD:
        lz_columns = feature_columns_for(group)[2]
        for _, man in per90[(per90["gender"] == "male") & (per90["position_group"] == group)].iterrows():
            value = market_value_of(pool, man["player"], man["team"])[0]
            if value is None or (best is not None and value <= best[0]):
                continue
            woman = _closest(per90, lz_columns, man, "female")
            if woman is None:
                continue
            back = _closest(per90, lz_columns, woman, "male")
            if back["player"] == man["player"] and back["team"] == man["team"]:
                best = (value, man, woman)
    value, man, woman = best
    man_name, woman_name = display_name(man), display_name(woman)
    return Finding(
        kind="cross_game", kicker="ACROSS THE GAME'S TWO HALVES", figure=f"{man_name} ↔ {woman_name}",
        headline=f"{man_name}'s closest match in the women's game plays for {woman['team']}",
        body=(f"{woman_name} ({woman['competition']}) is {man_name}'s closest match among the women, and he is "
              f"her closest among the men, out of {len(per90):,} players ranked within their own leagues."),
        link_label=f"Open {man_name}'s profile →", player=man["player"], team=man["team"], tone="down",
    )


def _closest(per90, lz_columns, row, gender):
    """The row of `gender` nearest to `row` in the lookalike space."""
    ranked = rank_matches(per90, lz_columns, row["player"], row["team"])
    ranked = ranked[ranked["gender"] == gender]
    return ranked.iloc[0] if len(ranked) else None


def build_findings(pool, xg_table):
    """The four cards, in page order.

    Args:
        pool (profile.Pool): from `profile.prepare_pool`.
        xg_table (pandas.DataFrame): `app_data/player_xg_table.parquet`.

    Returns:
        list[Finding]
    """
    over, under = _finishing_findings(pool, xg_table)
    return [over, under, _price_finding(pool), _cross_game_finding(pool)]


def write_findings(app_data_dir=APP_DATA_DIR):
    """Rebuild `findings.json` from the committed tables in `app_data_dir`."""
    app_data_dir = Path(app_data_dir)
    read = lambda name: pd.read_parquet(app_data_dir / f"{name}.parquet")  # noqa: E731
    pool = prepare_pool(read("player_per90"), read("shots_with_xg"), read("market_value"))
    findings = build_findings(pool, read("player_xg_table"))
    (app_data_dir / "findings.json").write_text(
        json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return findings


if __name__ == "__main__":
    for finding in write_findings():
        print(f"{finding.kind}: {finding.figure} | {finding.headline}")
