# Data Sources

→ [CLAUDE.md](../CLAUDE.md)

---

## StatsBomb Open Data (primary)

- Library: `statsbombpy` — no API key required; pulls programmatically
- Data volume: ~1–2 GB uncompressed locally (gitignored, per-match pickle cache in `data/cache/`)

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
| SkillCorner 2024/25 | 10 matches, physical tracking | Physical layer for player similarity (Module B) |

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
| Women's EURO 2025 | 31 matches, events + 360 | xG test — women's-football held-out tournament; **not wired**. Not yet cached at all: a pull attempt (2026-07-09) hit a persistent GitHub raw-content rate limit (`429`) across several retries — see [ML_TOOLING.md](ML_TOOLING.md) |
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
before that). Cross-league normalisation is still not designed — per-90 rates are compared raw
today, flagged as an open item in the app itself. `TRAIN_SETS`/`TEST_SETS` (Module A) remain
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

## Cache Files (gitignored, in `data/`)

| File | Format | Contents |
|---|---|---|
| `data/cache/*.pkl` | Pickle | Raw per-match StatsBomb events (nested dicts/lists — stays pickle, not Parquet) |
| `data/shots_train.parquet` | Parquet | Processed xG training features (flat → parquet-safe) |
| `data/shots_test.parquet` | Parquet | Processed xG test features (flat → parquet-safe) |
| `data/shots_generalisation.parquet` | Parquet | Combined shots across `config.GENERALISATION_TEST_SETS` (Phase 4c held-out tournaments), scored per-competition by `metrics.compute_generalisation_metrics` |
| `data/player_per90_pl_2015_16.pkl` | Pickle | Per-90 player features + position for PL 2015/16 clustering |
| `data/physical_per90_skillcorner_sample.pkl` | Pickle | SkillCorner physical per-90 features for A-League sample |

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
  StatsBomb has no league-table or derby metadata (see [MODULES.md](MODULES.md#L57)). A scraped
  standings table at the date of each match would unblock that without needing per-shot detail.
- **Verdict:** worth a small spike (one competition, one season) if/when Phase 4's data-availability
  friction or Module C gets picked up — not a default assumption that it will work cleanly.
