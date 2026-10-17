# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-10-17 (late afternoon) — Loose ends: Home price card, initials, page width, after-push check

Guilherme asked for the two open items, a fix for the side margins ("I don't love the space on
both sides of every page"), and an always-on look at the live app after each push.
- **Home price card covers both men's seasons.** Each man is matched within his own provider,
  as on his page. It now reads 91% (681 of 749). The other three cards can't include Wyscout:
  finishing needs xG (PL 2015/16 only), and the cross-game card needs women's leagues.
- **No Wyscout name is left as an initial.**
  - `find_name_candidates` also matches "D. Alli" by surname and initial. The surname is
    compared without spaces, because "N'Diaye" normalises to "n diaye" against Transfermarkt's
    "Ndiaye", but it must be whole words.
  - `app_data.spell_out_initials` then shows the confirmed Transfermarkt name: Dele Alli (who
    also gained his €80M value), Badou Ndiaye, Keita Baldé.
  - 2,911 values. StatsBomb's matches are unchanged.
- **Wider pages.** Content max width went from 1200 px to 1520 px. Running text is capped at
  ~980 px so it stays readable, and mobile padding shrinks. The page title no longer hides under
  the top bar ("HOW IT WORKS" was cut off, live too).
- **After-push check:**
  - CI comes from GitHub's REST API (no `gh`). The live app is checked with the new
    `tools/screenshot.py` (ML_TOOLING.md has why the plain approach failed).
  - Anonymous visits to the live URL got "You do not have access… / 404" while Guilherme, signed
    in, saw the app. He was asked to check in an incognito window, since it may be private.
- **Verified:**
  - 285 tests pass.
  - Real-browser screenshots at 1900 px (local): Home, and How it works before and after.
  - The rebuild's xG tables were float-noise only and restored from git.

---

## 2026-10-17 (afternoon) — Wyscout 2017/18 (Phase 4e): xG test rejected, ingestion built

Guilherme OK'd the redesigned live app by eye ("looked good"), then chose "xG first, then a
separate 2017/18 pool", in three stages (A ingestion, B pool plumbing, C pages), one commit each.
- **Probe** (scratchpad, not in the repo): figshare collection 4415000, CC BY 4.0, 77 MB zip.
  - Per-90 definitions differ from StatsBomb's: key passes 0.29×, interceptions 4.2×, and no
    pressures or blocks exist. So the players can't share a pool with StatsBomb players.
  - Its pitch is landmark-normalised, so coordinates go through kloppy's transform.
- **xG with 43k Wyscout shots added: rejected.** Mean held-out AUC went from 0.7790 to 0.7773, and
  calibration got worse. A learning curve shows the logistic is saturated at ~1k shots, so it is
  feature-limited. Numbers are in ML_LEARNING_LOG.md (Module A); production xG is unchanged.
- **Stage A, `src/wyscout.py` (new):**
  - Downloads into `<FAP_CACHE_DIR>/wyscout/`.
  - Minutes come from match sheets (red cards and the `"null"` substitutions handled).
  - Positions come from the Wyscout role. Names are unescaped (`Kanté`), and popular names
    are rebuilt ("L. Messi" → "Lionel Messi", "D. Faraoni" → "Davide Faraoni").
  - Nine outfield stats (`WY_ACTION_COLUMNS`) and three keeper stats.
  - `config.Dataset` gained `provider`; `config.WYSCOUT_SETS` holds the five leagues.
  - Real build: 1,503 outfield + 121 keepers, ~10 s per league.
  - Spot checks match the record books: Salah 32, Messi 34, Ronaldo 26, Immobile and Icardi 29,
    Lewandowski 29, Cavani 28, 18 Bundesliga teams. Kane shows 29, not 30, because his
    Stoke goal was credited after review. Median keeper save % is 0.69–0.71 (StatsBomb 0.70).
- **Verified:** 271 tests pass, 11 of them new in `tests/test_wyscout.py`. The app is unchanged
  until stage B.
- **Stage B, plumbing (code only, `app_data/` not rebuilt, so the live app is unchanged):**
  - Every "which columns" question now goes through `similarity.feature_columns_for(group,
    provider)`.
  - Percentiles are computed per (provider, position). Lookalikes and Compare stay within one
    provider, and Compare refuses a cross-provider pair with a page-ready message.
  - Home findings stay StatsBomb-only.
  - `app_data` builds and clusters the Wyscout tables after the StatsBomb ones, so the StatsBomb
    rows keep their order. Market values get a 2018-01-01 anchor for the five 2017/18 leagues.
  - **Key collision:** 329 Wyscout (player, team) pairs already exist in the StatsBomb 2015/16
    rows (Kane at Tottenham). Without a fix they would have picked up the other season's xG and
    value. Wyscout's `player` key now carries " · 2017/18", pages show `nickname` (always filled),
    and `normalize_name` drops the suffix for Transfermarkt matching.
  - 273 tests pass.
- **Stage C, the data and the pages (live):**
  - Rebuild in ~9 min: **3,794 players** (2,170 StatsBomb + 1,624 Wyscout) and 2,909 market
    values, ~98% of the men.
  - The StatsBomb rows, their values and `findings.json` came out byte-identical to the previous
    build. Wyscout values are dated 2017-06 to 2018-06, and the stars look right (Messi and
    Neymar €180M, Kane €120M).
  - Popular names were refined:
    - a lone surname gets the first given name ("Iniesta" → "Andrés Iniesta", "Lombán" →
      "David Lombán");
    - an initial can match a hyphenated given name ("E. Choupo-Moting" → "Eric Choupo-Moting").
  - Pages:
    - the player page tags "(Wyscout data)", shows only the men's list, and its caption says
      why;
    - Compare refuses a cross-provider pair (Kane 2015/16 vs Kane 2017/18);
    - How it works covers the second provider, its silhouettes (Wyscout 0.23–0.28 at K = 2) and
      the updated limits;
    - Leaderboard help text and the Home footer were updated.
  - Pool numbers were updated in CLAUDE.md, the README, PITCH.md and DATA.md (the doc-lint
    caught all of them).
  - The rebuild also rewrote `player_xg_table` and `shots_with_xg`, differing only by float
    noise (≤ 2.4e-13 in xG, same refit). They were restored from git so the commit carries only
    real changes.
- **Verified:**
  - 283 tests pass, including new real-data tests: Salah 2017/18's profile, the provider
    refusals, unique keys, and blank (not zero) pressures/blocks for Wyscout.
  - App smoke tests open a Wyscout page and both kinds of Compare.
  - Read by eye: Salah's lookalikes are Agüero, Immobile, Depay, Dybala and Mbappé. Coutinho
    shows twice in Messi's list (Liverpool + Barcelona, a January transfer), as for StatsBomb
    players.
- **Unresolved (handled in the next entry):**
  - Not checked in a real browser.
  - Home's finding cards stay StatsBomb-only.
  - A few Wyscout names stay as initials ("D. Alli").

---

## 2026-10-17 — Cleanup after the move to Drive; MPG Stats looked at (no code changes)

- **Drive clone checked:** clean, in sync with `origin/main`, and a test commit (`00e8edb`) was
  made and pushed from it, so the gitdir-outside-Drive setup works (it stays; ML_TOOLING.md says why).
- **Obsolete copies deleted:** `C:\dev\football-analytics-portfolio` (clean, level with origin at
  `947ad38`; `data/` identical to the Drive clone, only three older docs differed) and the
  corrupted-`.git` copy under `OneDrive ISCTE (arquivo)\...\Foot_Analytics_Port`. That one left an
  undeletable empty `.git`, removed by trashing the folder through the Drive API (ML_TOOLING.md).
  The snapshot zip stays; the original OneDrive ISCTE folder is read-only and was not touched.
- **MPG Stats (mpgstats.fr) evaluated as a data source and parked:** fantasy-game ratings, minutes,
  goals and prices; no shots, no x/y; source and licence not stated. "Real and current" was not
  verified. Findings and a side lead (clubelo.com for Module C) are in DATA.md.
- **Housekeeping:** this file passed 150 lines, so the three 2026-10-02/03 entries moved to
  PROGRESS_ARCHIVE.md, and the "Test commit" line left at the bottom by the test commit is gone.
- **Verified:** docs-only change; the 8 tests in `tests/test_metrics.py` (the doc-lint) pass. The
  full suite was not re-run.
- Next steps unchanged (CLAUDE.md "Next session, start here").

---

## 2026-10-10 (evening) — Moved to Google Drive; no code changes

OneDrive ISCTE is being archived into Google Drive, so the working tree now lives in
`G:\My Drive\Projetos\football-analytics-portfolio` with `.git` kept **outside** Drive
(`C:\dev\gitdirs\football-analytics-portfolio.git`, because Drive corrupted `.git/index`), the venv
in `C:\Users\guilh\venvs\football-analytics-portfolio`, and the cache still in `C:\Users\guilh\fap-cache`.
Details in CLAUDE.md ("Where things live") and ML_TOOLING.md. The 33 git-ignored `data/` files were
copied and size-verified; a full snapshot of the old working copy is in Drive under
`OneDrive ISCTE (arquivo)\_snapshots\`. 260 tests pass in the new location. Next steps are unchanged
(CLAUDE.md "Next session, start here").

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
