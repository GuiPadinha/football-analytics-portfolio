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
from sklearn.preprocessing import StandardScaler

from src.data_loader import load_events, load_lineups, load_matches, load_skillcorner_tracking

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


def _safe_bool_column(df, column):
    """Return `df[column]` as booleans, or all-False if the column is absent.

    statsbombpy only includes a column in a match's events DataFrame if at
    least one event in that match actually has it set (e.g. `pass_goal_assist`
    is missing entirely from matches with zero assists) — sparse flag columns
    can't be accessed directly without risking a KeyError on an otherwise
    ordinary match.
    """
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].eq(True)


def _safe_column(df, column, default=None):
    """Return `df[column]`, or an all-`default` Series if the column is absent.

    Same sparse-column issue as `_safe_bool_column`, for non-boolean fields
    (e.g. `pass_outcome` is absent entirely from a match with zero incomplete
    passes, `duel_type` from a match with zero duels of that type recorded).
    """
    if column not in df.columns:
        return pd.Series(default, index=df.index)
    return df[column]


def extract_player_match_actions(events):
    """Count per-player action totals for one match, for later per-90 conversion.

    Args:
        events (pandas.DataFrame): full event stream for one match.

    Returns:
        pandas.DataFrame: one row per (player, team), with raw counts of
            non-penalty goals, shots, key passes, assists, completed
            dribbles, progressive passes, pressures, interceptions, and
            tackles. These are summed across a season and divided by total
            minutes in `build_player_per90_features` — counting here and
            dividing later (rather than computing a per-match rate) avoids
            small-sample distortion from any single match.
    """
    shots = events[events["type"] == "Shot"].copy()
    shots["shot_outcome"] = _safe_column(shots, "shot_outcome")
    shots["shot_type"] = _safe_column(shots, "shot_type")
    non_penalty_goals = (
        shots[(shots["shot_outcome"] == "Goal") & (shots["shot_type"] != "Penalty")]
        .groupby(["player", "team"]).size().rename("non_penalty_goals")
    )
    shot_counts = shots.groupby(["player", "team"]).size().rename("shots")

    passes = events[events["type"] == "Pass"].copy()
    key_passes = (
        passes[_safe_bool_column(passes, "pass_shot_assist")]
        .groupby(["player", "team"]).size().rename("key_passes")
    )
    assists = (
        passes[_safe_bool_column(passes, "pass_goal_assist")]
        .groupby(["player", "team"]).size().rename("assists")
    )
    # "Progressive" here means a completed pass that advances the ball at least
    # 10 yards toward the opponent's goal. StatsBomb coordinates are already
    # direction-normalised (attacking goal always at x=120 regardless of period
    # or team), so a plain x-delta works without tracking attacking direction.
    completed_passes = passes[_safe_column(passes, "pass_outcome").isna()].copy()
    if len(completed_passes):
        dx = completed_passes["pass_end_location"].apply(lambda loc: loc[0]) - \
            completed_passes["location"].apply(lambda loc: loc[0])
        progressive_passes = (
            completed_passes[dx >= 10].groupby(["player", "team"]).size().rename("progressive_passes")
        )
    else:
        progressive_passes = pd.Series(name="progressive_passes", dtype=int)

    dribbles = events[events["type"] == "Dribble"].copy()
    dribbles_completed = (
        dribbles[_safe_column(dribbles, "dribble_outcome") == "Complete"]
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
        duels[_safe_column(duels, "duel_type") == "Tackle"]
        .groupby(["player", "team"]).size().rename("tackles")
    )

    actions = pd.concat(
        [non_penalty_goals, shot_counts, key_passes, assists, progressive_passes,
         dribbles_completed, pressures, interceptions, tackles],
        axis=1,
    ).fillna(0)
    return actions.reset_index()


ACTION_COLUMNS = [
    "non_penalty_goals", "shots", "key_passes", "assists", "progressive_passes",
    "dribbles_completed", "pressures", "interceptions", "tackles",
]


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
            `minutes_played`, and one `<action>_p90` column per entry in
            `ACTION_COLUMNS`. Goalkeepers are excluded.
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

        match_actions = extract_player_match_actions(events)
        match_actions["match_id"] = match_id
        all_actions.append(match_actions)

    minutes_df = pd.concat(all_minutes, ignore_index=True)
    actions_df = pd.concat(all_actions, ignore_index=True)

    season_minutes = (
        minutes_df.groupby(["player", "team"])
        .agg(minutes_played=("minutes_played", "sum"),
             position=("position", lambda s: s.mode().iat[0]))
        .reset_index()
    )
    season_actions = (
        actions_df.groupby(["player", "team"])[ACTION_COLUMNS].sum().reset_index()
    )

    features = season_minutes.merge(season_actions, on=["player", "team"], how="left")
    features[ACTION_COLUMNS] = features[ACTION_COLUMNS].fillna(0)
    features["position_group"] = features["position"].map(POSITION_GROUPS)

    features = features[features["minutes_played"] >= min_minutes]
    features = features[features["position_group"] != "Goalkeeper"]

    for col in ACTION_COLUMNS:
        features[f"{col}_p90"] = features[col] / features["minutes_played"] * 90

    keep_columns = ["player", "team", "position_group", "minutes_played"] + \
        [f"{col}_p90" for col in ACTION_COLUMNS]
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
