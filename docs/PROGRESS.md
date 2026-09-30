# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-09-30 — Repo health check after a 2.5-month gap

First session since 2026-07-14. Committed and pushed the leftover Leaderboard fix (`9d000ea`,
CI green), then ran a full health check: every doc read, code reviewed, notebooks re-executed
against current `src/`, CI annotations, the live app, and upstream sources (StatsBomb, Streamlit,
Python EOL). Nothing was fixed in code this pass. Findings, most important first:

- **Streamlit #7360 was already fixed upstream.** `st.dataframe(placeholder="")` exists in the
  installed 1.58, so the six-column text workaround (and its lexical click-sort) can go. See
  ML_TOOLING.md's correction.
- **README's 8 images have never been committed** (`outputs/*` is gitignored), so they render
  broken on GitHub.
- **README/notebook 03's Module B story is stale** since clearances/blocks were added on
  2026-07-05: cluster members, neighbour lists, and the Antonio one-man cluster (now gone). See
  ML_LEARNING_LOG.md. Notebooks 02/03 re-run clean. 01 fails only on the SSL issue below.
- **Python HTTPS is down on this machine** (Avast rotated its root cert). This blocks StatsBomb
  pulls, pip, and notebook 01. The original 2026-06-28 fix had been lost from ML_TOOLING.md;
  recovered there, with a durable fix.
- **Deadlines:** Python 3.10 reaches EOL on 2026-10-31. `ubuntu-latest` moves to Ubuntu 26 on
  2026-10-19. CI warns that `actions/checkout@v4`/`setup-python@v5` target deprecated Node 20. The
  "3.10 → newer" Phase 9 item now has a date on it.
- **Scope facts recovered or changed:** no FIFA World Cup 2026 in StatsBomb open data (the Phase 9
  "current tournament" model is moot as framed). Women's EURO 2025 is published with 360.
  StatsBomb also has Women's World Cup 2023 (360), Liga F/Serie A Women 2023/24, NWSL 2023 and
  MLS 2023 (360), none used here. 360 data exists for WC 2022/AFCON 2023/EURO 2020 too, not only
  Leverkusen/EURO 2024 as Phase 7 assumes, but **zero 360 frames are cached** (Phase 7's "should
  already be pulled" is wrong). `config.SETS_WITH_360` also skips WC 2022/AFCON 2023.
- **Unused cached data with a product use:** 16 Barcelona seasons of shots (2004/05–2020/21) plus
  La Liga/Serie A/Ligue 1 2015/16 shots are already extracted. Scoring them with the fitted model
  would give most of the similarity pool a Finishing panel, and a Messi-era per-season goals−xG
  "career" view. Neither needs new pulls, unlike the per-90 career idea.
- **Lost decision:** the 2026-07-14 (cont. 2) recommendation to pivot to Phase 5a (goals−xG
  uncertainty) never reached CLAUDE.md's "Next session" note.
- **Doc drift:** CLAUDE.md (test count 86 vs 89, scouting blurb still listed as open), FRAMEWORK.md
  (the README's "New here?" doc still says the app is "planned"), PRODUCT_SPEC.md (4 of 8 `#L`
  anchors wrong, v1 mockup still shows Leverkusen/"GKs excluded"), ARCHITECTURE.md (`app.py`
  missing from the import graph, "future" app), ROADMAP.md (Phase 7 checklist still says GitHub
  Desktop), PITCH.md (86 tests), and `config.py`'s SIMILARITY_SETS comment (says there is no
  cross-league normalisation yet). This file also had the 2026-07-14 (cont.) entry duplicated
  verbatim in PROGRESS_ARCHIVE.md; removed here.
- **Structure:** `app.py` is 1,406 lines. The Player explorer (~490 lines) is top-level script code
  while the other three views are functions, and its pure helpers have zero tests (the `AppTest`
  smoke runs were never committed). `plotly`/`seaborn` are unused. The app installs
  `jupyter`/`pytest` on Streamlit Cloud. `statsbombpy`/`kloppy` are import-time dependencies of the
  app via `similarity → data_loader`. The 8.2 GB `data/cache` lives inside OneDrive (DATA.md says
  ~1–2 GB).

**Docs updated:** ML_TOOLING.md (#7360 correction + the recovered/updated Avast certificate
entry), ML_LEARNING_LOG.md (feature change → stale qualitative claims), this file.

---

## 2026-07-14 (cont. 3) — Leaderboard "None" cell bug, round 2: Goals/Non-pen goals/Assists

