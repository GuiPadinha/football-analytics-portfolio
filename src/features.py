"""Feature engineering for the xG model and player similarity clustering.

Built out in Session S2 (xG features: distance, angle, body part, assist
type, game state) and Session S5 (per-90 player metrics).
"""

import numpy as np
import pandas as pd

from src.data_loader import load_events, load_matches, safe_bool_column, safe_column

# StatsBomb pitch is 120x80. Goal line sits at x=120, goal mouth spans
# y=36 to y=44 (8-yard width centred on y=40).
GOAL_X = 120
GOAL_POST_TOP = (GOAL_X, 44)
GOAL_POST_BOTTOM = (GOAL_X, 36)
GOAL_CENTER = (GOAL_X, 40)


def _shot_distance(x, y):
    """Euclidean distance from the shot location to the centre of the goal."""
    return np.hypot(GOAL_CENTER[0] - x, GOAL_CENTER[1] - y)


def _shot_angle(x, y):
    """Angle (degrees) subtended by the goalposts as seen from the shot location.

    A shot from directly in front of an open goal subtends close to 180
    degrees; a shot from a tight angle near the byline subtends close to 0.
    This is a stronger predictor than distance alone since it captures how
    much of the goal is actually visible/reachable from that spot.
    """
    post_top = np.array(GOAL_POST_TOP) - np.array([x, y])
    post_bottom = np.array(GOAL_POST_BOTTOM) - np.array([x, y])
    cos_angle = np.dot(post_top, post_bottom) / (
        np.linalg.norm(post_top) * np.linalg.norm(post_bottom)
    )
    return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))


def _classify_assist(pass_row):
    """Classify the pass that created a shot into a coarse assist type.

    Falls back to 'Standard Pass' for any open-play pass that isn't a cross,
    through ball, or cut-back — these three are the ones known to shift shot
    quality (different defensive shape, different angle of approach).
    """
    if pass_row is None:
        return "None"
    # These flag columns hold True/NaN (not True/False), and bool(nan) is
    # True in Python — an `is True` check is required to avoid every NaN
    # being misread as a positive flag.
    if pass_row.get("pass_cross") is True:
        return "Cross"
    if pass_row.get("pass_through_ball") is True:
        return "Through Ball"
    if pass_row.get("pass_cut_back") is True:
        return "Cut Back"
    return "Standard Pass"


def _compute_score_diff_before_shot(events):
    """Map each shot event's index to the shooting team's goal difference
    at the moment the shot was taken (i.e. before that shot's own outcome
    is applied).

    Game state changes shooting behaviour — teams chasing a goal take
    riskier shots than teams protecting a lead — so this needs to reflect
    the score as it stood *before* the shot, not after.

    Own goals are not credited here: StatsBomb logs them as separate
    'Own Goal For' / 'Own Goal Against' events rather than as part of the
    scoring team's own Shot events, and they are rare enough relative to
    open-play goals that omitting them is an accepted simplification for
    this feature.

    Args:
        events (pandas.DataFrame): full chronological event stream for one match.

    Returns:
        dict[int, int]: event index -> goal difference for the shooting team.
    """
    teams = events["team"].dropna().unique()
    goals_scored = {team: 0 for team in teams}
    score_diff_by_index = {}

    for idx, row in events.iterrows():
        if row.get("period") == 5:  # penalty shootout — not part of in-game score state
            continue
        if row["type"] != "Shot":
            continue
        team = row["team"]
        opponent_goals = sum(v for t, v in goals_scored.items() if t != team)
        score_diff_by_index[idx] = goals_scored[team] - opponent_goals
        if row["shot_outcome"] == "Goal":
            goals_scored[team] += 1

    return score_diff_by_index


