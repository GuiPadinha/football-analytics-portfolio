"""Pitch plots and charts (mplsoccer) for shots, xG, and player profiles.

Built out alongside Session S3/S4 (shot maps, xG timeline, rankings) and
Session S7 (radar charts, PCA scatter plot).
"""

import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch, Radar

OUTCOME_COLORS = {"Goal": "gold", "No Goal": "dimgrey"}


def plot_shot_map(shots, predicted_xg, title=None, ax=None):
    """Plot shots on a pitch, sized by predicted xG and coloured by outcome.

    Args:
        shots (pandas.DataFrame): output of `features.extract_shot_features`,
            must contain `x`, `y`, `is_goal` columns.
        predicted_xg (numpy.ndarray): model's predicted probability per shot,
            same row order as `shots`.
        title (str, optional): plot title.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on; a new
            pitch is created if omitted.

    Returns:
        matplotlib.axes.Axes: the axes the shots were drawn on.
    """
    pitch = Pitch(pitch_type="statsbomb", pitch_color="grass", line_color="white")
    if ax is None:
        _, ax = pitch.draw(figsize=(10, 7))
    else:
        # Draw the pitch markings onto the caller's axes too — otherwise a passed-in
        # ax that wasn't already a pitch would get bare scatter points on blank axes.
        pitch.draw(ax=ax)

    outcomes = shots["is_goal"].map({True: "Goal", False: "No Goal"})
    sizes = 100 + predicted_xg * 1500

    for outcome, color in OUTCOME_COLORS.items():
        mask = outcomes == outcome
        pitch.scatter(
            shots.loc[mask, "x"], shots.loc[mask, "y"],
            s=sizes[mask.values], color=color, edgecolors="black",
            linewidth=0.8, alpha=0.8, ax=ax, zorder=2,
        )

    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=10, label=label)
        for label, c in OUTCOME_COLORS.items()
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=10)
    if title:
        ax.set_title(title, fontsize=12)
    return ax


def plot_player_xg_ranking(ranking, n=10, ax=None, title=None):
    """Bar chart of the biggest xG over/underperformers.

    Args:
        ranking (pandas.DataFrame): output of `models.build_player_xg_table`,
            indexed by (player, team), must contain `xg_diff`.
        n (int): number of players to show from each end of the ranking
            (top `n` overperformers and bottom `n` underperformers).
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.
        title (str, optional): plot title.

    Returns:
        matplotlib.axes.Axes: the axes the bars were drawn on.
    """
    selected = pd.concat([ranking.head(n), ranking.tail(n)]).sort_values("xg_diff")
    labels = [f"{player} ({team})" for player, team in selected.index]
    colors = ["crimson" if v < 0 else "seagreen" for v in selected["xg_diff"]]

    if ax is None:
        _, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(selected))))

    ax.barh(labels, selected["xg_diff"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Goals minus expected goals (xG)")
    if title:
        ax.set_title(title, fontsize=12)
    return ax


def plot_elbow_curve(inertias, chosen_k=None, ax=None, title=None):
    """Plot K-means inertia against K, to read off the elbow by eye.

    Args:
        inertias (pandas.Series): output of `similarity.compute_elbow_scores`,
            indexed by K.
        chosen_k (int, optional): draws a vertical marker at this K, to show
            which value was actually picked.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.
        title (str, optional): plot title.

    Returns:
        matplotlib.axes.Axes: the axes the curve was drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))

    ax.plot(inertias.index, inertias.values, marker="o")
    if chosen_k is not None:
        ax.axvline(chosen_k, color="crimson", linestyle="--", label=f"chosen K={chosen_k}")
        ax.legend()
    ax.set_xlabel("K (number of clusters)")
    ax.set_ylabel("Inertia")
    if title:
        ax.set_title(title, fontsize=12)
    return ax


def plot_silhouette_curve(scores, ax=None, title=None):
    """Plot silhouette score against K, marking the K that maximises it.

    Unlike the elbow curve (inertia, monotonically decreasing — read by eye),
    the silhouette score has an actual peak, so the maximising K is drawn
    explicitly as the metric's own recommendation. Read it alongside the elbow
    curve, not instead of it: a sharp peak is a strong signal, a flat curve
    means the metric has no strong opinion and the choice falls back to the
    elbow and football sense.

    Args:
        scores (pandas.Series): output of `similarity.compute_silhouette_scores`,
            indexed by K.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.
        title (str, optional): plot title.

    Returns:
        matplotlib.axes.Axes: the axes the curve was drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))

    ax.plot(scores.index, scores.values, marker="o")
    best_k = scores.idxmax()
    ax.axvline(best_k, color="seagreen", linestyle="--", label=f"max at K={best_k}")
    ax.legend()
    ax.set_xlabel("K (number of clusters)")
    ax.set_ylabel("Silhouette score")
    if title:
        ax.set_title(title, fontsize=12)
    return ax


