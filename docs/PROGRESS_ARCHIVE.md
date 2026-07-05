# Progress Log — Historical (S1–S8, Phase 0–3)

Sessions from 2026-06-28 through 2026-07-05. Committed work only.
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

---

## 2026-07-02 — Phase 3 spine, Checkpoints A+B (CI + data manifest)

First code of the engineering & reproducibility spine.

**Checkpoint A — CI:** `.github/workflows/tests.yml` runs the suite on push/PR to main (Python 3.10 to match the pinned `requirements.txt`, `MPLBACKEND=Agg` so `visualisation.py`'s import-time matplotlib works headless). CI badge added to README (repo slug `GuiPadinha/football-analytics-portfolio`). Also cleared the 3a leftover: renumbered the two `src/config.py` comments that still called the 360 model "Phase 3" → Phase 7. *Push required for the badge to go live / first run to appear.*

**Checkpoint B — data manifest (3e):** new `src/manifest.py` + `tests/test_manifest.py`. `python -m src.manifest` writes `data/manifest.json` (tracked via a new `.gitignore` exception) pinning, per dataset, the sorted match-id set + a short set-hash + local cache coverage, plus content hashes of the two processed `shots_*.parquet` tables. Deliberately timestamp-free → pure function of the data, so only real drift diffs. Generated for real: **3 datasets, 465 matches pinned (380 PL 2015/16 + 51 EURO 2024 + 34 Leverkusen), all cached locally**; `statsbombpy 1.19.0` recorded. Feeds Phase 4's ingestion pipeline.

Tests **22 → 27 green** (+5 manifest tests, all network-free via an injected loader). Committed (`6a1876c`).

**Remaining in Phase 3 (at the time):** 3b (`metrics.json` single-source for key numbers) + 3d (`pipeline.py`/Makefile headless rebuild).

---

## 2026-07-02 — Phase 3 spine, Checkpoint C (3b: metrics.json single source)

Closed the drift vector the whole reprioritisation was about: headline numbers were hand-typed into four docs and had already drifted once (the 0.798→0.765 penalty-fix took four edits to chase).

**New `src/metrics.py`** computes them from the same code/data the models use — xG train/test ROC-AUC + Brier, in-distribution CV mean±std, the no-skill→geometry→full baseline ladder, per-group silhouette peaks, and shot counts — and `python -m src.metrics` writes the committed **`metrics.json`** (repo root, outside gitignored `data/`; deterministic + timestamp-free like the manifest). Split into pure compute (`compute_xg_metrics` / `compute_similarity_metrics` / `build_metrics`, tested on synthetic frames) and an IO wrapper (`write_metrics`) so the unit tests stay offline. **Every emitted value matched the docs on the first run** (0.765 / 0.786 / 0.783±0.009 / 0.5→0.712→0.765 / silhouette 0.236·0.264·0.262 at K=2 / 10,824 · 1,316) — the docs were honest, they just weren't *enforced*.

**Doc-lint** (`tests/test_metrics.py::test_current_state_docs_match_metrics_json`): fails the build if a *current-state* doc (README/CLAUDE/MODULES/DATA) prints a number that differs from `metrics.json`. Append-only history (PROGRESS, INITIATIVE log entries, ML_LEARNING_LOG, the archive) is deliberately exempt — an old dated entry may keep the 0.798 it reported then. Deferred the test-count number (a repo fact, not a model output). Docs now *reference* the file: README callout under the results table, CLAUDE.md key-numbers note, ROADMAP 3b marked done.

Tests **27 → 31 green** (+3 pure-compute, +1 doc-lint). Committed (`102a134`).

**Remaining in Phase 3 (at the time):** 3d (`pipeline.py`/Makefile headless rebuild).

---

## 2026-07-03 — Phase 3 spine, Checkpoint D (3d: pipeline.py + Makefile) → Phase 3 complete

Closed the last Phase 3 checkpoint. New **`src/pipeline.py`** chains the already-tested `src/` functions into a headless, non-notebook rebuild — mirrors notebooks 02/03 exactly rather than reimplementing them: build/reload the xG shot tables and the per-90 similarity table (skip the raw StatsBomb pull when the `data/` cache already exists, same `REBUILD` logic the notebooks use), train the logistic + GBM models and write all 4 Module A output PNGs, cluster each position group (K=4, matching the Phase 2 silhouette call) and write all 4 Module B output PNGs, then call `write_manifest()`/`write_metrics()` last (order matters — metrics.json reads the tables the earlier steps just built). Runnable as `python -m src.pipeline`, with `--force` (bypass caches, re-pull raw data) and `--skip-plots` (data + manifest/metrics only) flags.

A thin root **`Makefile`** wraps it (`make pipeline`, `make pipeline-force`, `make test`) for anyone with `make` on their PATH — confirmed it isn't on this Windows machine (checked both PowerShell and Git Bash), so `python -m src.pipeline` stays the primary, always-works entry point; the Makefile is a convenience for CI/WSL/Linux contributors, not a requirement.

**Verified for real, not just unit-tested:** ran `python -m src.pipeline` end-to-end against the existing local `data/` cache (no `--force`, so no fresh network pull) — reproduced `metrics.json` and `data/manifest.json` **byte-for-byte** (`git status` showed no diff on either), which is the concrete proof the pipeline is a faithful non-interactive twin of the notebooks rather than a rewrite that happens to look similar. All 8 output PNGs regenerated cleanly.

+5 unit tests (`tests/test_pipeline.py`) — the one piece of genuinely new logic (rebuild-vs-reuse cache decisions in `build_shot_tables`/`build_similarity_table`), tested network-free via monkeypatched builders, same pattern as `test_manifest.py`. Tests **31 → 36 green**. Committed as part of `ce45e74` (bundled with `ARCHITECTURE.md` + docs cleanup in that session's single commit).

**Phase 3 (engineering & reproducibility spine) is now fully done. Next: Phase 4 (multi-competition ingestion + data expansion).**

---

## 2026-07-04 — docs pass: git policy, ARCHITECTURE.md, SofaScore/FlashScore note

Guilherme is showing the repo to a friend and flagged two things: wanted the git-CLI-forbidden rule
relaxed (he'd only used GitHub Desktop because he thought I couldn't run git; I can), and wanted
more infra-level documentation of how `src/` actually fits together.

**Git policy relaxed:** CLAUDE.md's Session Workflow no longer says GitHub-Desktop-only; `git
status`/`log`/`diff`/`add`/`commit` are fine to run directly (still: only commit when asked, no
force-push, prefer new commits over amends — the normal global caution, not a project-specific one).

**New `docs/ARCHITECTURE.md`:** the module dependency graph CLAUDE.md's one-line-per-file layout
never had. Built from the actual `grep "from src"` import graph, not guessed — two things stood
out enough to call out explicitly: `models.py`/`visualisation.py` import nothing from `src/`
(dataset-agnostic, work for whatever DataFrame a caller hands them), and `features.py`/
`similarity.py` don't import `config.py` either (they take ids/`Dataset` objects as parameters —
only `manifest.py`/`metrics.py`/`pipeline.py` pin down *which* competitions via `config.py`
defaults). Also documents the DataFrame-schema contracts an import graph can't show (e.g.
`models.build_feature_matrix` hard-assumes column names `features.py` produces, with no shared
type checking it) and the pure-compute/IO-wrapper split `manifest.py`/`metrics.py` both use (why
the test suite stays offline). Cross-linked from CLAUDE.md's docs list; closes the Phase 9
backlog item flagged earlier the same day.

**DATA.md gap closed** (found while verifying doc consistency at Guilherme's request): the two
committed provenance/metrics files (`metrics.json`, `data/manifest.json`) were never documented
there — added a short table. Also added a **candidate alternative data source** note: SofaScore/
FlashScore match-info as a fallback if Phase 4's StatsBomb availability friction bites — with the
honest caveat that it's match-level/box-score data (no per-shot x/y), so it can't replace StatsBomb
for Module A, but could supply the external match-importance/standings labels Module C (PUP) has
been blocked on since it was scoped. Cross-linked from ROADMAP Phase 4d and MODULES.md's PUP spec.

Docs only — no `src/`, notebook, test, or data changes; 36 tests untouched. Committed as part of
`ce45e74`.

---

## 2026-07-04 (cont.) — doc-style cleanup: concept headers over narrative, paragraphs over crammed bullets

Guilherme flagged a recurring style issue across the docs: section headers written as narrative/
rhetorical framing ("Why this exists", "Who it's for") instead of direct concept labels, and bullet
points in PRODUCT_SPEC.md/ARCHITECTURE.md that were really 2+ sentences of connected reasoning
squeezed into one bullet rather than written as prose. Confirmed scope and direction with him first
(3 quick questions) rather than guessing across ~10 files: fix applies to all conceptual docs except
README (deliberately pitch-styled per CONTEXT.md's portfolio-framing policy); dated log entries in
PROGRESS/PROGRESS_ARCHIVE/ML_LEARNING_LOG get a soft touch only, keeping their day-to-day detail;
headers should stay short *phrases*, not compressed to single words that lose the "how/why" framing
(e.g. "How the Modules Combine", not "Module Interaction").

**FRAMEWORK.md** and **PRODUCT_SPEC.md** got the heaviest rewrite: renamed headers ("Why this
exists" → "Purpose", "Who it's for" → "Audience", "The one screen" → "Screen Layout", "Explicitly
NOT in scope (so we stop wondering)" → "Out of Scope", etc.) and trimmed conversational asides in
the intro prose ("This is the part where the user inputs something..." → a direct statement of what
the input is). Structured spec-sheet bullets (Input/What happens/Output/Decision-it-informs) were
left as bullets — that's parallel-field structure, not the narrative-bullet problem.

**ARCHITECTURE.md**: converted the "Implicit contracts" bullet pair (each one really 2-3 sentences
of connected reasoning about one schema dependency) into two prose paragraphs, per the fix
previewed and approved before the rewrite. Renamed a few headers to drop rhetorical parentheticals
("Import graph (who actually imports whom)" → "Import Graph") and standardised header capitalisation
across the file.

**CONTEXT.md, MODULES.md, DATA.md, ROADMAP.md, CLAUDE.md**: reviewed, no changes needed — already
concept-first with appropriately short/parallel bullets, not the flagged pattern.

**INITIATIVE.md**: two inline bold lead-ins echoed the same narrative-question pattern at
paragraph level ("**Why this initiative exists:**", "**Why the spine goes first (over the earlier
...)**") — reworded to "**Origin:**" and "**Sequencing rationale:**". Its dated "Log" section is
left alone, same reasoning as PROGRESS.md.

**PROGRESS.md / PROGRESS_ARCHIVE.md / ML_LEARNING_LOG.md**: reviewed under the "soft touch, keep
day-to-day detail" instruction — headers are already dated/factual (not the rhetorical-question
pattern) and bullets are one-gotcha-per-item, not multi-idea crams, so left unchanged rather than
edited for the sake of it.

Verified no stale cross-references after the header renames (grepped for every renamed heading's
old text and the one line-number anchor link that pointed into FRAMEWORK.md); full suite re-run,
36/36 still green, doc-lint untouched since none of the changed prose overlaps a `metrics.json`-
checked number. Docs only. Committed as part of `ce45e74`.

---

## 2026-07-04 (cont.) — quick experiment: does more league volume help xG generalisation? + obstacle-doc gaps closed

Guilherme asked three things before signing off: what obstacles this session hit and whether they're
documented, whether there's any evidence yet that the Phase 4 data actually helps the model, and
whether the non-shooting event data (passing, positioning, tackling) is being used anywhere.

**Obstacle docs:** most of the session's real obstacles were already logged (sparse-column crash →
ML_LEARNING_LOG.md/ARCHITECTURE.md; La Liga-is-mostly-Barcelona → DATA.md). Three weren't: Git Bash's
lack of network egress (PowerShell has it), a background pull's stdout-redirect hiding output from the
harness's own tracker, and the Serie A 2015/16 `IncompleteRead` transient pull failure. All three added
to ML_TOOLING.md, plus a "How to use this file" footer and a CLAUDE.md end-of-session checklist line
so this gets logged as it happens, not retrospectively.

**Non-shooting data:** Module B already uses it (`ACTION_COLUMNS` in `similarity.py` — key passes,
progressive passes, dribbles, pressures, interceptions, tackles — per-90 for player similarity).
xA/chance-creation (passing) and 360-context xG (positioning) are already scoped, unstarted backlog
items (Phase 9 / Phase 7). Flagged one new idea not yet on the roadmap: a possession-value
(VAEP/xT-style) model that scores every event, not just shots/completed passes — the real answer to
"value a tackle," a bigger lift than xA, Phase 9+ candidate.

**Quick retraining experiment** (scratch script, not committed — `phase4_train_expansion_experiment.py`):
same logistic pipeline, same untouched EURO 2024 test set, three training sets built from already-cached
Phase 4 data. Result:

| Training set | Shots | Test ROC-AUC | Test Brier |
|---|---|---|---|
| Baseline (Leverkusen+PL 2015/16) | 10,824 | 0.7654 | 0.0651 |
| + La Liga/Serie A/Ligue 1 2015/16 | 38,804 | 0.7662 | 0.0656 |
| + all 16 Barcelona seasons too | 50,789 | 0.7678 | 0.0659 |

Test ROC-AUC creeps up ~0.1–0.2 points per data addition — smaller than the ±0.009 fold-to-fold noise
the Phase 2 CV already measured, so not distinguishable from noise. Test Brier gets marginally *worse*
each time even as train ROC-AUC rises more (0.786→0.804→0.803): the added shots fit the training
distribution better without transferring to the out-of-distribution tournament test. Reads as
confirmation, not contradiction, of the earlier CV finding — the league→tournament shift is
structural, not a sample-size problem, so raw volume alone won't close it. Caveat: naive pooling, no
cross-league normalisation — Phase 4b's real version needs that before this is a final verdict; this
was a smoke test to answer "does it help at all," not the production wiring decision.

Docs only (`ML_TOOLING.md`, `CLAUDE.md` end-of-session checklist) + this log entry — the experiment
script itself is scratch, not part of the repo. 41 tests untouched. Also added to
[ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md)'s Module A gotcha list. Committed as part of `0d4d2fe`.

---

## 2026-07-04 (cont.) — +10 tests (model input/output/functioning validation) + Module A→B→C ordering pass

Guilherme asked for tests validating the models more directly (input/output/functioning/features,
beyond the existing unit tests), and to standardise on telling the module story as A→B→C everywhere
(narration and docs), reserving a lead-with-B exception for contexts where it genuinely reads better
(e.g. the recruitment walkthrough in FRAMEWORK.md, left as B→A since that's the real workflow order).

**New `tests/test_contracts.py`** (3 tests): pins the schema contracts `ARCHITECTURE.md` describes
but nothing previously enforced — `extract_shot_features`'s output covers every column
`build_feature_matrix` needs, `ASSIST_TYPES` covers every category `_classify_assist` can produce,
and `PER90_FEATURE_COLUMNS` stays a pure function of `ACTION_COLUMNS` rather than a second
hand-maintained list.

**Domain sanity checks** (`test_models.py`, +3): a closer shot must get higher predicted xG than a
farther one, a penalty must get higher predicted xG than an otherwise-identical open-play shot, and
`build_player_xg_table` aggregates shots/goals/xg_diff correctly — invariants a metric like ROC-AUC
can't directly guarantee (a model can rank well on average while getting an individual comparison
backwards).

**Coverage gaps closed:** `game_state_score_diff` reflects the score *before* a shot's own goal is
credited, not after (`test_features.py`, +1) — a subtlety the docstring already explained but nothing
tested; `find_similar_players` excludes the queried player, restricts to their position group, respects
`n`, and raises on an unknown player (`test_similarity.py`, +3) — previously zero coverage on the
function that actually powers the "players like X" lookup.

Tests **41 → 51 green**. CLAUDE.md's two test-count mentions updated to match (not doc-lint-enforced —
a repo fact, not a model output — but kept accurate manually).

**Ordering pass:** swapped `docs/FRAMEWORK.md`'s Target User table + Module B/A section order (was
B-then-A) to A-then-B; swapped `ML_LEARNING_LOG.md`'s section order (was A, C, B) to A, B, C;
reordered one Phase 4 table cell and one Phase 4 prose sentence in `INITIATIVE.md`/`ROADMAP.md` that
listed Module B before Module A. Left the FRAMEWORK.md recruitment walkthrough's B-then-A story order
alone — finding similar players before checking their xG is the actual workflow sequence, not a
labelling inconsistency.

Docs + tests only — no `src/` changes; suite re-run clean after every edit. Committed as part of
`1c8d90d`.

---

## 2026-07-04 (cont.) — +8 more tests (determinism, zero-shot edge case, real-data sanity checks) + a real bug fix

Followed up on the parked test ideas from the previous entry.

**New `tests/test_data_sanity.py`** (6 tests, parametrized over `shots_train.parquet`/
`shots_test.parquet`): the one deliberate exception to "network-free, synthetic data only" — reads
the real cached shot tables and checks geometry stays within pitch bounds, no missing values in any
model-input feature column, and goal rate stays in a wide plausible band. Skips cleanly (not fails)
wherever `data/` isn't present, e.g. CI or a fresh clone.

**Determinism test** (`test_models.py`, +1): fitting the logistic pipeline twice on identical data
must give identical coefficients — guards against a future stochastic-solver swap silently breaking
reproducibility.

**Zero-shot-match edge case** (`test_features.py`, +1) **found a real bug**: `extract_shot_features`
crashed on a synthetic match with zero Shot events, because `shot_body_part`/`shot_type`/
`shot_outcome`/`shot_key_pass_id` were still bare column accesses — the same sparse-column crash
shape as the Barcelona 2020/21 fix, one level sparser (missing because the match has no shots at
all, not just a missing flag on an existing shot). Fixed by routing all four through the existing
`safe_column` helper. Not yet hit by real data (StatsBomb matches essentially always have ≥1 shot),
but worth fixing now that ~2,400 Phase 4 matches make it not-quite-negligible, and the edge-case test
found it before production data did.

Tests **51 → 59 green**; CLAUDE.md's two test-count mentions updated. Logged in
[ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md). `src/features.py` changed (the fix); everything else
docs/tests only. Committed as part of `1c8d90d`.

---

## 2026-07-04 (cont.) — Phase 8 minimal build: app.py + app_data.py, jumped ahead of strict phase order

Agreed plan going into this: prioritise a minimal Streamlit build for the ~2026-07-11 friend demo
over finishing Phase 4b/4c first, since the demo needs "something clickable" and the earlier
smoke-test showed more league volume wasn't the highest-value next step anyway.

**New `src/app_data.py`** (`python -m src.app_data`): the offline build step — writes three small
Parquet artifacts to `app_data/` (committed, ~520KB total, no Git LFS needed): `player_per90.parquet`
(per-90 features + a K=4 style-archetype `cluster` label per position group), `player_xg_table.parquet`
(`build_player_xg_table` output), `shots_with_xg.parquet` (shots + predicted xG for the shot map).
Scoped to Premier League 2015/16 (`config.SIMILARITY_SET`) — the one dataset with a full similarity
*and* xG pool already computed; the spec's multi-competition sidebar pickers are a later pass, not v1.

**New `app.py`**: sidebar (position group → player → radar-axis multiselect) drives a radar chart,
a "players like X" ranking (`find_similar_players`), a finishing over/under panel (goals/xG/diff +
shot map), and an "under the hood" expander — reads `metrics.json` directly for headline numbers
plus a live (`st.cache_data`-cached) per-group silhouette curve, skipping a fourth precomputed
artifact just for the methodology plots. `.streamlit/config.toml` themes it (accent colour matches
the radar chart's own blue). `streamlit==1.58.0` pinned in `requirements.txt`.

**Verification, and its limits:** no browser tool available in this session, so verified headless via
Streamlit's own `AppTest` harness (`streamlit.testing.v1`) instead of skipping verification — ran the
full script for all 3 position groups, 8 different players (including one with zero logged shots, to
exercise the "no shot data" info branch, and one with an accented name, "Aleksandar Mitrović"), and the
zero-radar-axes edge case; zero exceptions across every combination. **This confirms script-level
correctness, not visual correctness** — the actual rendering hasn't been eyeballed in a browser yet;
say so plainly rather than claim more than was checked. `streamlit run app.py` locally is the
remaining step before trusting the visual layout.

Tests unaffected (59 green, unrelated to app.py/app_data.py). Docs updated: PRODUCT_SPEC.md's Build
Checklist (mostly checked off — deploy is the one step left, needs Guilherme's own Streamlit Cloud
account), ROADMAP.md/INITIATIVE.md's Phase 8 status, CLAUDE.md's Current Status + Repository Layout.
Archived the two oldest same-day entries below (docs pass, doc-style cleanup — already committed via
`ce45e74`) into PROGRESS_ARCHIVE.md, since this file was well past the 150-line threshold.

**Next: deploy to Streamlit Community Cloud (Guilherme's step), then decide Phase 4b/4c scope.**
Committed as part of `7f7a4e4`.

---

## 2026-07-05 — first real use of the app: two bugs found (not model bugs), then a UX pass

**Two real bugs, found by Guilherme actually running the app** (both environment/tooling, not a
model or logic bug): (1) Streamlit's first-run "Welcome" email prompt blocks the terminal silently
on a machine's very first `streamlit run` — pre-answered via `~/.streamlit/credentials.toml`.
(2) My own `.streamlit/config.toml` had `headless = true`, meant for deployment, which silently
stopped `streamlit run app.py` from auto-opening a browser locally. Removed it. A third non-bug:
Guilherme was launching `app.py` via VS Code's Run button, which invokes plain `python`, not
`streamlit run` — bare mode, no server, no browser, just harmless warnings. All three logged in
[ML_TOOLING.md](ML_TOOLING.md).

**UX pass on first feedback** (search, more stats, "expect more to come"): replaced the two-step
sidebar position→player flow with one global, prominent search box (Streamlit's own selectbox
already filters live while typing — no new dependency); added per-position "signature stats" (3
role-relevant per-90 metrics with percentile rank — defender/midfielder/forward each get a
different trio) and a full 9-stat table with percentiles in an expander. Found and fixed a real
Streamlit gotcha along the way: a selectbox whose `options` list changes (the search box, narrowed
by the position filter) needs an explicit `key` tied to what changes it, or Streamlit tries to carry
a now-invalid selection forward and raises a raw `KeyError` from its own session-state internals —
keyed it on the filter value so the widget resets cleanly instead. Verified headless via `AppTest`
across every position filter × several players again after each fix.

Named, not silently skipped: true SofaScore-depth stats (completion %, duels won %) need new
features from raw events (a denominator, not just a different chart) — flagged in the app itself
and in PRODUCT_SPEC.md, not faked with today's counts-only data.

Docs: PRODUCT_SPEC.md "Post-v1 additions" section, ML_TOOLING.md (+2 gotchas). Tests unaffected
(59 green — none cover `app.py` itself, per Phase 8's presentation-shell scope). Committed as part
of `7f7a4e4`.
