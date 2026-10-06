"""Unit tests for src/narrative.py: the rule-based sentences of the redesigned app.

The thresholds were calibrated on the real pool (ML_LEARNING_LOG.md, 2026-10-06). These tests pin
the rules on hand-built inputs, including the two cases that bit during that calibration: a lead
the reader couldn't see ("2.5 shots per 90, to 2.5") and a quiet keeper's best stat read as
"top 73%".
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.narrative import (
    CompareSide,
    Finishing,
    Lookalike,
    Saves,
    bottom_share,
    build_compare_verdict,
    build_short_version,
    closeness_band,
    describe_closest,
    describe_finishing,
    describe_price,
    describe_price_gap,
    describe_saves,
    describe_style,
    finishing_from_shots,
    goals_distribution,
    top_share,
)
from src.similarity import GK_PER90_FEATURE_COLUMNS, PER90_FEATURE_COLUMNS, PairCloseness


def _percentiles(columns, **values):
    """A player's percentile row: 0.3 everywhere except the stats named."""
    row = pd.Series(0.3, index=columns)
    for stat, pct in values.items():
        row[f"{stat}_p90"] = pct
    return row


def test_top_share_counts_the_player_and_everyone_above():
    assert top_share(1.0, 422) == 1                    # the best of 422
    assert top_share(418 / 422, 422) == 2              # the 5th best: 5/422 = 1.2%, rounded up
    assert top_share(0.9, 10) == 20                    # 2nd of 10


def test_bottom_share_counts_the_player_and_everyone_below():
    assert bottom_share(1 / 422) == 1
    assert bottom_share(0.27) == 27


def test_style_names_two_standouts_with_one_shared_rank():
    pct = _percentiles(PER90_FEATURE_COLUMNS, dribbles_completed=1.0, non_penalty_goals=0.999)
    assert describe_style("Midfielder", pct, 422) == "A dribbler and scorer: top 1% of midfielders for both."


def test_style_names_two_standouts_with_their_own_ranks():
    pct = _percentiles(PER90_FEATURE_COLUMNS, tackles=0.99, interceptions=0.95)
    assert describe_style("Defender", pct, 100) == "A tackler and interceptor: top 2% and top 6% of defenders."


def test_style_one_standout_takes_the_right_article():
    pct = _percentiles(PER90_FEATURE_COLUMNS, interceptions=0.97)
    assert describe_style("Defender", pct, 100) == "An interceptor: top 4% of defenders."


def test_style_counts_standouts_beyond_the_two_it_names():
    pct = _percentiles(PER90_FEATURE_COLUMNS, shots=0.99, non_penalty_goals=0.98, assists=0.95, tackles=0.91)
    assert describe_style("Forward", pct, 100).endswith(", plus two more stats in the top 10%.")


def test_style_without_a_standout_names_the_best_stat():
    pct = _percentiles(PER90_FEATURE_COLUMNS, pressures=0.7)
    assert describe_style("Midfielder", pct, 100) == "No standout stat: the best is pressures, top 31% of midfielders."


def test_style_all_below_median_is_a_quiet_keeper_not_a_top_73_percent():
    pct = _percentiles(GK_PER90_FEATURE_COLUMNS, punches=0.27)
    assert describe_style("Goalkeeper", pct, 168) == (
        "A quiet keeper: below the median on saves, claims, punches and sweeper actions."
    )
    assert describe_style("Defender", _percentiles(PER90_FEATURE_COLUMNS), 100) == (
        "A low-volume defender: below the median on every stat."
    )


def test_style_never_credits_a_keeper_with_goals_conceded_or_ranks_save_pct_as_style():
    pct = _percentiles(GK_PER90_FEATURE_COLUMNS, goals_conceded=1.0, saves=0.95)
    pct["save_pct"] = 1.0
    assert describe_style("Goalkeeper", pct, 100) == "A busy shot-stopper: top 6% of goalkeepers."


