"""Finishing skill, pooled across seasons: how much of goals minus xG is the player?

Phase 5a put a luck range around one season. This asks the question that range cannot: across
many shots and seasons, do players differ in finishing at all, and by how much? The model is
empirical Bayes. Per shot, a player scores with probability xG plus a skill shift; over n shots
the surplus (goals - xG) is n * skill + luck, where luck has variance sum(xG * (1 - xG)). Skill is
assumed normal around zero with variance tau^2 across players. Estimate tau^2 from the spread of
the surpluses beyond what luck explains, then shrink each player's surplus toward zero by how
little his shots can tell skill from luck. The tau^2 estimate also answers the honest first
question: is it distinguishable from zero?

Pure functions over a shot table (`player`, `is_goal`, `predicted_xg`, optionally `season_id`);
the warehouse read and the model scoring are at the bottom.
"""

import numpy as np
import pandas as pd

from src import config
from src.models import build_feature_matrix, out_of_fold_xg, train_logistic_regression

MIN_SHOTS = 30  # below this a player's surplus is mostly luck; he stays out of the tau^2 estimate
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 42


def team_adjusted_xg(shots, team_column="team", season_column="season_id"):
    """xG plus the surplus per shot of the shooter's *teammates* that season.

    A team can beat the model together: Barcelona out-scored its xG in every one of 17 seasons
    (+255 goals), with chances the features cannot see (the keeper's position, how open the goal
    is) or with a system that makes them. That is the team's, not any one player's skill, and
    pooled across seasons it would pass for his. So each shot's baseline moves up by the
    surplus per shot of the other players of that team and season, leaving the player compared
    with his own teammates. The shooter's own shots are left out of the shift (leave-one-out):
    a player taking 40% of a team's shots must not be measured against himself.

    Args:
        shots (pandas.DataFrame): `player`, `is_goal`, `predicted_xg`, team and season columns.
        team_column (str): the shooter's team.
        season_column (str): the season.

    Returns:
        pandas.Series: the adjusted probability, clipped to (0, 1), indexed like `shots`. A
            shooter with no teammate shots keeps his xG.
    """
    surplus = shots["is_goal"].astype(float) - shots["predicted_xg"]
    team_keys = [shots[team_column], shots[season_column]]
    team_sum = surplus.groupby(team_keys).transform("sum")
    team_n = surplus.groupby(team_keys).transform("size")
    own_keys = team_keys + [shots["player"]]
    own_sum = surplus.groupby(own_keys).transform("sum")
    own_n = surplus.groupby(own_keys).transform("size")
    others = (team_n - own_n).to_numpy()
    shift = np.divide(
        (team_sum - own_sum).to_numpy(), others, out=np.zeros(len(shots)), where=others > 0
    )
    return (shots["predicted_xg"] + shift).clip(0.001, 0.999)


def player_totals(shots):
    """One row per player: shots, goals, xG, and the variance of the surplus due to luck alone.

    Args:
        shots (pandas.DataFrame): `player`, `is_goal` (bool), `predicted_xg` (probability).

    Returns:
        pandas.DataFrame: `player`, `shots`, `goals`, `xg`, `surplus` (goals - xG), `luck_var`
            (sum of xG * (1 - xG): the variance of the goals a player with no skill would score).
    """
    frame = shots.assign(
        goal=shots["is_goal"].astype(int),
        luck_var=shots["predicted_xg"] * (1 - shots["predicted_xg"]),
    )
    totals = frame.groupby("player").agg(
        shots=("goal", "size"), goals=("goal", "sum"),
        xg=("predicted_xg", "sum"), luck_var=("luck_var", "sum"),
    )
    totals["surplus"] = totals["goals"] - totals["xg"]
    return totals.reset_index()


def common_shift(totals):
    """The group's shared surplus per shot: total goals minus total xG over total shots.

    A model fitted elsewhere (here: Premier League and Leverkusen) is a little off for another
    league or era, and a whole team can out-score its xG together (better chances than the
    features see). That is a shift every player in the group shares; it is not any one player's
    skill, and left in it would inflate the spread between players.

    Args:
        totals (pandas.DataFrame): `player_totals`' output.

    Returns:
        float: goals per shot above the model, pooled.
    """
    return float(totals["surplus"].sum() / totals["shots"].sum())


