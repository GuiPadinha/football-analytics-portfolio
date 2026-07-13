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
| **4** | Multi-competition ingestion + data expansion: config-driven pipeline, Module A generalization, Module B cross-league | 4 (reshaped) | 🟡 4a/4b/4d done, 4c mostly done 2026-07-09 (3/4 tournaments wired; Women's EURO 2025 still rate-limited, resumable, see log) |
| **5** | xG uncertainty + hierarchical/empirical-Bayes finishing model; header/foot interaction; calibration by stratum | *new* | ⬜ Not started |
| **6** | Module B upgrades: Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features | part of old 6 | ⬜ Not started |
| **7** | New model: 360-context xG + post-shot xG (xGOT) | **3** | ⬜ Not started |
| **8** | Product layer: lightweight Streamlit app — [spec done](PRODUCT_SPEC.md) 2026-07-01, minimal v1 built 2026-07-04 | **5** | ✅ Done — [live](https://gpfootball-analytics-portfolio.streamlit.app) (deployed 2026-07-09) |
| **9** | Opportunistic: xA/chance-creation model, Module C (PUP), remaining alt-models (hierarchical, cosine, monotonic GBM), 2026 World Cup predictive model (data-availability check first) | old 6 + Module C | ⬜ Not started |

Execution order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, with 9 opportunistic. Full per-phase task
lists live in [ROADMAP.md](ROADMAP.md).

**Sequencing rationale (revised from the earlier "data expansion first" call):** the data manifest
is a prerequisite of the config-driven ingestion pipeline, `metrics.json` should exist before we
10× the data and the numbers, and the spine is the cheapest credibility badge that also
structurally kills the doc drift — so every later phase writes into a clean, single-source system.

---

## Log

**This is a one-line-per-milestone index, not a second history** — full narrative detail for every
entry below (what changed, why, numbers, bugs found) lives dated the same in
[PROGRESS.md](PROGRESS.md) / [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md). Kept short deliberately
(trimmed 2026-07-13, previously ~150 lines duplicating that narrative) so this file stays the
"where-are-we" tracker its intro promises, not a file that has to be kept in sync with PROGRESS.md
by hand.

- **2026-06-29** — Initiative kicked off; `FRAMEWORK.md` charter written; Phase 0 started.
- **2026-06-29** — Phases 0 and 1 done (config/per-match cache/first tests foundation).
- **2026-06-30** — Caches rebuilt on the fixed pipeline; penalty-shootout fix confirmed in the
  numbers (test ROC-AUC 0.798 → 0.765).
- **2026-06-30** — Phase 2 Module A (xG) rigor done: scaled logistic, 5-fold CV, baseline ladder,
  calibrated GBM (still trails logistic).
- **2026-06-30** — Phase 2 Module B (similarity) rigor done → **Phase 2 complete**: silhouette
  score, minutes-weighted position assignment.
- **2026-07-02** — Reprioritisation: whole review backlog folded into this Phase 0–9 table (old
  Phase 3/360-xG → 7, old Phase 5/product → 8, old Phase 6 + Module C → 9).
- **2026-07-03** — **Phase 3 complete**: `pipeline.py` + Makefile, a headless reproducible rebuild.
- **2026-07-04** — Phase 4 data pulled (24 datasets), not yet wired; **Phase 8 minimal build
  jumped ahead** of strict phase order (demo-driven).
- **2026-07-05** — Phase 4b wired into the app (cross-league similarity pool, 1,511 players);
  goalkeeper features built, not yet wired; app UX/theme pass.
- **2026-07-09** — **Phase 4c mostly done**: Module A generalisation scored on 3 of 4 held-out
  tournaments (Women's EURO 2025 rate-limited, resumable).
- **2026-07-09 (cont.)** — **Phase 8 deployed** to Streamlit Community Cloud → **Phase 8 fully
  done**.
- **2026-07-13** — Pitch-prep app UX pass: a new "About & Roadmap" sidebar view, headline stats
  refactored to whole-number counts, the Phase 4c generalisation chart wired into the app for the
  first time.
- **2026-07-13 (cont. 3)** — Goalkeepers wired into the app (124 keepers, own feature set, not yet
  clustered); Leaderboard copy expanded.
- **2026-07-13 (cont. 4)** — Visual/brand pass: Leaderboard name/position filters, a proper Player
  explorer intro, a reusable page-header brand badge + richer sidebar, About & Roadmap expanded
  with "Data used"/"How each model works" sections and a Module C roadmap mention.

---

## How to resume

1. Read `CLAUDE.md` (project source of truth) and `docs/FRAMEWORK.md` (what the tool is for).
2. Check this table for the first ⬜ phase.
3. Open [ROADMAP.md](ROADMAP.md) for that phase's detailed task list.
4. Close the session by updating the Status column above, adding a Log entry, and following the
   standard CLAUDE.md session close-out (summary + suggested commit message + Progress Log).
