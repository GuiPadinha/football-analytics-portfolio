# Initiative — Framework Hardening & Expansion

Tracks the multi-phase improvement work that follows the S1–S8 build. Mirrors the Progress Log
style in `CLAUDE.md`. The full plan and rationale live in the approved plan file; this is the
where-are-we tracker.

**Origin:** a code review surfaced correctness, methodology, structure, and scaling gaps, and the
product story was unclear. Each phase below is independently executable in its own session.
Conceptual framing is settled in [FRAMEWORK.md](FRAMEWORK.md).

**Framing decisions (locked):** recruitment-led, both modules kept; product layer specified now and
built later. **Reprioritised 2026-07-02** ("do it all, structured"): the whole review backlog is
folded into one execution-ordered program (below). The headline shift — an engineering &
reproducibility spine goes *first* (manifest is a prerequisite of the data-expansion pipeline;
`metrics.json` must exist before we generate numbers across new competitions), and data expansion
is treated as engineering-at-scale-in-service-of-ML, not a download script.

---

## Phases

**This table is the single source of truth for phase numbering.** ROADMAP.md links here; do not
copy it. Phases 3–6 were renumbered on 2026-07-02 (see the "Was" column) when the review backlog
was folded in — the old Phase 3 (360 xG) and Phase 5 (product) moved *later* behind the unblockers.

| Phase | Focus | Was | Status |
|---|---|---|---|
| **0** | Framework charter (FRAMEWORK.md, this tracker, CLAUDE.md roadmap entry) | 0 | ✅ Done |
| **1** | Foundation: `config.py`, per-match cache, penalty/shootout fix, pinned deps, robustness fixes, first tests | 1 | ✅ Done |
| **2** | ML rigor: cross-validation, scaled logistic, baseline feature engineering, calibrated GBM, silhouette, minutes-weighted position | 2 | ✅ Done |
| **3** | Engineering & reproducibility spine: CI, `pipeline.py`/Makefile, `metrics.json` single-source, data manifest | *new* | ✅ Done |
| **4** | Multi-competition ingestion + data expansion: config-driven pipeline, Module A generalization, Module B cross-league | 4 (reshaped) | ⬜ **Next** |
| **5** | xG uncertainty + hierarchical/empirical-Bayes finishing model; header/foot interaction; calibration by stratum | *new* | ⬜ Not started |
| **6** | Module B upgrades: Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features | part of old 6 | ⬜ Not started |
| **7** | New model: 360-context xG + post-shot xG (xGOT) | **3** | ⬜ Not started |
| **8** | Product layer: lightweight Streamlit app — [spec done](PRODUCT_SPEC.md) 2026-07-01, minimal v1 built 2026-07-04 | **5** | 🟡 v1 built, deploy pending |
| **9** | Opportunistic: xA/chance-creation model, Module C (PUP), remaining alt-models (hierarchical, cosine, monotonic GBM), 2026 World Cup predictive model (data-availability check first) | old 6 + Module C | ⬜ Not started |

Execution order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, with 9 opportunistic. Full per-phase task
lists live in [ROADMAP.md](ROADMAP.md).

**Sequencing rationale (revised from the earlier "data expansion first" call):** the data manifest
is a prerequisite of the config-driven ingestion pipeline, `metrics.json` should exist before we
10× the data and the numbers, and the spine is the cheapest credibility badge that also
structurally kills the doc drift — so every later phase writes into a clean, single-source system.

---

## Log

- **2026-06-29** — Initiative kicked off. Code review (correctness/methodology/structure/scaling)
  written up; conceptual confusion about the framework's purpose resolved in `FRAMEWORK.md`
  (recruitment-led, two lenses: similarity = scouting/user-input, xG = valuation/no-input).
  Confirmed via web research that StatsBomb 360 freeze-frames are free for the Leverkusen 2023/24
  and EURO 2024 data already in use (Phase 3 fuel), and that Women's EURO 2025 (comp 53 / season
  315) is newly released with events + 360 (Phase 4 candidate). Phase 0 started.
