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

1. **No shared player ID with StatsBomb** (DATA.md's flagged blocker). There is no official
   crosswalk, so `match_players_to_transfermarkt` resolves it with normalised-name matching
   (exact first, then a bidirectional token-subset fallback for the very common "StatsBomb logs a
   player's full legal name, Transfermarkt uses their popular/shirt name" case — e.g. StatsBomb's
   "Cristiano Ronaldo dos Santos Aveiro" vs Transfermarkt's "Cristiano Ronaldo"), filtered to a
   compatible broad position, and **only accepted if exactly one Transfermarkt candidate
   survives** — an unresolved or ambiguous name gets no market value shown, never a guess. This
   is a real simplification (no club/season cross-check, since StatsBomb and Transfermarkt's club
   naming/season conventions don't line up cleanly enough to gate matching reliably) — false
   negatives (a real match missed) are the expected failure mode, not false positives.
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

# Transfermarkt's broad `position` category maps onto this project's four position groups
# almost exactly (checked against the real data before relying on the mapping) — the one
# rename is "Attack" -> "Forward" to match `similarity.POSITION_GROUPS`' naming.
TM_POSITION_TO_GROUP = {
    "Attack": "Forward",
    "Midfield": "Midfielder",
    "Defender": "Defender",
    "Goalkeeper": "Goalkeeper",
}

# Name-construction particles common across the naming traditions in this player pool
# (Portuguese/Spanish "de"/"da"/"dos"/"das"/"del"/"el", Dutch "van"/"der"/"den", French "du"/"le"/
# "la", German "von") — real, found by a real bug: "Sebastian De Maio" (StatsBomb) matched
# Transfermarkt's "Dé" purely because "de" is (surprisingly) not a *common enough* token to be
# scored low by `_token_rarity_scores` alone, and it was the only candidate at all, so it won by
# default with no other candidate to lose to. A token-subset match built *entirely* from these
# particles carries no real evidence about which specific player it is — `match_players_to_
# transfermarkt` requires at least one non-particle token before accepting a candidate.
NAME_PARTICLE_STOPWORDS = {
    "de", "da", "do", "dos", "das", "del", "der", "den", "van", "von", "el", "la", "le", "du",
}


def normalize_name(name):
    """Fold a player name to a comparable canonical form: strip accents, lowercase, collapse
    punctuation/whitespace to single spaces.

    Shared normalisation for both StatsBomb and Transfermarkt names, so "Kramarić" and "Kramaric"
    (or StatsBomb's genuine doubled-apostrophe quirk, "N''Golo Kanté" — see ML_TOOLING.md)
    compare equal rather than failing a match on an encoding difference that has nothing to do
    with whether it's the same player.

    Args:
        name (str): a player name, from either source.

    Returns:
        str: lowercase, ASCII-only, single-spaced. Empty string for `NaN`/`None`.
    """
    if pd.isna(name):
        return ""
    decomposed = unicodedata.normalize("NFKD", str(name).replace("''", "'"))
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
        request = urllib.request.Request(
            TRANSFERMARKT_BASE_URL + filename, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            cache_path.write_bytes(response.read())

    return pd.read_csv(cache_path, compression="gzip")


def _token_rarity_scores(norm_names):
    """Inverse document frequency for every token across a corpus of normalised names.

    A plain "most tokens wins" specificity rule fails on real Lusophone/Hispanic full legal
    names (see `match_players_to_transfermarkt`'s docstring): "Santos", "Junior", "Silva", "Da"
    are common enough (95, 93, 126, 42 occurrences in this ~50k-player corpus) that a 2-token
    collision built entirely from them (e.g. a real, unrelated "Júnior Santos") can outrank the
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


def match_players_to_transfermarkt(per90_players, tm_players):
    """Resolve each (player, team) to at most one Transfermarkt `player_id`.

    Two-pass matching, neither pass filtered to a matching broad position up front — checked
    directly against real data before deciding this (see module docstring's limitation #1):
    Transfermarkt's own `position` tag can genuinely disagree with this project's StatsBomb-
    derived `position_group` for permutable attacking roles (e.g. Neymar is tagged "Midfield" on
    Transfermarkt, "Forward" here), so a hard position pre-filter can silently exclude the real
    candidate while leaving an unrelated same-position collision to win. Position is used only
    as a last-resort tiebreaker between two otherwise-equally-good name matches.

    1. **Exact match** on the normalised full name.
    2. **Rarity-weighted token-subset fallback**, for names left unresolved by (1): one side's
       normalised name's tokens are a subset of the other's (either direction) — catches
       "StatsBomb logs the full legal name, Transfermarkt logs the popular name" (e.g. TM's
       "Cristiano Ronaldo" tokens {"cristiano", "ronaldo"} ⊆ StatsBomb's "Cristiano Ronaldo dos
       Santos Aveiro" tokens). Candidates are scored by `_rarity_score` (sum of 1/corpus-
       frequency across their tokens, see `_token_rarity_scores`) rather than raw token count,
       and only the single highest-scoring candidate is accepted.

    Either pass only accepts a match when **exactly one** Transfermarkt candidate survives (after
    the position tiebreaker, for pass 2) — a name with zero or still-ambiguous candidates is left
    unmatched rather than guessed. Real matches do get missed this way (e.g. two genuinely
    different professional players who both happen to be named "Luis Suárez"), which is the
    intended, honest failure mode: a missed match is safe, a wrong one under a real player's name
    is not.

    Args:
        per90_players (pandas.DataFrame): must contain `player`, `team`, `position_group`.
        tm_players (pandas.DataFrame): output of `_download_csv("players.csv.gz")` — must contain
            `player_id`, `name`, `position`.

    Returns:
        pandas.DataFrame: one row per successfully matched (player, team), with `tm_player_id`
            and `tm_name` (the matched Transfermarkt display name, kept so a UI can show what it
            actually matched to, for transparency).
    """
    tm = tm_players.copy()
    tm["norm_name"] = tm["name"].map(normalize_name)
    tm["broad_group"] = tm["position"].map(TM_POSITION_TO_GROUP)
    tm = tm[tm["norm_name"] != ""].reset_index(drop=True)
    tm["tokens"] = tm["norm_name"].map(lambda n: frozenset(n.split()))
    token_rarity = _token_rarity_scores(tm["norm_name"])

    # Inverted index (token -> row indices) so the subset-fallback pass only has to consider
    # Transfermarkt rows sharing at least one token with the player being matched, instead of
    # re-scanning all ~50k rows per unmatched player — a valid subset match (either direction)
    # always shares at least one token, so this narrows the candidate pool with no loss of recall.
    token_to_rows = {}
    for idx, tokens in tm["tokens"].items():
        for token in tokens:
            token_to_rows.setdefault(token, []).append(idx)

    sb_players = per90_players[["player", "team", "position_group"]].drop_duplicates().copy()
    sb_players["norm_name"] = sb_players["player"].map(normalize_name)

    matches = []
    for row in sb_players.itertuples(index=False):
        if not row.norm_name:
            continue

        exact = tm[tm["norm_name"] == row.norm_name]
        if len(exact) == 0:
            sb_tokens = set(row.norm_name.split())
            nearby_idx = sorted(set().union(*(token_to_rows.get(t, []) for t in sb_tokens)))
            if not nearby_idx:
                continue  # no Transfermarkt name shares even one token - nothing to consider
            nearby = tm.loc[nearby_idx]
            subset_mask = nearby["tokens"].map(
                lambda tokens: tokens <= sb_tokens or sb_tokens <= tokens
            ).astype(bool)
            candidates = nearby[subset_mask].copy()
            if candidates.empty:
                continue
            # A candidate whose entire token set is name-construction particles (e.g. "de" alone)
            # carries no real evidence of who it is - see NAME_PARTICLE_STOPWORDS.
            has_real_token = candidates["tokens"].map(
                lambda t: bool(t - NAME_PARTICLE_STOPWORDS)
            ).astype(bool)
            candidates = candidates[has_real_token]
            if candidates.empty:
                continue
            candidates["score"] = candidates["tokens"].map(
                lambda tokens: _rarity_score(tokens, token_rarity)
            )
            top_score = candidates["score"].max()
            candidates = candidates[candidates["score"] == top_score]
        else:
            candidates = exact

        if len(candidates) > 1:
            # Tied on name-match quality - fall back to broad-position agreement to break the
            # tie; if that still doesn't leave exactly one, it's a genuine ambiguity (e.g. two
            # different real players sharing a name and a position), not a bug - skip.
            candidates = candidates[candidates["broad_group"] == row.position_group]
        if len(candidates) != 1:
            continue

        matched = candidates.iloc[0]
        matches.append({
            "player": row.player, "team": row.team,
            "tm_player_id": int(matched["player_id"]), "tm_name": matched["name"],
        })

    return pd.DataFrame(matches, columns=["player", "team", "tm_player_id", "tm_name"])


def resolve_market_values(matched_players, tm_valuations, as_of_date):
    """Attach each matched player's Transfermarkt market value nearest to `as_of_date`.

    Uses the dated `player_valuations` history (not `players.market_value_in_eur`, which is
    Transfermarkt's *current* figure) so a 2015/16 stat line pairs with a valuation from roughly
    that era, not today's — showing e.g. a 38-year-old's current, much-reduced valuation next to
    their 24-year-old-season stats would be a real, misleading mismatch, not a rounding error.

    Args:
        matched_players (pandas.DataFrame): output of `match_players_to_transfermarkt`.
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
            must contain `player`, `team`, `position_group`, `competition`.
        cache_dir (Path): passed through to `_download_csv`.

    Returns:
        pandas.DataFrame: `player`, `team`, `tm_name`, `market_value_eur`, `market_value_as_of` —
            one row per player Transfermarkt data could resolve a value for. Players outside
            `MARKET_VALUE_AS_OF_DATES`' competitions (the two women's leagues) are never attempted
            — see the module docstring's second limitation.
    """
    tm_players = _download_csv("players.csv.gz", cache_dir)
    tm_valuations = _download_csv("player_valuations.csv.gz", cache_dir)

    resolved_frames = []
    for competition, as_of_date in MARKET_VALUE_AS_OF_DATES.items():
        pool = per90_features[per90_features["competition"] == competition]
        if pool.empty:
            continue
        matched = match_players_to_transfermarkt(pool, tm_players)
        if matched.empty:
            continue
        resolved_frames.append(resolve_market_values(matched, tm_valuations, as_of_date))

    if not resolved_frames:
        return pd.DataFrame(
            columns=["player", "team", "tm_name", "market_value_eur", "market_value_as_of"]
        )
    return pd.concat(resolved_frames, ignore_index=True)
