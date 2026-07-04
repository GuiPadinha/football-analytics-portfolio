# Progress Log — Historical (S1–S8)

Sessions from 2026-06-28 through 2026-06-29. Committed work only.
→ Recent sessions: [PROGRESS.md](PROGRESS.md)

---

## 2026-06-28 — Dev environment setup

Fixed `python`/`pip` not recognized: added Python 3.10.7 (`C:\Users\guilh\AppData\Local\Programs\Python\Python310\` + its `Scripts\`) to User PATH; pinned as workspace interpreter in `.vscode/settings.json`. Fixed `CERTIFICATE_VERIFY_FAILED` from Avast intercepting HTTPS — appended Avast root cert to both `certifi` cacert.pem files. `pip install -r requirements.txt` now succeeds (new terminals only — already-open terminals won't pick up PATH change). S1 scaffold partially done (folders, `.gitignore`, `requirements.txt`, `src/data_loader.py` + module stubs) — notebook 01 still pending.

---

## 2026-06-29 — S1 + S2 + S3

**S1:** Notebook 01 ran clean; bonus mplsoccer shot map (all outcomes Goal/Saved/Blocked/Off T/Wayward explicitly coloured).

**S2** (`src/features.py`): distance/angle computed from goalpost geometry (StatsBomb pitch, posts at y=36/44); assist type derived by joining `shot_key_pass_id` to source pass event. Hit real bug: `pass_cross`/`pass_through_ball`/`pass_cut_back` hold `True`/`NaN` — `bool(NaN)` is `True` in Python, so ~72% of assists misclassified as crosses; fixed with explicit `is True` checks.

**S3** (`src/models.py`, `src/visualisation.py`, notebook 02): logistic regression on Leverkusen 2023/24 + PL 2015/16 (10,824 shots, 10.1% conversion), tested on EURO 2024 (1,340 shots) — ROC-AUC 0.786 train / 0.798 test. Cached to `data/shots_*.pkl`. Flagged `assist_type` dummy-variable collinearity for S4. Nothing committed yet.

---

## 2026-06-29 (cont.) — S4

Fixed assist-type collinearity (drop "None" as reference category). Added `train_gradient_boosting()`: tuning sweep; even tuned, GBM (train 0.796/test 0.793) didn't beat logistic (0.786/0.798) — **logistic stays as recommended model**. Added `get_feature_importance()`, `build_player_xg_table()`, `plot_player_xg_ranking()`. Rebuilt cache with `competition_id` column to isolate PL 2015/16 from Leverkusen for the era-benchmark ranking. PL 2015/16 ranking passes sniff test: Agüero/Mahrez/Kane top overperformers, Mitrović/Bony/Jerome top underperformers. Added Learning Goals section to CLAUDE.md. S1–S4 committed.

---

## 2026-06-29 (cont.) — S5

`src/similarity.py`: minutes from StatsBomb `lineups` endpoint (more reliable than reconstructing from Starting XI + Substitution events — `lineups` tracks Tactical Shift position changes directly). Built per-90 event metrics for PL 2015/16 — 300 players at 900-min floor (118 Def / 104 Mid / 78 Fwd; GKs excluded). Hit sparse-column gotcha: `pass_goal_assist` missing from matches with zero assists — fixed with `_safe_bool_column`/`_safe_column` helpers. SkillCorner physical metrics derived from frame-to-frame position deltas; `min_observed_minutes=30` caps extrapolation at 3×. Confirmed zero player overlap between StatsBomb and SkillCorner datasets. Cached `data/player_per90_pl_2015_16.pkl`. S5 committed separately.

---

## 2026-06-29 (cont.) — S6

Added clustering to `similarity.py` and plotting to `visualisation.py`. Key design: **clustering per position group** (not across all outfield players — would just rediscover position). K=4 per group. Results: midfielder cluster Kanté/M'Vila/Gueye/Drinkwater (ball-winning destroyer, anchored by Kanté's title-winning Leicester season); Özil/Fàbregas/Lallana (creative playmaker, Özil's record-assist season); defender cluster Cresswell/Daniels/Bellerín/van Aanholt (overlapping full-backs). One-man defender cluster: Michail Antonio with absurd z-scores (+5.95 goals/90) — documented as labelling limitation, not a clustering bug. Notebook 03 runs clean.

---

## 2026-06-29 (cont.) — S7 + S8

**S7:** `find_similar_players()` — Euclidean distance in standardised space, within position group (continuous ranking, not just cluster membership). `plot_player_radar()` — mplsoccer Radar, axes at 5th-95th percentile. Hit StatsBomb quirk: Kanté stored as `N''Golo Kanté` (doubled apostrophe). Hit mplsoccer gotcha: `Radar.setup_axis` expects plain rectangular `Axes`, not polar (see `docs/ML_TOOLING.md`). Validated: Kanté → Gueye/Tioté/Coquelin/Fernando; Cresswell → Brunt/Davies/Sagna/Bertrand/Daniels; Kane → Vardy/Carroll/Ighalo/Defoe/Agüero. Added Theoretical Concepts Reference and Module C/PUP spec to ML_LEARNING_LOG.md.

**S8:** Replaced placeholder README.md with full project narrative — module framing, honest numbers, embedded PNGs, honest caveats (GBM non-win, Antonio cluster). S6/7/8 committed and pushed ("S6/7 - Radar charts + visuals + final polish + README"). All S1–S8 pushed.

---

## 2026-06-29 (cont. 7) — Phase 0 + Phase 1 complete

Kicked off Framework Hardening initiative. **Phase 0:** `docs/FRAMEWORK.md` charter + `docs/INITIATIVE.md` tracker. **Phase 1:** `src/config.py` (named `Dataset` constants replacing magic id tuples); per-match pickle cache in `data_loader.py`; **correctness fix — penalty-shootout shots (period 5) dropped in `extract_shot_features`** (~75% conversion was inflating EURO test set); null-location guard; `plot_shot_map` ax fix. Pinned `requirements.txt` (+pyarrow, pytest). Added `tests/` with 14 green unit tests (incl. truthy-NaN assist regression test). Notebook 02 rewired to config constants. Committed (`a3ff7cd`).

---

## 2026-06-30 — Parquet cache migration + kernel fix

Migrated notebook-02 shot caches to Parquet (flat tables are parquet-safe; raw per-match cache stays pickle). Rebuilt caches through the fixed pipeline — **penalty-shootout fix confirmed: EURO test 1,340→1,316 shots, test ROC-AUC 0.798→0.765** (honest number on in-game shots only). Updated README to 0.765. Fixed IDE Jupyter kernel (was defaulting to conda base Python 3.9.12): filtered via `.vscode/settings.json` `jupyter.kernels.filter`, normalized all three notebooks' kernelspec to portable `python3`.

---

## 2026-06-30 (cont.) — Phase 2 Module A (xG rigor) complete

Four rigor checks in `src/models.py` + notebook 02, all narrated:
1. **Scaled logistic** — Pipeline/ColumnTransformer; test ROC-AUC essentially unchanged (0.765) — the lesson is clean convergence + comparable coefficients (`distance_to_goal` −0.10 raw → −0.84 per-SD).
2. **5-fold CV** — 0.783 ± 0.009 in-distribution; EURO test (0.765) at bottom edge → real ~1.7-pt league→tournament cost.
3. **Baseline ladder** — no-skill 0.500 → geometry-only 0.712 → full 0.765. ~80% of discrimination is pure shot geometry.
4. **Calibrated GBM** (isotonic) — Brier 0.0661→0.0659, basically nothing; still trails logistic. "Logistic stays" survives a harder test.

New helpers: `build_logistic_pipeline`, `get_coefficients`, `cross_validate_model`, `train_baseline_classifier`, `train_calibrated_gbm`. +5 tests (19 green). Notebook 02 re-run clean. Committed (`bbc4ac8`).

---

## 2026-06-30 (cont.) — Phase 2 Module B (similarity rigor) complete → Phase 2 done

Two additions to `src/similarity.py` + notebook 03 + `visualisation.py`:

**Silhouette score** (`compute_silhouette_scores`, `plot_silhouette_curve`): peaked at K=2 for all three groups but at low absolute values (Defender 0.236 / Mid 0.264 / Fwd 0.262). Low value is the finding — play-styles within a position are a **continuum**, not crisp blobs. K=4 kept deliberately against the metric for archetype granularity, narrated honestly.

**Minutes-weighted position** (`resolve_season_positions`): assigns group by total season minutes, not modal match slot. Reclassified 10 borderline hybrids (Coutinho/Lingard/Mata/Sissoko Forward→Mid, Firmino/Berahino Mid→Forward, Schlupp Mid→Defender, …); counts 118/104/78 → 119/106/75. Did **not** move Michail Antonio — his real minutes are 920 RB/wing-back vs 761 wing, so the fix correctly keeps him a Defender. He's a true positional hybrid; no single-position rule can resolve that.

+3 tests (22 green). Per-90 cache rebuilt. Notebook 03 re-run clean. New `outputs/similarity_silhouette_curves.png`. Committed (`5e5aaef`).

---

## 2026-07-01 — .md restructure

Restructured all .md docs into modular files (none >200 lines). Rewrote CLAUDE.md as lean index (~130 lines). Split ML_LEARNING_LOG.md into: itself (gotchas/decisions log, ~100 lines) + docs/ML_THEORY.md (textbook theory) + docs/ML_TOOLING.md (env gotchas). Created docs/CONTEXT.md (owner/learning goals/career), docs/DATA.md (data sources/cache index), docs/MODULES.md (Module A/B/C specs), docs/ROADMAP.md (session table + Phase 3 scope), docs/PROGRESS.md (this file's parent), docs/PROGRESS_ARCHIVE.md (S1-S8 history). Added .claudeignore (excludes data/, outputs/, __pycache__, binary files). INITIATIVE.md and FRAMEWORK.md kept as-is (already ≤200 lines).

---

## 2026-07-01 — Phase 5 product-layer spec expanded (no build)

Expanded the thin Phase 5 lead (one ASCII sketch in FRAMEWORK.md) into a full interface spec: new `docs/PRODUCT_SPEC.md`. Covers the one-screen design (two lenses — similarity/scouting + xG/valuation), interaction model (sidebar selectors + customizable radar-axis multiselect), a **component→backend reuse map** (every panel powered by an existing tested `src/` function — no new chart code), precomputed-Parquet data flow (`app_data/`, no live StatsBomb pulls), tech decision (**Streamlit** chosen; Dash + static-site rejected with reasons), out-of-scope list, a turnkey build checklist, and ASCII mockups. FRAMEWORK.md product stub now links the spec; INITIATIVE.md + ROADMAP.md Phase 5 marked 🟡 spec-done/build-pending. Docs only — no app code, no model change, 22 tests untouched. Committed (`4be7844`).

---

## 2026-07-02 — Reprioritisation + de-drift (planning only)

"Do it all, structured." Folded the whole code-review backlog into one execution-ordered program and **renumbered the initiative to Phases 0–9**. New **Phase 3 = engineering & reproducibility spine** (CI, `pipeline.py`, `metrics.json` single-source, data manifest) — promoted ahead of data expansion (Phase 4) because the manifest is a prerequisite of the ingestion pipeline and `metrics.json` must exist before we 10× the data/numbers. Old Phase 3 (360 xG) → **Phase 7**; old Phase 5 (Streamlit build) → **Phase 8**; old Phase 6 + Module C → **Phase 9** (opportunistic). Added **Phase 5** (xG uncertainty + hierarchical/empirical-Bayes finishing, header/foot interaction, calibration by stratum) and **Phase 6** (Module B: Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features).

**De-drift in the same pass:** the phase table now lives **only** in INITIATIVE.md (ROADMAP links to it + holds the detailed per-phase task lists); the stale "all uncommitted" note here was corrected against git log (Phases 0–2 + restructure + product spec are committed — `a3ff7cd`/`bbc4ac8`/`5e5aaef`/`4be7844`); CLAUDE.md Current Status + MODULES.md forward-pointers updated. Docs only — no `src/`, notebook, test, or data changes; 22 tests untouched. Committed (`e862a59`).
