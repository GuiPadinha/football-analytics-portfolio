# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-07-14): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-10-03 — Live app moved to Python 3.14

Guilherme deleted the 3.10 app and redeployed. The new app crashed with `ModuleNotFoundError:
matplotlib`: its Python was the Cloud default, 3.14, and the pinned numpy 2.2.6 has no 3.14 wheel,
so nothing beyond Streamlit's own packages got installed (ML_TOOLING.md). Guilherme asked why not
just use 3.14. No reason not to: it's the Cloud default and supported until 2030.
- numpy 2.2.6 → 2.3.5, the only pin without 3.14 wheels. Every other runtime pin has them.
- Verified on 3.14.7 (local venv) and 3.12: 171 tests pass on both. The app's tests also pass
  with only `requirements.txt` installed, as on the Cloud. Pipeline outputs are identical across
  the two versions. `metrics.json` is unchanged, while `feature_importance.png` moved in the third
  decimal from the numpy bump (ML_LEARNING_LOG.md).
- CI matrix is now 3.12 (local) + 3.14 (Cloud), with the `app-runtime` job on 3.14. The runner stays
  pinned to `ubuntu-24.04`, so the image changes only on purpose. 3.10 references updated in the
  docs.

**Keepers: only shots on target count** (Guilherme's call). The "shots faced in total" figure next to
save % is gone. A save of a shot going wide ("Shot Saved Off Target") no longer counts as a save,
because StatsBomb's own shot outcome calls that shot off target: 166 saves across 90 keepers, at
most 5 each. Median save % 70.1% → 69.8%. Outfield data and market values are unchanged. 12 of 123
keepers moved archetype (soft continuum). Keeper silhouette 0.238 at K=2 (was 0.237), 0.187 at
K=4 (unchanged). The rebuilt xG tables differed only by float noise from the numpy bump, so the
committed files were kept.

**Market value: Luis Suárez and 158 more** (Guilherme asked "what's happening to Suárez?").
Transfermarkt has two "Luis Suárez" profiles, and the matcher dropped any name with two
candidates before the club check could tell them apart.
- StatsBomb's lineups carry each player's popular name (`player_nickname`: "Koke", "Dani Alves",
  "Luis Suárez"), which is how Transfermarkt names players. It now flows into the per-90 tables
  as `nickname`.
- Matching is now two plain steps. `find_name_candidates` lists every Transfermarkt player matching
  the nickname or the full name, exactly or by distinctive words. `keep_candidates_at_the_right_club`
  keeps the one valued at the player's club that season (no candidate or two left = blank).
  Letters like Ł/Đ/ð are transliterated the way Transfermarkt writes them. The position tiebreak
  changed nothing any more and was removed.
- 1,168 → **1,327 of 1,347 (~99%)**: no existing match changed, and all 159 new ones were reviewed by
  hand (Suárez €90M, Koke, Isco, Fàbregas, David Silva, Dani Alves, Pepe, Mikel...). 20 stay
  blank (spellings with no shared word, bare common names like "Nacho", parent-club loanees).
- The pipeline's similarity cache rebuilt itself for the new column. `metrics.json`, PNGs and the
  manifest are byte-identical, and per-90 values and clusters are unchanged.

---

## 2026-10-02 → 10-03 — Deep audit: three shipped data bugs, then hardening

Guilherme wasn't confident two health checks had found everything and asked for a ground-up
audit until there's a clear green light. Every `src/` module, `app.py`, the tests, CI, configs and
docs were read, and each suspicion was checked against real data before acting.

**Wrong data the live app was showing (fixed, with tests that read the shipped tables):**
- *Goalkeeper save %:* median 38% instead of ~70%. StatsBomb's "Shot Faced" is only the remainder
  (off target/blocked), not all shots. Shots faced, saves (incl. penalty saves), goals conceded
  (incl. penalties) and save % are now counted correctly, verified on 150 matches. Shots faced
  became display-only (it measures the defence), like outfield `goals`.
- *Ligue 1 had 21 teams:* "Marseille"/"Olympique de Marseille" and "Caen"/"Stade Malherbe Caen"
  split players' seasons (Mandanda appeared twice). Team names are now mapped onto each match
  sheet; the pool grew from 1,635 to 1,638 players, and from 124 to 123 keepers.
- *Market value attached to the wrong people:* Dani Alves, Koke, Gabi, Danilo, Fernandinho, Jonny
  Evans, David Silva (€100k from a 2024 valuation) and more. A club check now requires
  Transfermarkt to place the player at the StatsBomb team's club within 12 months of the season:
  76 of 1,244 matches removed, 1,168 kept (~87%), all stars still correct.

**Also fixed:**
- *"Key Passes" label:* StatsBomb flags a pass that set up a goal as an assist and never also as
  a shot assist (0 overlaps in 120 matches), so the count excludes assists (Özil: 123 + 19). The
  feature stays as is: disjoint is cleaner for clustering. The label now reads "Key Passes (excl.
  Assists)" in the app and on the radar; only `player_radar_examples.png` changed.
