# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-11-14 (later) — Audit and cleanup

Guilherme asked for an audit and refactor before the dbt expansion, and approved the cleanup.
- **dbt expansion plan recorded** (his notes): ROADMAP.md wild ideas, CLAUDE.md next session.
- **Dead code removed:** the July scouting blurb (`build_scouting_blurb`, `style_intensity_label`,
  `SIGNATURE_STATS_BY_POSITION`; the redesign replaced it with `narrative.py`), two orphaned
  matplotlib charts (`plot_player_radar_comparison`, `plot_diverging_bar`),
  `GK_PER90_LEAGUE_Z_COLUMNS`, an unused numpy import. Kept: `load_360_frames` (Phase 7),
  `load_competitions` and `train_calibrated_gbm` (notebooks). A new test replaces the lost
  label check: every stat a page shows has a label (`STAT_LABELS[stat]` would crash otherwise).
- **Later the same day:** `docs/PITCH.md` deleted (his call; it was stale and hand-refreshed).
  Ruff added (`ruff.toml`, pyflakes rules only; a CI step on 3.12; pinned in requirements-dev):
  it found one redundant import in a test, now fixed.

---

## 2026-11-14 — Half-updated deploys: a code fix (`src/freshness.py`)

Guilherme said "resume"; this was item 1 of the agreed order.
- **Cause, as far as known:** a push changes files under the running process, and the process keeps
  the `src.*`/`views.*` modules it already imported. A new page then imports a name the old module
  lacks (`ImportError`) until a reboot.
- **Fix:** `app.py` runs on every rerun. It fingerprints `src/*.py`, `views/*.py` and `app_data/*`
  (size + mtime, stat only) and keeps the last one in `st.cache_resource`. When it changes, it
  drops the project's modules from `sys.modules` and clears `st.cache_data` before any project
  import. The pure parts live in `src/freshness.py`, tested in `tests/test_freshness.py`.
- **Verified locally:** two copies of the app, `--server.fileWatcherType none`, a new name added to
  `src/presentation.py` and imported by How it works. The old `app.py` gave the live app's
  `ImportError`; the new one showed the new code. Freshness + app smoke tests pass (34).
- **Not verified:** on Cloud. The next push that changes a shared module is the real test.

---

## 2026-11-12 (late afternoon) — Build a player (the "Players like Guilherme" toy)

Guilherme picked it after the dbt pilot, and asked to close the session after it.
- **`profile.build_your_own`:**
  - Each slider is a standing within the league (0-1). It becomes the group's league-adjusted
    rate at that quantile, so the built player sits in the lookalikes' own space.
  - It is ranked by the same `rank_matches`. `_lookalikes` and the new function share
    `_match_lists`.
  - Outfield, StatsBomb only. Keepers are refused.
- **`views/build.py`, "Build a player"** in the top navigation:
  - Its first line says it is a toy.
  - A position, 11 sliders, an optional real player to start from, and Reset.
  - A "Your player" summary and the two games' lists. A name opens that player's page.
- **The toy is measured in the real space:** Mahrez rebuilt from his own percentiles finds Mahrez
  first, at distance ~0. Left off, his place goes to Mané and Morales, his own page's lookalikes.
  This is also why a starting player is excluded: at distance ~0 he squashed every other
  closeness bar to nothing.
- All sliders at 50 (the median forward) gives Floyd Ayité (Bastia) and Makenzy Doniak (San
  Diego Wave).
- **Verified:** the full suite passes (new tests in test_profile.py and test_app_smoke.py, the page
  in the every-page smoke). A real-browser screenshot of the page, local.
