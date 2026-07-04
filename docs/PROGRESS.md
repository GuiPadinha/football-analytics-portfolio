# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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
(59 green — none cover `app.py` itself, per Phase 8's presentation-shell scope).

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
docs/tests only.

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

Docs + tests only — no `src/` changes; suite re-run clean after every edit.

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
[ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md)'s Module A gotcha list.

---

## Commit Status

Verified against `git log`/`git status` 2026-07-04 (git CLI use is now fine — see the entry above).
Committed through `1c8d90d`:

- `25bbf79` — S6/7 — Radar charts + visuals + final polish + README
- `a3ff7cd` — Initiative Phases 0–1: framework charter, foundation hardening, data-integrity rebuild
- `bbc4ac8` — Phase 2 (Module A): xG ML-rigor (scaled logistic, CV, baseline ladder, calibrated GBM)
- `5e5aaef` — Phase 2 Module B rigor: silhouette score + minutes-weighted positions
- `4be7844` — Phase 5 (old numbering): expand product-layer interface spec + mockups (docs only)
- `e862a59` — Refactoring priorities and plan
- `6a1876c` — Phase 3 (spine A+B): CI workflow + data provenance manifest; config Phase 3→7 fix
- `102a134` — Phase 3 (spine 3b): metrics.json single source + doc-lint; docs reference it
- `ce45e74` — Phase 3 complete: headless pipeline.py + Makefile; add ARCHITECTURE.md; docs cleanup
- `0d4d2fe` — Phase 4 data expansion: config-driven datasets, sparse-column bug fix, obstacle docs
- `1c8d90d` — Model validation tests + Module A-B-C ordering pass + a real sparse-column fix

**Uncommitted as of this entry:** today's Phase 8 build (`app.py`, `src/app_data.py`, `app_data/`,
`.streamlit/config.toml`, `requirements.txt`) and this doc pass (this file, `docs/PROGRESS_ARCHIVE.md`,
`docs/PRODUCT_SPEC.md`, `docs/ROADMAP.md`, `docs/INITIATIVE.md`, `CLAUDE.md`) — ready to commit.
