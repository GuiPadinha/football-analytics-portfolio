"""src/finishing.py: pooled finishing skill (empirical Bayes) on simulated shots.

The simulation is the test that matters: shots are generated with a known skill spread, so the
estimator must recover it, and with none it must say "nothing there" instead of inventing a
ranking of finishers.
"""

import numpy as np
import pandas as pd

from src.finishing import (
    bootstrap_tau_squared,
    estimate_tau_squared,
    player_totals,
    shrink,
    split_half_check,
)


def simulate(tau, players=300, shots_each=200, seasons=4, seed=0):
    """Shots with xG drawn from a spread of chances and a per-player skill shift on the logit."""
    rng = np.random.default_rng(seed)
    skill = rng.normal(0, tau, players)  # in probability points per shot
    rows = []
    for player in range(players):
        xg = rng.beta(1.2, 8, shots_each)
        goal = rng.random(shots_each) < np.clip(xg + skill[player], 0.001, 0.999)
        rows.append(pd.DataFrame({
            "player": player, "predicted_xg": xg, "is_goal": goal,
            "season_id": rng.integers(0, seasons, shots_each),
        }))
    return pd.concat(rows, ignore_index=True), skill


def test_it_recovers_a_known_skill_spread():
    shots, _ = simulate(tau=0.02)
    tau_squared = estimate_tau_squared(player_totals(shots))
    assert abs(tau_squared**0.5 - 0.02) < 0.004
    low, high = bootstrap_tau_squared(player_totals(shots), draws=200)
    assert low <= tau_squared <= high


def test_with_no_skill_it_finds_none():
    shots, _ = simulate(tau=0.0)
    totals = player_totals(shots)
    tau_squared = estimate_tau_squared(totals)
    assert tau_squared**0.5 < 0.005
    shrunk = shrink(totals, tau_squared)
    assert shrunk["skill_per_shot"].abs().max() < 0.005


def test_shrinkage_pulls_few_shots_harder_than_many():
    totals = pd.DataFrame({
        "player": ["few", "many"], "shots": [20, 2000], "goals": [10, 400], "xg": [5.0, 300.0],
        "luck_var": [4.0, 250.0],
    })
    totals["surplus"] = totals["goals"] - totals["xg"]
    kept = shrink(totals, 0.0004).set_index("player")["weight"]
    assert kept["few"] < kept["many"] < 1


def test_the_split_half_prefers_shrunk_to_raw_when_skill_is_small():
    shots, _ = simulate(tau=0.01, players=400, shots_each=120)
    result = split_half_check(shots, min_shots=30)
    assert result["mse_shrunk"] < result["mse_raw"]


def test_a_shift_every_player_shares_is_not_skill():
    """Every shooter beats the model by 1 point per shot, as a whole team might: tau^2 stays ~0."""
    shots, _ = simulate(tau=0.0)
    shots["is_goal"] = np.random.default_rng(1).random(len(shots)) < (shots["predicted_xg"] + 0.01)
    totals = player_totals(shots)
    assert estimate_tau_squared(totals) ** 0.5 < 0.005
    from src.finishing import common_shift
    assert abs(common_shift(totals) - 0.01) < 0.003


def test_team_adjustment_leaves_the_shooters_own_shots_out():
    """A's baseline moves by B's surplus only; a lone shooter keeps his xG."""
    from src.finishing import team_adjusted_xg

    shots = pd.DataFrame({
        "player": ["A", "A", "B", "B", "C"],
        "team": ["T", "T", "T", "T", "U"],
        "season_id": [1] * 5,
        "predicted_xg": [0.5, 0.5, 0.2, 0.2, 0.3],
        "is_goal": [True, True, False, False, True],
    })
    adjusted = team_adjusted_xg(shots)
    assert adjusted.iloc[0] == 0.5 + (-0.2)  # B's surplus per shot is -0.2
    assert adjusted.iloc[2] == 0.2 + 0.5  # A's is +0.5
    assert adjusted.iloc[4] == 0.3  # C has no teammate shots
