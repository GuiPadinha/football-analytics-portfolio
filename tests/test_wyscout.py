"""Tests for the Wyscout ingestion (`src/wyscout.py`), on synthetic match sheets and events."""

import pandas as pd
import pytest

from src import wyscout
from src.wyscout import (
    WY_GK_TABLE_COLUMNS,
    WY_PER90_TABLE_COLUMNS,
    compute_match_minutes,
    extract_match_actions,
    per90_tables,
    popular_name,
    to_statsbomb_x,
    unescape_name,
)


def _event(player, event_id, subevent_id, tags=(), positions=((50, 50),), team=1):
    return {
        "playerId": player, "teamId": team, "eventId": event_id, "subEventId": subevent_id,
        "tags": [{"id": tag} for tag in tags],
        "positions": [{"x": x, "y": y} for x, y in positions],
    }


def _team(team_id, starters, bench=(), substitutions=None, red_cards=None):
    red_cards = red_cards or {}
    sheet = lambda pid: {"playerId": pid, "redCards": str(red_cards.get(pid, 0)), "goals": "null"}
    return {
        "teamId": team_id,
        "formation": {
            "lineup": [sheet(pid) for pid in starters],
            "bench": [sheet(pid) for pid in bench],
            "substitutions": substitutions if substitutions is not None else "null",
        },
    }


def test_unescape_name_decodes_literal_escapes_and_trims():
    assert unescape_name("Kant\\u00e9") == "Kanté"
    assert unescape_name("Mohamed ") == "Mohamed"
    assert unescape_name("") is None
    assert unescape_name(None) is None


@pytest.mark.parametrize("first, short, expected", [
    ("Lionel Andrés", "L. Messi", "Lionel Messi"),
    ("Marco Davide", "D. Faraoni", "Davide Faraoni"),   # known by a middle name
    ("Bamidele", "D. Alli", "D. Alli"),                  # no given name with that initial
    ("Neymar", "Neymar", "Neymar"),                      # already the popular name
    ("Riyad", None, None),
])
def test_popular_name(first, short, expected):
    assert popular_name(first, short) == expected


def test_to_statsbomb_x_maps_pitch_landmarks():
    # Goal line, penalty spot, box edge and halfway line land on StatsBomb's own landmarks.
    assert list(to_statsbomb_x([100, 90, 84, 50, 0])) == pytest.approx([120, 108, 102, 60, 0])


def test_compute_match_minutes_handles_subs_red_cards_and_null_subs():
    match = {"teamsData": {
        "1": _team(1, starters=[10, 11, 12], bench=[13],
                   substitutions=[{"playerIn": 13, "playerOut": 11, "minute": 60}],
                   red_cards={12: 70}),
        # "null" substitutions (the dataset's empty list) and a stoppage-time sub on the other side.
        "2": _team(2, starters=[20, 21], bench=[22],
                   substitutions=[{"playerIn": 22, "playerOut": 21, "minute": 93}]),
    }}
    minutes = {row["player_id"]: row["minutes_played"] for row in compute_match_minutes(match)}
    # Full time is the latest substitution (93), not 90; 12 was sent off at 70; 22 came on at the
    # final whistle, so played 0 minutes and gets no row.
    assert minutes == {10: 93, 11: 60, 12: 70, 13: 33, 20: 93, 21: 93}

    no_subs = {"teamsData": {"1": _team(1, starters=[10])}}
    assert compute_match_minutes(no_subs) == [{"player_id": 10, "team_id": 1, "minutes_played": 90}]


