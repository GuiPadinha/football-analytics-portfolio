# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-09 (cont. 5) — Clickable "similar player" drill-down (backlog item shipped), and a real bug caught by actually clicking it

Shipped the second open backlog item: clicking a row in the "Players like X" → "Table view"
table now jumps the whole page to that player (radar, signature stats, similar-players list, xG
all recompute for the new player) instead of being a static, unclickable table.

**Mechanism** (`app.py`): a row click sets `st.session_state["jump_to_player"] = (player, team)`
and calls `st.rerun()`. A new block at the very top of the script — before any widget is
created — checks for that key and, if present, pre-seeds the sidebar position/competition
filters, the search box, and the player-picker selectbox's session_state so the next run lands
directly on the target player with no stale filter hiding them. This is the only point Streamlit
allows a script to set a widget's value programmatically: session_state for a widget's `key` must
be written *before* that widget's `st.xxx(key=...)` call in the same run.

**A real bug, caught only by actually driving the click with Playwright, not by reading the code:**
the first version gave the "Table view" dataframe a fixed `key="similar_table"`. Streamlit
persists a dataframe's row-selection state in session_state by key across reruns — so after
landing on the new player's page, the *same* key's table rendered with row 0 still marked
selected from the previous click, which immediately re-triggered another jump to whoever *that*
player's own most-similar match was, cascading indefinitely. Static analysis / reading the diff
would not have caught this — it only showed up as visibly inconsistent, non-settling page state
under a real click. Fixed by scoping the key to the current player/team
(`key=f"similar_table_{player_name}_{team_name}"`), so each player's table is a fresh widget
instance with no carried-over selection. Re-verified after the fix: clicked twice in a row
(Fallou Diagne → Aïssa Mandi → back to Fallou Diagne, their mutual nearest match) and confirmed
the page settles to one consistent state each time rather than continuing to jump.

Verified live end-to-end via `streamlit run app.py` + the Playwright-over-Edge recipe
(`ML_TOOLING.md`) — canvas-based `st.dataframe` grids aren't clickable via normal DOM locators
(no real `<input>`/`<summary>` elements; row selection and the expander toggle are drawn on
`canvas`, testid `data-grid-canvas`), so verification clicked raw pixel coordinates inside the
canvas bounding box rather than a semantic locator. Full `pytest` suite (72 tests) green
throughout — no test coverage exists for `app.py` itself, this was live-verified only.

One open follow-up, not blocking: a fixed-key expander (`st.expander("Table view...")`, no `key=`)
appears to inherit its previous open/closed state across the jump in some cases and not others,
observed inconsistently during testing. Cosmetic only (worst case: expander shows collapsed after
a jump, one extra click to reopen) — not a correctness bug, not chased further this session.

---

## 2026-07-09 (cont. 4) — Penalty info on the player page (backlog item #4 shipped)

Shipped the smallest of the four open items from `PRODUCT_SPEC.md`'s "Backlog from 2026-07-06
feedback": the single-player "Player explorer" page showed only `non_penalty_goals`, so a
penalty-taker's page looked like it had no penalty data even though the leaderboard's `goals`
total (incl. penalties) already existed. Presentation-only, no data/rebuild work, as anticipated —
`penalties = goals - non_penalty_goals`, both columns already on `player_row_full`.

Added a `st.caption` right under the existing "Season totals..." caption (`app.py`, after the
signature-stats metric-card loop): `"Goals (incl. penalties): {total}{penalty_note}"`, only
rendered when `total_goals > 0` (skips the line entirely for non-scorers rather than showing a
"0 goals, 0 from penalties" line on every defender/GK page).

Verified end-to-end, not just unit-tested: ran `streamlit run app.py` locally and drove it with
the Playwright-over-Edge recipe from `ML_TOOLING.md` (system Edge via `channel="msedge"`, since
`playwright install chromium` still fails on this machine). Confirmed Fallou Diagne (Rennes,
`goals=5`, `non_penalty_goals=3`) renders `"Goals (incl. penalties): 5 (2 from penalties)"`, and a
true zero-goal player (Abdul Rahman Baba, Chelsea) shows no such line. Screenshot matched — caption
sits directly under the signature-stat cards as the backlog entry expected. Full `pytest` suite
(72 tests) still green — no test coverage existed for `app.py` itself (a Streamlit script, not a
`src/` module), so this was verified live, not via the suite.

Three items remain open in the backlog: clickable "similar player" drill-down, goalkeepers wired
into the app, and the "Under the hood" methodology expander rework (still explicitly on hold).

---

## 2026-07-09 (cont. 3) — doc-freshness enforcement: a git hook + CI backstop, not just a rule

Guilherme caught, twice in the same session, that the "log obstacles/findings as they happen"
convention in CLAUDE.md's Session Workflow was being followed inconsistently (a retry attempt went
unlogged; doc edits sat uncommitted) — then asked for an actual **mechanism**, not just a
restatement of the rule, since relying on memory had just visibly failed.

**Built two backstops, deliberately not just more prose in CLAUDE.md:**
- `.githooks/pre-commit` — blocks a commit touching `src/`/`app.py`/`tests/`/`notebooks/` unless
  the commit also touches `docs/PROGRESS.md`, `docs/ML_TOOLING.md`, or `ML_LEARNING_LOG.md`.
  Escape hatch for real trivial commits: `DOC_CHECK_ACK=1 git commit ...` (kept distinct from
  `--no-verify`, which would skip every hook, not just this one check).
- `.github/workflows/tests.yml`'s new "Check evolving docs were touched" step — the same check
  against the push/PR diff, as a non-blocking `::warning::` annotation, so the mechanism still
  fires even if the local hook was never enabled (a fresh clone doesn't auto-activate hooks).

**Enabling the hook is itself a persistence decision, not a passive doc edit** — the sandbox's own
auto-mode classifier correctly paused on `git config core.hooksPath .githooks` (a mechanism that
runs on every future commit, not just this session) until Guilherme explicitly confirmed enabling
both. Verified all three code paths actually work before relying on them: a code-only staged change
correctly blocks (exit 1, printed the exact violating files); `DOC_CHECK_ACK=1` correctly overrides
(exit 0); staging a real log-file touch alongside the code change correctly passes (exit 0) —
tested via scratch edits to `src/config.py`, fully reverted after, not left staged or committed.

Documented in `CLAUDE.md`'s Session Workflow ("This is enforced, not just requested") rather than
just added silently — the point is that a future session (or a human contributor) can see *why*
a blocked commit is happening, not just hit a wall.

---

## 2026-07-09 — Phase 4c mostly done: Module A generalisation across 3 of 4 held-out tournaments

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

**Status language corrected same session** (Guilherme flagged it): calling Phase 4/4c "✅ Done"
overstated it while Women's EURO 2025 stays unwired — downgraded to 🟡 "3/4 tournaments wired"
across CLAUDE/INITIATIVE/ROADMAP/this file. **One further retry attempt, later the same session**
(time-boxed per an explicit "don't waste time on it" ask): still `429`, and this time even
`sb.matches()` (metadata, not an event pull) was already rate-limited — a broader block than the
first attempt showed. Stopped after one try; logged in [ML_TOOLING.md](ML_TOOLING.md). Status
unchanged: still 3/4, still resumable for free whenever the limit clears.

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
