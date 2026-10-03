"""Market-value integration (Phase 9, 2026-07-13): pairs a "players like X" match with an
external Transfermarkt valuation, sharpening Module B's scouting story ("similar profile,
cheaper") — see FRAMEWORK.md's original ask and DATA.md's "Market value (Transfermarkt)" note.

Data source: `dcaribou/transfermarkt-datasets` (github.com/dcaribou/transfermarkt-datasets), a
maintained, openly-licensed CSV mirror of Transfermarkt — no official API exists, and this is
meaningfully lower-effort than scraping Transfermarkt directly. Two tables are used: `players`
(current profile + market value) and `player_valuations` (dated history, so a player's value can
be read as of roughly the right season instead of showing today's number next to a 2015/16 stat
line). Downloaded once and cached under `data/transfermarkt/` (gitignored, same pattern as
`data_loader.py`'s per-match StatsBomb cache) — re-running `python -m src.app_data` reuses the
cache rather than re-pulling.

**Two honest limitations, stated plainly rather than hidden:**

1. **No shared player ID with StatsBomb** (DATA.md's flagged blocker), so players are matched in
   two steps. `find_name_candidates` lists every Transfermarkt player whose name fits: StatsBomb's
   nickname (the popular name Transfermarkt also uses, e.g. "Koke"), the full name, or the full
   name's most distinctive words. `keep_candidates_at_the_right_club` then keeps the one
   candidate Transfermarkt places at the player's club that season. No candidate left, or more
   than one, means no market value is shown, never a guess. False negatives (a real match
   missed, e.g. a loanee valued at his parent club) are the expected failure mode, not false
   positives.
2. **This mirror only covers men's football** (verified directly against the real data before
   relying on it — every `current_club_domestic_competition_id` in the `players` table is a
   men's league code; zero rows matched any known women's club name). So market value is only
   ever resolved for the four men's competitions in `config.SIMILARITY_SETS`
   (`MARKET_VALUE_AS_OF_DATES` below); Frauen Bundesliga / FA WSL players are skipped outright,
   not silently attempted-and-failed every time.

Usage (build-time only, mirrors `app_data.py`'s "no live pulls from the app" architecture):
    from src.market_value import build_market_value_table
    market_value = build_market_value_table(per90_features)
"""

import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import urllib.request

from src.net import use_os_trust_store, with_retries, write_atomically

TRANSFERMARKT_BASE_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "transfermarkt"

# Transfermarkt's `players.position`/`player_valuations` cover only men's leagues (verified
# against the real data, see module docstring) — so a representative "as of" date is only given
# for the four men's competitions in `config.SIMILARITY_SETS`. A competition absent from this
# dict is skipped by `build_market_value_table` rather than matched-and-always-failing.
# Dates are a mid-season anchor (a "2015/16" season's Transfermarkt valuation history is denser
# around January than any other single date) — not the exact date of any specific StatsBomb
# match, which is the "value at the time of that season, not the exact matchday" simplification
# DATA.md flagged as a real decision, not a detail.
MARKET_VALUE_AS_OF_DATES = {
    "Premier League 2015/16": pd.Timestamp("2016-01-01"),
    "La Liga 2015/16 (full season)": pd.Timestamp("2016-01-01"),
    "Serie A 2015/16": pd.Timestamp("2016-01-01"),
    "Ligue 1 2015/16": pd.Timestamp("2016-01-01"),
}

# How far from the season's anchor date a valuation may be and still confirm which club a
# candidate was at (see `keep_candidates_at_the_right_club`). Twelve months either side spans the
# season plus each transfer window around it, so a January signing still shows his new club.
CLUB_CHECK_WINDOW = pd.DateOffset(months=12)

# Name-construction particles common across the naming traditions in this player pool
# (Portuguese/Spanish "de"/"da"/"dos"/"das"/"del"/"el", Dutch "van"/"der"/"den", French "du"/"le"/
# "la", German "von") — real, found by a real bug: "Sebastian De Maio" (StatsBomb) matched
# Transfermarkt's "Dé" purely because "de" is (surprisingly) not a *common enough* token to be
# scored low by `_token_rarity_scores` alone, and it was the only candidate at all, so it won by
# default with no other candidate to lose to. A token-subset match built *entirely* from these
# particles carries no real evidence about which specific player it is — `find_name_candidates`
# requires at least one non-particle token before accepting a candidate.
NAME_PARTICLE_STOPWORDS = {
    "de", "da", "do", "dos", "das", "del", "der", "den", "van", "von", "el", "la", "le", "du",
}

