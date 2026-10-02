# Roadmap — Framework Hardening & Expansion

→ [CLAUDE.md](../CLAUDE.md) | Session-by-session detail: [PROGRESS.md](PROGRESS.md)

One file for where the project is going: the phase table (status), a one-line-per-milestone
index, and the detailed task list for each phase. (Until 2026-10-02 the table and index lived in
a separate ROADMAP.md; merged so there's one place to look.)

**Origin:** after the original S1–S8 build (2026-06-28/29, logged in
[PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)), a code review surfaced correctness, methodology,
structure and scaling gaps, and an unclear product story. On 2026-07-02 that whole backlog was
folded into one execution-ordered program, Phases 0–9, with an engineering & reproducibility
spine first. Each phase is independently executable; conceptual framing lives in
[FRAMEWORK.md](FRAMEWORK.md).

---

## Phases

**This table is the single source of truth for phase numbering** — don't copy it elsewhere. Phases 3–6 were renumbered on 2026-07-02 (see the "Was" column) when the review backlog
was folded in — the old Phase 3 (360 xG) and Phase 5 (product) moved *later* behind the unblockers.

| Phase | Focus | Was | Status |
|---|---|---|---|
| **0** | Framework charter (FRAMEWORK.md, this roadmap, CLAUDE.md entry) | 0 | ✅ Done |
| **1** | Foundation: `config.py`, per-match cache, penalty/shootout fix, pinned deps, robustness fixes, first tests | 1 | ✅ Done |
| **2** | ML rigor: cross-validation, scaled logistic, baseline feature engineering, calibrated GBM, silhouette, minutes-weighted position | 2 | ✅ Done |
| **3** | Engineering & reproducibility spine: CI, `pipeline.py`, `metrics.json` single-source, data manifest | *new* | ✅ Done |
| **4** | Multi-competition ingestion + data expansion: config-driven pipeline, Module A generalization, Module B cross-league | 4 (reshaped) | 🟡 4a–4d done (4c closed 2026-10-01: 5 held-out tournaments incl. 2 women's); **4e pinned** (new sources + 360, see Phase 4e below) |
| **5** | xG uncertainty + hierarchical/empirical-Bayes finishing model; header/foot interaction; calibration by stratum | *new* | ⬜ Not started |
| **6** | Module B upgrades: Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features | part of old 6 | ⬜ Not started |
| **7** | New model: 360-context xG + post-shot xG (xGOT) | **3** | ⬜ Not started |
| **8** | Product layer: lightweight Streamlit app — [spec done](PRODUCT_SPEC.md) 2026-07-01, minimal v1 built 2026-07-04 | **5** | ✅ Done — [live](https://gpfootball-analytics-portfolio.streamlit.app) (deployed 2026-07-09) |
| **9** | Opportunistic: xA/chance-creation model, Module C (PUP), remaining alt-models (hierarchical, cosine, monotonic GBM), 2026 World Cup predictive model (data-availability check first) | old 6 + Module C | 🟡 Ongoing: market value, Compare players, scouting blurb shipped (2026-07-14); Python 3.12 repo + local done (2026-10-02, Cloud redeploy pending); the rest not started — see Phase 9 below |

Execution order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, with 9 opportunistic. Per-phase task lists
follow further down this file.

**Sequencing rationale (revised from the earlier "data expansion first" call):** the data manifest
is a prerequisite of the config-driven ingestion pipeline, `metrics.json` should exist before we
10× the data and the numbers, and the spine is the cheapest credibility badge that also
structurally kills the doc drift — so every later phase writes into a clean, single-source system.

---

## Milestones

**This is a one-line-per-milestone index, not a second history** — full narrative detail for every
entry below (what changed, why, numbers, bugs found) lives dated the same in
[PROGRESS.md](PROGRESS.md) / [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md). Kept short deliberately
(trimmed 2026-07-13, previously ~150 lines duplicating that narrative) so this file stays the
"where-are-we" tracker its intro promises, not a file that has to be kept in sync with PROGRESS.md
by hand.

- **2026-06-29** — Initiative kicked off; `FRAMEWORK.md` charter written; Phase 0 started.
- **2026-06-29** — Phases 0 and 1 done (config/per-match cache/first tests foundation).
- **2026-06-30** — Caches rebuilt on the fixed pipeline; penalty-shootout fix confirmed in the
  numbers (test ROC-AUC 0.798 → 0.765).
- **2026-06-30** — Phase 2 Module A (xG) rigor done: scaled logistic, 5-fold CV, baseline ladder,
  calibrated GBM (still trails logistic).
- **2026-06-30** — Phase 2 Module B (similarity) rigor done → **Phase 2 complete**: silhouette
  score, minutes-weighted position assignment.
- **2026-07-02** — Reprioritisation: whole review backlog folded into this Phase 0–9 table (old
  Phase 3/360-xG → 7, old Phase 5/product → 8, old Phase 6 + Module C → 9).
- **2026-07-03** — **Phase 3 complete**: `pipeline.py` + Makefile, a headless reproducible rebuild.
- **2026-07-04** — Phase 4 data pulled (24 datasets), not yet wired; **Phase 8 minimal build
  jumped ahead** of strict phase order (demo-driven).
- **2026-07-05** — Phase 4b wired into the app (cross-league similarity pool, 1,511 players);
  goalkeeper features built, not yet wired; app UX/theme pass.
- **2026-07-09** — **Phase 4c mostly done**: Module A generalisation scored on 3 of 4 held-out
  tournaments (Women's EURO 2025 rate-limited, resumable).
- **2026-07-09 (cont.)** — **Phase 8 deployed** to Streamlit Community Cloud → **Phase 8 fully
  done**.
- **2026-07-13** — Pitch-prep app UX pass: a new "About & Roadmap" sidebar view, headline stats
  refactored to whole-number counts, the Phase 4c generalisation chart wired into the app for the
  first time.
- **2026-07-13 (cont. 3)** — Goalkeepers wired into the app (124 keepers, own feature set, not yet
  clustered); Leaderboard copy expanded.
- **2026-07-13 (cont. 4)** — Visual/brand pass: Leaderboard name/position filters, a proper Player
  explorer intro, a reusable page-header brand badge + richer sidebar, About & Roadmap expanded
  with "Data used"/"How each model works" sections and a Module C roadmap mention.
- **2026-07-13 (cont. 5)** — Doc-interdependency review (4 real drift fixes) + a Style archetype
  panel, percentile bar charts, and Leaderboard diverging colour (outfield-only at this point).
- **2026-07-13 (cont. 6)** — **Phase 4b's cross-league normalisation open item resolved** —
  `similarity.normalize_within_competition` league-adjusts per-90 features before
  clustering/`find_similar_players` compare across leagues; goalkeepers K-means clustered for
  the first time (K=4, same archetype-granularity call as the outfield groups) and now share the
  Style archetype panel; the Leaderboard's long-standing "None" cell-text cosmetic bug fixed
  (confirmed as a real, still-open upstream Streamlit limitation, GitHub issue #7360 — fixed at
  the data layer, not the config layer). 75 tests green (72 + 3 new for the normalisation
  function), `metrics.json` unchanged (byte-identical — this pass's scope is the app's wider
  pool, not the notebook's narrow one).
- **2026-07-14** — **Phase 9 backlog: market value + Compare players view, both built.**
  `src/market_value.py` resolves a Transfermarkt valuation per player by name (no shared ID exists
  between StatsBomb and Transfermarkt) — a rarity-weighted token-matching approach, fixed twice
  against real bugs found in real data (a common-surname collision that nearly mismatched Neymar;
  a name-particle-only false match), ~90% match rate on the four men's competitions (1,215 of
  ~1,344 players); shown on a player's page, "players like X," and the Leaderboard. New "Compare
  players" sidebar view puts any two players side by side — market value/Finishing always compare;
  radar/signature-stats/percentiles only when both share a position group. 86 tests green (75 + 11
  new), `metrics.json` unchanged.
- **2026-09-30 / 10-01** — Repo health check, then its plan executed phase by phase: HTTPS fixed
  via the OS trust store + retrying downloads, Python 3.12 readiness (CI matrix), `app.py`
  restructure + app tests, and **Phase 4c closed**. Women's EURO 2025 + Women's World Cup 2023
  are now scored (0.763 / 0.777). **Phase 4e** (new data sources + 360) is pinned.

---

## How to resume

1. Read `CLAUDE.md` and the newest [PROGRESS.md](PROGRESS.md) entry.
2. Pick the first ⬜ phase in the table above, or a Phase 9 item.
3. Work from that phase's task list below.
4. Close the session per CLAUDE.md: update the Status column and Milestones here, add a PROGRESS.md
   entry.

---

## Phase 3 — Engineering & reproducibility spine  ✅ Done

Cheapest credibility badge for the target roles, and it structurally kills the doc drift so every
later phase writes into a single-source system. Goes first because 3e (manifest) is a prerequisite
of Phase 4's ingestion pipeline and 3b (`metrics.json`) must exist before the data/number 10×.

- **3a — De-drift** (docs done 2026-07-02): canonical phase table in INITIATIVE; ROADMAP links to
  it; Exhibit A fixed in PROGRESS.md; CLAUDE Current Status renumbered; FRAMEWORK/PRODUCT_SPEC
  product refs → Phase 8. *Leftover for the Phase 3 code session:* renumber the two stale
  `src/config.py` comments that call the 360 model "Phase 3" (now Phase 7) — deferred to keep the
  2026-07-02 commit docs-only.
- **3b — `metrics.json` single source** (done 2026-07-02): `src/metrics.py` computes the headline
  numbers (xG train/test ROC-AUC + Brier, CV mean±std, no-skill→geometry→full ladder, per-group
  silhouette peaks, shot counts) and `python -m src.metrics` writes the committed `metrics.json`.
  A doc-lint test (`tests/test_metrics.py::test_current_state_docs_match_metrics_json`) fails the
  build if a *current-state* doc (README/CLAUDE/MODULES/DATA) prints a number that differs from the
  file; append-only history (PROGRESS, INITIATIVE log, ML_LEARNING_LOG) is deliberately exempt.
  Deferred the test-count number (a repo fact, not a model output — CI reports it).
- **3c — CI:** `.github/workflows/tests.yml` runs the 22 pytest tests on push/PR (Python 3.10,
  pinned `requirements.txt`); green badge in README.
- **3d — `pipeline.py` + `Makefile`** (done 2026-07-03): `src/pipeline.py` chains the ingestion →
  features → model → outputs steps into a headless rebuild, runnable as `python -m src.pipeline`
  (`--force` to bypass caches, `--skip-plots` for data-only). A thin root `Makefile` wraps it
  (`make pipeline`; removed 2026-10-02 as redundant, since `make` isn't on Windows by default). Notebooks **stay** as the teaching surface (learning mandate) — the pipeline
  runs alongside them, not instead of them.
- **3e — Data manifest:** `data/manifest.json` pinning comp/season/match IDs + row counts + content
  hash per dataset; catches upstream StatsBomb changes; feeds Phase 4.

## Phase 4 — Multi-competition ingestion + data expansion  ✅ 4a–4d done · 📌 4e pinned

The flagship overlap item: engineering-at-scale in service of ML. Turns Module A's "generalises
from n=2 contexts" into a defensible claim and fixes Module B's single-season thinness.

- **4a — Config-driven ingestion** (done 2026-07-04): `src/config.py`'s `Dataset` registry already
  had the right shape, so every candidate below is a config line, no `data_loader.py` changes
  needed. New: `PHASE_4_EVENTS_ONLY` / `PHASE_4_EVENTS_AND_LINEUPS` groupings, pulled via a one-off
  script reusing `build_training_dataset`/`build_player_per90_features` — see [DATA.md](DATA.md#phase-4-data-expansion-2026-07-04)
  for the full dataset list, the "StatsBomb's La Liga = mostly Barcelona" gotcha, and the sampled
  women's-football viability check.
- **4b — Module B cross-league/season** (app-wired 2026-07-05, normalisation resolved
  2026-07-13): the Streamlit app's player pool now spans `config.SIMILARITY_SETS` — PL/La
  Liga/Serie A/Ligue 1 2015/16 + Frauen Bundesliga/FA WSL 2023/24 — clustered together per
  position group (`src/app_data.py`), not per league. `config.SIMILARITY_SET` (PL 2015/16 alone)
  is untouched and still what `metrics.json`/notebook 03/`pipeline.py` describe — the teaching
  example stays single-competition on purpose. **Cross-league normalisation (2026-07-13):**
  `similarity.normalize_within_competition` z-scores each per-90 stat within its own competition
  before clustering/`find_similar_players` ever compare across leagues — a relative, data-only
  fix (no external league-strength index exists in this project's data), not a true
  competitiveness rating, but a real improvement over comparing raw rates directly. Same-day
  follow-up also gave goalkeepers their first real K-means clustering (K=4, silhouette-informed
  like the outfield groups — see MODULES.md/ML_LEARNING_LOG.md). Real ceiling, not a to-do:
  StatsBomb's free data has no recent men's top-flight season at all, so "wider" (6 competitions)
  rather than "newer" is what Phase 4b actually delivers for the men's leagues; the women's
  leagues (2023/24) are the newest full-season data anywhere in this project.
- **4c — Module A generalisation** (3/4 wired 2026-07-09, Women's EURO 2025 still pending): the
  three cached-but-unscored Phase 4
  tournaments (Copa América 2024, FIFA World Cup 2022, Africa Cup of Nations 2023) are now scored
  against the `TRAIN_SETS`-fitted logistic model via a new `config.GENERALISATION_TEST_SETS` +
  `models.evaluate_by_competition` — **per tournament, not pooled into `TEST_SETS`**, so the
  headline `0.765` (EURO 2024) stays the one number every doc quotes while `metrics.json`'s new
  `xg_generalisation` section and `outputs/xg_generalisation_by_tournament.png` carry the wider
  picture. Result: EURO 2024 is the *floor* of the four (0.765), not a fluke — World Cup 2022 0.808,
  AFCON 2023 0.807, Copa América 2024 0.763 (751 shots, smallest sample). Women's EURO 2025 is still
  **not wired** — never cached, and a pull attempt hit a persistent GitHub rate limit (`429`) this
  session rather than the usual transient one; see [ML_TOOLING.md](ML_TOOLING.md). Full detail:
  [PROGRESS.md](PROGRESS.md)'s 2026-07-09 entry.
- **4d — Availability friction:** resolved for now — full-season non-La-Liga leagues (Serie A,
  Ligue 1, both women's leagues) were more available than assumed once verified by match/team
  count instead of competition name. Understat.com (free, Big-5-league shot coordinates,
  2014/15–present) is a further option if more volume is wanted later, deferred because it needs
  new ingestion code (different schema) — see [DATA.md](DATA.md#phase-4-data-expansion-2026-07-04).
  The originally-flagged SofaScore/FlashScore option is still there too, see
  [DATA.md](DATA.md#candidate-alternative--supplementary-data-sources-not-yet-used) (match-level
  stats + standings, not a per-shot xG source).

## Phase 4e — Data expansion: new sources + 360 (📌 pinned 2026-10-01, not started)

Guilherme's ask: "a pin for strengthening ingestion of more data (Kaggle may have something), and
for using 360". Every item below was checked on 2026-10-01, not assumed. The prerequisites are
done: HTTPS works through the OS trust store, downloads retry with backoff, and stale caches
rebuild themselves (`src/net.py`, `pipeline._cache_matches_datasets`).

**More StatsBomb open data (same schema, so "a config line, not code"):**
- *Liga F 2023/24* (240 matches, 16 teams), *Serie A Women 2023/24* (130 matches, 10 teams) and
  *NWSL 2023* (137 matches, 12 teams). All three are genuine full seasons, women's football, no
  360. They would roughly double the women's similarity pool (needs lineups pulls).
- *Not* usable as leagues: MLS 2023 (6 matches, Inter Miami only) and Ligue 1 2022/23 (32
  matches, PSG only). These are the same single-club trap as La Liga = Barcelona.
- Women's EURO 2025 + Women's World Cup 2023: wired into Phase 4c on 2026-10-01.

**360 freeze frames (feeds Phase 7):** six datasets have them: Leverkusen 2023/24, EURO 2024,
World Cup 2022, AFCON 2023, Women's EURO 2025, Women's World Cup 2023. A one-match probe (EURO
2024, match 3930166) gave:
- 52,558 rows (one per visible player per event), 7 columns (`id`, `visible_area`, `match_id`,
  `teammate`, `actor`, `keeper`, `location`), 2.7 MB pickled, fetched in 4s;
- **100% of its shots had a freeze frame**, joinable on the event `id`.

Estimate for all six datasets: ~296 matches, ~800 MB of cache, ~20 min to pull.
`load_360_frames` already exists and caches per match. `config.SETS_WITH_360` now derives from
every dataset (it used to skip WC 2022/AFCON 2023).

**External sources, ranked by unlock vs. engineering cost (each one is new ingestion code):**
1. **Understat** shots (Big 5 + RFPL, 2014/15 → current, x/y + xG + situation/body part). This is
   the only free route to *current* men's league seasons; there are several Kaggle mirrors, e.g.
   [Understat database](https://www.kaggle.com/datasets/mexwell/understat-database) and
   [player stats per game](https://www.kaggle.com/datasets/codytipton/player-stats-per-game-understat).
   Cost: a schema adapter in front of `features.extract_shot_features` (normalised 0–1
   coordinates, no freeze frames, no lineups). The Kaggle route needs an API token. Already
   flagged in DATA.md as the biggest unlock.
2. **Wyscout public dataset** (Pappalardo et al., *Sci Data* 2019, CC BY 4.0): every 2017/18
   top-5-league match + World Cup 2018 + EURO 2016, with full events.
   [figshare](https://figshare.com/collections/Soccer_match_event_dataset/4415000),
   [Kaggle mirror](https://www.kaggle.com/datasets/aleespinosa/soccer-match-event-dataset).
   **kloppy already reads it**, so it's the cheapest *new provider*. It would give a second
   season of full men's leagues for Module B, but provider-specific event definitions mean
   per-90 features need re-deriving and checking, not reusing.
3. **PFF FC World Cup 2022** (free on request): broadcast tracking + events for all 64 matches,
   [PFF FC blog](https://www.blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data). kloppy
   supports it. The same tournament StatsBomb covers, so it's a cross-provider check, and full
   tracking (not just 360 snapshots) for Phase 7/Module C ideas.
4. Index for later browsing: [withqwerty/open-football](https://github.com/withqwerty/open-football)
   (a curated map of open football data + tooling).

**Ingestion-robustness follow-ups (only if a bulk pull needs them):** a persistent
`raw.githubusercontent.com` 429 (as in July) can't be waited out in-process. The fallback would be
a sparse `git clone` of `statsbomb/open-data` read from local JSON, which avoids per-file HTTP
altogether. (The cache location is configurable since 2026-10-02: `FAP_CACHE_DIR`, used here to
keep 8.5 GB out of OneDrive.)

## Phase 5 — xG uncertainty + hierarchical finishing model  ⬜

The ML-depth differentiator: small → big, no new data, directly serves the valuation lens.

- **5a — Uncertainty on goals−xG:** bootstrap / analytic interval so "+8 on 40 shots" and "+8 on
  200 shots" stop reading as the same claim. The single best small addition.
- **5b — Hierarchical / empirical-Bayes finishing:** per-player finishing random effect over
  baseline xG, shrunk toward zero — the statistically correct goals−xG. Achieves PUP's "real or
  luck" with clean stats. (May add `statsmodels`.)
- **5c — Header/foot interaction (or split models):** one `body_part` flag assumes identical
  geometry→goal curves for headers and volleys; add an interaction or split.
- **5d — Calibration by stratum:** reliability diagrams split open-play / set-piece / header to
  expose miscalibration the single Brier number hides.

## Phase 6 — Module B metric/feature upgrades  ⬜

- **6a — Mahalanobis / PCA-whitened distance:** Euclidean double-counts correlated features
  (shots↔goals, tackles↔interceptions); respect the covariance.
- **6b — Possession-adjusted defensive actions:** per-100-opponent-touches so a presser at a
  possession side and one at a low block compare fairly.
- **6c — GMM soft membership:** the ~0.22–0.26 silhouette (continuum) motivates it. The Antonio
  one-man cluster already dissolved when clearances/blocks were added (he's now the far edge of the
  attacking full-back cluster) — soft membership would express his hybrid role directly instead
  of hiding it inside a hard label.
- **6d — Richer creative features:** xA / progressive-pass-distance over raw key passes.

## Phase 7 — 360-context xG + xGOT  ⬜  *(was Phase 3)*

StatsBomb `three-sixty` data gives freeze-frames (every visible player's position at the moment of each event). Six datasets have it: Leverkusen 2023/24 and EURO 2024 (the original pair), plus World Cup 2022, AFCON 2023, Women's EURO 2025 and Women's World Cup 2023 (see Phase 4e for the 2026-10-01 probe: 100% shot coverage, ~2.7 MB/match).

**Candidate 360 features:**
- Number of defenders between shot and goal (direct block probability)
- Goalkeeper position relative to goal centre
- Number of open-goal-path defenders
- Nearest defender distance to ball at shot moment

**Post-shot xG (xGOT):** shot trajectory context (where the ball ended up, keeper reaction) narrows the probability *after* the shot is taken. Distinction: pre-shot xG (chance quality before kick) vs. xGOT (includes where the shot went).

**Recommended approach:** keep the existing pre-shot logistic model as the baseline. Build 360-feature extension as a second model. Compare honestly — if the 360 features don't clearly add discrimination, say so.

**Entry checklist:**
- [ ] Confirm Phase 5–6 work is committed (`git status`)
- [ ] Pull 360 frames: **none were cached before 2026-10-01** (only the one probe match since).
  Loop `data_loader.load_360_frames` over `config.SETS_WITH_360` (~296 matches, ~800 MB)
- [x] Schema checked 2026-10-01: `sb.frames(match_id)` gives `id` (joins to event `id`),
  `visible_area`, `teammate`, `actor`, `keeper`, `location`

## Phase 8 — Product layer build (Streamlit)  ✅ Done  *(was Phase 5)*

Minimal v1 built 2026-07-04, ahead of strict phase order — a friend demo (~2026-07-11) made
"something clickable" more valuable than finishing 4–6 first. Since then it has grown to four
views over a 6-competition pool (1,635 players incl. goalkeepers). What the app does today, and
the UX decisions behind it, are in [PRODUCT_SPEC.md](PRODUCT_SPEC.md).

**Deployed 2026-07-09** to Streamlit Community Cloud:
[gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app)
— Python version pinned to 3.10 in the deploy's advanced settings (matches `requirements.txt`'s
tested versions; Cloud's newer default risked missing wheels for `kloppy`/`pyarrow`). Real-browser
rendering already confirmed locally via Playwright-over-Edge (2026-07-08) and now confirmed live in
the cloud by Guilherme directly.

## Phase 9 — Opportunistic  🟡 ongoing

Opportunistic work, grouped by theme. Done items are one-liners; their full story is in
PROGRESS.md / PROGRESS_ARCHIVE.md under the date given.

### Open — app / product

- **Leaderboard's name filter still needs Enter** — flagged 2026-07-14 (cont.), deliberately not
  fixed that session: it's an `st.text_input` feeding a multi-row `st.dataframe`, not a single-pick
  widget, so the live-filtering-selectbox trick that fixed the other three search boxes that
  session doesn't transfer directly. Options considered, none implemented:
  - **Leave as-is.** Streamlit's `text_input` genuinely cannot rerun per keystroke in this version
    (checked directly against the installed 1.58 API — no debounce/`update_on` param exists), and
    unlike the fixed search boxes, this one has no second widget silently disagreeing with it — it's
    a conventional "type, Enter, see a filtered table" pattern most users already know from any
    admin-table search box. Already honestly labelled ("then press Enter"). Plausibly not actually
    broken, just less slick than the fixed boxes — worth deciding this explicitly before spending
    effort on it.
  - **`st.multiselect` of player names instead of a free-text filter.** `multiselect` has the same
    client-side live type-to-filter as `selectbox` (the mechanism the other fixes rely on), so this
    would genuinely be live — but it changes the interaction from "narrow a big table by typing" to
    "hand-pick specific players to show," a different feature, not a pure UX fix. Would need a
    product call on whether that tradeoff is worth it for a browse-and-sort view.
  - **A third-party live-search component** (e.g. `streamlit-searchbox`) or a custom bidirectional
    component with real debounce. Would need a new `requirements.txt` dependency, re-verification
    on Streamlit Community Cloud's pinned Python 3.10, and more moving parts for one filter box —
    the highest-effort, highest-risk option of the three.
  - `st.fragment` (partial reruns) was considered and ruled out on inspection: it changes *what*
    reruns on an interaction, not *when* — it wouldn't make `text_input` rerun on keystroke, so it
    doesn't actually solve this problem.
- **New app features** — asked for after the 2026-07-14 (cont.) UX-debt pass; deliberately left as
  an open discussion, not a task list, same as the visual/docs item below. Candidates surfaced
  while thinking this through, roughly in "buildable from data already in `app_data/`" → "needs new
  data" order:
  - **Shareable deep links** via `st.query_params` — encode the current view/filters/picked player
    in the URL so a specific player's page (or a specific comparison) can be linked directly,
    instead of always landing on a blank search. Session-only state today; this would need no new
    data, just wiring existing selections through the URL.
  - **A team-level or "Best XI" view** — aggregate stats by team, or let a user assemble a squad
    from the pool and see combined market value / style mix. New scope, buildable from existing
    per-player data, no new pulls — but a genuinely new page, not a small addition.
  - **Multi-season "player career" page** — splits into two parts (found 2026-09-30):
    - **xG career, buildable now from cached data.** The shots for 16 Barcelona seasons
      (2004/05–2020/21) are already extracted (`data/shots_barcelona_*.parquet`). Scoring them with
      the fitted model gives every Barcelona player a per-season goals vs. xG line, including
      Messi's whole career there. Goals − xG needs no minutes, so no lineups pulls are needed.
    - **Per-90 career** needs new lineups pulls (minutes played).

    Trophies/awards/MOTM exist in no current source. Relatedly, scoring the La Liga/Serie A/Ligue 1
    2015/16 shots (also cached) would give most of the app's pool a Finishing panel; today only
    PL 2015/16 has one.
  - **xA / chance-creation model, Module C (PUP)** — both already listed below in this same Phase 9
    section; larger, model-layer undertakings rather than app-layer features.
- **Market-value tiebreak for same-name players** (found 2026-10-01): Luis Suárez (Barcelona) is
  unmatched because Transfermarkt has two same-position "Luis Suárez" profiles (born 1987/1997).
  `players.csv` has `date_of_birth`, and `player_valuations` has the club at each date. Either one
  breaks the tie deterministically: drop candidates too young for the season, or pick the one
  valued at the StatsBomb team on the as-of date.
- **The live demo sleeps** (found 2026-10-01): Streamlit Community Cloud hibernates an app with no
  traffic, so the first visitor from a CV/LinkedIn link sees a "wake this app up" screen and waits
  ~1 min. Options: a scheduled GitHub Action that opens the app in a headless browser (a plain
  HTTP GET doesn't wake it), or a line in README warning that the first load is slow.

### Open — models and data

- **xA / chance-creation model** — sibling to xG on the same pipeline; also upgrades 6d.
- **Module C (PUP)** — only if desired; carries a selection-bias confound + label-acquisition cost,
  and Phase 5 already delivers most of its payoff. Spec:
  [MODULES.md](MODULES.md#module-c--pup-performance-under-pressure).
- **Remaining alt-models** — hierarchical clustering, cosine, monotonic GBM.
- **2026 World Cup player/team performance model** (flagged 2026-07-05, not started) — a
  predictive model for the *current* tournament (~2026-06-11 to ~2026-07-19), rather than the
  retrospective xG/similarity framing used everywhere else in this project. **First step before
  any modelling: verify whether StatsBomb has open data for it at all.** Every tournament this
  project already uses (World Cup 2022, EURO 2024, AFCON 2023, Copa América 2024) was released
  *after* the tournament finished, not live — a still-in-progress or just-finished 2026 World Cup
  may simply have no open data yet, which would make this a "wait" item, not a "no data exists"
  item. Scope (prediction target, features, train set) deliberately left undefined until that
  availability check happens.
  **Availability check done 2026-10-02.** The tournament ended 2026-07-19, but **StatsBomb open
  data still has no World Cup 2026**: its newest update anywhere is 2026-05-26. Keep checking; past
  tournaments arrived months after the final. The best free source found instead is the
  [FIFA World Cup 2026 Dataset](https://github.com/mominullptr/FIFA-World-Cup-2026-Dataset) (CC0;
  also on Kaggle, Zenodo and Hugging Face). It has all 104 matches, 48 squads, 1,248 players with
  market values, lineups with minutes, goal/card/VAR events, per-team shots/possession, and
  match-level xG. Sources: FIFA, Sofascore, Transfermarkt. **It has no shot coordinates**, so it
  can't feed Module A's shot-level model or Module B's per-90 event features. It does fit a
  *match/team-level* model (Elo + team xG → results) and could serve as a held-out check for one.
  That reframes this item: "predict the tournament" becomes a retrospective team-strength model,
  not a shot model. Also seen: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
  (public-domain fixtures/results only).

### Open — infrastructure

- **Python 3.10 → 3.12** — flagged 2026-07-09 (the Streamlit Cloud deploy chose 3.10 to match the
  pinned requirements), deferred as housekeeping until the 2026-09-30 health check found a real
  deadline: **3.10 reaches end-of-life on 2026-10-31**. *Repo side done 2026-10-01:* the same
  pins install on 3.12 (all have wheels). The full suite passes on 3.12 locally (an isolated `uv`
  env) and CI now runs a 3.10/3.12 matrix. A new `app-runtime` CI job installs only
  `requirements.txt`, mirroring the Cloud. The app no longer needs `statsbombpy`/`kloppy` at all
  (lazy imports; requirements split into runtime vs. `requirements-dev.txt`). *Local switch done 2026-10-02:* Python 3.12.10 installed per-user and put first on PATH (3.10
  kept as rollback). `requirements-dev.txt` is installed into it, the full suite passes, and a
  `fap312` Jupyter kernel and the VS Code interpreter point at it (see ML_TOOLING.md). *Still
  open, needs Guilherme's Streamlit account:* **redeploy the Cloud app on 3.12**. Per
  [Streamlit's docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python),
  the Python version can't be changed on a deployed app. Delete it, then deploy again from
  `GuiPadinha/football-analytics-portfolio`, branch `main`, entrypoint `app.py`, with the custom
  subdomain `gpfootball-analytics-portfolio` and Python 3.12 under Advanced settings. The app has
  no secrets. Then drop 3.10 from the CI matrix and unpin the runner from `ubuntu-24.04`.
  *Same pass (listed by the 2026-10-02 re-audit):* update what still calls 3.10 the live version:
  the `tests.yml` matrix comments, README "Running it", CLAUDE.md (status + layout line),
  PRODUCT_SPEC.md's intro, PITCH.md, and the Leaderboard item above ("pinned Python 3.10").
  (The notebooks were already re-executed on 3.12 on 2026-10-02: identical results.)
- **`python -m src.app_data` is slow: ~10.6 min** (found 2026-10-02). It sits outside the
  pipeline on purpose: the pipeline is the reproducibility check, and `app_data/` is the deploy
  artifact. Measured per match: load events 77 ms, count outfield actions 114 ms, count goalkeeper
  actions 32 ms. Each competition is read twice, once per extractor. Reading each match once would
  save only ~27% (to ~7.5 min), because counting costs more than loading. The real win would be a
  per-competition per-90 cache, but that adds back the stale-cache risk fixed the same day. A column
  check can't see a counting-logic change. Revisit only if rebuilds become frequent (e.g. during
  Phase 5a). Moving `CACHE_DIR` out of OneDrive (Phase 4e's ingestion follow-ups) would help a little
  too.
- **Data-engineering showcase: a cloud ELT layer** (flagged 2026-10-02 from a LinkedIn post
  Guilherme shared): [paolomagni/football-platform](https://github.com/paolomagni/football-platform)
  ingests football-data.org into GCP. The stack is Cloud Run ingestion → Cloud Storage → BigQuery →
  dbt (staging/intermediate/marts, with tests) → Looker Studio, orchestrated by Cloud
  Scheduler/Workflows. It uses Terraform (dev/prod), GitHub Actions with OIDC (Workload Identity
  Federation, no service-account keys), and images tagged by commit SHA. Relevant here because this
  project's ML layer has no warehouse or scheduled ingestion. A small version of that pattern, e.g.
  a scheduled job landing StatsBomb/Understat pulls in BigQuery with dbt models feeding
  `app_data/`, would show Guilherme's data-engineering background next to the ML. Not started;
  scope undecided.

### Done

- **Architecture / dependency doc** — [ARCHITECTURE.md](ARCHITECTURE.md), 2026-07-04.
- **Market value (Transfermarkt) alongside "players like X"** — `src/market_value.py`, ~90% match
  rate on the men's leagues, 2026-07-14 (see [DATA.md](DATA.md)).
- **Side-by-side "Compare players" view** — 2026-07-14.
- **Auto-generated scouting-report blurb** — `build_scouting_blurb`, 2026-07-14.
- **2026-10-02 re-audit fixes** — the similarity-table cache now rebuilds when its columns change;
  the doc-lint also covers the per-tournament AUCs and the silhouette range; restructure leftovers
  (dead archive links, a Makefile mention) cleaned up; notebooks re-executed on 3.12.
- **A bigger visual + documentation pass** (flagged 2026-07-13) — done as the 2026-09-30 health
  check and its six-phase fix-up (2026-10-01/02): app restructure + tests, repo declutter, roadmap
  merge, PRODUCT_SPEC rewrite, slimmer CLAUDE.md/README.
