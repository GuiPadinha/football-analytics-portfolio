# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-11-15 — dbt expansion, step 2: an incremental model

Guilherme: "status, next steps e procede".
- **`int_player_match_actions` is incremental:** append, by match (`match_id not in {{ this }}`),
  `on_schema_change = 'fail'`; the SQL explains `is_incremental()` and the blind spot (a
  re-landed match keeps its old rows: `--full-refresh`).
- **A second dbt target, `file`:** `python -m tools.warehouse --persist [--full-refresh]` keeps
  the tables in `$FAP_CACHE_DIR/warehouse.duckdb`. The default and CI stay in memory, where the
  model is always a full build.
- **Proof:** full build 57 of 57; second run 8.2 s → 3.1 s on that model. Deleted the Premier
  League's 380 matches (10,450 rows) from the persisted table, reran: exactly those came back
  (75,614 rows, 2,616 matches), both parity tests green. Negative control without the filter:
  `unique_together` failed with 75,614 duplicates, 8 downstream nodes skipped.
- **Next:** dbt docs published (step 3), the app as an exposure (4), then README "The dbt layer".
- **Pushed as `2d4b0cc`.** Live app checked: Home and Mahrez's page render.
- **README rewritten** (Guilherme: "melhorias integrais, tralha antiga"): the app comes first
  (what it answers, the pool), then a "How it is built" diagram (Python vs dbt, what the app
  reads), shorter Module A/B, a new "The dbt layer" (it said "pilot, 14 tests, next step: raw
  events"), the run commands in one block, a current repo map. Out: internal jargon ("S1–S8 +
  Phase 2 rigor"), the feature-importance and elbow charts, a claim the player page shows an
  archetype (the redesign removed it). DATA.md: cache ~11 GB, 6,204 pickles (measured).
- **Steps 3–4** (Guilherme: "procede", and step 5 joins the plan): `tools.warehouse --docs DIR`
  builds in memory and runs `dbt docs generate --static` in the same runner (the catalog needs
  the tables), one 2.6 MB HTML. CI job `dbt-docs` (after `warehouse`, pushes only) deploys it to
  https://guipadinha.github.io/football-analytics-portfolio/; Pages enabled in the repo settings (source: GitHub Actions). `exposures.yml`: the app,
  depending on the three `app_data` sources it reads. Limit: CI has no raw layer, so those
  models show SQL and lineage, no column catalog. Live and checked (200, lineage graph renders).
- **Step 5, the app reads the marts:** `src/warehouse_tables.py` reads `player_per90_outfield`
  and `_goalkeepers` from `$FAP_CACHE_DIR/warehouse.duckdb`, drops the key columns and sorts as
  pandas' groupby; `app_data._build_combined_tables(from_warehouse=True)`, with `--from-pandas`
  as the escape hatch; duckdb==2.0.0 in requirements-dev. The goalkeeper mart now names its
  columns in pandas' order (save_pct after minutes). Against pandas, nine leagues: same rows and
  order, rates within 1e-9. Rebuilt `app_data/`: 3,794 players, 2,911 market values, **every
  cluster equal**, `findings.json` byte-identical, largest change 1.4e-14. Build ~68 s (was 3–5
  min). The exposure now depends on the two marts. `tests/test_warehouse_tables.py`: 4 tests.
  Corrected before writing it down: Leverkusen *is* landed; the xG tables stay in pandas because
  the SQL shot-feature parity covers the Premier League only.
- **Step 6, Leverkusen parity (one-off, local):** `int_shot_features` for competition 9 / season 281
  against `build_training_dataset([LEVERKUSEN_2023_24])`: 916 shots both sides, `except all` empty
  both ways, distance/angle differ by at most 2.5e-13. Not a dbt test yet: no committed reference
  for that season and CI has no raw layer.
- **Step 6, xG training shots from SQL:** `warehouse_tables.read_training_shots` + `python -m
  src.pipeline --force --from-warehouse` (`src/pipeline.py`). The match order comes from the cache's
  match lists (Python owns it), then event position. Against `build_training_dataset(TRAIN_SETS)`:
  10,824 shots, same columns/dtypes/order, every column equal except `angle_to_goal` (max 3.5e-13).
  Model trained on each: test ROC-AUC identical (0.7653850018938955), predictions differ by at most
  3.8e-14, out-of-fold xG by 3.5e-14. Needed a cast: a window sum is HUGEINT in DuckDB, float in pandas.
  Default stays pandas (CI has no warehouse). Tests: 2 new in `tests/test_warehouse_tables.py`.
- **Phase 5b, step 1: Barcelona landed.** `config.FINISHING_SETS` (the 16 La Liga seasons) and
  `python -m src.landing --finishing` (entries built like the manifest's, but not written to it:
  no model reads them yet). 486 matches landed from the cache, 11,985 shots (158 to 971 per season).
  dbt 57/57 with them in. The per-90 outfield mart now has 2,228 rows (was 2,170: the extra 58 are
  Barcelona players in non-app seasons; the app reads by competition and season, so it is unchanged).
- **Phase 5b, steps 2-3: the finishing model (`src/finishing.py`, not in the app yet).** Every La
  Liga shot in the warehouse (17 seasons, 20,908 open-play shots; penalties out) scored by the
  production xG model, out of fold where it trained and by the fitted model elsewhere. Empirical
  Bayes: tau (the spread of skill between players, goals per shot) from the method of moments,
  90% interval by bootstrapping players, shrinkage toward the group. Simulation tests recover a
  known tau and find none when there is none. Real data, in three honest passes:
  1. Naive: tau 0.051 per shot. Wrong: Barcelona beat the model's xG in all 17 seasons (+255 goals
     over 8,148 shots, +0.040 per shot), a shift the whole team shares.
  2. Centred on the group's shift: tau 0.019-0.021, but still mixing team and player.
  3. Each shot's baseline raised by its *teammates'* surplus that season (leave-one-out, so Messi
     is not measured against himself; `team_adjusted_xg`): **tau 0.026 per shot, 90% interval
     0.015-0.030**, so players do differ. Messi +81 goals over his teammates' baseline (shrunk
     +59, weight 0.93); Iniesta -19 (-15).
  Split-half (alternating seasons, 26 players with 30+ shots in the first half): the shrunken
  estimate does **not** beat the group shift alone (MSE 0.00176 vs 0.00158; raw 0.00214). So: skill
  spread is there in-sample, and no gain predicting the other seasons, with 26 players. Not
  shown in the app until that is settled.

