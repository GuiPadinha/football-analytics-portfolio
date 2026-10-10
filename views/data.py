"""Loading and caching for the app's pages: the one place that reads `app_data/`.

Every page asks for the same prepared `profile.Pool` and findings, so a visit pays the Parquet
reads and the percentile ranking once per server process. Nothing here downloads or trains.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.profile import display_name, prepare_pool

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DATA_DIR = REPO_ROOT / "app_data"
POPULAR_PICKS = 4


@st.cache_resource
def load_pool():
    """The prepared player pool (`profile.Pool`). `cache_resource` hands every session the same
    object, so pages must treat it as read-only."""
    market_value_path = APP_DATA_DIR / "market_value.parquet"
    market_value = (
        pd.read_parquet(market_value_path) if market_value_path.exists()
        else pd.DataFrame(columns=["player", "team", "tm_name", "market_value_eur", "market_value_as_of"])
    )
    return prepare_pool(
        pd.read_parquet(APP_DATA_DIR / "player_per90.parquet"),
        pd.read_parquet(APP_DATA_DIR / "shots_with_xg.parquet"),
        market_value,
    )


@st.cache_data
def load_xg_table():
    """The Premier League 2015/16 finishing table."""
    return pd.read_parquet(APP_DATA_DIR / "player_xg_table.parquet")


@st.cache_data
def load_metrics():
    """`metrics.json`: the headline model numbers, the single source for any figure quoted."""
    return json.loads((REPO_ROOT / "metrics.json").read_text(encoding="utf-8"))


@st.cache_data
def load_findings():
    """The Home page's cards (`src/findings.py`)."""
    return json.loads((APP_DATA_DIR / "findings.json").read_text(encoding="utf-8"))


@st.cache_data
def player_options():
    """`(labels, key_by_label)` for every search box: "Name (Club) · League", sorted. A label is
    the popular name, so a fan finds "Philippe Coutinho" without knowing his legal name."""
    per90 = load_pool().per90
    key_by_label = {
        f"{display_name(row)} ({row['team']}) · {row['competition']}": (row["player"], row["team"])
        for _, row in per90.iterrows()
    }
    return sorted(key_by_label), key_by_label


def label_of(key):
    """The search-box label of a `(player, team)` key, or `None` if it isn't in the pool."""
    labels, key_by_label = player_options()
    return next((label for label in labels if key_by_label[label] == tuple(key)), None)


@st.cache_data
def popular_picks():
    """The most valuable outfield men: one-click starting points for a visitor who doesn't know
    who to look up. Ranked by Transfermarkt value, so the list changes only if the data does."""
    pool = load_pool()
    values = pool.market_values["market_value_eur"].sort_values(ascending=False)
    picks = []
    for player, team in values.index:
        row = pool.per90[(pool.per90["player"] == player) & (pool.per90["team"] == team)]
        if len(row) and row.iloc[0]["position_group"] != "Goalkeeper":
            picks.append((player, team))
        if len(picks) == POPULAR_PICKS:
            break
    return picks


def open_player(key):
    """Make `key` the selected player for the Players page (the page seeds its search box from it)."""
    st.session_state["selected_player"] = tuple(key)
