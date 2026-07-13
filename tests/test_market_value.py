"""Unit tests for Transfermarkt entity resolution and market-value lookup (src/market_value.py).

Every test uses small synthetic frames, matching this project's precedent for anything that
would otherwise need the network (e.g. `test_manifest.py`/`test_pipeline.py`'s monkeypatched
loaders) - `_download_csv`/`build_market_value_table`'s network call is never exercised here.
Several cases below reproduce real bugs found and fixed against the actual Transfermarkt data
while building this feature (see ML_LEARNING_LOG.md) - Neymar's position-tag disagreement, the
"Santos"/"Junior" common-surname collision, and the "de"-particle false match - so a regression
in the matching logic fails a test, not just a silent quality drop.
"""

import pandas as pd
import pytest

from src.market_value import (
    match_players_to_transfermarkt,
    normalize_name,
    resolve_market_values,
)


def test_normalize_name_strips_accents_and_case():
    assert normalize_name("Kramarić") == "kramaric"
    assert normalize_name("Zlatan Ibrahimović") == "zlatan ibrahimovic"


def test_normalize_name_collapses_statsbomb_doubled_apostrophe():
    # StatsBomb's genuine data quirk (see ML_TOOLING.md) - "N''Golo Kanté" - the doubled
    # apostrophe must not survive into two separate stray tokens.
    assert normalize_name("N''Golo Kanté") == "n golo kante"


def test_normalize_name_handles_missing():
    assert normalize_name(None) == ""
    assert normalize_name(float("nan")) == ""


def _tm_players(rows):
    return pd.DataFrame(rows, columns=["player_id", "name", "position"])


def test_match_exact_name_and_position():
    per90 = pd.DataFrame([
        {"player": "Harry Kane", "team": "Spurs", "position_group": "Forward"},
    ])
    tm = _tm_players([{"player_id": 1, "name": "Harry Kane", "position": "Attack"}])

    result = match_players_to_transfermarkt(per90, tm)
    assert len(result) == 1
    assert result.iloc[0]["tm_player_id"] == 1
    assert result.iloc[0]["tm_name"] == "Harry Kane"


def test_match_full_legal_name_against_transfermarkt_popular_name():
    # The real Cristiano Ronaldo case: StatsBomb logs the full legal name, Transfermarkt the
    # popular one. Includes decoy same-position, non-matching-token entries to prove the subset
    # check (not just "any Attack player") is doing the disambiguating work.
    per90 = pd.DataFrame([
        {"player": "Cristiano Ronaldo dos Santos Aveiro", "team": "Real Madrid", "position_group": "Forward"},
    ])
    tm = _tm_players([
        {"player_id": 1, "name": "Cristiano Ronaldo", "position": "Attack"},
        {"player_id": 2, "name": "Ronaldo Mendes", "position": "Attack"},  # decoy: extra token "mendes"
        {"player_id": 3, "name": "Cristiano", "position": "Attack"},  # decoy: shorter subset, not most specific
    ])

    result = match_players_to_transfermarkt(per90, tm)
    assert len(result) == 1
    assert result.iloc[0]["tm_player_id"] == 1


def test_match_prefers_rare_token_over_common_surname_collision():
    # The real bug this was built to fix: Transfermarkt tags Neymar "Midfield" (StatsBomb-derived
    # position here is "Forward"), and a real, unrelated "Júnior Santos" (also Attack/Forward)
    # is a valid 2-token subset match purely because "Santos"/"Junior" are extremely common
    # surname tokens. A naive "most tokens wins" rule picks the wrong player; rarity-weighting
    # must prefer the rare, single-token "Neymar" mononym instead.
    per90 = pd.DataFrame([
        {"player": "Neymar da Silva Santos Junior", "team": "Barcelona", "position_group": "Forward"},
    ])
    # A padded corpus so "santos"/"junior"/"da"/"silva" are common tokens and "neymar" is rare -
    # mirrors the real corpus's frequency shape, not just a 2-row toy case.
    padding = [
        {"player_id": 100 + i, "name": f"Santos Player{i}", "position": "Defender"} for i in range(5)
    ] + [
        {"player_id": 200 + i, "name": f"Junior Player{i}", "position": "Defender"} for i in range(5)
    ]
    tm = _tm_players([
        {"player_id": 1, "name": "Neymar", "position": "Midfield"},  # real player, wrong broad position
        {"player_id": 2, "name": "Júnior Santos", "position": "Attack"},  # real, unrelated collision
        {"player_id": 3, "name": "Santos", "position": "Attack"},
    ] + padding)

    result = match_players_to_transfermarkt(per90, tm)
    assert len(result) == 1
    assert result.iloc[0]["tm_player_id"] == 1  # the real Neymar, not the Santos/Junior collision