def test_goals_distribution_is_a_distribution_over_zero_to_n_goals():
    pmf = goals_distribution([0.1, 0.5, 0.8])
    assert len(pmf) == 4
    assert pmf.sum() == pytest.approx(1.0)
    assert goals_distribution([]).tolist() == [1.0]


def test_goals_distribution_matches_the_binomial_when_every_shot_is_alike():
    pmf = goals_distribution([0.2] * 5)
    expected = [math.comb(5, k) * 0.2**k * 0.8 ** (5 - k) for k in range(6)]
    assert pmf == pytest.approx(expected)


def test_finishing_from_shots_reads_both_tails():
    finishing = finishing_from_shots(np.array([0.5, 0.5]), goals=2)
    assert finishing.expected_goals == pytest.approx(1.0)
    assert finishing.p_at_least == pytest.approx(0.25)
    assert finishing.p_at_most == pytest.approx(1.0)


@pytest.mark.parametrize(
    "finishing, expected",
    [
        (Finishing(1, 0.7, 0.5, 0.8), "1 goal from chances worth 0.7: too few chances to judge the finishing."),
        (Finishing(6, 7.3, 0.78, 0.37), "6 goals from chances worth 7.3: about what an average finisher would score."),
        # More goals than xG is still par while an average finisher does it more than one season in 5.
        (Finishing(9, 8.0, 0.35, 0.80), "9 goals from chances worth 8.0: about what an average finisher would score."),
    ],
)
def test_finishing_short_answers(finishing, expected):
    assert describe_finishing(finishing) == expected


def test_finishing_rare_overperformance_says_likely_skill_with_the_odds():
    text = describe_finishing(Finishing(24, 17.5, 0.045, 0.98))
    assert text == (
        "24 goals from chances worth 17.5. An average finisher scores that many from the same chances "
        "about one season in 22: some of it is likely skill, but don't pay for all of it."
    )


def test_finishing_unusual_overperformance_says_judge_on_the_chances():
    text = describe_finishing(Finishing(17, 12.5, 0.072, 0.96))
    assert "about one season in 14, so luck alone could explain it: judge on the 12.5, not the 17." in text


def test_finishing_band_edges_are_inclusive():
    assert "likely skill" in describe_finishing(Finishing(10, 6.0, 0.05, 0.99))
    assert "luck alone" in describe_finishing(Finishing(10, 6.0, 0.20, 0.99))


def test_finishing_underperformance_bands_and_zero_goals():
    assert describe_finishing(Finishing(4, 7.0, 0.95, 0.12)).endswith(
        "about one season in 8, likely bad luck: if the chances keep coming, the goals usually follow."
    )
    assert describe_finishing(Finishing(0, 2.9, 1.0, 0.033)) == (
        "No goals from chances worth 2.9. An average finisher scores none from the same chances "
        "about one season in 30: more than bad luck usually explains."
    )


def test_finishing_odds_beyond_a_thousand_are_capped():
    assert "less than one season in 1,000" in describe_finishing(Finishing(20, 5.0, 1e-6, 1.0))


def test_saves_rank_reads_top_or_bottom():
    assert describe_saves(Saves(0.83, 92, 1.0), 168) == "Saved 83% of 92 shots on target: top 1% of goalkeepers."
    assert describe_saves(Saves(0.67, 90, 0.335), 168) == "Saved 67% of 90 shots on target: bottom 34% of goalkeepers."


def test_price_needs_a_value_for_the_player_and_a_lookalike():
    assert describe_price(None, [Lookalike("A", 1e6)]) is None
    assert describe_price(float("nan"), [Lookalike("A", 1e6)]) is None
    assert describe_price(20e6, [Lookalike("A", None), Lookalike("B", float("nan"))]) is None


def test_price_names_the_two_cheapest_and_counts_the_rest():
    lookalikes = [
        Lookalike("A", 20e6), Lookalike("B", 3e6), Lookalike("C", 3.5e6), Lookalike("D", 1e6), Lookalike("E", None),
    ]
    assert describe_price(20e6, lookalikes) == (
        "Similar profiles cost half as much or less: D (€1.0M) and B (€3.0M), plus one more of the five closest."
    )