def estimate_tau_squared(totals):
    """Between-player variance of finishing skill, per shot, by the method of moments.

    A player's surplus has variance n^2 * tau^2 (skill, scaled by his shots) plus luck_var, so
    E[surplus^2 - luck_var] = n^2 * tau^2. Summing over players and dividing by sum(n^2) gives
    tau^2. It can come out negative when the players spread *less* than luck alone would; it is
    floored at zero, which reads as "no detectable skill variation".

    Args:
        totals (pandas.DataFrame): `player_totals`' output, already restricted to the players
            to estimate from.

    Returns:
        float: tau^2 in (goals per shot)^2, at least 0.
    """
    centred = totals["surplus"] - totals["shots"] * common_shift(totals)
    excess = (centred**2 - totals["luck_var"]).sum()
    return max(0.0, excess / (totals["shots"] ** 2).sum())


def shrink(totals, tau_squared):
    """Each player's skill estimate (goals per shot) and its shrunken surplus (goals).

    The posterior mean of a normal skill given a normal surplus: raw surplus times
    n^2 tau^2 / (n^2 tau^2 + luck_var), the share of its variance that is skill. A player with
    few shots, or a tau^2 near zero, is pulled to zero; with many shots he keeps most of it.

    Args:
        totals (pandas.DataFrame): `player_totals`' output.
        tau_squared (float): from `estimate_tau_squared`.

    Returns:
        pandas.DataFrame: `totals` plus `weight` (the share kept), `shrunk_surplus` and
            `skill_per_shot` (the shrunken surplus over his shots).
    """
    skill_variance = totals["shots"] ** 2 * tau_squared
    weight = skill_variance / (skill_variance + totals["luck_var"])
    result = totals.assign(weight=weight)
    # Relative to the group: the shared shift is taken out first and is not his.
    centred = result["surplus"] - result["shots"] * common_shift(totals)
    result["shrunk_surplus"] = centred * weight
    result["skill_per_shot"] = result["shrunk_surplus"] / result["shots"]
    return result