def test_match_rejects_particle_only_candidate():
    # The real bug: "Sebastian De Maio" matched Transfermarkt's "Dé" (normalises to "de" alone)
    # purely because it was the *only* subset candidate, with nothing to lose to. A match built
    # entirely from a name-construction particle carries no real evidence and must be rejected
    # outright, not accepted by default.
    per90 = pd.DataFrame([
        {"player": "Sebastian De Maio", "team": "Genoa", "position_group": "Defender"},
    ])
    tm = _tm_players([{"player_id": 1, "name": "Dé", "position": "Defender"}])

    result = match_players_to_transfermarkt(per90, tm)
    assert result.empty


def test_match_leaves_genuine_ambiguity_unresolved():
    # Two different real players who happen to share the exact same name and broad position -
    # no signal in this design distinguishes them, so neither should be guessed.
    per90 = pd.DataFrame([
        {"player": "Luis Suárez", "team": "Barcelona", "position_group": "Forward"},
    ])
    tm = _tm_players([
        {"player_id": 1, "name": "Luis Suárez", "position": "Attack"},
        {"player_id": 2, "name": "Luis Suárez", "position": "Attack"},
    ])

    result = match_players_to_transfermarkt(per90, tm)
    assert result.empty


def test_match_returns_empty_frame_with_expected_columns_when_nothing_matches():
    per90 = pd.DataFrame([{"player": "Nobody Special", "team": "FC Nowhere", "position_group": "Forward"}])
    tm = _tm_players([{"player_id": 1, "name": "Someone Else", "position": "Attack"}])

    result = match_players_to_transfermarkt(per90, tm)
    assert list(result.columns) == ["player", "team", "tm_player_id", "tm_name"]
    assert result.empty


def _valuations(rows):
    return pd.DataFrame(rows, columns=["player_id", "date", "market_value_in_eur"])


def test_resolve_market_values_picks_nearest_date():
    matched = pd.DataFrame([{"player": "Harry Kane", "team": "Spurs", "tm_player_id": 1, "tm_name": "Harry Kane"}])
    valuations = _valuations([
        {"player_id": 1, "date": "2015-06-01", "market_value_in_eur": 20_000_000},
        {"player_id": 1, "date": "2016-02-01", "market_value_in_eur": 30_000_000},  # nearest to Jan 1 2016
        {"player_id": 1, "date": "2017-01-01", "market_value_in_eur": 45_000_000},
    ])

    result = resolve_market_values(matched, valuations, pd.Timestamp("2016-01-01"))
    assert len(result) == 1
    assert result.iloc[0]["market_value_eur"] == 30_000_000
    assert result.iloc[0]["market_value_as_of"] == "2016-02-01"


def test_resolve_market_values_drops_players_with_no_valuation_history():
    matched = pd.DataFrame([
        {"player": "Has History", "team": "T", "tm_player_id": 1, "tm_name": "Has History"},
        {"player": "No History", "team": "T", "tm_player_id": 2, "tm_name": "No History"},
    ])
    valuations = _valuations([{"player_id": 1, "date": "2016-01-01", "market_value_in_eur": 1_000_000}])

    result = resolve_market_values(matched, valuations, pd.Timestamp("2016-01-01"))
    assert list(result["player"]) == ["Has History"]
