"""Player similarity: per-90 feature engineering (Session S5) and clustering (Session S6).

Event-based per-90 metrics come from StatsBomb data. SkillCorner physical metrics are built
separately (`build_physical_per90_features`) and are NOT joined to the same players — SkillCorner's
open data covers Australian A-League broadcast tracking with zero player overlap with the
StatsBomb competitions used here. The two are two standalone demonstrations of capability
(event-data clustering vs. physical-tracking literacy), not a fused per-player dataset. See
CLAUDE.md Learning Goals / S5 progress notes for the reasoning.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.data_loader import (
    load_events, load_lineups, load_matches, load_skillcorner_tracking,
    safe_bool_column, safe_column,
)

# Common broadcast-tracking thresholds for classifying running intensity (km/h).
HIGH_SPEED_RUNNING_THRESHOLD_KMH = 19.8
SPRINT_THRESHOLD_KMH = 25.2

# StatsBomb's standard position taxonomy collapsed into four broad groups for clustering.
# Goalkeepers are excluded from similarity clustering entirely — their per-90 profile
# (distribution, claims, sweeping) has almost nothing in common with outfield metrics.
POSITION_GROUPS = {
    "Goalkeeper": "Goalkeeper",
    "Right Back": "Defender",
    "Right Center Back": "Defender",
    "Center Back": "Defender",
    "Left Center Back": "Defender",
    "Left Back": "Defender",
    "Right Wing Back": "Defender",
    "Left Wing Back": "Defender",
    "Right Defensive Midfield": "Midfielder",
    "Center Defensive Midfield": "Midfielder",
    "Left Defensive Midfield": "Midfielder",
    "Right Midfield": "Midfielder",
    "Right Center Midfield": "Midfielder",
    "Center Midfield": "Midfielder",
    "Left Center Midfield": "Midfielder",
    "Left Midfield": "Midfielder",
    "Right Attacking Midfield": "Midfielder",
    "Center Attacking Midfield": "Midfielder",
    "Left Attacking Midfield": "Midfielder",
    "Right Wing": "Forward",
    "Left Wing": "Forward",
    "Right Center Forward": "Forward",
    "Center Forward": "Forward",
    "Left Center Forward": "Forward",
    "Striker": "Forward",
    "Secondary Striker": "Forward",
}


def _parse_clock(time_str):
    """Convert a StatsBomb 'MM:SS' clock string to minutes as a float.

    StatsBomb's match clock does not reset at half-time (e.g. second-half
    stoppage time reads '95:12'), so this is a plain minutes+seconds/60
    conversion, not a period-relative one.
    """
    minutes, seconds = time_str.split(":")
    return int(minutes) + int(seconds) / 60


def compute_minutes_played(lineups, match_duration):
    """Compute total minutes played and primary position per player for one match.

    Uses StatsBomb's `lineups` endpoint, which already tracks each player's
    on-pitch stints (start/end time, reason, position) directly — this is
    more reliable than reconstructing minutes from Starting XI + Substitution
    events, since `lineups` also captures in-match position changes
    ("Tactical Shift") that the raw event stream doesn't label as cleanly.

    Args:
        lineups (dict[str, pandas.DataFrame]): output of `data_loader.load_lineups`.
        match_duration (float): final whistle minute for this match (e.g. the
            max `minute` value across that match's events), used to close out
            stints with no recorded end time (player still on at full time).

    Returns:
        pandas.DataFrame: one row per player with `player`, `team`,
            `position` (their most-played position that match), and
            `minutes_played`.
    """
    records = []
    for team, lineup_df in lineups.items():
        for _, player_row in lineup_df.iterrows():
            minutes_by_position = {}
            for stint in player_row["positions"]:
                start = _parse_clock(stint["from"])
                end = _parse_clock(stint["to"]) if stint["to"] else match_duration
                duration = max(end - start, 0)
                minutes_by_position[stint["position"]] = (
                    minutes_by_position.get(stint["position"], 0) + duration
                )

            if not minutes_by_position:
                continue

            primary_position = max(minutes_by_position, key=minutes_by_position.get)
            records.append({
                "player": player_row["player_name"],
                "team": team,
                "position": primary_position,
                "minutes_played": sum(minutes_by_position.values()),
            })

    return pd.DataFrame(records)


def resolve_season_positions(minutes_df):
    """Assign each player's season position group by total minutes, not match count.

    `minutes_df` is the concatenated per-match output of `compute_minutes_played`:
    one row per (player, team, match) carrying that match's primary position and
    the player's minutes in it. The naive aggregation — take the *modal* per-match
    position — has a real failure mode for versatile players. When a player's
    attacking minutes are spread across several position labels (Right Wing /
    Left Wing / Centre Forward) while their occasional defensive cameos all share
    one label (Right Back), the single defensive label can win a per-match *count*
    vote even though attacking minutes dominate the season. That is exactly what
    put Michail Antonio — a winger — into a one-man "defender" cluster in S6.

    The fix resolves the position *group* from summed minutes: total each player's
    minutes per group across the season and take the argmax. Summing at the group
    level (not the raw position level) is deliberate — it reunites the fragmented
    RW/LW/CF minutes into one "Forward" total before comparing, so attacking time
    can't be split into losing the vote to a single consistent defensive label.
    The representative `position` is then the highest-minutes position within the
    winning group. Total `minutes_played` is the player's full season presence
    (across every position, mapped or not), unchanged from before — only the group
    assignment logic changes.

    Args:
        minutes_df (pandas.DataFrame): concatenated per-match output of
            `compute_minutes_played`, with `player`, `team`, `position`,
            `minutes_played`.

    Returns:
        pandas.DataFrame: one row per (player, team) with `minutes_played`
            (season total), `position_group`, and `position`. Players whose every
            recorded position is outside `POSITION_GROUPS` are dropped (no group
            to assign) — this never happens for standard StatsBomb position labels.
    """
    df = minutes_df.copy()
    df["position_group"] = df["position"].map(POSITION_GROUPS)

    records = []
    for (player, team), player_df in df.groupby(["player", "team"]):
        mapped = player_df.dropna(subset=["position_group"])
        if mapped.empty:
            continue

        # Winning group = most season minutes; winning position = most minutes
        # within that group. Ties resolve to whichever label sorts first (idxmax).
        primary_group = mapped.groupby("position_group")["minutes_played"].sum().idxmax()
        in_group = mapped[mapped["position_group"] == primary_group]
        primary_position = in_group.groupby("position")["minutes_played"].sum().idxmax()

        records.append({
            "player": player,
            "team": team,
            # Full presence across all positions (incl. any unmapped), so the
            # min_minutes filter still measures total pitch time, not time-in-group.
            "minutes_played": player_df["minutes_played"].sum(),
            "position_group": primary_group,
            "position": primary_position,
        })

    return pd.DataFrame(records)


def extract_player_match_actions(events):
    """Count per-player action totals for one match, for later per-90 conversion.

    Args:
        events (pandas.DataFrame): full event stream for one match.

    Returns:
        pandas.DataFrame: one row per (player, team), with raw counts of
            non-penalty goals, shots, key passes, assists, completed
            dribbles, progressive passes, pressures, interceptions,
            tackles, clearances, and blocks. These are summed across a
            season and divided by total minutes in
            `build_player_per90_features` — counting here and dividing
            later (rather than computing a per-match rate) avoids
            small-sample distortion from any single match.
    """
    shots = events[events["type"] == "Shot"].copy()
    shots["shot_outcome"] = safe_column(shots, "shot_outcome")
    shots["shot_type"] = safe_column(shots, "shot_type")
    non_penalty_goals = (
        shots[(shots["shot_outcome"] == "Goal") & (shots["shot_type"] != "Penalty")]
        .groupby(["player", "team"]).size().rename("non_penalty_goals")
    )
    shot_counts = shots.groupby(["player", "team"]).size().rename("shots")

    passes = events[events["type"] == "Pass"].copy()
    key_passes = (
        passes[safe_bool_column(passes, "pass_shot_assist")]
        .groupby(["player", "team"]).size().rename("key_passes")
    )
    assists = (
        passes[safe_bool_column(passes, "pass_goal_assist")]
        .groupby(["player", "team"]).size().rename("assists")
    )
    # "Progressive" here means a completed pass that advances the ball at least
    # 10 yards toward the opponent's goal. StatsBomb coordinates are already
    # direction-normalised (attacking goal always at x=120 regardless of period
    # or team), so a plain x-delta works without tracking attacking direction.
    completed_passes = passes[safe_column(passes, "pass_outcome").isna()].copy()
    if len(completed_passes):
        dx = completed_passes["pass_end_location"].apply(lambda loc: loc[0]) - \
            completed_passes["location"].apply(lambda loc: loc[0])
        progressive_passes = (
            completed_passes[dx >= 10].groupby(["player", "team"]).size().rename("progressive_passes")
        )
    else:
        # Not just `pd.Series(dtype=int)` — that has a plain default RangeIndex, not the
        # 2-level (player, team) MultiIndex every other action Series here carries even when
        # empty. Mixing the two shapes in the `pd.concat` below silently corrupted the whole
        # result's index (reset_index() stopped producing player/team columns at all) whenever
        # this was the only all-empty column — unreachable with real match data (StatsBomb
        # matches always have passes) but a real landmine, found by testing zero-Pass synthetic
        # events for the new clearances/blocks columns, not by hitting it in production.
        progressive_passes = completed_passes.groupby(["player", "team"]).size().rename("progressive_passes")

    dribbles = events[events["type"] == "Dribble"].copy()
    dribbles_completed = (
        dribbles[safe_column(dribbles, "dribble_outcome") == "Complete"]
        .groupby(["player", "team"]).size().rename("dribbles_completed")
    )

    pressures = (
        events[events["type"] == "Pressure"]
        .groupby(["player", "team"]).size().rename("pressures")
    )
    interceptions = (
        events[events["type"] == "Interception"]
        .groupby(["player", "team"]).size().rename("interceptions")
    )
    duels = events[events["type"] == "Duel"].copy()
    tackles = (
        duels[safe_column(duels, "duel_type") == "Tackle"]
        .groupby(["player", "team"]).size().rename("tackles")
    )
    # StatsBomb has no separate "goal-line clearance" sub-type (checked against the real
    # `Clearance` event schema before writing this — its only sub-fields are body part /
    # aerial-won flags, no last-ditch-ness label) — a plain clearance count is the closest
    # available proxy for that kind of defending, so that's what this is, not a sofascore-
    # style "last-ditch" stat masquerading as something more specific.
    clearances = (
        events[events["type"] == "Clearance"]
        .groupby(["player", "team"]).size().rename("clearances")
    )
    blocks = (
        events[events["type"] == "Block"]
        .groupby(["player", "team"]).size().rename("blocks")
    )

    actions = pd.concat(
        [non_penalty_goals, shot_counts, key_passes, assists, progressive_passes,
         dribbles_completed, pressures, interceptions, tackles, clearances, blocks],
        axis=1,
    ).fillna(0)
    return actions.reset_index()


ACTION_COLUMNS = [
    "non_penalty_goals", "shots", "key_passes", "assists", "progressive_passes",
    "dribbles_completed", "pressures", "interceptions", "tackles", "clearances", "blocks",
]


def extract_goalkeeper_match_actions(events):
    """Count per-goalkeeper action totals for one match, for later per-90 conversion.

    Mirrors `extract_player_match_actions`'s counting-not-rating approach, but reads the
    `Goal Keeper` event type's `goalkeeper_type` sub-classification instead of the outfield
    event types `ACTION_COLUMNS` counts — a keeper's meaningful actions (saves, claims,
    sweeping) live entirely inside one StatsBomb event type the outfield columns never touch,
    which is exactly why GKs were excluded from clustering rather than just scored near-zero
    on tackles/passes (see `POSITION_GROUPS`'s note).

    Args:
        events (pandas.DataFrame): full event stream for one match.

    Returns:
        pandas.DataFrame: one row per (player, team), with raw counts of shots faced,
            saves, goals conceded, claims, punches, and sweeper actions.
    """
    gk_events = events[events["type"] == "Goal Keeper"].copy()
    gk_events["goalkeeper_type"] = safe_column(gk_events, "goalkeeper_type")

    shots_faced = (
        gk_events[gk_events["goalkeeper_type"] == "Shot Faced"]
        .groupby(["player", "team"]).size().rename("shots_faced")
    )
    # StatsBomb logs a few rare synonym labels for the same "the keeper stopped it" outcome
    # family alongside the common "Shot Saved" — grouped together as one `saves` count.
    saved_types = ["Shot Saved", "Shot Saved Off Target", "Shot Saved to Post", "Save", "Penalty Saved"]
    saves = (
        gk_events[gk_events["goalkeeper_type"].isin(saved_types)]
        .groupby(["player", "team"]).size().rename("saves")
    )
    goals_conceded = (
        gk_events[gk_events["goalkeeper_type"] == "Goal Conceded"]
        .groupby(["player", "team"]).size().rename("goals_conceded")
    )
    claims = (
        gk_events[gk_events["goalkeeper_type"] == "Collected"]
        .groupby(["player", "team"]).size().rename("claims")
    )
    punches = (
        gk_events[gk_events["goalkeeper_type"] == "Punch"]
        .groupby(["player", "team"]).size().rename("punches")
    )
    sweeper_actions = (
        gk_events[gk_events["goalkeeper_type"] == "Keeper Sweeper"]
        .groupby(["player", "team"]).size().rename("sweeper_actions")
    )

    actions = pd.concat(
        [shots_faced, saves, goals_conceded, claims, punches, sweeper_actions], axis=1,
    ).fillna(0)
    return actions.reset_index()


GK_ACTION_COLUMNS = ["shots_faced", "saves", "goals_conceded", "claims", "punches", "sweeper_actions"]


def _build_season_minutes_and_actions(competition_id, season_id, extract_match_actions):
    """Shared season-build loop: minutes played + one action-extractor's per-match counts.

    Factored out of `build_player_per90_features`/`build_goalkeeper_per90_features` — both
    need the same per-match minutes/lineup iteration, differing only in *which* actions get
    counted from each match's events (outfield vs. goalkeeper).

    Args:
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.
        extract_match_actions (callable): `extract_player_match_actions` or
            `extract_goalkeeper_match_actions` — one match's events in, one row per
            (player, team) of that match's raw action counts out.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: (season_minutes, actions_df) — the
            minutes-weighted position table (`resolve_season_positions`) and the
            concatenated raw per-match action counts, not yet summed or per-90'd.
    """
    matches = load_matches(competition_id, season_id)

    all_minutes = []
    all_actions = []
    for match_id in matches["match_id"]:
        events = load_events(match_id)
        match_duration = events["minute"].max()
        lineups = load_lineups(match_id)

        match_minutes = compute_minutes_played(lineups, match_duration)
        match_minutes["match_id"] = match_id
        all_minutes.append(match_minutes)

        match_actions = extract_match_actions(events)
        match_actions["match_id"] = match_id
        all_actions.append(match_actions)

    minutes_df = pd.concat(all_minutes, ignore_index=True)
    actions_df = pd.concat(all_actions, ignore_index=True)

    # Minutes-weighted position assignment (see resolve_season_positions): assign
    # each player to the group they logged the most season minutes in, not their
    # modal per-match position — the latter mislabels versatile players whose
    # attacking minutes are split across several labels (the S6 Antonio case).
    return resolve_season_positions(minutes_df), actions_df


def build_player_per90_features(competition_id, season_id, min_minutes=900):
    """Build a per-90, per-player feature table for one competition/season.

    Args:
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.
        min_minutes (float): drop players below this many total minutes —
            per-90 rates from a handful of substitute appearances are noisy
            and would distort clustering (e.g. one lucky shot in 10 minutes
            looks like a strong goal-scoring rate).

    Returns:
        pandas.DataFrame: one row per player, with `position_group`,
            `minutes_played`, one raw season-total `<action>` column and one
            `<action>_p90` rate column per entry in `ACTION_COLUMNS` — the
            raw totals are kept alongside the rates (not just an intermediate
            dropped after dividing) since a whole-number season total (e.g.
            "24 goals") is what a human reads as the headline number, while
            the per-90 rate is what clustering/percentiles actually compare
            on. Goalkeepers are excluded — see `build_goalkeeper_per90_features`
            for their own feature set.
    """
    season_minutes, actions_df = _build_season_minutes_and_actions(
        competition_id, season_id, extract_player_match_actions
    )
    season_actions = (
        actions_df.groupby(["player", "team"])[ACTION_COLUMNS].sum().reset_index()
    )

    features = season_minutes.merge(season_actions, on=["player", "team"], how="left")
    features[ACTION_COLUMNS] = features[ACTION_COLUMNS].fillna(0)

    features = features[features["minutes_played"] >= min_minutes]
    features = features[features["position_group"] != "Goalkeeper"]

    for col in ACTION_COLUMNS:
        features[f"{col}_p90"] = features[col] / features["minutes_played"] * 90

    keep_columns = ["player", "team", "position_group", "minutes_played"] + \
        ACTION_COLUMNS + [f"{col}_p90" for col in ACTION_COLUMNS]
    return features[keep_columns].reset_index(drop=True)


def build_goalkeeper_per90_features(competition_id, season_id, min_minutes=900):
    """Build a per-90, per-goalkeeper feature table for one competition/season.

    A separate function rather than a branch inside `build_player_per90_features` on
    purpose: a keeper's tackles/progressive-passes rate is meaningless (they're all near
    zero), so reusing `ACTION_COLUMNS` would just rediscover "this player is a goalkeeper"
    rather than distinguish *between* keepers. `GK_ACTION_COLUMNS` (shots faced, saves,
    goals conceded, claims, punches, sweeper actions) is the goalkeeper-appropriate analogue
    of the same counting-not-rating approach — same pattern as `build_physical_per90_features`
    being its own function for a different feature domain (physical tracking), not a branch
    inside this one.

    Args:
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.
        min_minutes (float): as `build_player_per90_features` — drop keepers below this
            many total minutes.

    Returns:
        pandas.DataFrame: one row per goalkeeper, with `minutes_played`, `save_pct`
            (saves / shots faced, computed from raw season totals rather than the per-90
            rates so it reads as a plain ratio; 0 for a keeper who faced no shots, not NaN),
            and one `<action>_p90` column per entry in `GK_ACTION_COLUMNS`.
    """
    season_minutes, actions_df = _build_season_minutes_and_actions(
        competition_id, season_id, extract_goalkeeper_match_actions
    )
    season_actions = (
        actions_df.groupby(["player", "team"])[GK_ACTION_COLUMNS].sum().reset_index()
    )

    features = season_minutes.merge(season_actions, on=["player", "team"], how="left")
    features[GK_ACTION_COLUMNS] = features[GK_ACTION_COLUMNS].fillna(0)

    features = features[features["minutes_played"] >= min_minutes]
    features = features[features["position_group"] == "Goalkeeper"].copy()

    features["save_pct"] = np.where(
        features["shots_faced"] > 0, features["saves"] / features["shots_faced"], 0.0
    )
    for col in GK_ACTION_COLUMNS:
        features[f"{col}_p90"] = features[col] / features["minutes_played"] * 90

    keep_columns = ["player", "team", "position_group", "minutes_played", "save_pct"] + \
        [f"{col}_p90" for col in GK_ACTION_COLUMNS]
    return features[keep_columns].reset_index(drop=True)


def build_physical_per90_features(match_id, min_observed_minutes=30.0):
    """Derive per-90 physical output (distance, high-speed running, sprints) from
    SkillCorner broadcast tracking for one match.

    SkillCorner's open data does not populate speed/distance columns directly
    (`to_df()`'s `_s`/`_d` columns are entirely null) — they have to be derived
    from frame-to-frame position deltas. Positions are normalised (0-1), so
    they're rescaled to metres using the match's actual pitch dimensions before
    computing distance, and speed thresholds (19.8 km/h high-speed running,
    25.2 km/h sprinting) are standard sports-science broadcast-tracking cutoffs.

    Deltas are only computed between truly consecutive frames with valid
    positions for that player (frame_id gap of exactly 1) — broadcast tracking
    has visibility gaps (player off-camera), and naively diffing across a gap
    would register a teleport as an enormous, fictitious sprint.

    "Minutes" here means minutes *observed* by the broadcast camera, not
    necessarily minutes actually on the pitch — broadcast tracking only
    captures players when the camera frames them, so this systematically
    undercounts true playing time. That's a real limitation of broadcast
    (vs. full-pitch multi-camera) tracking data, not a bug.

    This also means the "_p90" extrapolation here is less trustworthy than
    the StatsBomb event-based per-90 metrics: scaling a short, possibly
    unrepresentative observed window up to a full 90 minutes assumes uniform
    intensity across the match, which doesn't hold if a player's tracked
    window happens to catch (or miss) a sprint-heavy phase of play. A
    default `min_observed_minutes=30` keeps the extrapolation factor to at
    most 3x; lowering it trades reliability for keeping more players in the
    output (e.g. at 10 observed minutes, one player's figures above were a
    9x extrapolation from a single short window — not a number to build a
    scouting decision on).

    Args:
        match_id (int): SkillCorner open data match id.
        min_observed_minutes (float): drop players tracked for less than this
            many minutes — too little data to extrapolate a per-90 rate from.

    Returns:
        pandas.DataFrame: one row per player, with `team`, `observed_minutes`,
            and per-90 total distance, high-speed running distance, sprint
            distance, and sprint count.
    """
    tracking = load_skillcorner_tracking(match_id=match_id)
    df = tracking.to_df()

    pitch_length = tracking.metadata.pitch_dimensions.pitch_length
    pitch_width = tracking.metadata.pitch_dimensions.pitch_width
    dt = 1 / tracking.metadata.frame_rate

    player_name_by_id = {}
    team_by_player_id = {}
    for team in tracking.metadata.teams:
        for player in team.players:
            player_name_by_id[player.player_id] = player.name
            team_by_player_id[player.player_id] = team.name

    frame_gap = df["frame_id"].diff()
    player_ids = sorted({
        col[:-2] for col in df.columns
        if col.endswith("_x") and not col.startswith("ball")
    })

    records = []
    for player_id in player_ids:
        x = df[f"{player_id}_x"] * pitch_length
        y = df[f"{player_id}_y"] * pitch_width
        valid = x.notna() & y.notna()

        observed_minutes = valid.sum() * dt / 60
        if observed_minutes < min_observed_minutes:
            continue

        valid_step = valid & valid.shift(1).fillna(False) & (frame_gap == 1)
        step_distance = np.sqrt(x.diff() ** 2 + y.diff() ** 2).where(valid_step, 0)
        speed_kmh = (step_distance / dt * 3.6).where(valid_step, np.nan)

        is_sprinting = (speed_kmh >= SPRINT_THRESHOLD_KMH).fillna(False)
        sprint_bouts = int((is_sprinting & ~is_sprinting.shift(1).fillna(False)).sum())

        scale = 90 / observed_minutes
        records.append({
            "player": player_name_by_id.get(player_id, player_id),
            "team": team_by_player_id.get(player_id),
            "observed_minutes": observed_minutes,
            "total_distance_m_p90": step_distance.sum() * scale,
            "high_speed_running_m_p90": step_distance[
                (speed_kmh >= HIGH_SPEED_RUNNING_THRESHOLD_KMH) & (speed_kmh < SPRINT_THRESHOLD_KMH)
            ].sum() * scale,
            "sprint_distance_m_p90": step_distance[speed_kmh >= SPRINT_THRESHOLD_KMH].sum() * scale,
            "sprint_count_p90": sprint_bouts * scale,
        })

    return pd.DataFrame(records)


PER90_FEATURE_COLUMNS = [f"{col}_p90" for col in ACTION_COLUMNS]
GK_PER90_FEATURE_COLUMNS = [f"{col}_p90" for col in GK_ACTION_COLUMNS]


def scale_features(features, feature_columns=PER90_FEATURE_COLUMNS):
    """Standardise features to mean 0, std 1 before clustering.

    K-means measures similarity as Euclidean distance, so any feature with a
    naturally larger numeric range will dominate that distance regardless of
    its actual football relevance — `progressive_passes_p90` (tens) would
    swamp `non_penalty_goals_p90` (usually well under 1) purely because of
    units, not because progressive passing matters more. None of the S2-S4
    xG models needed this: logistic regression and gradient boosting are
    scale-invariant (or close enough) because they fit a coefficient/split
    per feature rather than comparing features directly to each other.

    Args:
        features (pandas.DataFrame): per-player feature table.
        feature_columns (list[str]): columns to scale and cluster on.

    Returns:
        tuple[pandas.DataFrame, sklearn.preprocessing.StandardScaler]: the
            scaled feature matrix (same index as `features`) and the fitted
            scaler (kept in case new players need to be projected later).
    """
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features[feature_columns])
    return pd.DataFrame(scaled, columns=feature_columns, index=features.index), scaler


def compute_elbow_scores(X_scaled, k_range=range(2, 11)):
    """Fit K-means across a range of K and return inertia for each.

    Inertia (within-cluster sum of squared distances) always decreases as K
    grows — the elbow method looks for where it stops decreasing sharply,
    trading off "clusters are tight" against "we haven't just made one
    cluster per player." There's no single correct K here, unlike a
    classification metric such as ROC-AUC; this is read by eye.

    Args:
        X_scaled (pandas.DataFrame): output of `scale_features`.
        k_range (range): candidate values of K to try.

    Returns:
        pandas.Series: inertia indexed by K.
    """
    inertias = {}
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias[k] = kmeans.inertia_
    return pd.Series(inertias)


def compute_silhouette_scores(X_scaled, k_range=range(2, 11), random_state=42):
    """Fit K-means across a range of K and return the silhouette score for each.

    Complementary to `compute_elbow_scores`. Inertia *always* falls as K rises,
    so the elbow method has no internal optimum — you eyeball where the curve
    bends, which is subjective. The silhouette score instead measures how well
    each point sits in its cluster: for a point, `a` is its mean distance to the
    other points in its own cluster (cohesion) and `b` is its mean distance to
    the points of the nearest *other* cluster (separation); its silhouette is
    `(b - a) / max(a, b)`, averaged over all points. It ranges -1 to 1 (higher =
    tighter, better-separated clusters; near 0 = points sit on cluster borders;
    negative = points likely in the wrong cluster) and, crucially, does NOT
    increase monotonically with K — so unlike inertia it can be *maximised* to
    suggest a K, a quantitative second opinion on the by-eye elbow read.

    It's still only a heuristic: it rewards convex, roughly equal-sized, well-
    separated blobs, and real play-style data is none of those cleanly — so it
    informs the K choice alongside the elbow curve and football sense, it doesn't
    settle it on its own.

    Args:
        X_scaled (pandas.DataFrame): output of `scale_features`.
        k_range (range): candidate values of K. Must be >= 2 — the silhouette
            score is undefined for a single cluster (no "other cluster" for `b`).
        random_state (int): seed for K-means' centroid initialisation.

    Returns:
        pandas.Series: silhouette score indexed by K.
    """
    scores = {}
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        scores[k] = silhouette_score(X_scaled, labels)
    return pd.Series(scores)


def fit_kmeans(X_scaled, n_clusters, random_state=42):
    """Fit K-means and return the model plus a cluster label per row.

    Args:
        X_scaled (pandas.DataFrame): output of `scale_features`.
        n_clusters (int): K, typically chosen from the elbow curve.
        random_state (int): seed for reproducibility (K-means' starting
            centroids are random, so results can shift run to run otherwise).

    Returns:
        tuple[sklearn.cluster.KMeans, numpy.ndarray]: fitted model and the
            cluster label assigned to each row of `X_scaled`.
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    return kmeans, labels


def profile_clusters(features, feature_columns, cluster_labels):
    """Describe each cluster by how far its average feature values sit from the
    overall population average, in standard deviations (z-scores).

    There's no ground-truth label to check a cluster against — "is this
    cluster good" isn't a question with a clean metric the way ROC-AUC
    answers it for the xG model. This is the practical substitute: a
    cluster whose `non_penalty_goals_p90` z-score is +1.8 and whose
    `tackles_p90` z-score is -0.9 can be read directly as "a goalscoring,
    defensively-light cluster" — i.e. how a human decides whether the
    grouping makes football sense.

    Args:
        features (pandas.DataFrame): per-player feature table.
        feature_columns (list[str]): columns the clustering was run on.
        cluster_labels (numpy.ndarray): output of `fit_kmeans`.

    Returns:
        pandas.DataFrame: one row per cluster, one column per feature,
            values are z-scores of the cluster mean vs. the population mean.
    """
    labelled = features[feature_columns].copy()
    labelled["cluster"] = cluster_labels
    cluster_means = labelled.groupby("cluster")[feature_columns].mean()
    population_mean = features[feature_columns].mean()
    population_std = features[feature_columns].std()
    return (cluster_means - population_mean) / population_std


def find_similar_players(features, feature_columns, player, team, n=5):
    """Find the `n` most similar players to a given player, by Euclidean distance
    in standardised feature space, restricted to the player's own position group.

    Restricting to the same position group (rather than all outfield players) is
    the same reasoning as the clustering itself (S6): comparing a forward's
    distance to a center-back's would mostly just measure "is this a forward",
    not which forward plays a similar role. K-means cluster membership isn't used
    here directly — raw distance gives a continuous ranking ("most to least
    similar") rather than the coarser in-cluster/out-of-cluster split clustering
    gives, which is the more useful shape for a "players like X" lookup.

    Args:
        features (pandas.DataFrame): per-player feature table, must contain
            `player`, `team`, `position_group`, and `feature_columns`.
        feature_columns (list[str]): columns to compute similarity on.
        player (str): name of the player to find matches for.
        team (str): that player's team, needed since player names aren't
            guaranteed unique across teams.
        n (int): number of similar players to return.

    Returns:
        pandas.DataFrame: the `n` nearest players (excluding the player
            themselves), sorted by ascending distance, with a `distance` column.
    """
    target = features[(features["player"] == player) & (features["team"] == team)]
    if target.empty:
        raise ValueError(f"No player found matching player={player!r}, team={team!r}")
    position_group = target["position_group"].iloc[0]

    subset = features[features["position_group"] == position_group].reset_index(drop=True)
    X_scaled, _ = scale_features(subset, feature_columns)
    target_idx = subset.index[(subset["player"] == player) & (subset["team"] == team)][0]

    distances = np.linalg.norm(X_scaled.values - X_scaled.loc[target_idx].values, axis=1)
    result = subset.copy()
    result["distance"] = distances
    result = result[result.index != target_idx].sort_values("distance")

    keep_columns = ["player", "team", "position_group", "distance"] + feature_columns
    if "competition" in features.columns:
        # Optional provenance column (present on the app's multi-competition pool, absent on
        # single-dataset callers like the notebooks/pipeline) — passed through when it exists
        # rather than assumed, so a "similar player" result can show it came from a different
        # league without requiring every caller of this function to carry the column.
        keep_columns = ["player", "team", "position_group", "competition", "distance"] + feature_columns
    return result[keep_columns].head(n).reset_index(drop=True)


def run_pca(X_scaled, n_components=2, random_state=42):
    """Reduce scaled features to a small number of components for plotting.

    Args:
        X_scaled (pandas.DataFrame): output of `scale_features`.
        n_components (int): number of components to keep (2 for a scatter plot).
        random_state (int): seed for reproducibility.

    Returns:
        tuple[numpy.ndarray, sklearn.decomposition.PCA]: the projected
            components and the fitted PCA object (`.explained_variance_ratio_`
            shows how much signal survives the reduction to 2D — this is the
            tradeoff PCA makes: easier to plot, but each axis is a blend of
            the original features and loses their individual interpretability).
    """
    pca = PCA(n_components=n_components, random_state=random_state)
    components = pca.fit_transform(X_scaled)
    return components, pca