- A page crash when fewer than three radar axes were selected. Goals Conceded is now drawn
  reversed on the radar.
- Cache writes are atomic (`net.write_atomically`). The manifest now pins the six similarity
  leagues too: 13 datasets, 2,109 matches.
- The game-state feature walks events in StatsBomb's own order; no shot was affected.
- Doc-lint now also checks the app numbers (players, keepers, market values, match rate) against
  `app_data/`.
- Removed dead config (`PHASE_4_*` lists) and a dead tuple branch; one home for `CLUSTER_K` and
  the outfield group list; shared GBM settings; corrected docstrings (CV "random slices",
  `--force` "re-pull", "offline" builds) and six app statements wrongly saying Leverkusen
  players have xG.
- Checked and left alone: CV scheme (mean 0.783 under every scheme, logged), dependency audit (no
  known vulnerabilities), statsbombpy row order (no impact).

**Verified:** 170 tests pass. The pipeline run gives `metrics.json` and all 9 PNGs byte-identical
(25 s now). `app_data/` was rebuilt with the fixes, and the notebooks re-executed.

---

## 2026-10-02 (cont. 2) — Closing the open items

Guilherme asked to close every open item (asking where needed). VS Code restarted, so both shells
now resolve `python` to 3.12.10.
- *Test crash found while doing it:* a subset of test files crashed with `0x80000003` (Tk backend
  plus AppTest threads). Present before any change; the full suite only passed by import-order
  luck. `tests/conftest.py` now forces Agg (ML_TOOLING.md). 152 passed.
- *Cache out of OneDrive:* new `FAP_CACHE_DIR` setting (`data_loader.resolve_cache_dir`; the default
  is still `data/cache`). The 4,378 files (8.5 GB) moved to a folder outside OneDrive in 1 s (same
  drive), and the variable is set for Guilherme's user account. The first cache miss in a run now
  prints where it downloads to, so a process that can't see the variable won't silently
  re-download gigabytes. +4 tests.
- *Faster app-data build:* `similarity.build_season_per90_tables` reads each match once for both
  the outfield and goalkeeper tables. With the cache outside OneDrive, `python -m src.app_data`
  went from 636 s to 191 s; all four tables are identical to the committed ones (to 1e-12) and no
  file was re-downloaded. +1 test (one pass, same output as the separate builders).

---

## 2026-10-02 (cont.) — Re-audit of the health check

Guilherme asked for a last check for loose ends before moving on. Every 2026-09-30 finding was
re-verified against the repo.
- **Closed, verified:** every item except the Cloud redeploy on 3.12, which is still pending and
  comes next. Full suite 147 passed. Every relative link and `#L` anchor resolves except two in the
  archive (below). README PNGs are tracked; CI is on actions v7 + `ubuntu-24.04`; the requirements
  split is in place. The Suárez correction is in DATA.md. `app_data/` rebuilt on 3.12 gives
  identical frames, so the committed 3.10 files were kept (diff ≤ 9e-16, see ML_LEARNING_LOG.md).
- **Killed:** a leftover `streamlit run` (port 8599, Python 3.10, `0.0.0.0`) from the 10-01
  browser check had been running for a day. No local Streamlit process is left (ML_TOOLING.md).
- **New, logged in ML_TOOLING.md:** this VS Code session still resolved `python` to 3.10.7, because
  it predates the PATH change (fix: restart VS Code). A form-feed byte had corrupted a path in
  ML_TOOLING.md's uv entry; it is repaired and the way it happened is noted.
- **New, logged as ROADMAP.md Phase 9 "Re-audit fixes":**
  - the similarity-table cache only checks that the file exists (latent; no number is wrong today);
  - the doc-lint covers 9 xG numbers, not the per-tournament AUCs or the silhouettes;
  - `src.app_data` takes ~10.6 min, re-reads events twice per competition, and isn't part of
    the pipeline;
  - three restructure leftovers (Makefile/INITIATIVE mentions, two dead archive links);
  - a list of the docs that need updating once the redeploy happens.

