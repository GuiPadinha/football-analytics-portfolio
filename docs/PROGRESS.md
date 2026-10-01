# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-07-14): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-10-01 — Executing the health-check plan, one commit per phase

Guilherme approved the 2026-09-30 plan. Every health-check item gets fixed before any further
model work. He asked for one commit + push per item, and for a "pin" on expanding data ingestion
(Kaggle and other sources) and on using 360. The order was changed to put HTTPS first, because it
unblocks pip and every data pull. Phases:
(1) HTTPS + ingestion resilience, (2) quick wins, (3) `app.py` restructure + tests,
(4) Python 3.12 readiness, (5) ingestion: women's tournaments + the data/360 pin, (6) docs
restructure.

**Phase 1: HTTPS + ingestion resilience.**
- *Fixed the machine:* upgraded pip 22.2.2 → 26.2.1, bootstrapped with a throwaway CA bundle. It
  now verifies against the Windows store by default. Also installed `truststore` 0.10.4.
- *Fixed the project:* new `src/net.py`.
  - `use_os_trust_store()` (`truststore.inject_into_ssl()`, a no-op when `truststore` is absent)
    runs at `data_loader` import and before the Transfermarkt download.
  - `with_retries()` retries 429/5xx/dropped connections with exponential backoff and honours
    `Retry-After`. A 429 starts at 30s, a dropped connection at 2s. A 404 or a certificate error
    fails fast.
  - Every StatsBomb fetch (`_disk_cached`, `load_competitions`, `load_matches`) and the
    Transfermarkt download go through both.
- *Tests:* `tests/test_net.py` (11 tests, offline, injected `sleep`) caught a real bug while being
  written. `urllib.error.HTTPError` proxies unknown attributes to its response file, so
  `getattr(exc, "response", None)` raised `KeyError` instead of returning `None`; it's now
  type-checked first.
- *Verified live:* `load_competitions()` (80 competitions), `load_matches` for Women's EURO 2025
  (31 matches), and a Transfermarkt GET all work from Python again. Notebook 01 re-executes clean
  (it had failed on SSL yesterday). Full suite: 100 passed.
- *Docs:* ML_TOOLING.md (the applied fix), ARCHITECTURE.md + CLAUDE.md layout (`net.py`). Also
  archived the two 2026-07-14 entries to keep this file short.

**Phase 2: quick wins.**
- *2a, Leaderboard back to numeric columns:* `placeholder=""` replaces the six hand-formatted
  text columns, so click-to-sort is numeric again (verified in Edge: "Non-pen goals" descending
  reads 37, 33, 31, 29 …). Goalkeeper rows stay blank rather than "None". Market value is now a
  numeric € millions column. Side finding while checking the output: **Luis Suárez (Barcelona) has
  no market value.** Transfermarkt has two "Luis Suárez" profiles with the same position (born
  1987 and born 1997), so the matcher correctly leaves him unmatched. But DATA.md claims he was
  one of the spot-checked stars that resolved. That claim is fixed in the docs phase, and a
  birth-date/club tiebreak goes to the backlog.
- *2b, README images:* the full pipeline re-run (89s, from cache) left `metrics.json` and
  `data/manifest.json` **byte-identical**, so the rebuild is still reproducible after 2.5 months.
  Its 9 PNGs (~3.1 MB, the EURO 2024 shot map alone is 2.1 MB) are now committed through a
  `!outputs/*.png` exception in `.gitignore`. README's 8 embedded charts render on GitHub for the
  first time.
- *2c, Module B narrative:* recomputed notebook 03's clustering with the current 11 features and
  rewrote every stale claim to match. That covered README's cluster examples and neighbour table
  (its "all five lists" was also wrong: the table has three rows), MODULES.md's
  "validated against" line, ROADMAP 6c, and two `src/` docstrings that still called Antonio a
  mislabelled winger. Notebook 03 was re-executed in place and its outputs now match
  `metrics.json` (0.223/0.256/0.244). The most interesting finding: **Antonio is still the most
  extreme defender** (nearest neighbour 6.3 standardised units away, 2–3× typical), but K-means
  now spends its fourth defender cluster on a real archetype, ball-playing centre-backs
  (Alderweireld, van Dijk, Koscielny), and absorbs him into the attacking full-backs as their
  farthest member. A hard cluster label can hide an outlier as easily as reveal one (logged in
  ML_LEARNING_LOG.md).