def extract_shot_features(events):
    """Build engineered shot features from a single match's event stream.

    Args:
        events (pandas.DataFrame): full event stream for one match, as
            returned by `load_events`.

    Returns:
        pandas.DataFrame: one row per shot, with engineered features and
            the `is_goal` target. In-game penalties and free kicks are kept
            but flagged via `is_penalty`/`is_free_kick` rather than dropped,
            since they're a meaningful chunk of high-xG shots — but
            penalty-shootout attempts (period 5) ARE dropped: they convert
            at ~75%, aren't part of open/in-game play, and would otherwise
            inflate the penalty base rate and contaminate any tournament
            test set with knockout shootouts (e.g. EURO 2024). For a
            non-penalty xG (npxG) view, filter the returned `is_penalty`
            column — npxG is the recommended headline for player rankings.
    """
    shots = events[events["type"] == "Shot"].copy()

    # Drop penalty-shootout attempts (period 5) — see docstring. Guarded because
    # `period` is always present in StatsBomb events, but a malformed/empty stream
    # shouldn't hard-crash here.
    if "period" in shots.columns:
        shots = shots[shots["period"] != 5]
    # Guard against the rare shot logged without a location (would crash the
    # loc[0]/loc[1] unpacking below); such rows can't be placed on the pitch anyway.
    shots = shots[shots["location"].notna()].copy()

    shots["x"] = shots["location"].apply(lambda loc: loc[0])
    shots["y"] = shots["location"].apply(lambda loc: loc[1])
    shots["distance_to_goal"] = _shot_distance(shots["x"], shots["y"])
    shots["angle_to_goal"] = [
        _shot_angle(x, y) for x, y in zip(shots["x"], shots["y"])
    ]

    # shot_body_part/shot_type/shot_outcome/shot_key_pass_id are themselves shot-only fields —
    # entirely absent from `events` if the match has zero Shot events at all (a sparser version
    # of the same statsbombpy quirk as shot_first_time/under_pressure below), so a bare access
    # would crash on the all-shots-dropped edge case (e.g. every shot lost to the period-5/
    # null-location filters above). Guarded the same way.
    shots["is_header"] = safe_column(shots, "shot_body_part") == "Head"
    # shot_first_time / under_pressure are sparse flag columns (statsbombpy only includes them
    # if at least one event in the match has them set) — a match with zero first-time shots or
    # zero pressured shots drops the column entirely, which crashed extract_shot_features on a
    # genuinely new competition (Barcelona 2020/21, Phase 4 data expansion) before this fix.
    shots["is_first_time"] = safe_bool_column(shots, "shot_first_time")
    shots["under_pressure"] = safe_bool_column(shots, "under_pressure")
    shots["is_penalty"] = safe_column(shots, "shot_type") == "Penalty"
    shots["is_free_kick"] = safe_column(shots, "shot_type") == "Free Kick"

    passes_by_id = (
        events[events["type"] == "Pass"].set_index("id").to_dict(orient="index")
    )
    shots["assist_type"] = [
        _classify_assist(passes_by_id.get(key_pass_id))
        for key_pass_id in safe_column(shots, "shot_key_pass_id")
    ]

    score_diff_by_index = _compute_score_diff_before_shot(events)
    shots["game_state_score_diff"] = shots.index.map(score_diff_by_index)

    shots["is_goal"] = safe_column(shots, "shot_outcome") == "Goal"

    feature_columns = [
        "match_id",
        "player",
        "team",
        "minute",
        "x",
        "y",
        "distance_to_goal",
        "angle_to_goal",
        "shot_body_part",
        "is_header",
        "is_first_time",
        "under_pressure",
        "is_penalty",
        "is_free_kick",
        "assist_type",
        "game_state_score_diff",
        "shot_statsbomb_xg",
        "is_goal",
    ]
    return shots.reindex(columns=feature_columns)


def build_training_dataset(datasets):
    """Build a combined shot-feature dataset across multiple competitions/seasons.

    Args:
        datasets: iterable of `config.Dataset` objects (preferred), e.g.
            `config.TRAIN_SETS`. The `context` ("league"/"tournament") is carried
            through as `league_context` so the two can be separated later (see
            CLAUDE.md's train/test split rationale). Plain
            `(competition_id, season_id, context)` tuples are still accepted for
            backward compatibility.

    Returns:
        pandas.DataFrame: one row per shot across all requested matches, with
            `competition_id` and `league_context` columns attached.
    """
    all_shots = []
    for dataset in datasets:
        # Accept either a config.Dataset or a legacy (comp_id, season_id, context) tuple.
        competition_id = getattr(dataset, "comp_id", None)
        if competition_id is None:
            competition_id, season_id, league_context = dataset
        else:
            season_id, league_context = dataset.season_id, dataset.context

        matches = load_matches(competition_id, season_id)
        for match_id in matches["match_id"]:
            events = load_events(match_id)
            events["match_id"] = match_id
            shots = extract_shot_features(events)
            shots["league_context"] = league_context
            shots["competition_id"] = competition_id
            all_shots.append(shots)

    return pd.concat(all_shots, ignore_index=True)
