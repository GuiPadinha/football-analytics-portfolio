"""Unit tests for Transfermarkt entity resolution and market-value lookup (src/market_value.py).

Every test uses small synthetic frames, matching this project's precedent for anything that
would otherwise need the network (e.g. `test_manifest.py`/`test_pipeline.py`'s monkeypatched
loaders) - `_download_csv`/`build_market_value_table`'s network call is never exercised here.
Several cases below reproduce real bugs found and fixed against the actual Transfermarkt data
(see ML_LEARNING_LOG.md): the "Santos"/"Junior" common-surname collision against Neymar, the
"de"-particle false match, wrong identities for Dani Alves and Koke, and the two Luis Suárez - so
a regression in the matching logic fails a test, not just a silent quality drop.
"""

import pandas as pd

from src.market_value import (
    find_name_candidates,
    keep_candidates_at_the_right_club,
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


def test_normalize_name_transliterates_letters_without_a_plain_base():
    # Accent-stripping alone would drop these letters ("ukasz"); Transfermarkt spells them out.
    assert normalize_name("Łukasz Fabiański") == "lukasz fabianski"
    assert normalize_name("Damjan Đoković") == "damjan djokovic"
    assert normalize_name("Gylfi Sigurðsson") == "gylfi sigurdsson"


def _sb_players(rows):
    return pd.DataFrame(rows, columns=["player", "team", "nickname"])


def _tm_players(rows):
    return pd.DataFrame(rows, columns=["player_id", "name"])


def test_candidates_include_an_exact_full_name_match():
    per90 = _sb_players([("Harry Kane", "Spurs", None)])
    tm = _tm_players([(1, "Harry Kane")])

    result = find_name_candidates(per90, tm)
    assert list(result["tm_player_id"]) == [1]
    assert list(result["tm_name"]) == ["Harry Kane"]


def test_candidates_use_the_statsbomb_nickname():
    # The real Koke case: nothing in "Jorge Resurrección Merodio" is in "Koke", and the full name
    # alone only finds an unrelated "Jorge". StatsBomb's nickname finds the real player; the
    # namesake stays a candidate for the club check to reject.
    per90 = _sb_players([("Jorge Resurrección Merodio", "Atlético Madrid", "Koke")])
    tm = _tm_players([(1, "Koke"), (2, "Jorge"), (3, "Merodio Someone")])

    result = find_name_candidates(per90, tm)
    assert list(result["tm_player_id"]) == [1, 2]


def test_candidates_match_the_nickname_by_its_words_too():
    # Real cases: Transfermarkt's "Charly Musonda Jr." and "Mikel John Obi" (same words, another
    # order) are no exact match for StatsBomb's nicknames, and the full names share nothing.
    per90 = _sb_players([
        ("Charly Musonda Junior", "Real Betis", "Charly Musonda"),
        ("John Michael Nchekwube Obinna", "Chelsea", "John Obi Mikel"),
    ])
    tm = _tm_players([(1, "Charly Musonda Jr."), (2, "Mikel John Obi")])

    result = find_name_candidates(per90, tm).set_index("player")["tm_player_id"]
    assert result["Charly Musonda Junior"] == 1
    assert result["John Michael Nchekwube Obinna"] == 2


def test_candidates_match_full_legal_name_against_transfermarkt_popular_name():
    # The real Cristiano Ronaldo case: StatsBomb logs the full legal name, Transfermarkt the
    # popular one. The decoys prove the subset check and the rarity score do the work.
    per90 = _sb_players([("Cristiano Ronaldo dos Santos Aveiro", "Real Madrid", None)])
    tm = _tm_players([
        (1, "Cristiano Ronaldo"),
        (2, "Ronaldo Mendes"),  # decoy: extra token "mendes"
        (3, "Cristiano"),  # decoy: a subset too, but less specific
    ])

    result = find_name_candidates(per90, tm)
    assert list(result["tm_player_id"]) == [1]


def test_candidates_prefer_rare_token_over_common_surname_collision():
    # The real bug rarity scoring fixed: a real, unrelated "Júnior Santos" is a valid 2-token
    # subset match of Neymar's full name purely because "Santos"/"Junior" are very common
    # surname tokens. A "most tokens wins" rule picks him; rarity must prefer "Neymar".
    per90 = _sb_players([("Neymar da Silva Santos Junior", "Barcelona", None)])
    # A padded corpus so "santos"/"junior" are common tokens and "neymar" is rare - mirrors the
    # real corpus's frequency shape, not just a 2-row toy case.
    padding = [(100 + i, f"Santos Player{i}") for i in range(5)] + [
        (200 + i, f"Junior Player{i}") for i in range(5)
    ]
    tm = _tm_players([(1, "Neymar"), (2, "Júnior Santos"), (3, "Santos")] + padding)

    result = find_name_candidates(per90, tm)
    assert list(result["tm_player_id"]) == [1]


def test_candidates_reject_particle_only_names():
    # The real bug: "Sebastian De Maio" matched Transfermarkt's "Dé" (normalises to "de" alone)
    # purely because it was the only subset candidate. A name made only of a particle carries no
    # evidence about who the player is.
    per90 = _sb_players([("Sebastian De Maio", "Genoa", None)])
    tm = _tm_players([(1, "Dé")])

    assert find_name_candidates(per90, tm).empty


def test_candidates_keep_every_namesake():
    # Transfermarkt has two players named "Luis Suárez": names alone can't choose, so both stay.
    per90 = _sb_players([("Luis Alberto Suárez Díaz", "Barcelona", "Luis Suárez")])
    tm = _tm_players([(1, "Luis Suárez"), (2, "Luis Suárez")])

    result = find_name_candidates(per90, tm)
    assert sorted(result["tm_player_id"]) == [1, 2]


def test_candidates_empty_frame_has_expected_columns():
    per90 = _sb_players([("Nobody Special", "FC Nowhere", None)])
    tm = _tm_players([(1, "Someone Else")])

    result = find_name_candidates(per90, tm)
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


def _club_valuations(rows):
    frame = pd.DataFrame(rows, columns=["player_id", "date", "current_club_name"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def _candidates(rows):
    return pd.DataFrame(rows, columns=["player", "team", "tm_player_id", "tm_name"])


# Three real Barcelona players, valued at Barcelona: they teach the check the team's club.
BARCELONA_CORE = [
    ("Messi", "Barcelona", 1, "Lionel Messi"),
    ("Neymar", "Barcelona", 2, "Neymar"),
    ("Busquets", "Barcelona", 3, "Sergio Busquets"),
]
BARCELONA_CORE_VALUATIONS = [
    (1, "2015-10-01", "FC Barcelona"), (2, "2016-02-01", "FC Barcelona"), (3, "2015-08-01", "FC Barcelona"),
]


def test_club_check_drops_a_name_match_valued_at_another_club():
    # The Dani Alves case: the only name candidate was a namesake at Union Saint-Gilloise.
    candidates = _candidates(BARCELONA_CORE + [("Daniel Alves da Silva", "Barcelona", 99, "Alves Da Silva")])
    valuations = _club_valuations(BARCELONA_CORE_VALUATIONS + [(99, "2016-01-15", "Royale Union Saint-Gilloise")])

    kept = keep_candidates_at_the_right_club(candidates, valuations, pd.Timestamp("2016-01-01"))
    assert list(kept["player"]) == ["Messi", "Neymar", "Busquets"]


def test_club_check_picks_the_namesake_at_the_right_club():
    # The Luis Suárez case: two Transfermarkt players share the name; only one was at Barcelona.
    candidates = _candidates(BARCELONA_CORE + [
        ("Luis Alberto Suárez Díaz", "Barcelona", 10, "Luis Suárez"),
        ("Luis Alberto Suárez Díaz", "Barcelona", 11, "Luis Suárez"),
    ])
    valuations = _club_valuations(BARCELONA_CORE_VALUATIONS + [
        (10, "2015-11-22", "FC Barcelona"), (11, "2016-01-10", "Atlético Nacional"),
    ])

    kept = keep_candidates_at_the_right_club(candidates, valuations, pd.Timestamp("2016-01-01"))
    suarez = kept[kept["player"] == "Luis Alberto Suárez Díaz"]
    assert list(suarez["tm_player_id"]) == [10]
    assert len(kept) == 4


def test_club_check_leaves_namesakes_at_the_same_club_unmatched():
    # Nothing tells two candidates at the same club apart, so neither is guessed.
    candidates = _candidates(BARCELONA_CORE + [
        ("Twin", "Barcelona", 20, "Twin"), ("Twin", "Barcelona", 21, "Twin"),
    ])
    valuations = _club_valuations(BARCELONA_CORE_VALUATIONS + [
        (20, "2016-01-01", "FC Barcelona"), (21, "2016-01-01", "FC Barcelona"),
    ])

    kept = keep_candidates_at_the_right_club(candidates, valuations, pd.Timestamp("2016-01-01"))
    assert "Twin" not in set(kept["player"])


def test_club_check_keeps_a_mid_season_signing_and_drops_out_of_window_valuations():
    candidates = _candidates([
        ("A", "Sampdoria", 1, "A"), ("B", "Sampdoria", 2, "B"),
        ("January signing", "Sampdoria", 3, "C"), ("Long retired namesake", "Sampdoria", 4, "D"),
    ])
    valuations = _club_valuations([
        (1, "2015-09-01", "UC Sampdoria"), (2, "2016-03-01", "UC Sampdoria"),
        # Valued at his old club before the move and at Sampdoria after it: both in the window.
        (3, "2015-09-01", "Torino FC"), (3, "2016-07-01", "UC Sampdoria"),
        # Right club name, but years away from the season: not evidence about 2015/16.
        (4, "2010-01-01", "UC Sampdoria"),
    ])

    kept = keep_candidates_at_the_right_club(candidates, valuations, pd.Timestamp("2016-01-01"))
    assert list(kept["player"]) == ["A", "B", "January signing"]


def test_club_check_handles_no_candidates():
    kept = keep_candidates_at_the_right_club(
        _candidates([]), _club_valuations([]), pd.Timestamp("2016-01-01")
    )
    assert kept.empty