def test_price_exactly_half_counts_and_one_cheaper_is_singular():
    assert describe_price(20e6, [Lookalike("A", 10e6), Lookalike("B", 15e6)]) == (
        "A similar profile costs half as much or less: A (€10.0M)."
    )


def test_price_when_the_player_is_the_cheap_one():
    lookalikes = [Lookalike(name, value) for name, value in zip("ABCDE", [12e6, 20e6, 35e6, 15e6, 18e6])]
    assert describe_price(2e6, lookalikes) == "Cheaper than all five closest matches (€12.0M to €35.0M)."
    assert describe_price(2e6, lookalikes[:2]) == "Cheaper than both closest matches (€12.0M to €20.0M)."
    assert describe_price(2e6, [Lookalike("A", 12e6), Lookalike("B", None)]) == (
        "Cheaper than every close match with a value (€12.0M)."
    )


def test_price_when_nothing_is_much_cheaper():
    lookalikes = [Lookalike(name, value) for name, value in zip("ABCDE", [12e6, 25e6, 30e6, 15e6, 18e6])]
    assert describe_price(20e6, lookalikes) == "None of the five closest matches costs half as much."


def test_closest_names_each_game():
    looks = [Lookalike("Khadija Shaw", None)]
    assert describe_closest(looks, Lookalike("Karim Benzema", None), "male") == (
        "Closest match: Khadija Shaw; in the men's game, Karim Benzema."
    )
    assert describe_closest(looks) == "Closest match: Khadija Shaw."
    assert describe_closest([]) is None


def test_short_version_keeper_uses_saves_not_finishing():
    text = build_short_version(
        "Goalkeeper", _percentiles(GK_PER90_FEATURE_COLUMNS, saves=0.95), 100,
        finishing=Finishing(1, 0.7, 0.5, 0.8), saves=Saves(0.75, 80, 0.8),
    )
    assert "Saved 75% of 80 shots on target" in text
    assert "chances worth" not in text


def test_short_version_without_a_price_closes_on_the_closest_matches():
    text = build_short_version(
        "Forward", _percentiles(PER90_FEATURE_COLUMNS, non_penalty_goals=0.99), 100,
        lookalikes=[Lookalike("Khadija Shaw", None)], other_game_closest=Lookalike("Karim Benzema", None),
        other_game="male",
    )
    assert text == "A scorer: top 2% of forwards. Closest match: Khadija Shaw; in the men's game, Karim Benzema."


def test_short_version_prefers_the_price_when_there_is_one():
    text = build_short_version(
        "Forward", _percentiles(PER90_FEATURE_COLUMNS, non_penalty_goals=0.99), 100,
        market_value_eur=20e6, lookalikes=[Lookalike("A", 3e6)],
        other_game_closest=Lookalike("B", None), other_game="female",
    )
    assert text.endswith("A similar profile costs half as much or less: A (€3.0M).")
    assert "Closest match" not in text


@pytest.mark.parametrize("rank, band", [(1, "like-for-like"), (5, "like-for-like"), (6, "similar"),
                                        (25, "similar"), (26, "different")])
def test_closeness_band_edges(rank, band):
    assert closeness_band(rank) == band


def _side(name, value=None, save_pct=None, columns=PER90_FEATURE_COLUMNS, **rates):
    per90 = pd.Series(1.0, index=columns)
    for stat, rate in rates.items():
        per90[f"{stat}_p90"] = rate
    return CompareSide(name, per90, value, save_pct)


def _closeness(rank=1, from_a=True, size=194, gender="female", position="Forward",
               columns=PER90_FEATURE_COLUMNS, gaps=None):
    standing_a = pd.Series(0.0, index=columns)
    for stat, gap in (gaps or {}).items():
        standing_a[f"{stat}_p90"] = gap
    return PairCloseness(rank, from_a, size, gender, position, standing_a, pd.Series(0.0, index=columns))


