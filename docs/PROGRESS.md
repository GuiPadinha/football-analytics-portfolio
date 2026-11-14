# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-11-14 (evening) — dbt expansion, step 1 pilot: raw events → shot features in SQL

Guilherme said "procede" to a pilot of the landing step. Not committed yet.
- **Cache check first:** 3,102 matches cached (events + lineups, 11 GB); all 2,616 match ids of
  `data/manifest.json` are there. The 486 extra are not in the manifest (not looked into).
- **Landing (`src/landing.py`, `python -m src.landing`):** the cache is pickled pandas, which
  dbt cannot read. Each match becomes one Parquet file under
  `$FAP_CACHE_DIR/raw/events/competition_id=…/season_id=…/`. Premier League 2015/16 landed: 380
  matches, 1,313,773 events, 112 MB, ~1 minute. Flags become booleans, locations lists of
  floats, nested columns (freeze frames, tactics) JSON strings. 27 "contract" columns are always
  written, typed, because statsbombpy drops a column from a match where nothing set it.
- **dbt:** source `raw.events` (a `read_parquet` glob, `union_by_name`), `stg_events` (view),
  `int_shot_features` (the SQL twin of `features.extract_shot_features`: geometry, flags, assist
  type by a join to the key pass, score state by two window functions).
- **Parity:** `assert_shot_features_match_pandas` compares it to `app_data/shots_with_xg.parquet`:
  9,908 shots, every column equal. `dbt build`: 31 of 31. Negative control: changing the
  shoot-out filter made the test fail with 5,424 rows.
- **CI is unchanged:** with no raw layer, `tools/warehouse.py` excludes `source:raw+` and runs
  the 17 nodes it ran before (checked locally by pointing `FAP_CACHE_DIR` at nothing).
- **Gotcha (ML_LEARNING_LOG.md):** rounding both sides to 9 decimals is not a float comparison.
- **Next:** the same for the player table (`similarity.py`'s extraction half, with lineups for
  minutes), then the incremental model. The xG model itself stays in Python: SQL builds
  features and aggregates, scikit-learn scores.

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

Older entries (2026-11-12 night shift and before): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md).

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
