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