def plot_pca_clusters(components, cluster_labels, ax=None, title=None):
    """Scatter plot of players in 2D PCA space, coloured by cluster.

    Args:
        components (numpy.ndarray): output of `similarity.run_pca` (n_samples, 2).
        cluster_labels (numpy.ndarray): output of `similarity.fit_kmeans`.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.
        title (str, optional): plot title.

    Returns:
        matplotlib.axes.Axes: the axes the scatter was drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))

    scatter = ax.scatter(components[:, 0], components[:, 1], c=cluster_labels, cmap="tab10", alpha=0.8)
    legend = ax.legend(*scatter.legend_elements(), title="Cluster", loc="best")
    ax.add_artist(legend)
    ax.set_xlabel("PCA component 1")
    ax.set_ylabel("PCA component 2")
    if title:
        ax.set_title(title, fontsize=12)
    return ax


def plot_player_radar(
    player_row, population, feature_columns, ax=None, title=None,
    circle_facecolor="#f0f0f0", circle_edgecolor="#cccccc", radar_facecolor="#1a78cf",
):
    """Draw a radar chart of one player's per-90 metrics against their position group's range.

    Uses mplsoccer's `Radar` rather than a hand-rolled polar plot — no reason to
    rebuild what the library already provides.

    Each axis is scaled to the *5th-95th percentile* of `population`, not the
    true min/max. True min/max would let a single extreme outlier (e.g. the
    one-player defender cluster dominated by Michail Antonio's attacking
    output, see notebook 03 S6) compress every other player's radar into an
    unreadable sliver near the centre — percentile bounds trade a little bit of
    range accuracy for a chart that stays legible across the whole group.

    Args:
        player_row (pandas.Series): one row of a per-player feature table,
            must contain `feature_columns`.
        population (pandas.DataFrame): the comparison group (typically the
            player's own position group) used to set each axis's range.
        feature_columns (list[str]): columns to plot, one per radar axis.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on (a plain
            rectangular axes — mplsoccer's `Radar` configures it internally,
            it should not be created with a polar projection); a new figure
            is created if omitted.
        title (str, optional): plot title.
        circle_facecolor (str): background fill for the radar's ring circles —
            default is light-grey (paper/notebook friendly); the app overrides
            this to a dark panel colour to match its theme.
        circle_edgecolor (str): ring/gridline colour, same light-vs-dark
            override reasoning as `circle_facecolor`.
        radar_facecolor (str): the player's own filled shape colour.

    Returns:
        matplotlib.axes.Axes: the axes the radar was drawn on.
    """
    labels = [col.replace("_p90", "").replace("_", " ").title() for col in feature_columns]
    min_range = population[feature_columns].quantile(0.05).tolist()
    max_range = population[feature_columns].quantile(0.95).tolist()

    radar = Radar(labels, min_range, max_range, num_rings=4)

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    # mplsoccer's setup_axis() hardcodes facecolor='#FFFFFF' when not passed explicitly here —
    # it calls ax.set_facecolor() itself, which silently overwrote a dark theme's rcParams
    # after Axes creation (the actual cause of the app's radar chart still rendering white).
    radar.setup_axis(ax=ax, facecolor=circle_facecolor)
    radar.draw_circles(ax=ax, facecolor=circle_facecolor, edgecolor=circle_edgecolor)
    radar.draw_radar(
        player_row[feature_columns].tolist(), ax=ax,
        kwargs_radar={"facecolor": radar_facecolor, "alpha": 0.6},
        kwargs_rings={"facecolor": circle_edgecolor, "alpha": 0.3},
    )
    radar.draw_param_labels(ax=ax, fontsize=10)
    if title:
        ax.set_title(title, fontsize=13, pad=30)
    return ax


def plot_similar_players_bar(similar, accent_color="steelblue", grid_color="#dddddd", ax=None):
    """Horizontal bar chart of "players like X" results, closest match at top.

    A plain ranked table of distances is a magnitude comparison on one entity at a
    time (one player's neighbours), not several parallel series needing distinct
    identity colours — so this uses one hue with an opacity ramp (closest = most
    opaque) rather than a categorical palette, and puts the actual distance value
    at each bar's tip rather than making the reader cross-reference an axis.

    Args:
        similar (pandas.DataFrame): output of `similarity.find_similar_players`,
            must contain `player`, `team`, `distance`, already sorted ascending
            by distance (closest/most similar first).
        accent_color (str): the single bar hue; the app overrides this to match
            its theme, same reasoning as `plot_player_radar`'s colour params.
        grid_color (str): vertical gridline colour, one step off the surface.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.

    Returns:
        matplotlib.axes.Axes: the axes the bars were drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 0.7 * len(similar) + 1))

    # Reversed so the closest match (first row, ascending distance) ends up at
    # the top of a horizontal bar chart, which barh otherwise draws bottom-up.
    ordered = similar.iloc[::-1].reset_index(drop=True)
    labels = [f"{row.player} ({row.team})" for row in ordered.itertuples()]

    n = len(ordered)
    # Closest (last after the reversal, i.e. highest y) gets full opacity; farthest
    # gets the lightest — intensity carries "how similar," not a second hue.
    alphas = [0.45 + 0.55 * (i / max(n - 1, 1)) for i in range(n)]

    bars = ax.barh(labels, ordered["distance"], color=accent_color)
    for bar, alpha in zip(bars, alphas):
        bar.set_alpha(alpha)

    span = ordered["distance"].max() or 1.0
    for bar, distance in zip(bars, ordered["distance"]):
        ax.text(
            bar.get_width() + span * 0.02, bar.get_y() + bar.get_height() / 2,
            f"{distance:.2f}", va="center", fontsize=9,
        )

    ax.set_xlabel("Distance (standardised per-90 features, closer = more similar)")
    ax.grid(axis="x", color=grid_color, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.margins(x=0.18)
    return ax


def plot_calibration_curve(mean_predicted, observed_freq, ax=None, label=None):
    """Plot a model's calibration curve against the perfect-calibration diagonal.

    Args:
        mean_predicted (numpy.ndarray): mean predicted xG per probability bin.
        observed_freq (numpy.ndarray): observed goal frequency per bin.
        ax (matplotlib.axes.Axes, optional): existing axes to draw on.
        label (str, optional): legend label for this curve.

    Returns:
        matplotlib.axes.Axes: the axes the curve was drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Perfect calibration")
    ax.plot(mean_predicted, observed_freq, marker="o", label=label or "Model")
    ax.set_xlabel("Mean predicted xG")
    ax.set_ylabel("Observed goal frequency")
    ax.legend()
    return ax
