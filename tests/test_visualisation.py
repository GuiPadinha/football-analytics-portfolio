"""Regression tests for src/visualisation.py output determinism.

The pipeline's PNGs are committed (README embeds them), so a chart that renders different
pixels for identical input creates a diff on every rebuild and hides real changes.
"""

import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.visualisation import plot_shot_map


def _render_shot_map():
    shots = pd.DataFrame({"x": [100.0, 110.0, 95.0], "y": [40.0, 35.0, 50.0], "is_goal": [True, False, False]})
    ax = plot_shot_map(shots, np.array([0.3, 0.1, 0.05]), title="test")
    buffer = io.BytesIO()
    ax.figure.savefig(buffer, format="png", dpi=50)
    plt.close(ax.figure)
    return buffer.getvalue()


def test_shot_map_renders_identical_bytes_for_identical_input():
    # mplsoccer's grass texture draws from the global numpy RNG; unseeded, these differed.
    np.random.seed(1)
    first = _render_shot_map()
    np.random.seed(2)
    second = _render_shot_map()
    assert first == second


def test_shot_map_leaves_the_callers_random_state_untouched():
    np.random.seed(123)
    expected = np.random.random()
    np.random.seed(123)
    _render_shot_map()
    assert np.random.random() == expected
