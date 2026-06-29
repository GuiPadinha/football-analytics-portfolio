"""Pitch plots and charts (mplsoccer) for shots, xG, and player profiles.

Built out alongside Session S3/S4 (shot maps, xG timeline, rankings) and
Session S7 (radar charts, PCA scatter plot).
"""

import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

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
    if ax is None:
        pitch = Pitch(pitch_type="statsbomb", pitch_color="grass", line_color="white")
        _, ax = pitch.draw(figsize=(10, 7))
    else:
        pitch = Pitch(pitch_type="statsbomb", pitch_color="grass", line_color="white")

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
