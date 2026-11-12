# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-03): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

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
  licence" section crediting the four sources. The code is now MIT-licensed (`LICENSE`); Claude
  picked MIT under the autonomy given, so Guilherme should confirm or change it.
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
  keep-alive now opens that page too, since Home alone hid the break (ML_TOOLING.md).
- **Verified:** 285 tests pass locally before any change; CI green on `cddb68b`; the rewritten
  tool finds the live Home in 8 s and returns 1 for a marker that isn't there.

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
  - `86cf569`: CI green.
  - **Resolved:** the app had been running on another subdomain
    (`football-analytics-portfolio-tzl6…streamlit.app`), so every documented link hit "You do not
    have access… / does not exist". Guilherme restored `gpfootball-analytics-portfolio`, and an
    anonymous rendered visit now shows the latest deploy (3,794 players, 2,911 values, wider
    pages).
- **Verified:**
  - 285 tests pass.
  - Real-browser screenshots at 1900 px (local): Home, and How it works before and after.
  - The rebuild's xG tables were float-noise only and restored from git.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
