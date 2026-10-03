# Data Sources

→ [CLAUDE.md](../CLAUDE.md)

---

## StatsBomb Open Data (primary)

- Library: `statsbombpy` — no API key required; pulls programmatically
- Data volume: ~8.5 GB locally as of 2026-10 (~4,400 per-match pickles). They live in `data/cache/`
  (gitignored) unless the `FAP_CACHE_DIR` environment variable points elsewhere. Guilherme's machine
  uses `C:/Users/guilh/fap-cache` (since 2026-10-02), so OneDrive doesn't sync them.

**Key data objects:**
- `competitions` — available competitions list
- `matches` — match metadata per competition/season
- `events` — granular event data (shots, passes, dribbles, pressures, ~3400 events/match)
- `lineups` — per-player on-pitch stints with from/to times and positions (including Tactical Shift changes) — more reliable than reconstructing from Starting XI + Substitution events
- `three-sixty` — freeze-frames: position of every visible player at moment of each event (selected matches only)

---

## Priority Datasets

| Dataset | Coverage | Role |
|---|---|---|
| Bayer Leverkusen 2023/24 | 34 matches, events + 360 | xG training (league) — tactically unique unbeaten season |
| Premier League 2015/16 | 380 matches, events | xG training (league) — volume + era benchmark |
| UEFA EURO 2024 | 51 matches, events + 360 | xG test/validation (tournament) — out-of-distribution test |
| SkillCorner 2024/25 | 10 matches, physical tracking | Standalone physical-metrics demo (no player overlap with the StatsBomb pool, so not joined into Module B) |

