# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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

## 2026-10-10 — Redesign step 1b: the pages (in stages)

Stages, one commit + push each: **A** view models (done) · B Player page + top navigation + theme ·
C Compare · D Home, Leaderboard, How it works · E docs.
- **A. `src/profile.py`:** `prepare_pool` (adds each player's game, ranks every position group
  once), `build_player_profile` (strength/weakness bars, finishing or saves, price, men's and
  women's top-5 lookalikes, the short version) and `build_compare_view` (verdict + one row per
  stat). Pure functions, tested on the real tables (`tests/test_profile.py`); a profile builds in
  ~0.05 s.
- **A. `src/findings.py`:** the Home cards are computed, not typed (the mockup still said six
  leagues). Biggest over/under-performer against their chances (Agüero +6.5, Jerome −4.2), the
  share of valued men with a half-price top-3 lookalike (94% of 282 at €10M+; stated as a fact
  about the pool with its caveat, because "the biggest gap" picks Ronaldo vs. Bony), and the most
  valuable man whose closest woman has him as her closest man (Agüero ↔ Khadija Shaw, both Man
  City). `python -m src.findings` writes `app_data/findings.json` in ~16 s, and `src.app_data`
  calls it at the end of a rebuild.
- **B. The new shell, Home and Players pages.** `app.py` is now just the page frame and a top
  `st.navigation` (Home, Players, Compare, Leaderboard, How it works); each page is a script under
  `views/`. `views/components.py` holds the stylesheet (the mockup's palette, also in
  `.streamlit/config.toml`), the escaped HTML builders and a native Altair shot map, cropped to
  where the player shoots from. `views/data.py` caches the pool. Home shows the four computed
  cards; Players is the three questions, with men's and women's lookalike tabs (own game first) and
  a "similar style is not the same level" caveat next to prices. The old radar, percentile chart,
  sidebar filters and Euclidean/σ captions are gone from player pages. Compare, Leaderboard and
  How it works still run the old code, moved verbatim to `views/legacy.py` until C and D.
  Checked in a real browser (Edge via Playwright): a star, a keeper and a women's player. The smoke
  tests were rewritten for the new pages (15 AppTest cases, `tests/test_components.py`).
- **C. Compare.** Two search boxes, a card per player (the colours run through the bars), the
  verdict, a side-by-side per 90, then "are their goals real?" (or save % for keepers). Any two
  outfielders, whatever their position; a keeper against an outfielder gets a plain warning. The
  player page's "Compare X with another player" button prefills player A. Checked in Edge.
- **D. Leaderboard, How it works, cleanup.** The Leaderboard is one sortable table (game, position
  and name filters; a row opens the player). How it works holds all the method, with every figure
  from `metrics.json` or computed live (the per-tournament chart is native). `views/legacy.py`
  (the old code) is deleted, and the app no longer imports matplotlib, so matplotlib, mplsoccer
  and seaborn moved from `requirements.txt` to `requirements-dev.txt`; a runtime-only Python 3.14
  environment runs the smoke tests (the CI `app-runtime` job does the same).
- **E. Docs:** PRODUCT_SPEC rewritten (views, backend map, data flow, decision log, known gaps),
  README, PITCH demo script, ARCHITECTURE, ROADMAP and CLAUDE.md updated.
- Small: `format_rate` is public (two decimals under 1: "0.38 per 90"), and the label reads
  "Non-Penalty Goals" (so `outputs/player_radar_examples.png` was regenerated with the hyphen; the
  other pipeline outputs and `metrics.json` are unchanged).
- **Verified:** 260 tests pass on 3.12; a clean Python 3.14 environment with only
  `requirements.txt` (no matplotlib) passes the smoke and presentation tests (57). Pages checked in
  Edge: Home, Players (star, keeper, women's), Compare, Leaderboard, How it works. A Vega bar chart
  drew shifted off-screen (a `translate(1485,0)` autosize quirk with long labels), so the shot-model
  scores are HTML bars in the site's own style.
- **Open:** the redesigned live app has not been looked at by Guilherme yet (see CLAUDE.md's next
  steps).

---

## 2026-10-06 — Redesign step 1a: the rule-based text

Guilherme approved the plan, plus the league-adjusted ranking below ("go ahead, log all that").
- **`src/narrative.py` (new).** The player page's short version: standout stats, then finishing
  (or saves), then price. Without a price (women's football, unmatched men) the closest match in
  each game takes the last slot. Compare's verdict: closeness rank, each side's leads, keepers'
  save %, then the price gap. Every threshold is a named constant calibrated on the real pool.
- **`similarity.py`:** `rank_matches` is the full ranking (`find_similar_players` is now its top n,
  output unchanged). `league_adjusted_percentiles` is the new basis for "top N%".
  `pair_closeness` is Compare's rank, in the right space for each position pair. Also
  `config.GENDER_BY_COMPETITION`, `presentation.ordinal` and `presentation.popular_name`.
- **Decisions, each measured first** (ML_LEARNING_LOG.md has the numbers):
  - Percentiles rank league standing, not raw rates (a ~6-point mean shift, up to ~50).
  - Finishing is quoted as exact odds for an average finisher ("about one season in 22").
  - Closeness is a rank, not a distance cutoff.
  - Mixed-position pairs get their own space, because `_lz` is position-relative.
  - A lead needs both a league-SD gap and a visible raw gap.
- **Checked on 16 players and 8 pairs:**
  - Mahrez reads almost word for word like the mockup.
  - Benzema–Pajor: "closest match among 194 women's forwards".
  - Also checked: keepers, women, players with no xG, Kanté ("too few chances to judge"), and a
    keeper against an outfielder (refused).
  - Reading the output changed three rules: leads must be visible in the raw numbers, all-below-
    median keepers are "quiet keepers", and women get the cross-game sentence.
- **Verified:** 233 tests pass, and the pipeline's `metrics.json`, PNGs and manifest are
  byte-identical. `app.py` is untouched, so the live app doesn't change until step 1b.
- **Open for 1b:**
  - 159 players have no nickname and a long legal name ("Mary Alexandra Earps", Liga F double
    surnames).
  - The page must say "similar style, not the same level" next to prices.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
