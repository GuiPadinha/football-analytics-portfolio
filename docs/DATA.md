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
| Copa América 2024 | 32 matches, events | Optional extension if EURO 2024 test is interesting |
| SkillCorner 2024/25 | 10 matches, physical tracking | Physical layer for player similarity (Module B) |
| Messi-era La Liga | Multiple seasons | Reference/benchmarks only if needed |
| Women's EURO 2025 | comp 53 / season 315, events + 360 | Phase 4 candidate (newly released as of 2026-06-29) |

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