- **2026-06-29** — Phases 0 and 1 completed in one session. Phase 0: `FRAMEWORK.md` charter +
  this tracker + CLAUDE.md roadmap entry. Phase 1: `src/config.py` (named `Dataset` constants),
  per-match pickle cache in `data_loader.py`, penalty-shootout (period 5) + null-location fixes in
  `features.py` (cached test set needs rebuilding to apply), `plot_shot_map` ax fix, pinned
  `requirements.txt` (+pyarrow/pytest), and `tests/` with 14 green unit tests (incl. a truthy-NaN
  assist regression test). Notebook 02 rewired to config. **Next: Phase 2 (ML rigor).**
- **2026-06-30** — Rebuilt the caches as Parquet through the fixed pipeline (notebook 02 executed
  end-to-end on the 3.10 interpreter via nbconvert). Penalty-shootout fix confirmed in the numbers:
  EURO 2024 test set 1,340 → 1,316 shots (24 shootout pens dropped), logistic test ROC-AUC
  0.798 → **0.765** (the old figure was inflated by trivially-rankable shootout penalties),
  calibration slightly better (Brier 0.067 → 0.065); README updated to match. Also fixed the IDE
  Jupyter kernel — it was defaulting to conda base (Python 3.9.12); filtered that interpreter out in
  `.vscode/settings.json` and normalized all three notebooks' kernelspec to the portable `python3`.
  pyarrow/pytest pinned. **Next: Phase 2 (ML rigor).**
- **2026-06-30** — Phase 2 **Module A (xG) rigor done** (notebook 02 + `src/models.py`): scaled
  logistic (continuous features standardised via `Pipeline`/`ColumnTransformer`; test ROC-AUC
  essentially unchanged at 0.765 — the win is convergence + comparable coefficients, e.g.
  `distance_to_goal` −0.10 → −0.84 per-SD), 5-fold cross-validation (in-distribution 0.783 ± 0.009;
  held-out EURO test sits at the bottom edge → a real ~1.7-pt league→tournament shift cost the single
  number hid), a baseline ladder (no-skill 0.500 → geometry-only 0.712 → full 0.765), and a
  calibrated GBM (isotonic barely moved Brier 0.0661 → 0.0659, still trails logistic — second honest
  non-win, "logistic stays" holds). New `models.py` helpers: `build_logistic_pipeline`,
  `get_coefficients`, `cross_validate_model`, `train_baseline_classifier`, `train_calibrated_gbm`.
  +5 unit tests (19 green). Notebook 02 re-executed clean end-to-end. **Module B (silhouette,
  minutes-weighted position) still pending — finishes Phase 2.**
- **2026-06-30** — Phase 2 **Module B (similarity) rigor done → Phase 2 complete.** Two additions
  to `src/similarity.py` + notebook 03. (1) **Silhouette score** (`compute_silhouette_scores`,
  `plot_silhouette_curve`): peaks at K=2 for all three position groups but at a *low* level
  (Defender 0.236 / Mid 0.264 / Fwd 0.262) — the low absolute value is the finding (play-styles
  within a position are a continuum, not crisp blobs), and K=4 is kept deliberately against the
  metric for archetype granularity, narrated honestly. (2) **Minutes-weighted position assignment**
  (`resolve_season_positions`): assigns the position *group* by total season minutes, not modal
  per-match position — reclassified 10 borderline winger/forward/midfield hybrids
  (Coutinho/Lingard/Mata/Sissoko/Firmino/Berahino/Schlupp/…); counts 118/104/78 → 119/106/75. It
  did *not* move Michail Antonio, which disproved the S6 "mostly a winger" premise (his minutes are
  920 RB/wing-back vs 761 wing vs 452 mid — genuinely a defender by minutes); he stays a one-man
  cluster as a true positional hybrid, which only multi-position/soft membership could resolve.
  +3 unit tests (22 green). Cached per-90 table rebuilt; notebook 03 re-executed clean end-to-end;
  new `outputs/similarity_silhouette_curves.png`. **Next: Phase 3 (360-context xG + xGOT).**