- **Live: a second half-updated deploy.** The new page threw an `ImportError` on `build_your_own`
  (CI green; Mahrez's page fine) until Guilherme rebooted the app again. Second time in one
  day, so it is an open problem, not bad luck (ML_TOOLING.md; first item in CLAUDE.md's next steps).

---

## 2026-11-12 (afternoon) — dbt + DuckDB pilot

Guilherme said "segue" to the proposed pilot (the career pick from ROADMAP's wild ideas).
- **Scope:** the raw-event layer was out, because the 11 GB event cache is gone. The pilot sits on
  what is local: `app_data/shots_with_xg.parquet` → `stg_shots` → `player_xg` and `team_xg`.
- **Tests (14):**
  - not null, unique, and `unique_together` on (player, team);
  - `probability` on every xG;
  - club totals reconcile with the shots;
  - parity: the dbt `player_xg` equals the pandas `player_xg_table.parquet` row for row.
- **The tests can fail:** multiplying xG by 1.0001 failed parity on 463 rows and the
  reconciliation on 1.
- **Runner:** `python -m tools.warehouse` runs the build in memory, with no `.duckdb` file in the
  synced folder. dbt's `target/` and `logs/` go to the temp folder. `--show` prints the club table.
- **CI:** a `warehouse` job on 3.12 with its own `requirements-warehouse.txt` (dbt-core 1.12.7,
  dbt-duckdb 1.11.1, duckdb 2.0.0), so dbt's pins never reach the app.
- **Finding:** Leicester's title season was 67 goals from 67.9 xG, so their finishing was ordinary.
  West Ham were the most above their chances (+7.3), West Brom the most below (−11.1). A penalty
  is worth 0.80 xG on average (91 penalties, 74 scored).
- **Verified:** `dbt build` gave PASS=17 (3 models, 14 tests) locally.

---

## 2026-11-12 — Night shift: keep-alive, hygiene, shareable links, Phase 5a (full autonomy given)

Guilherme asked for a sweep of the repo after 26 days away, then said "commit and proceed with
everything": one commit and push per item, with the CI and the live app checked after each.
- **The live app was asleep.** An anonymous visit got Streamlit's "gone to sleep" page (open in
  ROADMAP.md since 10-01). Woken by hand, then fixed for good:
  - `tools/screenshot.py` now wakes a sleeping app (clicks the page's button), runs on Linux, and
    exits 1 when its marker is missing.
  - It also reads the app's iframe. On Streamlit Cloud the top document's text is empty, so the
    10-17 version never found its marker on the live URL (ML_TOOLING.md).
  - `.github/workflows/keepalive.yml` runs it every four hours. The Cloud's limit is 12 hours
    without traffic (its docs, read today). Known limit: GitHub pauses scheduled workflows after
    60 days without a commit.
- **Repo hygiene:** `.gitattributes` (LF everywhere; notebooks out of GitHub's language bar, which
  read 87% "Jupyter Notebook"), `pytest.ini` (no `.pytest_cache` in the synced folder), the dev
  container on Python 3.12, and the redesign's mock-ups kept under `docs/redesign-2026-10/`.
- **GitHub front door:** the README opens with what the app answers and a screenshot of its Home
  (`docs/img/app_home.png`), instead of "Phase 8 (deployed 2026-07-09)". It gained a "Data and
  licence" section crediting the four sources. The code is now MIT-licensed (`LICENSE`): Claude's
  pick under the autonomy given, confirmed by Guilherme the same day.
- **Shareable links, and the look at the Wyscout pool** (CLAUDE.md's agreed next step 1):
  - A player's page and a comparison each have their own address, e.g.
    `/players?player=Mohamed Salah&league=Premier League 2017/18` and
    `/compare?player_a=Harry Kane&player_b=Jamie Vardy`. The page rewrites the address in full
    (name, club, league) whenever the player changes, so copying it shares that exact page.
  - A link is followed once per visit. After that the address mirrors the page, so a later pick
    in the search box isn't undone by the address the visit started from.
  - `profile.find_linked_player` forgives case, accents and a missing club or league; a name in
    both seasons' data resolves to the season with the most minutes. An unknown name gets a
    warning and the starting points.
  - Looked at in a real browser (local, through the new links): Salah 2017/18's page (32 goals,
    €80M, lookalikes Agüero, Immobile, Depay, Dybala, Mbappé), Salah against Kane 2017/18, and
    the cross-provider refusal. All read correctly.
  - One fix from that look: a comparison of two players without shot data showed two "n/a"
    panels; it now says so once.
- **Phase 5a, uncertainty on goals − xG** (agreed next step 2; committed locally, not pushed, at
  Guilherme's "we'll review the push later"):
  - xG is out-of-fold (`models.out_of_fold_xg`, 5 folds by match), rebuilt with the new
    `python -m src.app_data --xg-only` (seconds; the player table and prices are untouched).
  - Each player gets a 90% luck range (`narrative.likely_goals_range`), shown as a "What luck
    alone gives" tile (Mahrez: 17 goals, 8–17). How it works quotes the census live
    (`profile.finishing_census`): 8 of 164 outside, 8.1 expected by luck.
  - Home moved: Agüero +6.5 → +6.7 (1 in 22 → 1 in 25), Jerome 1 in 27 → 1 in 26.
  - Model uncertainty measured and left out (~8% of the luck). ML_LEARNING_LOG.md has the numbers.
  - `findings.json` is now written with LF on Windows too.
- **Wild ideas mapped** in ROADMAP.md (Phase 9): no-server app, tournament stories, dbt + DuckDB,
  LLM reports with a fact-check, build-your-own-player, each with a cost and a verdict.
- **The 11 GB cache is gone:** `C:\Users\guilh\fap-cache` doesn't exist, and why is not known. The
  `--xg-only` rebuild didn't need it (it reads `data/`); a full rebuild will download it again.
- **After the push (Guilherme's OK, same day):** CI green, but the live player page had died with
  an `ImportError`. The Cloud ran the new pages against the old `views/data.py` it held in
  memory. Guilherme rebooted the app; Mahrez's page then showed "What luck alone gives". The
  keep-alive now opens that page too, since Home alone hid the break (ML_TOOLING.md). Its first
  run, set off by that push, hit the redeploy and failed; on a push it now waits 150 s.
- **Verified:** 285 tests pass locally before any change; CI green on `cddb68b`; the rewritten
  tool finds the live Home in 8 s and returns 1 for a marker that isn't there.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
