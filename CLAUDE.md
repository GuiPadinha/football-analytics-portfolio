# Football Analytics Portfolio — CLAUDE.md

Project source of truth. Read this first every session, then load linked docs on demand.

---

## Current Status

**Active initiative:** Framework Hardening & Expansion — Phases 0–3 and Phase 8 fully ✅ complete;
Phase 4 is 🟡 4c mostly done (2026-07-09: Module A scored separately against three more held-out
tournaments, see Key numbers below — a fourth, Women's EURO 2025, is still rate-limited and pending
a retry, not folded into "done"). Phase 8: minimal Streamlit build shipped 2026-07-04 (ahead of
strict phase order, for an upcoming demo), extended 2026-07-05 with real-time search, a dark theme,
and a widened multi-competition player pool; a 2026-07-06 pass fixed a real radar dark-theme bug +
added whole-number totals; a 2026-07-08 pass shipped the all-players **leaderboard** (goals incl.
penalties + xG where available) and verified both app views in a real browser (Playwright-over-Edge
screenshots); **deployed to Streamlit Community Cloud 2026-07-09**; a 2026-07-09 (cont. 4) pass
shipped penalty info (total goals + penalty split) on the single-player page; a 2026-07-09 (cont. 5)
pass shipped the clickable "similar player" recursive drill-down (and fixed a real infinite-jump
cascade bug it exposed — see PROGRESS.md); a 2026-07-13 pitch-prep pass promoted the app's framework
explanation into its own **"About & Roadmap"** sidebar view (what it is, how to use it, what's
built, what's next, and a "Methodology" expander), rewrote the headline stat tiles to whole-number
counts instead of decimal model scores, and wired the Phase 4c generalisation chart into the app for
the first time; a same-day (cont. 3) pass **wired goalkeepers into the app** (own feature set, a 4th
position filter, 124 keepers — not yet clustered at that point, see MODULES.md; K-means clustered in
a later same-day cont. 6 pass, below) and expanded the Leaderboard view's own explanatory copy; a
same-day (cont. 4) visual/
brand pass added Leaderboard name/position filters, a proper Player explorer intro, a reusable
`render_page_header` (icon + slogan badge on every page), a live-stat-carrying sidebar, and
expanded "About & Roadmap" with visible (non-decimal) "Data used" and "How each model works"
sections plus a third "Module C / Performance-Under-Pressure" roadmap paragraph; a same-day
(cont. 5) pass opened the "bigger visual + docs" ask flagged at the end of cont. 4 — read all 16
`.md` files end-to-end and fixed four real doc-drift findings (a self-contradicting README, a
missing `docs/PRODUCT_SPEC.md` entry in this file's own Repository Layout, `ARCHITECTURE.md` never
mentioning `app_data.py`, two markdown-to-markdown line-anchors that had already drifted to the
wrong section), then shipped two new app features reusing already-computed data with no new
modelling: a **Style archetype panel** (Player explorer, outfield players — surfaces the K=4
cluster label `app_data.py` has computed since Phase 4 but the app never showed, via
`similarity.profile_clusters`'s z-score readout) and a **percentile bar chart** replacing the plain
per-90 stats table, both via a new shared `visualisation.plot_diverging_bar`; plus a diverging
background colour on the Leaderboard's G-xG column —
**[live demo](https://gpfootball-analytics-portfolio.streamlit.app)** (Python 3.10 pinned in the
deploy settings to match `requirements.txt`, not Cloud's newer default — see ROADMAP.md's Phase 9
backlog note on why that version bump is deliberately deferred); a same-day (cont. 6) pass closed
out three explicitly-scoped items: goalkeepers are now **K-means clustered** (K=4, same
silhouette-informed-but-archetype-driven call as the outfield groups, checked against the real
124-keeper pool — see MODULES.md) and share the Style archetype panel with outfield players;
**cross-league similarity normalisation** is designed and implemented
(`similarity.normalize_within_competition` — per-90 stats are now z-scored within each competition
before clustering/"players like X" ever compare across leagues, a relative fix since no external
league-strength data exists in this project); and the Leaderboard's long-standing blank-cell-shows-
"None" bug is fixed (confirmed as a real, still-open upstream Streamlit limitation — GitHub issue
#7360 — fixed at the data layer via hand-formatted text columns, not the config layer three prior
attempts tried). 75 tests green; `metrics.json` unchanged (byte-identical); a same-day (2026-07-14)
follow-up shipped two more Phase 9 backlog items: **market value** (`src/market_value.py` matches
each player onto an external Transfermarkt valuation by name — no shared ID exists between the two
data sources, so this needed real entity-resolution engineering, including finding and fixing two
genuine matching bugs against real data; ~90% match rate on the four men's competitions, shown on a
player's page, "players like X," and the Leaderboard) and a new **Compare players** view (any two
players side by side; market value/Finishing always compare directly, a radar/signature-stats/
percentile comparison only when both share a position group). 86 tests green; a same-day (cont.)
UX-debt pass fixed three things flagged from actually using the deployed app: the Player
explorer/Compare players search boxes felt dead (typed text did nothing until Enter — replaced
with live-filtering, blank-start `st.selectbox`es, one deliberate revisit of a widget shape
PRODUCT_SPEC.md records as explicitly rejected once before, confirmed with Guilherme first given
that history); the **Style archetype** panel led with raw σ jargon (now plain language first, exact
z-scores demoted to a collapsed expander); and a real **percentile-direction bug** where a
goalkeeper's Goals Conceded percentile read backwards (a leaky keeper looked "elite") — fixed via
new `similarity.goodness_percentiles`, with a plain-language tier word (Elite/Good/Average/Poor/…)
now shown next to every percentile in the app. 89 tests green. Both this pass and the market
value/Compare players work above are **committed and pushed** (`78db78f`, `78feefe`).
See [docs/PROGRESS.md](docs/PROGRESS.md). Full review backlog folded into a renumbered 0–9 program on
2026-07-02.
**Next session, start here:** nothing mid-flight — pick up an open backlog item.
**Next (open backlog, all documented, none started):** (1) a multi-season "player career" page/view
(needs new lineups pulls; international-tournament trophies/awards/MOTM data does not exist in any
current source and would need new scraping infra); (2) the Leaderboard's name filter still needs
Enter (feeds a multi-row table, not a single pick, so the live-selectbox fix above doesn't transfer
directly — three options weighed, none chosen, see ROADMAP.md's Phase 9 list); (3) "new app
features" — an open discussion, not a task list, with a curated candidate set (auto-generated
scouting-report blurb, shareable deep links via `st.query_params`, a team-level/"Best XI" view) in
the same ROADMAP.md Phase 9 section. Known small gaps in what shipped 2026-07-14: market-value
matching can miss a real match (name/position collision, no club/season cross-check) and has zero
coverage for the two women's leagues (that Transfermarkt mirror only covers men's football) — both
stated honestly in-app, not silently hidden. Exact code entry points for anything else still open
are in [PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md)'s "Backlog from 2026-07-06 feedback" section and
[ROADMAP.md](docs/ROADMAP.md)'s Phase 9 list — the PRODUCT_SPEC section also has one minor open
cosmetic follow-up from the drill-down work (an expander's open/closed state not always carrying
over consistently across a jump).**
(360-context xG is now Phase 7; the Streamlit product build is now Phase 8 — see the phase table.)
Run the app locally: `python -m src.app_data` (once, to build `app_data/`) then `streamlit run app.py`
— or just use the [live demo](https://gpfootball-analytics-portfolio.streamlit.app).

Key numbers: xG logistic test ROC-AUC **0.765** (EURO 2024, in-game shots only, penalty shootouts dropped) — Phase 4c (2026-07-09) shows this is the *floor* across four held-out tournaments, not a fluke: FIFA World Cup 2022 0.808, Africa Cup of Nations 2023 0.807, Copa América 2024 0.763 (see `metrics.json`'s `xg_generalisation`, [docs/MODULES.md](docs/MODULES.md)). Similarity: K=4 per position group, silhouette ~0.24 (soft continuum) on the notebook/pipeline's single-competition (PL 2015/16) scope — the app's own player pool is wider (6 competitions, now cross-league normalised, and goalkeepers are K-means clustered too — see MODULES.md). **1,215** players matched to a Transfermarkt market value (men's competitions only, ~90% match rate — see DATA.md). 89 unit tests passing. *(xG/similarity numbers are emitted to [metrics.json](metrics.json) by `python -m src.metrics`; a doc-lint test fails the build if a current-state doc drifts from it — see Phase 3b. Whole rebuild — data, models, outputs, manifest, metrics — runs headless via `python -m src.pipeline`, see Phase 3d.)*

→ Phase tracker: [docs/INITIATIVE.md](docs/INITIATIVE.md) | Session log: [docs/PROGRESS.md](docs/PROGRESS.md)

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
src/
  config.py          ← named Dataset constants (competition/season IDs, has_360)
  data_loader.py     ← StatsBomb + SkillCorner ingestion, per-match pickle cache
  features.py        ← xG feature engineering (distance, angle, assist type, flags)
  models.py          ← logistic pipeline, CV, calibration, GBM, player xG table
  similarity.py      ← clustering, PCA, find_similar_players, resolve_season_positions
  visualisation.py   ← shot map, calibration curve, elbow, PCA, radar, xG ranking
  market_value.py    ← Transfermarkt entity resolution + valuation lookup (Phase 9, 2026-07-14)
  manifest.py        ← data provenance manifest (`python -m src.manifest`)
  metrics.py         ← metrics.json single source (`python -m src.metrics`)
  pipeline.py        ← headless rebuild: data → models → outputs → manifest/metrics (`python -m src.pipeline`)
  app_data.py        ← Phase 8 build step: writes app_data/*.parquet (`python -m src.app_data`)
Makefile               ← thin wrapper around src/pipeline.py
app.py                 ← Phase 8 Streamlit app (`streamlit run app.py`) — reads app_data/, no live pulls
app_data/              ← precomputed Parquet artifacts the app reads (small, committed — not gitignored)
.streamlit/config.toml ← Streamlit theme
.githooks/pre-commit    ← enforces the "End of session" doc-log rule below (see Session Workflow)
notebooks/
  01_data_exploration.ipynb
  02_xg_model.ipynb          ← Phase 2 ML rigor section added
  03_player_similarity.ipynb ← silhouette + minutes-weighting added
docs/
  FRAMEWORK.md           ← what the tool is for (purpose, user story, scope)
  ARCHITECTURE.md        ← module dependency graph, data flow, pure/IO-split pattern
  PRODUCT_SPEC.md        ← Streamlit app interface spec, component→backend map, build/feedback log
  INITIATIVE.md          ← phase tracker (Phases 0–9)
  MODULES.md             ← Module A/B/C specs and current state
  DATA.md                ← data sources, datasets table, cache file index
  CONTEXT.md             ← owner, learning goals, career context, portfolio framing
  ROADMAP.md             ← historical S1–S9 session log (separate scheme from the Phase 0–9
                            table above — see the note in the file) + detailed per-phase task lists
  PROGRESS.md            ← recent session log, auto-archived to PROGRESS_ARCHIVE.md above 150 lines
  PROGRESS_ARCHIVE.md    ← full historical session log (S1–S8 onward)
  PITCH.md               ← living pre-demo pitch cheat sheet, refreshed by hand before each pitch
  ML_THEORY.md           ← ML/stats theory reference (textbook-level)
  ML_TOOLING.md          ← Windows/environment gotchas
ML_LEARNING_LOG.md       ← ML gotchas and decisions log (pointers to above docs)
tests/                   ← 86 pytest unit tests, all green
outputs/                 ← saved PNGs (gitignored)
data/                    ← per-match cache + Parquet feature tables (gitignored)
```

---

## Session Workflow

**Git CLI is fine** (as of 2026-07-04) — `git status`/`log`/`diff`/`add`/`commit` may be run directly. Still: only commit when explicitly asked, never force-push or push without confirmation, prefer new commits over amending. (Earlier sessions used GitHub Desktop only, on the mistaken assumption `git` wasn't reachable — that restriction is lifted.)

**Start of session:**
1. Read this file; check [docs/PROGRESS.md](docs/PROGRESS.md) for last session state
2. Give 2-line: where we are + what we're doing today
3. Never modify files outside the repo

**End of session:**
1. Add dated entry to [docs/PROGRESS.md](docs/PROGRESS.md) (move old entries to PROGRESS_ARCHIVE.md when it exceeds 150 lines)
2. Log any new environment/tooling obstacle to [docs/ML_TOOLING.md](docs/ML_TOOLING.md), any new ML/data gotcha to [ML_LEARNING_LOG.md](ML_LEARNING_LOG.md) — as it happens, not just when asked to retrospectively
3. Give 3-line summary: done / unresolved / commit message suggestion

**This is enforced, not just requested (added 2026-07-09):** relying on memory to follow the rule
above failed within a single session (a real retry attempt went unlogged until asked twice). Two
mechanisms now backstop it — see `.githooks/pre-commit`'s own header comment for full detail:
- **Local hook** (`.githooks/pre-commit`, active once `git config core.hooksPath .githooks` has
  been run in a given clone): blocks a commit that touches `src/`/`app.py`/`tests/`/`notebooks/`
  without touching `docs/PROGRESS.md`, `docs/ML_TOOLING.md`, or `ML_LEARNING_LOG.md`. Escape hatch
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

→ Concepts log: [ML_LEARNING_LOG.md](ML_LEARNING_LOG.md) | Theory: [docs/ML_THEORY.md](docs/ML_THEORY.md) | Env gotchas: [docs/ML_TOOLING.md](docs/ML_TOOLING.md)