def bootstrap_tau_squared(totals, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    """90% interval for tau^2 by resampling players with replacement.

    Args:
        totals (pandas.DataFrame): `player_totals`' output (the players estimated from).
        draws (int): number of resamples.
        seed (int): fixed so the interval is reproducible.

    Returns:
        tuple[float, float]: the 5th and 95th percentile of tau^2.
    """
    rng = np.random.default_rng(seed)
    n = len(totals)
    estimates = [
        estimate_tau_squared(totals.iloc[rng.integers(0, n, n)]) for _ in range(draws)
    ]
    low, high = np.percentile(estimates, [5, 95])
    return float(low), float(high)


def split_half_check(shots, season_column="season_id", min_shots=MIN_SHOTS):
    """Does the estimate from some seasons predict the surplus in the others?

    Seasons are split by alternating rank (1st, 3rd, ... vs 2nd, 4th, ...), so both halves span
    the same years. For players with shots in both halves, predict the second half's surplus per
    shot from the first half's raw rate, from the shrunken rate (tau^2 estimated on the first
    half only), and from zero (every finisher is average). The error is weighted by the second
    half's shots.

    Args:
        shots (pandas.DataFrame): `player`, `is_goal`, `predicted_xg`, and `season_column`.
        season_column (str): what to split on.
        min_shots (int): players need this many shots in the first half.

    Returns:
        dict: `players`, `tau_squared` (first half), `shift` (the group's shared surplus per
            shot), and the weighted squared error of predicting from the raw rate (`mse_raw`), the
            shift plus the shrunken skill (`mse_shrunk`), the shift alone (`mse_shift`) and
            nothing (`mse_zero`). Skill is real if `mse_shrunk` beats `mse_shift`.
    """
    seasons = sorted(shots[season_column].unique())
    first_seasons = set(seasons[::2])
    in_first = shots[season_column].isin(first_seasons)
    first, second = player_totals(shots[in_first]), player_totals(shots[~in_first])
    first = first[first["shots"] >= min_shots]
    tau_squared = estimate_tau_squared(first)
    shift = common_shift(first)
    shrunk = shrink(first, tau_squared)
    both = shrunk.merge(second, on="player", suffixes=("", "_next"))
    target = both["surplus_next"] / both["shots_next"]
    weights = both["shots_next"]

    def mse(prediction):
        return float(np.average((target - prediction) ** 2, weights=weights))

    return {
        "players": len(both),
        "tau_squared": tau_squared,
        "shift": shift,
        "mse_raw": mse(both["surplus"] / both["shots"]),
        "mse_shrunk": mse(shift + both["skill_per_shot"]),
        "mse_shift": mse(shift),
        "mse_zero": mse(0.0),
    }


def forward_check(shots, season_order, min_shots=MIN_SHOTS, min_next_shots=10,
                  draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    """Fit on the seasons so far, predict the next one, for every season in turn.

    The split-half used 26 players; this walks forward in time, so every player with enough past
    shots and some shots the next season is one test row, in every season he qualifies. For each
    step the past seasons give the group's shift and tau^2 (players with `min_shots`+ shots in
    the past); the prediction for a player's next-season surplus per shot is the shift (all
    alike), his raw past rate, or the shift plus his shrunken skill. Squared error is weighted by
    the next season's shots. Skill is real if the shrunken prediction beats the shift alone, and
    the interval on that gap comes from resampling the test rows.

    Args:
        shots (pandas.DataFrame): `player`, `is_goal`, `predicted_xg` (team-adjusted or not) and
            `season_id`.
        season_order (list): season ids, oldest first. Ids are not chronological, so the caller
            says what comes before what.
        min_shots (int): past shots a player needs to be predicted.
        min_next_shots (int): shots in the target season for a row to count.
        draws (int): bootstrap resamples of the test rows.
        seed (int): fixed for a reproducible interval.

    Returns:
        dict: `rows`, `mse_shift`, `mse_shrunk`, `mse_raw`, and `gain` (shift minus shrunk, so
            positive means skill helps) with `gain_low`, `gain_high` (90% interval).
    """
    rows = []
    for step in range(1, len(season_order)):
        past = shots[shots["season_id"].isin(season_order[:step])]
        future = shots[shots["season_id"] == season_order[step]]
        totals = player_totals(past)
        totals = totals[totals["shots"] >= min_shots]
        if len(totals) < 2:
            continue
        shift = common_shift(totals)
        shrunk = shrink(totals, estimate_tau_squared(totals))
        merged = shrunk.merge(player_totals(future), on="player", suffixes=("", "_next"))
        merged = merged[merged["shots_next"] >= min_next_shots]
        rows.append(pd.DataFrame({
            "target": merged["surplus_next"] / merged["shots_next"],
            "weight": merged["shots_next"],
            "shift": shift,
            "shrunk": shift + merged["skill_per_shot"],
            "raw": merged["surplus"] / merged["shots"],
        }))
    table = pd.concat(rows, ignore_index=True)

    def mse(frame, column):
        return float(np.average((frame["target"] - frame[column]) ** 2, weights=frame["weight"]))

    rng = np.random.default_rng(seed)
    gains = []
    for _ in range(draws):
        sample = table.iloc[rng.integers(0, len(table), len(table))]
        gains.append(mse(sample, "shift") - mse(sample, "shrunk"))
    low, high = np.percentile(gains, [5, 95])
    return {
        "rows": len(table),
        "mse_shift": mse(table, "shift"),
        "mse_shrunk": mse(table, "shrunk"),
        "mse_raw": mse(table, "raw"),
        "gain": mse(table, "shift") - mse(table, "shrunk"),
        "gain_low": float(low),
        "gain_high": float(high),
    }


def score_shots(shots, train_shots):
    """xG for every shot, never from a model that saw that shot's match.

    Shots in the training seasons are scored out of fold; all the others by one model fitted on
    the training shots (they were never in it, so that is already out of sample).

    Args:
        shots (pandas.DataFrame): the shots to score, with the model's feature columns, `match_id`
            and `season_id`/`competition_id`.
        train_shots (pandas.DataFrame): the xG training shots (`config.TRAIN_SETS`), same columns.

    Returns:
        pandas.Series: `predicted_xg`, indexed like `shots`.
    """
    train_keys = {(d.comp_id, d.season_id) for d in config.TRAIN_SETS}
    in_train = pd.Series(
        [(c, s) in train_keys for c, s in zip(shots["competition_id"], shots["season_id"])],
        index=shots.index,
    )
    model = train_logistic_regression(*build_feature_matrix(train_shots))
    predicted = pd.Series(np.nan, index=shots.index)
    outside = shots[~in_train]
    if len(outside):
        predicted[~in_train] = model.predict_proba(build_feature_matrix(outside)[0])[:, 1]
    inside = shots[in_train]
    if len(inside):
        predicted[in_train] = out_of_fold_xg(inside)
    return predicted