- *2d/2e, CI + deps housekeeping:* `actions/checkout@v7` + `actions/setup-python@v7` (both Node
  24; CI had warned that v4/v5 target the deprecated Node 20). `runs-on` pinned to `ubuntu-24.04`,
  because `ubuntu-latest` moves to Ubuntu 26 on 2026-10-19 and this job still tests Python 3.10.
  Dropped the unused `plotly`. `seaborn` stays pinned: nothing here imports it, but `mplsoccer`
  depends on it, so the pin keeps a future release from breaking the plots. The fuller
  requirements split (app runtime vs. dev) is Phase 4.

**Phase 3: `app.py` restructure + tests.**
- Pure presentation helpers moved to a new `src/presentation.py`: `percentile_tier`,
  `format_percentile`, `style_intensity_label`, `build_scouting_blurb`, `format_market_value`,
  `lookup_market_value`, `STAT_LABELS`, `SIGNATURE_STATS_BY_POSITION`. There is also a new
  `feature_columns_for(position_group)` that replaces two copies of the goalkeeper-vs-outfield
  branching.
- The Player explorer was ~430 lines of top-level script; it is now `render_player_explorer()`,
  like the other three views.
- Dated history narration in comments was trimmed to the "why" (the 18-line search-box saga is
  now 5 lines pointing at PRODUCT_SPEC.md). `app.py` went from 1,406 to ~1,190 lines.
- New `tests/test_presentation.py` (34 cases) and `tests/test_app_smoke.py` (9 `AppTest` runs:
  every view, an outfield player in and outside the xG set, a goalkeeper, the row-click jump,
  same- and cross-position Compare). These are the checks earlier sessions ran by hand and never
  committed. Full suite: 143 passed.
- *A test caught a markup bug:* `build_scouting_blurb` wrapped already-bolded traits in another
  `**…**`. It turned out to be invisible, because Streamlit's renderer nests the `<strong>` tags
  (checked in Edge), but it relied on renderer leniency. Fixed; each trait is now bold on its own,
  like the Style archetype sentence.
- Verified in a real browser after a clean server restart: Harry Kane's full page renders the
  same as before (blurb, stats, archetype, radar, neighbours, Finishing 25 / 20.8 / +4.2, shot
  map).
- *Docs:* ARCHITECTURE.md import graph. It had also drifted: `app.py` was missing entirely, and
  `config`/`models`/`pipeline`/`similarity` didn't list `app_data.py` as a consumer. Also the
  CLAUDE.md layout, and the ROADMAP.md pointer to the blurb.

**Phase 4: Python 3.12 readiness.**
- *The app no longer needs the ingestion libraries.* `data_loader` imports `statsbombpy`/`kloppy`
  lazily (`_statsbomb()`), so importing `similarity` (and through it `app.py`) loads neither.
- *Requirements split.* `requirements.txt` is now the app's runtime only: streamlit, pandas,
  numpy, scikit-learn, matplotlib, mplsoccer, seaborn, pyarrow. That's what Streamlit Cloud
  installs; it no longer pulls jupyter/pytest/statsbombpy/kloppy. `requirements-dev.txt`
  (`-r requirements.txt` + ingestion, truststore, jupyter, pytest) is for development.
- *Verified on 3.12 before touching CI.* Two isolated `uv` envs on CPython 3.12.14, short path
  under `%TEMP%`, deleted afterwards:
  - runtime-only + pytest: full suite **143 passed**, with statsbombpy/kloppy not even installed;
  - full dev env: installs cleanly, `load_competitions()` works through `truststore`, and a
    pickled events cache written by 3.10 reads fine on 3.12.

  The same pins work on both versions; no version bumps were needed.
