# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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
checked number. Docs only.

Suggested commit: `docs: replace narrative headers with concept labels, unbundle crammed bullets into paragraphs`

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

Docs only — no `src/`, notebook, test, or data changes; 36 tests untouched.

Suggested commit: `docs: relax git policy, add ARCHITECTURE.md, note SofaScore/FlashScore as a Phase 4/9 candidate`

---

## Commit Status

Verified against `git log`/`git status` 2026-07-04 (git CLI use is now fine — see the entry above).
Committed through `0d4d2fe`:

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

**Uncommitted as of this entry:** the quick retraining-experiment write-up above (this file +
`ML_LEARNING_LOG.md` + `docs/PROGRESS_ARCHIVE.md` reshuffle) — docs only, no `src/`/test/data changes,
left for Guilherme to review before pushing since he'd already signed off when the experiment finished.