Guilherme, driving the live app himself: "player leaderboards still has multiple missing/(empty)
values." The 2026-07-13 fix (see the archived entry, and CLAUDE.md's Current Status) only converted
xG/G-xG/Market value to hand-formatted text columns — Goals, Non-pen goals, and Assists were left on
`column_config.NumberColumn(format="%d")`. Those three are genuinely `NaN` for all 124 goalkeepers
(outfield feature set doesn't cover them — documented, intentional), so every goalkeeper row hit the
exact same Streamlit issue #7360 (`NumberColumn` renders a missing numeric cell as the literal text
"None") the prior fix was written to kill. Confirmed via `player_per90.parquet`
(`goals`/`non_penalty_goals`/`assists` all null for the 124-row Goalkeeper group, 0 nulls elsewhere)
before touching code.

**Fix:** same pattern as the 2026-07-13 fix, applied to the three remaining columns —
`render_leaderboard` now hand-formats Goals/Non-pen goals/Assists to text (blank string for NaN,
`f"{v:.0f}"` otherwise) *after* the Goals sort already ran on the numeric column, and their
`column_config` entries switched from `NumberColumn` to `TextColumn`. Extended the existing
"known trade-off" comment (lexical, not numeric, click-to-sort) to cover all six now-text columns,
not just xG/G-xG.

**Verification.** Full `pytest` suite still green (89, unchanged — display-only). Killed and
restarted the local Streamlit server (on-disk change, per the standing "reload isn't enough"
lesson), then Playwright-over-Edge: filtered the Leaderboard's in-page position filter down to
Goalkeeper-only (124 rows, where every one of these three columns is null) and screenshotted the
result — genuinely blank cells, no "None" text anywhere in the grid.

**Docs:** none beyond this entry — no new gotcha class, just the same fix applied to columns the
first pass missed.

---

## 2026-07-14 (cont. 2) — Scouting-report blurb + phase-alignment check-in

Two things this pass. First, a strategic check-in Guilherme raised directly: after several
sessions in a row inside Phase 8/9 (product/UX work), are Phases 5–7 (the core ML-depth phases —
xG uncertainty, Module B metric upgrades, 360-context xG) being quietly forgotten? Answered
honestly: yes, that's a real drift worth naming, not a false alarm — the Phase 8 order-jump on
2026-07-04 had a real deadline (a friend demo) that's since been satisfied, so continuing in Phase
9 no longer has that same justification. Recommended pivoting to Phase 5a (uncertainty on
goals−xG) next session. Before that, asked to rank the two open Phase 9 backlog items (the
Leaderboard filter question, the "new app features" candidates) by effort and do the fastest one
first — the **auto-generated scouting-report blurb** (reuses already-computed data, no new
modelling), clearly faster than a deep-link feature, a new team-level view, or the Leaderboard
filter's unresolved design question.

**Scouting-report blurb.** New `app.py` function `build_scouting_blurb` stitches three
already-rendered panels into one paragraph at the top of a player's page (new "Scouting report"
subheader, right after the page header): the Style archetype read (top 2 cluster traits + the
weakest one), the single best percentile stat (`percentiles.idxmax()`, using the same
goodness-adjusted percentiles and `percentile_tier` wording the rest of the page already uses),
and market value. A fixed template over already-verified numbers, not an LLM-generated summary —
it literally cannot say anything the rest of the page doesn't already say, since every value comes
from a computation that panel below it also uses. Required moving three existing computations
(`percentiles`, the cluster/`profile_clusters` read, the market-value lookup) earlier in the script
so the blurb has what it needs before its own panels render further down — reused, not duplicated;
the Style archetype and signature-stat sections below now read from the same already-computed
variables instead of recomputing them.

**Verification.** Full `pytest` suite green (**89**, unchanged — this is presentation-only, no
`src/` logic touched beyond the reordering, which changes nothing about what's computed). Playwright
-over-Edge confirmed the blurb reads sensibly for two different feature sets: a forward (Messi —
"A Key Passes and Progressive Passes forward, light on Clearances... Stands out most for Dribbles
Completed, ranking in the 100th percentile (Elite)... Valued at €120.0M") and a goalkeeper (Kasper
Schmeichel — confirms `goodness_percentiles`' goals-conceded flip doesn't surface a misleadingly
"good"-sounding stat via `idxmax()`). One honest nuance noted, not fixed: `idxmax()` can surface a
volume/context stat (e.g. a keeper's Shots Faced) as "stands out most for," which isn't really a
skill judgment the way Save % would be — inherited from the existing feature-set design (only
Goals Conceded is flagged direction-sensitive), not a new bug, and the same ambiguity already
exists in the percentile chart the blurb reads from.

**Docs updated:** ROADMAP.md (Phase 9 candidate list — scouting blurb marked done).

---

## Commit Status

Verified against `git log`/`git status` 2026-09-30. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit on `origin/main`: `9d000ea` (Leaderboard "None" fix, round 2). The
2026-09-30 health-check entry above and its ML_TOOLING/ML_LEARNING_LOG additions are **not yet
committed**.
