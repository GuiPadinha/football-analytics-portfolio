# Session Roadmap & Initiative Status

→ [CLAUDE.md](../CLAUDE.md) | Initiative detail: [INITIATIVE.md](INITIATIVE.md)

---

## Session Roadmap (S1–S9)

| Session | Focus | Status |
|---|---|---|
| S1 | Scaffold + data exploration | ✅ Done |
| S2 | xG feature engineering | ✅ Done |
| S3 | xG model — baseline | ✅ Done |
| S4 | xG model — upgrade + visuals | ✅ Done |
| S5 | Player similarity — features | ✅ Done |
| S6 | Player similarity — clustering | ✅ Done |
| S7 | Radar charts + visuals | ✅ Done |
| S8 | README + polish | ✅ Done |
| S9 (future) | Module C — PUP | 💡 Scoped only |

---

## Framework Hardening & Expansion Initiative

Kicked off post-S8 (2026-06-29). On 2026-07-02 the full code-review backlog was folded into one
execution-ordered program and renumbered to Phases 0–9.

**The phase table + status lives only in [INITIATIVE.md](INITIATIVE.md#L18) — do not duplicate it
here.** This doc holds the *detailed task lists* per phase. Execution order: 0→1→2→3→4→5→6→7→8,
with 9 opportunistic. Phases 0–3 are done.

---

## Phase 3 — Engineering & reproducibility spine  ✅ Done

Cheapest credibility badge for the target roles, and it structurally kills the doc drift so every
later phase writes into a single-source system. Goes first because 3e (manifest) is a prerequisite
of Phase 4's ingestion pipeline and 3b (`metrics.json`) must exist before the data/number 10×.

- **3a — De-drift** (docs done 2026-07-02): canonical phase table in INITIATIVE; ROADMAP links to
  it; Exhibit A fixed in PROGRESS.md; CLAUDE Current Status renumbered; FRAMEWORK/PRODUCT_SPEC
  product refs → Phase 8. *Leftover for the Phase 3 code session:* renumber the two stale
  `src/config.py` comments that call the 360 model "Phase 3" (now Phase 7) — deferred to keep the
  2026-07-02 commit docs-only.
- **3b — `metrics.json` single source** (done 2026-07-02): `src/metrics.py` computes the headline
  numbers (xG train/test ROC-AUC + Brier, CV mean±std, no-skill→geometry→full ladder, per-group
  silhouette peaks, shot counts) and `python -m src.metrics` writes the committed `metrics.json`.
  A doc-lint test (`tests/test_metrics.py::test_current_state_docs_match_metrics_json`) fails the
  build if a *current-state* doc (README/CLAUDE/MODULES/DATA) prints a number that differs from the
  file; append-only history (PROGRESS, INITIATIVE log, ML_LEARNING_LOG) is deliberately exempt.
  Deferred the test-count number (a repo fact, not a model output — CI reports it).
- **3c — CI:** `.github/workflows/tests.yml` runs the 22 pytest tests on push/PR (Python 3.10,
  pinned `requirements.txt`); green badge in README.
- **3d — `pipeline.py` + `Makefile`** (done 2026-07-03): `src/pipeline.py` chains the ingestion →
  features → model → outputs steps into a headless rebuild, runnable as `python -m src.pipeline`
  (`--force` to bypass caches, `--skip-plots` for data-only). A thin root `Makefile` wraps it
  (`make pipeline`). Notebooks **stay** as the teaching surface (learning mandate) — the pipeline
  runs alongside them, not instead of them.
- **3e — Data manifest:** `data/manifest.json` pinning comp/season/match IDs + row counts + content
  hash per dataset; catches upstream StatsBomb changes; feeds Phase 4.

## Phase 4 — Multi-competition ingestion + data expansion  🟡 Data pull in progress

The flagship overlap item: engineering-at-scale in service of ML. Turns Module A's "generalises
from n=2 contexts" into a defensible claim and fixes Module B's single-season thinness.

- **4a — Config-driven ingestion** (done 2026-07-04): `src/config.py`'s `Dataset` registry already
  had the right shape, so every candidate below is a config line, no `data_loader.py` changes
  needed. New: `PHASE_4_EVENTS_ONLY` / `PHASE_4_EVENTS_AND_LINEUPS` groupings, pulled via a one-off
  script reusing `build_training_dataset`/`build_player_per90_features` — see [DATA.md](DATA.md#phase-4-data-expansion-2026-07-04)
  for the full dataset list, the "StatsBomb's La Liga = mostly Barcelona" gotcha, and the sampled
  women's-football viability check.
- **4b — Module B cross-league/season:** data pulled (La Liga 2015/16, Serie A 2015/16, Ligue 1
  2015/16, Frauen Bundesliga 2023/24, FA WSL 2023/24) — not yet wired into `SIMILARITY_SET` or
  cross-league normalisation designed. Next actual step once the pull finishes.
- **4c — Module A generalisation:** held-out test candidates pulled (Copa América 2024, FIFA World
  Cup 2022, Africa Cup of Nations 2023, Women's EURO 2025) — not yet wired into `TEST_SETS`.
- **4d — Availability friction:** resolved for now — full-season non-La-Liga leagues (Serie A,
  Ligue 1, both women's leagues) were more available than assumed once verified by match/team
  count instead of competition name. Understat.com (free, Big-5-league shot coordinates,
  2014/15–present) is a further option if more volume is wanted later, deferred because it needs
  new ingestion code (different schema) — see [DATA.md](DATA.md#phase-4-data-expansion-2026-07-04).
  The originally-flagged SofaScore/FlashScore option is still there too, see
  [DATA.md](DATA.md#candidate-alternative--supplementary-data-sources-not-yet-used) (match-level
  stats + standings, not a per-shot xG source).

## Phase 5 — xG uncertainty + hierarchical finishing model  ⬜

The ML-depth differentiator: small → big, no new data, directly serves the valuation lens.

- **5a — Uncertainty on goals−xG:** bootstrap / analytic interval so "+8 on 40 shots" and "+8 on
  200 shots" stop reading as the same claim. The single best small addition.
- **5b — Hierarchical / empirical-Bayes finishing:** per-player finishing random effect over
  baseline xG, shrunk toward zero — the statistically correct goals−xG. Achieves PUP's "real or
  luck" with clean stats. (May add `statsmodels`.)
- **5c — Header/foot interaction (or split models):** one `body_part` flag assumes identical
  geometry→goal curves for headers and volleys; add an interaction or split.
- **5d — Calibration by stratum:** reliability diagrams split open-play / set-piece / header to
  expose miscalibration the single Brier number hides.

## Phase 6 — Module B metric/feature upgrades  ⬜

- **6a — Mahalanobis / PCA-whitened distance:** Euclidean double-counts correlated features
  (shots↔goals, tackles↔interceptions); respect the covariance.
- **6b — Possession-adjusted defensive actions:** per-100-opponent-touches so a presser at a
  possession side and one at a low block compare fairly.
- **6c — GMM soft membership:** the ~0.25 silhouette (continuum) motivates it; also dissolves the
  Antonio one-man-cluster.
- **6d — Richer creative features:** xA / progressive-pass-distance over raw key passes.

## Phase 7 — 360-context xG + xGOT  ⬜  *(was Phase 3)*

StatsBomb `three-sixty` data gives freeze-frames (every visible player's position at the moment of each event). Leverkusen 2023/24 and EURO 2024 both have 360 — the two datasets already in use.

**Candidate 360 features:**
- Number of defenders between shot and goal (direct block probability)
- Goalkeeper position relative to goal centre
- Number of open-goal-path defenders
- Nearest defender distance to ball at shot moment

**Post-shot xG (xGOT):** shot trajectory context (where the ball ended up, keeper reaction) narrows the probability *after* the shot is taken. Distinction: pre-shot xG (chance quality before kick) vs. xGOT (includes where the shot went).

**Recommended approach:** keep the existing pre-shot logistic model as the baseline. Build 360-feature extension as a second model. Compare honestly — if the 360 features don't clearly add discrimination, say so.

**Entry checklist:**
- [ ] Confirm Phase 3–6 work committed via GitHub Desktop
- [ ] Verify `data/cache/` has Leverkusen 2023/24 360 frames (should already be pulled)
- [ ] Check StatsBomb `three-sixty` schema: `statsbombpy.sb.three_sixty(match_id=X)`

## Phase 8 — Product layer build (Streamlit)  🟡 minimal v1 built, deploy pending  *(was Phase 5)*

Minimal v1 built 2026-07-04, ahead of strict phase order — a friend demo (~2026-07-11) made
"something clickable" more valuable than finishing 4–6 first this time; see
[PRODUCT_SPEC.md](PRODUCT_SPEC.md)'s Build Checklist for exactly what's done vs. left. Scoped to
Premier League 2015/16 (the one dataset with a full similarity + xG pool already computed) — a
later pass can widen this once Phase 4b/4c pick a wider training/similarity set to showcase.

**Remaining:** deploy to Streamlit Community Cloud (needs the maintainer's account — not
automatable) and a from-scratch visual check in a real browser (verified so far via Streamlit's
headless `AppTest` harness only — script-level correctness, not a look at the actual rendering).

## Phase 9 — Opportunistic  ⬜

- **xA / chance-creation model** — sibling to xG on the same pipeline; also upgrades 6d.
- **Module C (PUP)** — only if desired; carries a selection-bias confound + label-acquisition cost,
  and Phase 5 already delivers most of its payoff. Spec: [MODULES.md](MODULES.md#L53).
- **Remaining alt-models** — hierarchical clustering, cosine, monotonic GBM.
- ~~**Architecture / dependency doc**~~ — flagged 2026-07-04, done same day:
  [ARCHITECTURE.md](ARCHITECTURE.md) (import graph, data flow for both modules, the pure/IO-split
  pattern, and the implicit DataFrame-schema contracts an import graph can't show).