---

## 2026-11-14 (night) — dbt expansion, step 1 done: the player table from raw events

Guilherme: "commit e push e procede". The pilot went out as `b509319`; this is the rest of step 1.
- **Landing grew:** lineups, one row per stint (a player's spell in one position), and the
  season's match sheet (the one small download; team names are canonical there). Seven more
  event columns joined the contract, so the Premier League was re-landed with `--force`.
- **Models:** `stg_lineup_stints`, `stg_matches`; `int_team_names` (a source's team name → the
  sheet's), `int_player_match_minutes`, `int_player_seasons` (group by most season minutes),
  `int_player_match_actions` (16 counts, outfield and goalkeeper, as `count(*) filter`);
  marts `player_per90_outfield` and `player_per90_goalkeepers`. The 26 position labels are a
  dbt seed. The action lists and the per-90 SQL are macros, shared with the parity tests.
- **Parity with `app_data/player_per90.parquet`, Premier League 2015/16:** 300 outfield players
  and 27 goalkeepers, same group and nickname, same counts, minutes and rates within 1e-9.
  `dbt build`: 53 of 53. Negative controls: a misspelt tackle and punch failed both tests (300
  and 27 rows); sorting the group minutes the wrong way failed 171 players.
- **Without the raw layer** (CI): 20 nodes, green.
- **Then all nine leagues** (commit after `b205143`): `python -m src.landing --all` landed the
  manifest's 16 datasets (2,616 matches, 796 MB, ~12 min). The parity tests now compare every
  landed league of the app, joined on competition (a `competitions` seed carries the app's
  names): **2,170 players, the app's whole StatsBomb pool** (2,001 outfield + 169 keepers),
  57 of 57 in 58 s. `int_team_names` renamed 40 match/source names. A new warn-level test lists
  app leagues not landed, so parity on one league cannot pass for parity on nine.
  `tests/test_warehouse_seeds.py` keeps the two seeds equal to the Python constants.
- **CI and live app after `b205143`:** tests green; Home renders ("Scout by data").
- **Next:** the incremental model (step 2), dbt docs (3), the app as an exposure (4).

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

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