def test_verdict_opening_reads_from_the_list_the_rank_came_from():
    a, b = _side("Karim Benzema"), _side("Ewa Pajor")
    verdict = build_compare_verdict(a, b, _closeness(rank=1, from_a=True))
    assert verdict.startswith("A like-for-like pair: Ewa Pajor is Karim Benzema's closest match among 194 women's forwards.")
    verdict = build_compare_verdict(a, b, _closeness(rank=558, from_a=False, size=1246, gender="male", position="Outfield"))
    assert verdict.startswith(
        "Not a like-for-like swap: Karim Benzema is only Ewa Pajor's 558th-closest match among 1,246 men's outfielders."
    )


def test_verdict_names_a_lead_only_when_both_the_standing_and_the_rate_show_it():
    closeness = _closeness(gaps={"shots": 1.0, "dribbles_completed": -0.8, "tackles": 0.3})
    # Shots: a full standard deviation apart but the same rate on the page, so no lead.
    same_rate = build_compare_verdict(_side("A", shots=2.5), _side("B", shots=2.5, dribbles_completed=2.0), closeness)
    assert "A leads on" not in same_rate
    assert "B leads on dribbling: 2.0 dribbles per 90, to A's 1.0." in same_rate
    visible = build_compare_verdict(_side("A", shots=3.2), _side("B", shots=2.5), closeness)
    assert "A leads on shooting: 3.2 shots per 90, to B's 2.5." in visible
    assert "tackling" not in visible                       # a 0.3 SD gap is too small to name


def test_verdict_can_lead_over_a_zero_rate_and_says_so_when_nothing_separates():
    lead = build_compare_verdict(_side("A", assists=0.2), _side("B", assists=0.0), _closeness(gaps={"assists": 1.0}))
    assert "A leads on assists: 0.20 assists per 90, to B's 0." in lead
    assert "No stat separates them by much." in build_compare_verdict(_side("A"), _side("B"), _closeness())


def test_verdict_never_makes_goals_conceded_a_keeper_lead():
    columns = GK_PER90_FEATURE_COLUMNS
    a = _side("A", columns=columns, goals_conceded=2.0)
    b = _side("B", columns=columns, goals_conceded=1.0)
    verdict = build_compare_verdict(a, b, _closeness(columns=columns, position="Goalkeeper", gaps={"goals_conceded": 1.5}))
    assert "goals conceded" not in verdict


def test_verdict_keepers_compare_save_pct():
    columns = GK_PER90_FEATURE_COLUMNS
    closeness = _closeness(columns=columns, position="Goalkeeper", gender="male")
    better = build_compare_verdict(_side("A", save_pct=0.83, columns=columns), _side("B", save_pct=0.73, columns=columns), closeness)
    assert "A saved a bigger share of shots on target: 83% to 73%." in better
    level = build_compare_verdict(_side("A", save_pct=0.72, columns=columns), _side("B", save_pct=0.71, columns=columns), closeness)
    assert "Both saved about the same share of shots on target (72% and 71%)." in level


@pytest.mark.parametrize(
    "value_a, value_b, band, expected",
    [
        (32e6, 8e6, "different", "B costs a quarter as much (€8.0M against €32.0M), but does a different job."),
        (20e6, 3e6, "like-for-like", "B costs a seventh as much (€3.0M against €20.0M), for a close profile."),
        (30e6, 12e6, "similar", "B costs €18.0M less (€12.0M against €30.0M), for a partly different profile."),
        (35e6, 2e6, "like-for-like", "B costs less than a tenth as much (€2.0M against €35.0M), for a close profile."),
        (20e6, 22e6, "different", "Both are valued about the same (€20.0M and €22.0M)."),
    ],
)
def test_price_gap_phrases(value_a, value_b, band, expected):
    assert describe_price_gap(_side("A", value_a), _side("B", value_b), band) == expected


def test_price_gap_needs_both_values():
    assert describe_price_gap(_side("A", 20e6), _side("B"), "different") is None
    assert "costs" not in build_compare_verdict(_side("A", 20e6), _side("B"), _closeness())
