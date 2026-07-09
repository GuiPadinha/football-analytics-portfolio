# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-09 — Phase 4c done: Module A generalisation across 4 held-out tournaments (Phase 4 now fully ✅)

Picked up the model-track backlog (not the app UX one): Phase 4c was the one remaining open item
in Phase 4 — Copa América 2024, FIFA World Cup 2022, and Africa Cup of Nations 2023 were pulled
back on 2026-07-04 but never scored against the trained xG model, leaving EURO 2024 as the only
held-out generalisation evidence anywhere in the docs.

**Design call: report per-tournament, don't pool.** `config.TEST_SETS` (still `[EURO_2024]`) and
the headline `0.765` test ROC-AUC every doc quotes are untouched on purpose — folding four
structurally different tournaments (a settled European field, a smaller CONMEBOL sample, a
different tactical culture, etc.) into one aggregate number would answer a coarser question than
the honest one Phase 4c actually asks: does the model generalise *evenly*? New
`config.GENERALISATION_TEST_SETS` (EURO 2024 + the three Phase 4 tournaments) is scored
separately per competition by a new `models.evaluate_by_competition` (fits once on `TRAIN_SETS`,
then slices the combined held-out table by `competition_id`), assembled into
`metrics.json`'s new `xg_generalisation` section by `metrics.compute_generalisation_metrics`, and
plotted by a new `visualisation.plot_xg_generalisation_bar` (invoked the dataviz skill first: a
magnitude comparison across a handful of named categories is a single-hue bar chart, not a
categorical palette — direct ROC-AUC labels at each tip, a dashed no-skill/0.5 reference line,
sample size folded into the label itself since a small held-out sample is exactly the caveat that
shouldn't be missable). `pipeline.py` gained a `build_generalisation_table` step (same
cache-or-rebuild pattern as the existing shot tables) and now writes
`outputs/xg_generalisation_by_tournament.png`; `manifest.py`'s default dataset list now includes
the three new tournaments too (deduped against `TEST_SETS`, since `GENERALISATION_TEST_SETS`
overlaps it on `EURO_2024`).

**The actual finding is a good one, not just a wiring exercise:** EURO 2024 (0.765) turns out to be
the *floor*, not a fluke — the same model scores 0.808 on FIFA World Cup 2022, 0.807 on Africa Cup
of Nations 2023, and 0.763 on Copa América 2024 (751 shots, the smallest sample of the four, flagged
as such). The honest story sharpens from "the model holds up reasonably on one tournament" to "the
model holds up as well or better everywhere tested" — a stronger generalisation claim than the
single EURO 2024 number alone supported, and worth surfacing over README's/CLAUDE.md's headline
number rather than replacing it.

**Women's EURO 2025 stays unwired — a real rate limit, not a data problem.** Attempted the pull
(never previously cached, unlike the other three) and hit persistent `429 Too Many Requests` from
`raw.githubusercontent.com` on the first or second match across several retries spaced minutes
apart — this didn't clear the way the one-off `IncompleteRead` from the original Phase 4 pull did.
Left genuinely unwired rather than forcing it or guessing at a fix; logged in
[ML_TOOLING.md](ML_TOOLING.md). The resumable per-match cache means a later session's retry picks
up wherever this one stopped, at no extra cost.

Notebook 02 is deliberately untouched — same precedent as Phase 4a/4b (the notebook stays the
fixed single-competition/single-tournament teaching example; the wider multi-dataset checks live in
`src`/`metrics.json`/`pipeline.py` only). +6 tests (`evaluate_by_competition`,
`compute_generalisation_metrics`, `build_metrics`'s new optional section, `build_generalisation_table`'s
cache logic) — **72 green** (66 → 72). Full `python -m src.pipeline` run regenerated `metrics.json`
and `data/manifest.json` against real data (not synthetic-only tests) — every dataset now shows
`n_cached_locally == n_matches`, confirming no partial/rate-limited state leaked into what's
actually wired in.

---

## 2026-07-09 (cont.) — Phase 8 deployed to Streamlit Community Cloud (Phase 8 now fully ✅)

Same-day continuation, ahead of the ~2026-07-11 friend demo. Guilherme deployed `app.py` himself
via Streamlit Community Cloud's "New app" flow; I verified beforehand that the repo was actually
ready (pinned `requirements.txt`, committed `app_data/*.parquet`, no secrets needed since the app
reads only static local artifacts, no live StatsBomb pulls at runtime) and flagged one real risk in
the deploy form: `app.py` imports `src.similarity` → `src.data_loader`, which imports `kloppy` at
module level even though the app itself never calls it — `kloppy` is the heaviest/least-common
dependency in `requirements.txt`, so a build failure would likely start there.

**Set Python version to 3.10 in the deploy's advanced settings, overriding Cloud's 3.14 default.**
Every pinned dependency was tested against 3.10 locally; deploying on a newer interpreter risked
missing wheels for `kloppy`/`pyarrow`/`statsbombpy`, forcing an unplanned dependency-bump-and-
reverify right before the demo for zero functional gain. Recommended *against* actually modernising
the project's Python target for the same reason when Guilherme asked — added as a low-priority
Phase 9 opportunistic backlog item instead (see ROADMAP.md), explicitly not now.

**Live at [gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app)**,
confirmed rendering correctly by Guilherme in a real browser — the strongest verification yet,
stronger than the local Playwright-over-Edge check from 2026-07-08. README now links it at the top
next to the CI badge. Phase 8 is now fully ✅ done; the only work left in the whole initiative is
Phases 5–7 and the small app-UX backlog in CLAUDE.md's Current Status.

---

## Commit Status

Verified against `git log` 2026-07-09. Git CLI is used directly now (see CLAUDE.md's Session
Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git status`.
Latest commit: `d3093e7` (Phase 4c + the `.gitignore` fix, pushed to `origin/main`). Everything
through this session's work is committed and pushed; nothing outstanding.
