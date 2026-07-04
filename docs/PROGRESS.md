# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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

## 2026-07-03 — Phase 3 spine, Checkpoint D (3d: pipeline.py + Makefile) → Phase 3 complete

Closed the last Phase 3 checkpoint. New **`src/pipeline.py`** chains the already-tested `src/` functions into a headless, non-notebook rebuild — mirrors notebooks 02/03 exactly rather than reimplementing them: build/reload the xG shot tables and the per-90 similarity table (skip the raw StatsBomb pull when the `data/` cache already exists, same `REBUILD` logic the notebooks use), train the logistic + GBM models and write all 4 Module A output PNGs, cluster each position group (K=4, matching the Phase 2 silhouette call) and write all 4 Module B output PNGs, then call `write_manifest()`/`write_metrics()` last (order matters — metrics.json reads the tables the earlier steps just built). Runnable as `python -m src.pipeline`, with `--force` (bypass caches, re-pull raw data) and `--skip-plots` (data + manifest/metrics only) flags.

A thin root **`Makefile`** wraps it (`make pipeline`, `make pipeline-force`, `make test`) for anyone with `make` on their PATH — confirmed it isn't on this Windows machine (checked both PowerShell and Git Bash), so `python -m src.pipeline` stays the primary, always-works entry point; the Makefile is a convenience for CI/WSL/Linux contributors, not a requirement.

**Verified for real, not just unit-tested:** ran `python -m src.pipeline` end-to-end against the existing local `data/` cache (no `--force`, so no fresh network pull) — reproduced `metrics.json` and `data/manifest.json` **byte-for-byte** (`git status` showed no diff on either), which is the concrete proof the pipeline is a faithful non-interactive twin of the notebooks rather than a rewrite that happens to look similar. All 8 output PNGs regenerated cleanly.

+5 unit tests (`tests/test_pipeline.py`) — the one piece of genuinely new logic (rebuild-vs-reuse cache decisions in `build_shot_tables`/`build_similarity_table`), tested network-free via monkeypatched builders, same pattern as `test_manifest.py`. Tests **31 → 36 green**.

Suggested commit: `Phase 3 (spine 3d): headless pipeline.py + Makefile — Phase 3 complete`

**Phase 3 (engineering & reproducibility spine) is now fully done. Next: Phase 4 (multi-competition ingestion + data expansion).**

---

## 2026-07-02 — Phase 3 spine, Checkpoint C (3b: metrics.json single source)

Closed the drift vector the whole reprioritisation was about: headline numbers were hand-typed into four docs and had already drifted once (the 0.798→0.765 penalty-fix took four edits to chase).

**New `src/metrics.py`** computes them from the same code/data the models use — xG train/test ROC-AUC + Brier, in-distribution CV mean±std, the no-skill→geometry→full baseline ladder, per-group silhouette peaks, and shot counts — and `python -m src.metrics` writes the committed **`metrics.json`** (repo root, outside gitignored `data/`; deterministic + timestamp-free like the manifest). Split into pure compute (`compute_xg_metrics` / `compute_similarity_metrics` / `build_metrics`, tested on synthetic frames) and an IO wrapper (`write_metrics`) so the unit tests stay offline. **Every emitted value matched the docs on the first run** (0.765 / 0.786 / 0.783±0.009 / 0.5→0.712→0.765 / silhouette 0.236·0.264·0.262 at K=2 / 10,824 · 1,316) — the docs were honest, they just weren't *enforced*.

**Doc-lint** (`tests/test_metrics.py::test_current_state_docs_match_metrics_json`): fails the build if a *current-state* doc (README/CLAUDE/MODULES/DATA) prints a number that differs from `metrics.json`. Append-only history (PROGRESS, INITIATIVE log entries, ML_LEARNING_LOG, the archive) is deliberately exempt — an old dated entry may keep the 0.798 it reported then. Deferred the test-count number (a repo fact, not a model output). Docs now *reference* the file: README callout under the results table, CLAUDE.md key-numbers note, ROADMAP 3b marked done.

Tests **27 → 31 green** (+3 pure-compute, +1 doc-lint). Uncommitted.

Suggested commit: `Phase 3 (spine 3b): metrics.json single source + doc-lint; docs reference it`

**Remaining in Phase 3:** 3d (`pipeline.py`/Makefile headless rebuild).

---

## 2026-07-02 — Phase 3 spine, Checkpoints A+B (CI + data manifest)

First code of the engineering & reproducibility spine.

**Checkpoint A — CI:** `.github/workflows/tests.yml` runs the suite on push/PR to main (Python 3.10 to match the pinned `requirements.txt`, `MPLBACKEND=Agg` so `visualisation.py`'s import-time matplotlib works headless). CI badge added to README (repo slug `GuiPadinha/football-analytics-portfolio`). Also cleared the 3a leftover: renumbered the two `src/config.py` comments that still called the 360 model "Phase 3" → Phase 7. *Push required for the badge to go live / first run to appear.*

**Checkpoint B — data manifest (3e):** new `src/manifest.py` + `tests/test_manifest.py`. `python -m src.manifest` writes `data/manifest.json` (tracked via a new `.gitignore` exception) pinning, per dataset, the sorted match-id set + a short set-hash + local cache coverage, plus content hashes of the two processed `shots_*.parquet` tables. Deliberately timestamp-free → pure function of the data, so only real drift diffs. Generated for real: **3 datasets, 465 matches pinned (380 PL 2015/16 + 51 EURO 2024 + 34 Leverkusen), all cached locally**; `statsbombpy 1.19.0` recorded. Feeds Phase 4's ingestion pipeline.

Tests **22 → 27 green** (+5 manifest tests, all network-free via an injected loader). Uncommitted.

Suggested commit: `Phase 3 (spine A+B): CI workflow + data provenance manifest; config Phase 3→7 comment fix`

**Remaining in Phase 3:** 3b (`metrics.json` single-source for key numbers) + 3d (`pipeline.py`/Makefile headless rebuild).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-04 (git CLI use is now fine — see the entry above).
Committed through `102a134`:

- `25bbf79` — S6/7 — Radar charts + visuals + final polish + README
- `a3ff7cd` — Initiative Phases 0–1: framework charter, foundation hardening, data-integrity rebuild
- `bbc4ac8` — Phase 2 (Module A): xG ML-rigor (scaled logistic, CV, baseline ladder, calibrated GBM)
- `5e5aaef` — Phase 2 Module B rigor: silhouette score + minutes-weighted positions
- `4be7844` — Phase 5 (old numbering): expand product-layer interface spec + mockups (docs only)
- `e862a59` — Refactoring priorities and plan
- `6a1876c` — Phase 3 (spine A+B): CI workflow + data provenance manifest; config Phase 3→7 fix
- `102a134` — Phase 3 (spine 3b): metrics.json single source + doc-lint; docs reference it

**Uncommitted as of this entry:** Phase 3d (`src/pipeline.py`, `Makefile`, `tests/test_pipeline.py`)
and this session's docs pass (`docs/ARCHITECTURE.md` new; `CLAUDE.md`, `README.md`,
`docs/{DATA,INITIATIVE,MODULES,PROGRESS,ROADMAP}.md` modified). Suggested commit messages are in
each entry above.
