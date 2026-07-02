# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-02 — Phase 3 spine, Checkpoints A+B (CI + data manifest)

First code of the engineering & reproducibility spine.

**Checkpoint A — CI:** `.github/workflows/tests.yml` runs the suite on push/PR to main (Python 3.10 to match the pinned `requirements.txt`, `MPLBACKEND=Agg` so `visualisation.py`'s import-time matplotlib works headless). CI badge added to README (repo slug `GuiPadinha/football-analytics-portfolio`). Also cleared the 3a leftover: renumbered the two `src/config.py` comments that still called the 360 model "Phase 3" → Phase 7. *Push required for the badge to go live / first run to appear.*

**Checkpoint B — data manifest (3e):** new `src/manifest.py` + `tests/test_manifest.py`. `python -m src.manifest` writes `data/manifest.json` (tracked via a new `.gitignore` exception) pinning, per dataset, the sorted match-id set + a short set-hash + local cache coverage, plus content hashes of the two processed `shots_*.parquet` tables. Deliberately timestamp-free → pure function of the data, so only real drift diffs. Generated for real: **3 datasets, 465 matches pinned (380 PL 2015/16 + 51 EURO 2024 + 34 Leverkusen), all cached locally**; `statsbombpy 1.19.0` recorded. Feeds Phase 4's ingestion pipeline.

Tests **22 → 27 green** (+5 manifest tests, all network-free via an injected loader). Uncommitted.

Suggested commit: `Phase 3 (spine A+B): CI workflow + data provenance manifest; config Phase 3→7 comment fix`

**Remaining in Phase 3:** 3b (`metrics.json` single-source for key numbers) + 3d (`pipeline.py`/Makefile headless rebuild).

---

## 2026-07-02 — Reprioritisation + de-drift (planning only)

"Do it all, structured." Folded the whole code-review backlog into one execution-ordered program and **renumbered the initiative to Phases 0–9**. New **Phase 3 = engineering & reproducibility spine** (CI, `pipeline.py`, `metrics.json` single-source, data manifest) — promoted ahead of data expansion (Phase 4) because the manifest is a prerequisite of the ingestion pipeline and `metrics.json` must exist before we 10× the data/numbers. Old Phase 3 (360 xG) → **Phase 7**; old Phase 5 (Streamlit build) → **Phase 8**; old Phase 6 + Module C → **Phase 9** (opportunistic). Added **Phase 5** (xG uncertainty + hierarchical/empirical-Bayes finishing, header/foot interaction, calibration by stratum) and **Phase 6** (Module B: Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features).

**De-drift in the same pass:** the phase table now lives **only** in INITIATIVE.md (ROADMAP links to it + holds the detailed per-phase task lists); the stale "all uncommitted" note here was corrected against git log (Phases 0–2 + restructure + product spec are committed — `a3ff7cd`/`bbc4ac8`/`5e5aaef`/`4be7844`); CLAUDE.md Current Status + MODULES.md forward-pointers updated. Docs only — no `src/`, notebook, test, or data changes; 22 tests untouched. Uncommitted.

Suggested commit: `docs: fold review backlog into Phases 3–9 program; single-source phase table; fix stale uncommitted note`

---

## 2026-07-01 — Phase 5 product-layer spec expanded (no build)

Expanded the thin Phase 5 lead (one ASCII sketch in FRAMEWORK.md) into a full interface spec: new `docs/PRODUCT_SPEC.md`. Covers the one-screen design (two lenses — similarity/scouting + xG/valuation), interaction model (sidebar selectors + customizable radar-axis multiselect), a **component→backend reuse map** (every panel powered by an existing tested `src/` function — no new chart code), precomputed-Parquet data flow (`app_data/`, no live StatsBomb pulls), tech decision (**Streamlit** chosen; Dash + static-site rejected with reasons), out-of-scope list, a turnkey build checklist, and ASCII mockups. FRAMEWORK.md product stub now links the spec; INITIATIVE.md + ROADMAP.md Phase 5 marked 🟡 spec-done/build-pending. Docs only — no app code, no model change, 22 tests untouched. Uncommitted.

---

## 2026-07-01 — .md restructure

Restructured all .md docs into modular files (none >200 lines). Rewrote CLAUDE.md as lean index (~130 lines). Split ML_LEARNING_LOG.md into: itself (gotchas/decisions log, ~100 lines) + docs/ML_THEORY.md (textbook theory) + docs/ML_TOOLING.md (env gotchas). Created docs/CONTEXT.md (owner/learning goals/career), docs/DATA.md (data sources/cache index), docs/MODULES.md (Module A/B/C specs), docs/ROADMAP.md (session table + Phase 3 scope), docs/PROGRESS.md (this file), docs/PROGRESS_ARCHIVE.md (S1-S8 history). Added .claudeignore (excludes data/, outputs/, __pycache__, binary files). INITIATIVE.md and FRAMEWORK.md kept as-is (already ≤200 lines). Uncommitted.

---

## 2026-06-30 (cont.) — Phase 2 Module B (similarity rigor) complete → Phase 2 done

Two additions to `src/similarity.py` + notebook 03 + `visualisation.py`:

**Silhouette score** (`compute_silhouette_scores`, `plot_silhouette_curve`): peaked at K=2 for all three groups but at low absolute values (Defender 0.236 / Mid 0.264 / Fwd 0.262). Low value is the finding — play-styles within a position are a **continuum**, not crisp blobs. K=4 kept deliberately against the metric for archetype granularity, narrated honestly.

**Minutes-weighted position** (`resolve_season_positions`): assigns group by total season minutes, not modal match slot. Reclassified 10 borderline hybrids (Coutinho/Lingard/Mata/Sissoko Forward→Mid, Firmino/Berahino Mid→Forward, Schlupp Mid→Defender, …); counts 118/104/78 → 119/106/75. Did **not** move Michail Antonio — his real minutes are 920 RB/wing-back vs 761 wing, so the fix correctly keeps him a Defender. He's a true positional hybrid; no single-position rule can resolve that.

+3 tests (22 green). Per-90 cache rebuilt. Notebook 03 re-run clean. New `outputs/similarity_silhouette_curves.png`. Uncommitted.

---

## 2026-06-30 (cont.) — Phase 2 Module A (xG rigor) complete

Four rigor checks in `src/models.py` + notebook 02, all narrated:
1. **Scaled logistic** — Pipeline/ColumnTransformer; test ROC-AUC essentially unchanged (0.765) — the lesson is clean convergence + comparable coefficients (`distance_to_goal` −0.10 raw → −0.84 per-SD).
2. **5-fold CV** — 0.783 ± 0.009 in-distribution; EURO test (0.765) at bottom edge → real ~1.7-pt league→tournament cost.
3. **Baseline ladder** — no-skill 0.500 → geometry-only 0.712 → full 0.765. ~80% of discrimination is pure shot geometry.
4. **Calibrated GBM** (isotonic) — Brier 0.0661→0.0659, basically nothing; still trails logistic. "Logistic stays" survives a harder test.

New helpers: `build_logistic_pipeline`, `get_coefficients`, `cross_validate_model`, `train_baseline_classifier`, `train_calibrated_gbm`. +5 tests (19 green). Notebook 02 re-run clean. Uncommitted.

---

## 2026-06-30 — Parquet cache migration + kernel fix

Migrated notebook-02 shot caches to Parquet (flat tables are parquet-safe; raw per-match cache stays pickle). Rebuilt caches through the fixed pipeline — **penalty-shootout fix confirmed: EURO test 1,340→1,316 shots, test ROC-AUC 0.798→0.765** (honest number on in-game shots only). Updated README to 0.765. Fixed IDE Jupyter kernel (was defaulting to conda base Python 3.9.12): filtered via `.vscode/settings.json` `jupyter.kernels.filter`, normalized all three notebooks' kernelspec to portable `python3`. Uncommitted.

---

## 2026-06-29 (cont. 7) — Phase 0 + Phase 1 complete

Kicked off Framework Hardening initiative. **Phase 0:** `docs/FRAMEWORK.md` charter + `docs/INITIATIVE.md` tracker. **Phase 1:** `src/config.py` (named `Dataset` constants replacing magic id tuples); per-match pickle cache in `data_loader.py`; **correctness fix — penalty-shootout shots (period 5) dropped in `extract_shot_features`** (~75% conversion was inflating EURO test set); null-location guard; `plot_shot_map` ax fix. Pinned `requirements.txt` (+pyarrow, pytest). Added `tests/` with 14 green unit tests (incl. truthy-NaN assist regression test). Notebook 02 rewired to config constants. Uncommitted.

---

## Commit Status

Phases 0–2 + the .md restructure + the Phase 5 product spec are **committed** (verified against git
log 2026-07-02). Git via GitHub Desktop. Relevant commits:

- `a3ff7cd` — Initiative Phases 0–1: framework charter, foundation hardening, data-integrity rebuild
- `bbc4ac8` — Phase 2 (Module A): xG ML-rigor (scaled logistic, CV, baseline ladder, calibrated GBM)
- `5e5aaef` — Phase 2 Module B rigor: silhouette score + minutes-weighted positions
- `4be7844` — Phase 5 (old numbering): expand product-layer interface spec + mockups (docs only)

Working tree is otherwise clean. The 2026-07-02 planning/reprioritisation edits (this restructure)
are the only uncommitted docs — suggested commit below in that day's entry.