def test_extract_match_actions_counts_each_definition():
    events = [
        _event(7, 10, 100, tags=[101]),                    # open-play goal
        _event(7, 3, 35, tags=[101]),                      # penalty goal
        _event(7, 10, 100),                                # missed shot
        _event(8, 8, 85, tags=[302, 1801], positions=((40, 50), (60, 50))),  # key pass, +24 yd
        _event(8, 8, 85, tags=[301, 1801], positions=((50, 50), (55, 50))),  # assist, +6 yd
        _event(8, 8, 85, tags=[1802], positions=((10, 50), (90, 50))),       # inaccurate
        _event(8, 3, 30, tags=[1801], positions=((99, 1), (100, 100))),      # corner, +1 yd
        _event(9, 1, 11, tags=[703, 503]),                 # dribble won
        _event(9, 1, 11, tags=[701, 504]),                 # dribble lost
        _event(9, 1, 12, tags=[703]),                      # tackle won
        _event(9, 1, 12, tags=[701, 1601]),                # sliding tackle, lost: still a tackle
        _event(9, 1, 12, tags=[701]),                      # lost defending duel: not a tackle
        _event(9, 7, 71),                                  # clearance
        _event(9, 8, 85, tags=[1401, 1801], positions=((30, 50), (31, 50))),  # interception
        _event(1, 9, 91, tags=[1801]),                     # save
        _event(1, 9, 90, tags=[101, 1802]),                # goal conceded
        _event(1, 4, 40),                                  # sweeper action
    ]
    actions = extract_match_actions(events).set_index("player_id")
    assert actions.loc[7, ["goals", "non_penalty_goals", "shots"]].tolist() == [2, 1, 3]
    assert actions.loc[8, ["key_passes", "assists", "progressive_passes"]].tolist() == [1, 1, 1]
    assert actions.loc[9, ["dribbles_completed", "tackles", "clearances", "interceptions"]].tolist() \
        == [1, 2, 1, 1]
    assert actions.loc[1, ["saves", "goals_conceded", "sweeper_actions"]].tolist() == [1, 1, 1]


def test_per90_tables_splits_keepers_applies_floor_and_rates():
    minutes = pd.DataFrame([
        {"player_id": 7, "team_id": 1, "minutes_played": 900},
        {"player_id": 7, "team_id": 1, "minutes_played": 900},
        {"player_id": 1, "team_id": 1, "minutes_played": 1800},
        {"player_id": 5, "team_id": 1, "minutes_played": 450},   # under the floor
    ])
    actions = extract_match_actions([
        _event(7, 10, 100, tags=[101]), _event(7, 10, 100, tags=[101]),
        _event(1, 9, 91, tags=[1801]), _event(1, 9, 91, tags=[1801]),
        _event(1, 9, 91, tags=[1801]), _event(1, 9, 90, tags=[101]),
    ])
    players = {
        7: {"player": "Mohamed Salah Ghaly", "nickname": "Mohamed Salah",
            "birth_date": pd.Timestamp("1992-06-15"), "position_group": "Forward"},
        1: {"player": "Keeper One", "nickname": None,
            "birth_date": pd.Timestamp("1990-01-01"), "position_group": "Goalkeeper"},
        5: {"player": "Sub Five", "nickname": None,
            "birth_date": pd.Timestamp("1995-01-01"), "position_group": "Midfielder"},
    }
    outfield, keepers = per90_tables(minutes, actions, players, {1: "Liverpool"})

    assert list(outfield.columns) == WY_PER90_TABLE_COLUMNS
    assert list(keepers.columns) == WY_GK_TABLE_COLUMNS
    assert outfield["player_id"].tolist() == [7]
    salah = outfield.iloc[0]
    assert salah["team"] == "Liverpool" and salah["minutes_played"] == 1800
    assert salah["non_penalty_goals_p90"] == pytest.approx(0.1)
    keeper = keepers.iloc[0]
    assert keeper["save_pct"] == pytest.approx(0.75)
    assert keeper["saves_p90"] == pytest.approx(0.15)


def test_cached_file_reads_from_cache_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(wyscout, "WYSCOUT_CACHE_DIR", tmp_path)
    (tmp_path / "teams.json").write_text(
        '[{"wyId": 1613, "name": "Deportivo Alav\\\\u00e9s"}]', encoding="utf-8"
    )
    assert wyscout.load_team_names() == {1613: "Deportivo Alavés"}
