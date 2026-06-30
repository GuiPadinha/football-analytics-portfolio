# Initiative — Framework Hardening & Expansion

Tracks the multi-phase improvement work that follows the S1–S8 build. Mirrors the Progress Log
style in `CLAUDE.md`. The full plan and rationale live in the approved plan file; this is the
where-are-we tracker.

**Why this initiative exists:** a code review surfaced correctness, methodology, structure, and
scaling gaps, and the product story was unclear. Each phase below is independently executable in
its own session. Conceptual framing is settled in [FRAMEWORK.md](FRAMEWORK.md).

**Framing decisions (locked):** recruitment-led, both modules kept; product layer specified now and
built later; StatsBomb 360 on data we already pull is the headline new model.

---

## Phases

| Phase | Focus | Status |
|---|---|---|
| **0** | Framework charter (FRAMEWORK.md, this tracker, CLAUDE.md roadmap entry) | ✅ Done |
| **1** | Foundation: `config.py`, per-match cache, penalty/shootout fix, pinned deps, robustness fixes, first tests | ✅ Done |
| **2** | ML rigor: cross-validation, scaled logistic, baseline feature engineering, calibrated GBM, silhouette, minutes-weighted position | ✅ Done |
| **3** | New model: 360-context xG + post-shot xG (xGOT) | ⬜ Not started |
| **4** | More data + cross-league/season normalization | ⬜ Not started |
| **5** | Product layer: interface spec + lightweight Streamlit app | ⬜ Not started |
| **6** | Alternative models (GMM, hierarchical, cosine, monotonic GBM) — exploratory | ⬜ Not started |

Execution order: 0 → 1 → 2 → 3 → 4 → 5, with 6 opportunistic.

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

---

## How to resume

1. Read `CLAUDE.md` (project source of truth) and `docs/FRAMEWORK.md` (what the tool is for).
2. Check this table for the first ⬜ phase.
3. Open the plan file for that phase's detailed task list.
4. Close the session by updating the Status column above, adding a Log entry, and following the
   standard CLAUDE.md session close-out (summary + suggested commit message + Progress Log).