- **2026-07-02** — **Reprioritisation ("do it all, structured").** Folded the entire code-review
  backlog into one execution-ordered program and **renumbered Phases 3–6 → 3–9** (see the "Was"
  column). New Phase 3 = engineering & reproducibility spine (CI, `pipeline.py`, `metrics.json`
  single-source, data manifest), promoted ahead of data expansion because the manifest is a
  prerequisite of the ingestion pipeline and `metrics.json` must exist before the data/number 10×.
  Old Phase 3 (360 xG) → Phase 7; old Phase 5 (product build) → Phase 8; old Phase 6 + Module C →
  Phase 9 (opportunistic). Added Phase 5 (xG uncertainty + hierarchical finishing) and Phase 6
  (Module B upgrades: Mahalanobis, possession-adjust, GMM, creative features). **De-drift done in
  the same pass:** single canonical phase table now lives here only; ROADMAP links to it and holds
  the detailed task lists; the stale "all uncommitted" note in PROGRESS.md was corrected against git
  log. Planning/docs only — no `src/`, notebook, test, or data changes; 22 tests untouched.
  **Next: Phase 3 (engineering & reproducibility spine).**
- **2026-07-03** — **Phase 3 complete (3d: `pipeline.py` + Makefile).** New `src/pipeline.py`
  chains the already-tested `src/` functions into a headless, non-notebook rebuild — shot-table
  ingestion, per-90 similarity features, xG model training + all 4 Module A output PNGs, per-group
  clustering + all 4 Module B output PNGs, then `write_manifest`/`write_metrics` — runnable as
  `python -m src.pipeline` (`--force` to bypass the data/ caches, `--skip-plots` for a data-only
  run). A root `Makefile` thinly wraps it (`make pipeline`, `make pipeline-force`, `make test`);
  `python -m src.pipeline` remains the primary entry point since `make` isn't guaranteed on
  Windows. Ran end-to-end against the existing cached data: reproduced `metrics.json` and
  `data/manifest.json` byte-for-byte (both are deliberately deterministic — see Phase 3b/3e), the
  concrete proof the pipeline is a faithful twin of notebooks 02/03, not a rewrite. +5 unit tests
  (31 → 36 green), covering the one piece of real new logic (rebuild-vs-reuse cache decisions),
  network-free via monkeypatched builders. **Phase 3 (engineering & reproducibility spine) is now
  fully done. Next: Phase 4 (multi-competition ingestion + data expansion).**
- **2026-07-04** — **Phase 4 data pulled (24 datasets, ~43k new shots), not yet wired**, then
  **Phase 8 minimal build jumped ahead of strict order.** Reasoning: a friend demo (~2026-07-11)
  makes visible progress worth more than finishing Phase 4b/4c first, and a quick retraining
  smoke-test showed raw league volume barely moves xG's held-out ROC-AUC (0.765→0.766→0.768,
  smaller than the ±0.009 CV noise) — confirming the league→tournament shift is structural, not a
  data-volume problem, so pouring days into more training volume wasn't the highest-value next
  step anyway. New `src/app_data.py` build step (`python -m src.app_data`) precomputes three small
  Parquet artifacts (per-90 features + cluster labels, player xG table, shots+predicted-xG) scoped
  to Premier League 2015/16 — the one dataset with a full similarity + xG pool already built. New
  `app.py`: sidebar (position → player → radar-axis multiselect) driving a radar chart, "players
  like X" ranking, a finishing over/under panel with shot map, and an "under the hood" expander
  reading `metrics.json` directly plus a live per-group silhouette curve. Verified headless via
  Streamlit's `AppTest` harness across all 3 position groups, 8 players (incl. one with zero shots
  and one with an accented name), and the zero-radar-axes edge case — zero exceptions; not yet
  checked in an actual browser. Also +8 tests (41→59: schema-contract tests, domain sanity checks,
  a determinism check, real-data sanity checks, `find_similar_players` coverage) and a genuine
  sparse-column bug fix found by one of them. Full detail: [PROGRESS.md](PROGRESS.md).
  **Next: deploy Phase 8 to Streamlit Community Cloud (maintainer's own step), then decide Phase
  4b/4c scope.**

---

## How to resume

1. Read `CLAUDE.md` (project source of truth) and `docs/FRAMEWORK.md` (what the tool is for).
2. Check this table for the first ⬜ phase.
3. Open [ROADMAP.md](ROADMAP.md) for that phase's detailed task list.
4. Close the session by updating the Status column above, adding a Log entry, and following the
   standard CLAUDE.md session close-out (summary + suggested commit message + Progress Log).
