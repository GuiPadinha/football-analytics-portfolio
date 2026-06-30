# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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

## Uncommitted Work Summary

Phase 0+1+2 hardening + 2026-07-01 .md restructure — all uncommitted. Git via GitHub Desktop.

Suggested commit: `Phase 1+2 hardening: config, cache, penalty fix, tests, ML rigor (scaled logistic, CV, calibration, silhouette, minutes-weighted positions) + docs restructure`