# Letters Unicode can't split into a plain letter plus an accent, so stripping accents would drop
# them ("Łukasz" -> "ukasz"). Spelled the way Transfermarkt writes them ("Lukasz Fabianski",
# "Gylfi Sigurdsson", "Damjan Djokovic"; checked 2026-10-03).
TRANSLITERATIONS = str.maketrans({
    "ł": "l", "Ł": "L", "đ": "dj", "Đ": "Dj", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th",
    "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ß": "ss", "ı": "i",
})


def normalize_name(name):
    """Fold a player name to a comparable canonical form: strip accents, lowercase, collapse
    punctuation/whitespace to single spaces.

    Shared normalisation for both StatsBomb and Transfermarkt names, so "Kramarić" and "Kramaric"
    (or StatsBomb's genuine doubled-apostrophe quirk, "N''Golo Kanté" — see ML_TOOLING.md)
    compare equal rather than failing a match on an encoding difference that has nothing to do
    with whether it's the same player. Letters with no plain-letter base ("Ł", "Đ", "ð") are
    transliterated first (`TRANSLITERATIONS`), so "Łukasz Fabiański" reads "lukasz fabianski".

    Args:
        name (str): a player name, from either source.

    Returns:
        str: lowercase, ASCII-only, single-spaced. Empty string for `NaN`/`None`.
    """
    if pd.isna(name):
        return ""
    decomposed = unicodedata.normalize("NFKD", str(name).replace("''", "'").translate(TRANSLITERATIONS))
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", ascii_only)
    return " ".join(cleaned.lower().split())