**Fixed the same day** (Guilherme: fix rather than just log; one commit + push each):
- *Similarity cache:* `pipeline.build_similarity_table` now rebuilds when the cached columns differ
  from the new `similarity.PER90_TABLE_COLUMNS`, which is also what `build_player_per90_features`
  returns. The real pipeline run on 3.12 detected the stale July pickle and rebuilt it on its
  own. `metrics.json`, the manifest and all 9 PNGs came out byte-identical. +1 test.
- *Doc-lint:* now also requires the six per-tournament AUCs in README/CLAUDE/MODULES and the
  silhouette range ("0.22–0.26") in CLAUDE/MODULES/PITCH. A deliberately drifted AUC is caught.
- *Restructure leftovers:* two dead archive links and the "Makefile" in the phase table.
- *Notebooks on 3.12:* all three re-executed on the `fap312` kernel with 0 errors (01 in 74s, 02
  in 14s, 03 in 11s). Every printed result is unchanged; only warning paths differ. 03 ran on the
  rebuilt similarity pickle. The kernelspec stays the portable `python3`.
- *Deferred, then done in the next entry:* speeding up `src.app_data` (a real per-90 cache was
  rejected: it would bring back the stale-cache risk).

**Next:** (1) restart VS Code, then redeploy the Cloud app on 3.12 and do its CI/doc pass;
(2) Phase 5a.

---

## 2026-09-30 → 10-02 — Health check after a 2.5-month gap, then a six-phase fix-up

Full detail (every finding, number and bug) is in [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)
under the same dates. One commit + push per item, CI green throughout.

- **Health check (09-30).** Read every doc and reviewed the code; re-ran the notebooks and checked
  CI, the live app and the upstream sources. Results were logged before any fix.
- **Phase 1, HTTPS + ingestion.** Avast rotated its root cert, so Python HTTPS was dead. New
  `src/net.py` routes downloads through the OS trust store (`truststore`) and adds
  retry/backoff. pip was upgraded (22 → 26). The lost certifi gotcha was recovered into
  ML_TOOLING.md.
- **Phase 2, quick wins.**
  - The Leaderboard is numeric again via `st.dataframe(placeholder="")`; Streamlit #7360 had been
    fixed upstream since 2025-11.
  - README images were committed; they had been broken on GitHub because `outputs/` was ignored.
  - The Module B narrative was rewritten for the 11-feature clusters. The Antonio one-man cluster
    no longer exists, but he's still the most extreme defender.
  - CI actions bumped to v7; plotly dropped.
- **Phase 3, `app.py`.** Text helpers moved to `src/presentation.py`, the Player explorer became a
  function, and `tests/test_presentation.py` + `tests/test_app_smoke.py` (AppTest) were added. A
  nested-bold blurb bug was caught along the way.
- **Phase 4, Python 3.12.** Requirements split into runtime vs. dev; statsbombpy/kloppy are now
  lazy-imported. CI runs a 3.10/3.12 matrix plus an `app-runtime` job. The local interpreter is
  3.12.10 (10-02), and the pipeline reproduces byte-for-byte on 3.12. *The Streamlit Cloud
  redeploy on 3.12 is still open* (approved by Guilherme, next session).
- **Phase 5, ingestion.**
  - A stale-cache bug was fixed (caches now check competition ids).
  - Women's EURO 2025 + Women's World Cup 2023 were wired in (0.763 / 0.777, no women's
    under-prediction).
  - "EURO 2024 is the floor" was corrected: it was false, because Copa América is lower.
  - The shot map was made deterministic (mplsoccer's grass texture used the global RNG).
  - Phase 4e (new sources + 360) was pinned.
- **Phase 6, declutter + docs.** `.vscode` untracked; Makefile and .claudeignore removed;
  conftest/ML_LEARNING_LOG moved; INITIATIVE merged into ROADMAP; PRODUCT_SPEC rewritten as the
  app's spec (458 → 168 lines); CLAUDE.md slimmed (218 → 154 lines); README docs map added; Phase
  9 regrouped.
- **Also logged:** World Cup 2026 is not in StatsBomb open data yet; the CC0 match-level dataset
  has no shot coordinates. paolomagni/football-platform is noted as a DE-showcase reference. The
  Luis Suárez market-value tiebreak and the sleeping live demo went to the backlog.

**Next:** (1) redeploy the Cloud app on Python 3.12, then drop 3.10 from CI; (2) Phase 5a,
uncertainty on goals − xG.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