**Pulled 2026-07-04, Phase 4 data expansion (see below) — wired into `config.SIMILARITY_SETS`
(the app's player pool, 2026-07-05) or `config.GENERALISATION_TEST_SETS` (Module A held-out
tournaments, 2026-07-09) unless noted otherwise. `TRAIN_SETS`/`TEST_SETS` themselves remain
untouched by design (see ML_LEARNING_LOG.md — more league volume didn't help) — the Phase 4c
tournaments are additional, separately-reported evidence, not folded into the headline test set:**

| Dataset | Coverage | Role |
|---|---|---|
| Barcelona 2004/05–2020/21 (16 seasons) | 866 matches, events only (no lineups pulled) | xG training volume — Messi-era, single-club (see gotcha below); **not wired anywhere yet** — no lineups means no minutes-played, so not usable for Module B as-is |
| La Liga 2015/16 | 380 matches, events + lineups (lineups pulled 2026-07-05) | In `SIMILARITY_SETS` — genuine full 20-team season |
| Serie A 2015/16 | 380 matches, events + lineups (lineups pulled 2026-07-05) | In `SIMILARITY_SETS` — same-era full league as PL 2015/16 |
| Ligue 1 2015/16 | 377 matches, events + lineups (lineups pulled 2026-07-05) | In `SIMILARITY_SETS` — same-era full league as PL 2015/16 |
| Frauen Bundesliga 2023/24 | 132 matches, events + lineups | In `SIMILARITY_SETS` — women's-football expansion, newest full-season data in this project |
| FA Women's Super League 2023/24 | 132 matches, events + lineups | In `SIMILARITY_SETS` — women's-football expansion, newest full-season data in this project |
| Women's EURO 2025 | 31 matches, events + 360 | xG test — women's held-out tournament; **wired 2026-10-01** (the July 429 had cleared): ROC-AUC 0.763, goals ÷ xG 0.98 |
| FIFA Women's World Cup 2023 | 64 matches, events + 360 | xG test — women's held-out tournament; **wired 2026-10-01**: ROC-AUC 0.777, goals ÷ xG 0.83 |
| Copa América 2024 | 32 matches, events | xG test — additional held-out tournament; **wired 2026-07-09** (Phase 4c), scored separately in `metrics.json`'s `xg_generalisation`: ROC-AUC 0.763 |
| FIFA World Cup 2022 | 64 matches, events + 360 | xG test — additional held-out tournament; **wired 2026-07-09** (Phase 4c): ROC-AUC 0.808 |
| Africa Cup of Nations 2023 | 52 matches, events + 360 | xG test — additional held-out tournament; **wired 2026-07-09** (Phase 4c): ROC-AUC 0.807 |

---

## Phase 4 Data Expansion (2026-07-04)

Datasets identified and pulled for Phase 4 (multi-competition ingestion). All named in
`src/config.py` (`PHASE_4_EVENTS_ONLY` / `PHASE_4_EVENTS_AND_LINEUPS`); cached locally via a
one-off script that reuses `build_training_dataset`/`build_player_per90_features` — no new
ingestion code, per Phase 4a's "config line, not code edit" goal. Module B's app pool (2026-07-05):
La Liga/Serie A/Ligue 1 2015/16 + Frauen Bundesliga/FA WSL 2023/24 now in `config.SIMILARITY_SETS`
(their lineups pulled 2026-07-05 to enable minutes-played; La Liga/Serie A/Ligue 1 had only events
before that). **Cross-league normalisation designed and implemented 2026-07-13** —
`similarity.normalize_within_competition` z-scores each per-90 stat within its own competition
before clustering/`find_similar_players` compare across leagues (see MODULES.md); a relative,
data-only adjustment, not a true competitiveness rating, since no external league-strength index
exists in this project's data. `TRAIN_SETS`/`TEST_SETS` (Module A) remain
untouched by design (see ML_LEARNING_LOG.md); the three tournament pulls (Copa América 2024, FIFA
World Cup 2022, Africa Cup of Nations 2023) sat cached-but-unscored until Phase 4c (2026-07-09)
wired them into `config.GENERALISATION_TEST_SETS` instead — see [MODULES.md](MODULES.md)'s Module A
section and [ROADMAP.md](ROADMAP.md)'s Phase 4c entry for the generalisation finding.

**Gotcha: StatsBomb's "La Liga" entry is mostly Barcelona, not the league.** Checked by
match/team count (not assumed from the competition name — the same trap caught a "Bundesliga
2023/24" entry that turned out to be Leverkusen-only, and a "Ligue 1 2022/23" entry that was all
Paris Saint-Germain). Of La Liga's 17 available seasons, 16 have every single match involving
Barcelona — StatsBomb's well-known Messi-era open-data release, filed under the league rather
than under a separate club label. Only **2015/16** is a genuine full 20-team, 380-match season.
Total Barcelona-only volume: 866 matches, 2004/05–2020/21. Guilherme is fine leaning into the
Messi era for this (see CONTEXT.md's Portfolio Framing, updated 2026-07-04) — the correction here
is about what the data *is*, not whether it's acceptable to use.

**Women's football — is it viable?** Sampled real shot/goal events (not guessed) before
committing to the pull:

| | Shots/match (sampled) | Conversion | Full-season shots (est.) |
|---|---|---|---|
| Frauen Bundesliga 23/24 | 25.6 | 14.1% | ~3,400 |
| FA WSL 23/24 | 25.9 | 12.6% | ~3,400 |
| Women's Euro 2025 | 27.6 | 12.3% | ~860 |
| *(existing) PL+Leverkusen train* | *26.1* | *10.1%* | *10,824* |
| *(existing) EURO 2024 test* | *25.8* | *8.1%* | *1,316* |

Shot volume per match is basically identical to men's football — not a bottleneck. Conversion
rate is consistently higher (12–14% vs. 8–10%) across all three samples, a real and narratable
difference, not one to assert a cause for without more digging. The one real risk is **Module B**:
a 12-team league yields roughly half the qualifying-player pool of PL 2015/16 per position
group (estimate, not an exact count yet) — expect thinner clusters, possibly more Antonio-style
one-player clusters, and say so plainly if that's what happens rather than hiding it.

**Deferred: Understat.com.** Free, scrapable shot-level data with real x/y coordinates across the
Big 5 leagues + Russian league, 2014/15–present (a ready-made Kaggle mirror exists too) — a
genuinely bigger unlock than any paid option investigated (StatsBomb/Opta are enterprise
sales-quote only with no individual pricing; Wyscout's €299/year individual tier is video +
box-score stats, not raw shot coordinates). Not pulled in this pass because it needs real new
engineering — a different event schema than StatsBomb's (`extract_shot_features` assumes
StatsBomb's column names), so it's new ingestion code, not a `config.py` line. Worth its own scoped
session, not bundled into a same-day data pull.

---

## xG Model Data Split Strategy

Tournament and league football have **structurally different shot profiles**: fewer games, higher stakes, more conservative tactics. We treat them as separate contexts intentionally — this is the kind of analytical decision to highlight in interviews.

- **Training (league context):** Leverkusen 2023/24 + PL 2015/16 — high volume, consistent pressure dynamics
- **Test (tournament context):** UEFA EURO 2024 — deliberately out-of-distribution

Current processed data state:
- `data/shots_train.parquet` — 10,824 shots, 10.1% conversion
- `data/shots_test.parquet` — 1,316 shots (penalty shootouts / period 5 dropped; honest measure on in-game shots)

---

## SkillCorner Open Data (physical layer)

- Repo: `github.com/SkillCorner/opendata`
- Contains: broadcast tracking data (X/Y coordinates at 10fps) for 10 matches, 2024/25 A-League
- Speed columns in `to_df()` are entirely null — metrics derived from frame-to-frame position deltas instead (rescaled from normalised 0-1 coords using real pitch dimensions, 105×68m)
- `min_observed_minutes=30` caps extrapolation factor at 3× (shorter windows produced unreliable per-90 rates)
- **Zero player overlap with StatsBomb datasets** — demonstrated as two parallel capability demos, not one fused player profile

---

## Transfermarkt Market Value Data (Phase 9, built 2026-07-14)

Pairs a "players like X" match with a market-value number (e.g. "similar profile, cheaper") —
raised ahead of a pitch on 2026-07-13 as a candidate addition (see the git history for that
research spike), built the next day. See `src/market_value.py` for the implementation and
[FRAMEWORK.md](FRAMEWORK.md)'s Out of Scope note on the modelling-vs-displaying distinction.

**Source:** [dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets),
a maintained, weekly-refreshed, openly-licensed CSV mirror of Transfermarkt (also on
[Kaggle](https://www.kaggle.com/datasets/davidcariboo/player-scores)) — no official Transfermarkt
API exists. Two tables used: `players.csv.gz` (current profile) and `player_valuations.csv.gz`
(dated history, ~508k rows) — fetched via a plain `urllib` GET with a browser `User-Agent` (the
hosting R2 bucket returns `403` for Python's default UA, and for HEAD/Range requests — checked
directly, not assumed) and cached under `data/transfermarkt/`.

**Entity resolution (the real cost, exactly as flagged in the original research spike):** there is
no shared player ID between StatsBomb and Transfermarkt, so players are matched in two steps.

1. **Name candidates** (`find_name_candidates`): every Transfermarkt player whose name fits, from
   three kinds of evidence. The strongest is StatsBomb's own nickname for the player: its lineups
   record the popular name ("Koke" for "Jorge Resurrección Merodio"), which is the name
   Transfermarkt uses (added 2026-10-03). Then the full name, exactly. Last, the full name's best
   token-subset match (StatsBomb's "Cristiano Ronaldo dos Santos Aveiro" ↔ Transfermarkt's
   "Cristiano Ronaldo"). The subset match weights tokens by inverse corpus frequency: a plain "most
   tokens wins" rule nearly matched Neymar to an unrelated "Júnior Santos", purely because
   "Santos"/"Junior" are common surnames. A candidate made only of a name particle ("de") never
   counts. See `_token_rarity_scores` and ML_LEARNING_LOG.md.
2. **Club check** (`keep_candidates_at_the_right_club`, added 2026-10-02; it has also broken ties
   since 2026-10-03). A candidate is kept only if Transfermarkt valued it at the StatsBomb team's
   club within 12 months of the season, and a player is matched only if exactly one candidate is
   left. Names alone had attached other people's valuations to famous players with long legal
   names: Dani Alves, Koke, Gabi, Danilo, Fernandinho, Jonny Evans and David Silva (€100k from a
   2024 valuation). Names also can't tell namesakes apart: Transfermarkt has two "Luis Suárez",
   born 1987 and 1997. Two data traps: the sources name clubs differently ("Barcelona" vs "FC
   Barcelona"), so each team's Transfermarkt club is learned by majority vote over its
   single-candidate players; and `player_valuations.current_club_id` is the player's club
   *today*, so only `current_club_name` (the club at the valuation date) can be used.

Result: **~99% of the four men's competitions matched (1,327 of 1,347 players)**, every valuation
from 2015–16. The 2026-10-03 changes added 159 players to the 2026-10-02 version (1,168) and
changed none of its matches. The nickname and the club tiebreak account for 148 of them, including
Suárez (€90M), Koke, Isco, Fàbregas, Diego Costa, David Silva, Marcelo, Dani Alves and Pepe. The
other 11 come from two smaller fixes: letters with no plain-letter base are transliterated the way
Transfermarkt spells them (Łukasz Fabiański → "Lukasz Fabianski", Đoković → "Djokovic"), and the
nickname is also matched by its words ("Mikel John Obi", "Charly Musonda Jr."). All 159 were
reviewed by hand. Messi, Ronaldo, Neymar, Kane, Agüero, Ibrahimović and Higuaín resolve to
era-correct valuations as before. The 20 still blank are mostly spellings that share no word
(Robbie/Robert Brady, Sebastien/Sebastian De Maio), bare common names with nothing distinctive to
match (Nacho, Alex, Tiago), and loanees Transfermarkt values at their parent club (Ranocchia and
Dodô at Inter).

**Valuation is dated, not one number:** uses `player_valuations`' history, picking the entry
nearest a representative "as of" date per competition (`market_value.MARKET_VALUE_AS_OF_DATES` —
2016-01-01 for the four 2015/16 men's leagues), not `players.market_value_in_eur` (Transfermarkt's
*current* figure, which would show e.g. a 38-year-old's much-reduced valuation next to their
24-year-old-season stats).

**Coverage gap, verified not assumed:** this Transfermarkt mirror only covers men's football —
checked directly against the real `players` table (every `current_club_domestic_competition_id` is
a men's league code; zero rows matched any known women's club name) before relying on it. Frauen
Bundesliga / FA WSL players are skipped outright by `build_market_value_table` (never
attempted-and-failed), not silently blank with no explanation.

**Legality:** secondhand, not independently reviewed — Transfermarkt's own ToS hasn't been checked;
the upstream mirror is itself built by scraping public pages, so using it inherits that risk rather
than removing it. Treated as acceptable for a personal portfolio demo, as before.

---

## Cache Files (gitignored, in `data/`)

| File | Format | Contents |
|---|---|---|
| `data/cache/*.pkl` (or `$FAP_CACHE_DIR`) | Pickle | Raw per-match StatsBomb events and lineups (nested dicts/lists — stays pickle, not Parquet) |
| `data/shots_train.parquet` | Parquet | Processed xG training features (flat → parquet-safe) |
| `data/shots_test.parquet` | Parquet | Processed xG test features (flat → parquet-safe) |
| `data/shots_generalisation.parquet` | Parquet | Combined shots across `config.GENERALISATION_TEST_SETS` (Phase 4c held-out tournaments), scored per-competition by `metrics.compute_generalisation_metrics` |
| `data/player_per90_pl_2015_16.pkl` | Pickle | Per-90 player features + position for PL 2015/16 clustering |
| `data/physical_per90_skillcorner_sample.pkl` | Pickle | SkillCorner physical per-90 features for A-League sample |
| `data/transfermarkt/players.csv.gz`, `player_valuations.csv.gz` | CSV (gzip) | Raw Transfermarkt tables, downloaded once and reused by `market_value.build_market_value_table` |

---

## Committed Provenance & Metrics Files (not gitignored)

Two files are the deliberate exceptions to "`data/` is never committed" — they're small,
deterministic, and exist specifically so someone reading the repo (not running it) can see the
data's provenance and the model's headline numbers without pulling StatsBomb or rebuilding anything.

| File | Written by | Contents |
|---|---|---|
| `metrics.json` (repo root) | `python -m src.metrics` | xG train/test ROC-AUC + Brier, CV mean±std, baseline ladder, per-group silhouette peaks — the single source the docs quote (see `src/metrics.py`, Phase 3b) |
| `data/manifest.json` | `python -m src.manifest` | Per-dataset match-id set + hash + local cache coverage, processed-table content hashes, `statsbombpy` version — provenance pin, catches upstream data drift (see `src/manifest.py`, Phase 3e) |

Both regenerate byte-for-byte from unchanged data/models (no timestamps) — a real diff on either
file means something upstream actually moved. `python -m src.pipeline` regenerates both as its
last step (Phase 3d).

---

## Candidate Alternative / Supplementary Data Sources (not yet used)

Flagged 2026-07-04 as a Phase 4 option if free full-season StatsBomb league coverage keeps proving
scarce (see [ROADMAP.md](ROADMAP.md) Phase 4d, "availability friction"): **SofaScore / FlashScore**
match-info pages (lineups, match stats, league standings at the time of the match).

Honest assessment before reaching for this:
- **Not a StatsBomb replacement for Module A.** These sites expose match-level and box-score-style
  stats (shots, possession, cards, ratings), not event-level x/y shot locations — there's no
  `distance_to_goal`/`angle_to_goal` to recover, so they can't feed the existing xG model as-is.
  They'd suit a coarser *match-outcome* or *team-strength* model, not a per-shot one.
- **No official API** — this is scraping, not a published open-data endpoint like
  `statsbombpy`. That means ToS review before relying on it for anything public-facing, and
  brittleness (page-structure changes break the scraper with no changelog to warn you).
- **Where it's genuinely useful:** league standings / rivalry context is exactly the
  "external match-importance label" Module C (PUP) has been blocked on since it was scoped —
  StatsBomb has no league-table or derby metadata (see
  [MODULES.md](MODULES.md#module-c--pup-performance-under-pressure)). A scraped
  standings table at the date of each match would unblock that without needing per-shot detail.
- **Verdict:** worth a small spike (one competition, one season) if/when Phase 4's data-availability
  friction or Module C gets picked up — not a default assumption that it will work cleanly.