def _download_csv(filename, cache_dir=CACHE_DIR):
    """Download-or-reuse one Transfermarkt CSV table, cached to disk (StatsBomb per-match cache's
    "skip if already on disk" pattern, see `data_loader.py`).

    A plain `urllib` GET with a browser `User-Agent` — the R2 bucket serving these files returns
    `403 Forbidden` for Python's default urllib UA and for HEAD/Range requests, but accepts a
    normal `GET` with any browser-like UA string (checked directly, not assumed).

    Args:
        filename (str): e.g. `"players.csv.gz"` — must exist in the dataset's `data/` folder.
        cache_dir (Path): local cache directory, created if missing.

    Returns:
        pandas.DataFrame: the parsed table.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / filename

    if not cache_path.exists():
        use_os_trust_store()
        request = urllib.request.Request(
            TRANSFERMARKT_BASE_URL + filename, headers={"User-Agent": "Mozilla/5.0"}
        )

        def fetch():
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()

        write_atomically(cache_path, with_retries(fetch, describe=f"Transfermarkt {filename}"))

    return pd.read_csv(cache_path, compression="gzip")


def _token_rarity_scores(norm_names):
    """Inverse document frequency for every token across a corpus of normalised names.

    A plain "most tokens wins" specificity rule fails on real Lusophone/Hispanic full legal
    names: "Santos", "Junior", "Silva", "Da" are common enough (95, 93, 126, 42 occurrences in
    this ~50k-player corpus) that a 2-token collision built entirely from them (e.g. a real, unrelated "Júnior Santos") can outrank the
    correct single-token mononym match ("Neymar" — only 2 occurrences, i.e. genuinely
    distinctive) under naive token-count ranking. Weighting by rarity instead — 1/frequency, so
    a token nearly every name doesn't share contributes far more evidence than a token half the
    corpus has — fixes this without a fuzzy-matching dependency.

    Args:
        norm_names (pandas.Series): normalised names (output of `normalize_name`) to build the
            frequency table from.

    Returns:
        dict[str, float]: token -> 1/document_frequency.
    """
    doc_freq = Counter()
    for name in norm_names:
        doc_freq.update(set(name.split()))
    return {token: 1.0 / count for token, count in doc_freq.items()}


def _rarity_score(tokens, token_rarity):
    return sum(token_rarity.get(t, 0.0) for t in tokens)


def find_name_candidates(per90_players, tm_players):
    """List every Transfermarkt player whose name fits each (player, team).

    Step one of matching: this gathers the name evidence, and `keep_candidates_at_the_right_club`
    picks among it. A StatsBomb player has up to two names: his full name and, from StatsBomb's
    lineups, his popular name ("Koke" for "Jorge Resurrección Merodio"), which is the name
    Transfermarkt lists him under (added 2026-10-03; most of the famous blanks were found by it).
    Each name is looked up two ways, and every candidate found is kept:

    1. **Exactly**, after `normalize_name`.
    2. **By its best token-subset match.** One name's tokens are a subset of the other's
       (Transfermarkt's "Cristiano Ronaldo" within "Cristiano Ronaldo dos Santos Aveiro", or
       "Charly Musonda" within "Charly Musonda Jr."). Only the top `_rarity_score` counts, so
       common tokens can't outvote a distinctive one (a "Júnior Santos" against "Neymar"), and a
       candidate made only of name particles ("de") never counts.

    Several candidates for one player are normal (Transfermarkt has two players named "Luis
    Suárez" and eight named "Danilo"): the club check tells them apart.

    Args:
        per90_players (pandas.DataFrame): must contain `player`, `team` and `nickname` (missing
            where StatsBomb records none).
        tm_players (pandas.DataFrame): output of `_download_csv("players.csv.gz")` — must contain
            `player_id` and `name`.

    Returns:
        pandas.DataFrame: one row per (player, team, candidate), with `tm_player_id` and `tm_name`
            (the Transfermarkt display name, kept so the UI can show what a player was matched to).
    """
    tm = tm_players[["player_id", "name"]].copy()
    tm["norm_name"] = tm["name"].map(normalize_name)
    tm = tm[tm["norm_name"] != ""].reset_index(drop=True)
    tm["tokens"] = tm["norm_name"].map(lambda n: frozenset(n.split()))
    token_rarity = _token_rarity_scores(tm["norm_name"])
    rows_by_name = tm.groupby("norm_name").indices

    # Inverted index (token -> rows), so the subset search only looks at Transfermarkt names
    # sharing a token with the player instead of all ~50k. A subset match always shares one.
    rows_by_token = {}
    for idx, tokens in tm["tokens"].items():
        for token in tokens:
            rows_by_token.setdefault(token, []).append(idx)

    def best_subset_rows(norm_name):
        tokens = frozenset(norm_name.split())
        nearby = tm.loc[sorted(set().union(*(rows_by_token.get(t, []) for t in tokens)))]
        fits = nearby["tokens"].map(
            lambda t: (t <= tokens or tokens <= t) and bool(t - NAME_PARTICLE_STOPWORDS)
        ).astype(bool)
        nearby = nearby[fits]
        if nearby.empty:
            return []
        scores = nearby["tokens"].map(lambda t: _rarity_score(t, token_rarity))
        return list(nearby.index[scores == scores.max()])

    sb_players = per90_players[["player", "team", "nickname"]].drop_duplicates(["player", "team"])
    candidates = []
    for row in sb_players.itertuples(index=False):
        rows = []
        for name in (row.nickname, row.player):
            norm_name = normalize_name(name)
            if norm_name:
                rows += list(rows_by_name.get(norm_name, [])) + best_subset_rows(norm_name)
        for idx in dict.fromkeys(rows):  # one row per candidate, first evidence first
            candidates.append({
                "player": row.player, "team": row.team,
                "tm_player_id": int(tm.at[idx, "player_id"]), "tm_name": tm.at[idx, "name"],
            })

    return pd.DataFrame(candidates, columns=["player", "team", "tm_player_id", "tm_name"])


def keep_candidates_at_the_right_club(candidates, tm_valuations, as_of_date, window=CLUB_CHECK_WINDOW):
    """Keep, for each player, the one name candidate Transfermarkt places at his team's club.

    Names alone can't tell namesakes apart (two "Luis Suárez"), and they attached confident wrong
    identities before this check existed (found 2026-10-02: StatsBomb's "Daniel Alves da Silva"
    matched an "Alves Da Silva" at Royale Union Saint-Gilloise). Transfermarkt's valuation history
    says where each candidate played, so a candidate is kept only if it was valued at the StatsBomb
    team's club within `window` of `as_of_date`, and a player is matched only if exactly one
    candidate is left. Two namesakes at the same club stay unmatched, and so does a loanee valued
    at his parent club: a missed value is safe, a wrong one under a real player's name is not.

    The two sources name clubs differently ("Barcelona" vs "FC Barcelona"), so each team's
    Transfermarkt club is learned from the data: the club most of its single-candidate players
    were valued at in the window (most of those are right, so the majority is the real club). Club
    names are compared, not ids: in `player_valuations`, `current_club_id` is the player's club
    *today*, and only `current_club_name` is the club at the valuation date (checked on De Bruyne's
    history).

    Args:
        candidates (pandas.DataFrame): output of `find_name_candidates`.
        tm_valuations (pandas.DataFrame): `player_valuations` with `player_id`, `date` (datetime),
            `current_club_name`.
        as_of_date (pandas.Timestamp): the season's anchor date.
        window (pandas.DateOffset): how far either side of `as_of_date` a valuation may be.

    Returns:
        pandas.DataFrame: one row per matched (player, team), same columns as `candidates`.
    """
    in_window = tm_valuations[
        (tm_valuations["date"] >= as_of_date - window) & (tm_valuations["date"] <= as_of_date + window)
    ]
    clubs_by_player = in_window.groupby("player_id")["current_club_name"].agg(set).to_dict()
    candidate_clubs = [clubs_by_player.get(pid, set()) for pid in candidates["tm_player_id"]]
    per_player = candidates.groupby(["player", "team"])["tm_player_id"].transform("size")

    votes = Counter(
        (team, club)
        for team, clubs, count in zip(candidates["team"], candidate_clubs, per_player) if count == 1
        for club in clubs
    )
    team_club = {}
    for (team, club), _ in votes.most_common():  # highest count first, so the first seen wins
        team_club.setdefault(team, club)

    at_right_club = pd.Series(
        [team_club.get(team) in clubs for team, clubs in zip(candidates["team"], candidate_clubs)],
        index=candidates.index, dtype=bool,
    )
    at_club = candidates[at_right_club]
    left = at_club.groupby(["player", "team"])["tm_player_id"].transform("size")
    return at_club[left == 1].reset_index(drop=True)


def resolve_market_values(matched_players, tm_valuations, as_of_date):
    """Attach each matched player's Transfermarkt market value nearest to `as_of_date`.

    Uses the dated `player_valuations` history (not `players.market_value_in_eur`, which is
    Transfermarkt's *current* figure) so a 2015/16 stat line pairs with a valuation from roughly
    that era, not today's — showing e.g. a 38-year-old's current, much-reduced valuation next to
    their 24-year-old-season stats would be a real, misleading mismatch, not a rounding error.

    Args:
        matched_players (pandas.DataFrame): output of `keep_candidates_at_the_right_club`.
        tm_valuations (pandas.DataFrame): output of `_download_csv("player_valuations.csv.gz")` —
            must contain `player_id`, `date`, `market_value_in_eur`.
        as_of_date (pandas.Timestamp): the representative date to find the nearest valuation to.

    Returns:
        pandas.DataFrame: `matched_players` plus `market_value_eur` and `market_value_as_of` (the
            actual valuation date used — always shown alongside the number so "as of" is never
            implied to be the exact StatsBomb season date). Players with no valuation history at
            all in Transfermarkt's data are dropped (nothing to attach).
    """
    valuations = tm_valuations.copy()
    valuations["date"] = pd.to_datetime(valuations["date"])

    resolved = []
    for row in matched_players.itertuples(index=False):
        player_valuations = valuations[valuations["player_id"] == row.tm_player_id]
        if player_valuations.empty:
            continue
        nearest_idx = (player_valuations["date"] - as_of_date).abs().idxmin()
        nearest = player_valuations.loc[nearest_idx]
        resolved.append({
            "player": row.player, "team": row.team, "tm_name": row.tm_name,
            "market_value_eur": float(nearest["market_value_in_eur"]),
            "market_value_as_of": nearest["date"].date().isoformat(),
        })

    return pd.DataFrame(
        resolved, columns=["player", "team", "tm_name", "market_value_eur", "market_value_as_of"]
    )


def build_market_value_table(per90_features, cache_dir=CACHE_DIR):
    """End-to-end: download/cache Transfermarkt tables, match, and resolve a market value per
    player for every competition in `MARKET_VALUE_AS_OF_DATES`.

    Args:
        per90_features (pandas.DataFrame): the app's combined per-90 table (outfield + goalkeeper),
            must contain `player`, `team`, `nickname`, `competition`.
        cache_dir (Path): passed through to `_download_csv`.

    Returns:
        pandas.DataFrame: `player`, `team`, `tm_name`, `market_value_eur`, `market_value_as_of` —
            one row per player Transfermarkt data could resolve a value for. Players outside
            `MARKET_VALUE_AS_OF_DATES`' competitions (the two women's leagues) are never attempted
            — see the module docstring's second limitation.
    """
    tm_players = _download_csv("players.csv.gz", cache_dir)
    tm_valuations = _download_csv("player_valuations.csv.gz", cache_dir)
    tm_valuations["date"] = pd.to_datetime(tm_valuations["date"])

    resolved_frames = []
    for competition, as_of_date in MARKET_VALUE_AS_OF_DATES.items():
        pool = per90_features[per90_features["competition"] == competition]
        if pool.empty:
            continue
        candidates = find_name_candidates(pool, tm_players)
        matched = keep_candidates_at_the_right_club(candidates, tm_valuations, as_of_date)
        if matched.empty:
            continue
        resolved_frames.append(resolve_market_values(matched, tm_valuations, as_of_date))

    if not resolved_frames:
        return pd.DataFrame(
            columns=["player", "team", "tm_name", "market_value_eur", "market_value_as_of"]
        )
    return pd.concat(resolved_frames, ignore_index=True)
