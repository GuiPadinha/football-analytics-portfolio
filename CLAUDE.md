# Football Analytics Portfolio — CLAUDE.md

Project source of truth. Read this first every session, then load linked docs on demand.

---

## Current Status (updated 2026-10-10)

**Where we are:** Phases 0–4 ✅ (4c closed 2026-10-01 with two women's tournaments; **4e**, new data
sources + 360, started 2026-10-03 with the women's leagues), Phase 8 ✅ ([live app](https://gpfootball-analytics-portfolio.streamlit.app)),
Phase 9 ongoing. Phases 5–7, the ML-depth work, are not started. The 2026-09-30 repo health check
and all its fixes were completed on 2026-10-02: HTTPS via the OS trust store, Python 3.12, the
`app.py` restructure + app tests, and the repo/doc declutter. A deep audit (10-02/03) then found
and fixed three data bugs the live app was showing (goalkeeper save %, Ligue 1 clubs split under two
names, wrong-identity market values) plus a radar crash. On 10-03 the live app moved to Python
3.14, keepers started counting only on-target shots, and market values started matching on
StatsBomb's nickname, with the club check breaking ties (Luis Suárez). Then the pool grew to 9
competitions (three more women's leagues), and Guilherme judged the app "numbers, no insights,
cheap-looking". The agreed redesign, **conclusions first**, then shipped in stages (10-06 → 10-10):
rule-based text (`src/narrative.py`), league-adjusted percentiles, and new pages on top navigation
(Home with computed findings, Players as three questions, Compare with a verdict, Leaderboard, How
it works), with native charts and no matplotlib in the app. Session detail is in
[docs/PROGRESS.md](docs/PROGRESS.md); phases and backlog are in [docs/ROADMAP.md](docs/ROADMAP.md).

**Next session, start here (agreed order):**
1. **Look at the redesigned live app with Guilherme** and take his feedback (it was checked in a
   real browser only locally, on a star, a keeper and a women's player). Known small gaps are in
   PRODUCT_SPEC.md: no deep links, 159 long registered names, uneven Home card heights.
2. **Wyscout 2017/18** (Phase 4e): the only route to more men's data and a second season.
3. **Phase 5a** (uncertainty on goals−xG). Score each shot with a model that never saw it
   (out-of-fold xG): see ML_LEARNING_LOG.md's 2026-10-03 entry. The page's exact-odds sentence
   already assumes an average finisher; 5a replaces its in-sample xG.

Environment: the live app runs Python 3.14 at gpfootball-analytics-portfolio.streamlit.app; local
is 3.12; CI tests both. `FAP_CACHE_DIR` (cache outside OneDrive) is visible after VS Code's
2026-10-03 restart.

Key numbers: xG logistic test ROC-AUC **0.765** (EURO 2024, in-game shots only, penalty shootouts
dropped). Five more held-out tournaments rank as well (0.76–0.81): World Cup 2022 0.808, AFCON 2023
0.807, Women's World Cup 2023 0.777, Copa América 2024 0.763, Women's EURO 2025 0.763. EURO 2024 is
near the bottom, not "the floor". Similarity: K=4 per position group, silhouette ~0.22–0.26 (a
soft continuum) on the notebook's PL 2015/16 scope; the app's pool is 9 competitions and
2,170 players, league-normalised, with goalkeepers clustered too. **1,327** players matched to a
Transfermarkt market value (men's competitions, ~99%, each confirmed at the right club).
*(xG/similarity numbers come from
[metrics.json](metrics.json) via `python -m src.metrics`. A doc-lint test fails the build if a
current-state doc drifts on the headline xG numbers, the per-tournament AUCs, the silhouette
range or the app-pool numbers, and `tests/test_app_data.py` checks the shipped app tables. `python -m src.pipeline` rebuilds data, models and outputs headless, and
`metrics.json` and the PNGs come out byte-identical on Python 3.12 and 3.14. `python -m
src.app_data` rebuilds the app's data separately, in ~3–5 min.)*

---

## What This Project Is

Player Evaluation Framework — two modules on StatsBomb/SkillCorner open data:
- **Module A — xG**: supervised binary classification. Logistic regression (recommended over GBM — honest non-win). Train: Leverkusen 2023/24 + PL 2015/16. Test: EURO 2024 (deliberate distribution shift).
- **Module B — Player similarity**: unsupervised K-means/PCA. Per-90 per position group (Defender/Mid/Forward on the notebook/pipeline's single-competition scope; the app's own pool also clusters Goalkeepers, own feature set, since 2026-07-13). "Players like X" nearest-neighbour lookup + radar charts, plus an external Transfermarkt market value matched by name (2026-07-14, men's competitions only).
- **Module C — PUP** (scoped only, not started): per-player performance-under-pressure KPI.

→ Module specs: [docs/MODULES.md](docs/MODULES.md) | Data sources: [docs/DATA.md](docs/DATA.md) | Owner/context: [docs/CONTEXT.md](docs/CONTEXT.md) | Product framing: [docs/FRAMEWORK.md](docs/FRAMEWORK.md)

---

## Repository Layout

```
app.py                   ← Streamlit entry: page frame + top navigation (`streamlit run app.py`)
views/                   ← one script per page (home, players, compare, leaderboard, how_it_works) + components.py (stylesheet, HTML builders, shot map) + data.py (cached loaders); reads app_data/, never downloads
requirements.txt         ← app runtime deps only (what Streamlit Cloud installs; no matplotlib)
requirements-dev.txt     ← + ingestion, truststore, matplotlib/mplsoccer, jupyter, pytest (includes requirements.txt)
metrics.json             ← headline numbers, single source (`python -m src.metrics`)
src/
  config.py          ← named Dataset constants (competition/season ids, has_360, gender)
  net.py             ← download plumbing: OS trust store (truststore) + retry/backoff
  data_loader.py     ← StatsBomb + SkillCorner ingestion, per-match pickle cache
  features.py        ← xG feature engineering (distance, angle, assist type, flags)
  models.py          ← logistic pipeline, CV, calibration, GBM, player xG table
  similarity.py      ← per-90 features, league normalisation, clustering, find_similar_players
  market_value.py    ← Transfermarkt entity resolution + valuation lookup
  visualisation.py   ← all charts (shot map, radar, calibration, PCA, ...)
  presentation.py    ← labels and formatters: stat names, popular_name, ordinals, market value
  narrative.py       ← rule-based sentences: a player's short version, Compare's verdict
  profile.py         ← what a page shows: player profile, Compare view, leaderboard table (pure, tested)
  findings.py        ← Home's four computed cards → app_data/findings.json (`python -m src.findings`)
  manifest.py        ← data provenance manifest (`python -m src.manifest`)
  metrics.py         ← writes metrics.json
  pipeline.py        ← headless rebuild: data → models → outputs → manifest/metrics
  app_data.py        ← writes app_data/*.parquet for the app (`python -m src.app_data`)
app_data/                ← precomputed Parquet the app reads (small, committed)
notebooks/               ← 01 exploration, 02 xG model, 03 similarity (the teaching surface)
tests/                   ← pytest suite incl. AppTest smoke tests of every app page; conftest.py
outputs/                 ← pipeline PNGs, committed (README embeds them; pipeline is the only writer)
data/                    ← processed tables (gitignored) + manifest.json (committed); the ~8.5 GB
                           per-match cache is data/cache/, or $FAP_CACHE_DIR (outside OneDrive here)
docs/
  FRAMEWORK.md           ← what the tool is for (purpose, user, scope)
  ARCHITECTURE.md        ← import graph, data flow, pure/IO-split pattern
  PRODUCT_SPEC.md        ← the app as it is: views, panel→function map, UX decision log
  MODULES.md             ← Module A/B/C specs and results
  DATA.md                ← data sources, datasets, caveats, cache index
  ROADMAP.md             ← phase table (0–9) + milestones + per-phase task lists + backlog
  PROGRESS.md            ← recent session log (archived to PROGRESS_ARCHIVE.md above 150 lines)
  PROGRESS_ARCHIVE.md    ← full history, incl. the original S1–S9 build
  ML_LEARNING_LOG.md     ← ML/data gotchas and decisions
  ML_THEORY.md           ← textbook theory reference
  ML_TOOLING.md          ← Windows/environment gotchas
  CONTEXT.md             ← owner, learning goals, career context
  PITCH.md               ← pre-demo cheat sheet, refreshed by hand
.github/workflows/tests.yml  ← CI: pytest on 3.12 + 3.14, plus an app-runtime-only smoke job (3.14)
.githooks/pre-commit         ← enforces the doc-log rule below
.streamlit/config.toml       ← app theme
```

---

## Session Workflow

**Git:** the CLI is used directly. Commit only when Guilherme asks, and when he does, commit **and push** (no separate confirmation). When executing a plan he approved, make one commit + push per plan item so history stays organised. Every push redeploys the live app, so verify before pushing. Never force-push; prefer new commits over amending.

**Start of session:**
1. Read this file; check [docs/PROGRESS.md](docs/PROGRESS.md) for last session state
2. Give 2-line: where we are + what we're doing today
3. Never modify files outside the repo

**End of session:**
1. Add dated entry to [docs/PROGRESS.md](docs/PROGRESS.md) (move old entries to PROGRESS_ARCHIVE.md when it exceeds 150 lines)
2. Log any new environment/tooling obstacle to [docs/ML_TOOLING.md](docs/ML_TOOLING.md), any new ML/data gotcha to [docs/ML_LEARNING_LOG.md](docs/ML_LEARNING_LOG.md) — as it happens, not just when asked to retrospectively
3. Give 3-line summary: done / unresolved / commit message suggestion

**This is enforced, not just requested (added 2026-07-09):** relying on memory to follow the rule
above failed within a single session (a real retry attempt went unlogged until asked twice). Two
mechanisms now backstop it — see `.githooks/pre-commit`'s own header comment for full detail:
- **Local hook** (`.githooks/pre-commit`, active once `git config core.hooksPath .githooks` has
  been run in a given clone): blocks a commit that touches `src/`/`app.py`/`tests/`/`notebooks/`
  without touching `docs/PROGRESS.md`, `docs/ML_TOOLING.md`, or `docs/ML_LEARNING_LOG.md`. Escape hatch
  for genuinely trivial commits: `DOC_CHECK_ACK=1 git commit ...` (prefer this over `--no-verify`,
  which would skip every hook, not just this check).
- **CI backstop** (`.github/workflows/tests.yml`'s "Check evolving docs were touched" step): the
  same check against every push/PR diff, as a non-blocking `::warning::` annotation — fires even
  if the local hook was never enabled (e.g. a fresh clone).

---

## Coding Standards

- **Language**: English only — code, comments, docstrings, commits
- **Style**: PEP8, meaningful names, no magic numbers; dataset IDs go in `src/config.py`
- **Functions**: all `src/` functions require docstrings (the "why", not just the "what")
- **No hardcoded paths**: use `config.py` constants or relative paths
- **Notebooks**: must run clean top-to-bottom without errors
- **Data**: never commit — `data/` is gitignored
- **Small decisions**: use best judgement, no confirmation needed for minor choices

---

## Model Selection

| Task | Model |
|---|---|
| Code, debugging, features, notebooks (90% of work) | **Sonnet** (default) |
| Architecture, repeated failures, complex ML tradeoffs | Opus (only if Sonnet fails 2–3×) |
| Quick lookups, syntax, reformatting | Haiku (Claude.ai sidebar, not Claude Code) |

Token efficiency: `/compact` when session history is long; `/clear` when switching modules; point to files directly, don't paste code into chat.

---

## Learning Mandate

**This project is primarily for Guilherme to learn hands-on ML** — the portfolio is the by-product.
- Narrate the "why" behind every modelling decision, not just the "what"
- Report tradeoffs and negative results honestly (GBM didn't beat logistic — said so)
- Flag real ML/stats gotchas when they come up
- When Guilherme asks "why", explain conceptually before writing more code

→ Concepts log: [docs/ML_LEARNING_LOG.md](docs/ML_LEARNING_LOG.md) | Theory: [docs/ML_THEORY.md](docs/ML_THEORY.md) | Env gotchas: [docs/ML_TOOLING.md](docs/ML_TOOLING.md)