- *CI:* the `pytest` job is now a 3.10/3.12 matrix on `requirements-dev.txt`. A new
  `app-runtime` job installs only `requirements.txt` on 3.12 and runs the app smoke tests, which
  catches the app depending on a dev-only package before the live deployment does.
- *Left for Guilherme,* both in ROADMAP.md's Phase 9 item: redeploy the Cloud app on 3.12
  (delete + redeploy, same subdomain) and switch the local interpreter. Then drop 3.10 from CI.
- *Docs:* README "Running it", CLAUDE.md layout, ROADMAP.md, ML_TOOLING.md (a venv under the
  ~180-character scratchpad path fails with `0xc0000106` = STATUS_NAME_TOO_LONG; uv needs
  `UV_SYSTEM_CERTS=1` behind Avast).
- *A loose end from 2b:* notebooks 02/03 also `savefig`'d the same eight PNGs the pipeline writes.
  Re-running notebook 03 (item 2c) rewrote `player_radar_examples.png` with slightly different
  bytes, which would have caused committed-file churn depending on which ran last. The notebooks
  now display their figures inline only. A comment names `python -m src.pipeline` as the one
  producer. Both were re-executed (0 errors) and `outputs/` stayed untouched.

**Phase 5: ingestion.**
- *5a, latent stale-cache bug fixed first:* `pipeline.py`'s three shot-table caches were keyed only
  on "the file exists". So adding a tournament to `GENERALISATION_TEST_SETS` would have silently
  reused the old table, and the new tournament would never have reached `metrics.json`. New
  `_cache_matches_datasets` compares the cached `competition_id`s with the config list and
  rebuilds on any mismatch. Two new tests cover the cases: a config that gained a tournament, and
  a legacy cache with no competition ids.
- *5b, women's tournaments pulled and scored:* new `Dataset.gender` field, plus
  `WOMENS_WORLD_CUP_2023`. Both women's tournaments are in `GENERALISATION_TEST_SETS`. The new
  staleness check rebuilt the table on its own; there was no 429 this time. 7,215 held-out shots
  across 6 tournaments.
  - ROC-AUC: WWC 2023 **0.777**, Women's EURO 2025 **0.763**, inside the men's 0.763–0.808 band.
  - Goals ÷ xG: 0.98 and 0.83, so no women's-specific under-prediction. The Women's EURO Brier
    (0.092, worst) reflects its higher base goal rate (logged in ML_LEARNING_LOG.md).
  - **Correction:** "EURO 2024 is the floor" had been false since July, because Copa América's
    0.763 is lower. Fixed in README, MODULES, PITCH, CLAUDE.md and the app's copy (whose
    hardcoded "4 tournaments" now reads from `metrics.json`).
  - The headline 0.765 and `metrics.json`'s `xg` block are unchanged.
- *5c, a non-deterministic PNG:* `euro2024_shot_map.png` changed on every pipeline run. mplsoccer
  paints the "grass" pitch from the *global* `np.random`. `plot_shot_map` now seeds just that draw
  and restores the caller's RNG state. Two runs now give identical hashes, and
  `tests/test_visualisation.py` guards both properties.
- *5d, the pin* (ROADMAP.md Phase 4e):
  - New StatsBomb leagues checked: Liga F, Serie A Women and NWSL are full seasons; MLS 2023 is
    Inter Miami only (6 matches).
  - 360 probe on one match: 100% of shots have a freeze frame, 2.7 MB/match, ~800 MB for all six
    360 datasets. `config.SETS_WITH_360` now derives from a new `ALL_DATASETS` (it used to skip
    WC 2022/AFCON).
  - External sources ranked: Understat, then the Wyscout public set, then PFF WC 2022 tracking.
  - Two more backlog items in Phase 9: the Suárez market-value tiebreak (DATA.md's
    spot-check claim was false), and the live demo sleeping.

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

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
