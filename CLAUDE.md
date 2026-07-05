# Football Analytics Portfolio — CLAUDE.md

Project source of truth. Read this first every session, then load linked docs on demand.

---

## Current Status

**Active initiative:** Framework Hardening & Expansion — Phases 0–3 complete; Phase 4a/4d done,
4b wired into the app (2026-07-05, see below), 4c still pending; Phase 8 minimal Streamlit build
shipped 2026-07-04 (ahead of strict phase order, for an upcoming demo), then extended 2026-07-05
with real-time search, a dark theme, and a widened multi-competition player pool — see
[docs/PROGRESS.md](docs/PROGRESS.md). Full review backlog folded into a renumbered 0–9 program on
2026-07-02.
**Next: a "player career" page/view is under discussion (multi-season drill-down, international
tournament data — trophies/awards/MOTM data does not exist in any current source and would need
new scraping infra); deploy Phase 8 to Streamlit Community Cloud remains the maintainer's own step.**
(360-context xG is now Phase 7; the Streamlit product build is now Phase 8 — see the phase table.)
Run the app locally: `python -m src.app_data` (once, to build `app_data/`) then `streamlit run app.py`.

Key numbers: xG logistic test ROC-AUC **0.765** (EURO 2024, in-game shots only, penalty shootouts dropped). Similarity: K=4 per position group, silhouette ~0.24 (soft continuum) on the notebook/pipeline's single-competition (PL 2015/16) scope — the app's own player pool is wider (6 competitions, see MODULES.md). 65 unit tests passing. *(xG/similarity numbers are emitted to [metrics.json](metrics.json) by `python -m src.metrics`; a doc-lint test fails the build if a current-state doc drifts from it — see Phase 3b. Whole rebuild — data, models, outputs, manifest, metrics — runs headless via `python -m src.pipeline`, see Phase 3d.)*

→ Phase tracker: [docs/INITIATIVE.md](docs/INITIATIVE.md) | Session log: [docs/PROGRESS.md](docs/PROGRESS.md)

---

## What This Project Is

Player Evaluation Framework — two modules on StatsBomb/SkillCorner open data:
- **Module A — xG**: supervised binary classification. Logistic regression (recommended over GBM — honest non-win). Train: Leverkusen 2023/24 + PL 2015/16. Test: EURO 2024 (deliberate distribution shift).
- **Module B — Player similarity**: unsupervised K-means/PCA. Per-90 per position group (Defender/Mid/Forward, GKs excluded). "Players like X" nearest-neighbour lookup + radar charts.
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
  manifest.py        ← data provenance manifest (`python -m src.manifest`)
  metrics.py         ← metrics.json single source (`python -m src.metrics`)
  pipeline.py        ← headless rebuild: data → models → outputs → manifest/metrics (`python -m src.pipeline`)
  app_data.py        ← Phase 8 build step: writes app_data/*.parquet (`python -m src.app_data`)
Makefile               ← thin wrapper around src/pipeline.py
app.py                 ← Phase 8 Streamlit app (`streamlit run app.py`) — reads app_data/, no live pulls
app_data/              ← precomputed Parquet artifacts the app reads (small, committed — not gitignored)
.streamlit/config.toml ← Streamlit theme
notebooks/
  01_data_exploration.ipynb
  02_xg_model.ipynb          ← Phase 2 ML rigor section added
  03_player_similarity.ipynb ← silhouette + minutes-weighting added
docs/
  FRAMEWORK.md           ← what the tool is for (purpose, user story, scope)
  ARCHITECTURE.md        ← module dependency graph, data flow, pure/IO-split pattern
  INITIATIVE.md          ← phase tracker (Phases 0–9)
  MODULES.md             ← Module A/B/C specs and current state
  DATA.md                ← data sources, datasets table, cache file index
  CONTEXT.md             ← owner, learning goals, career context, portfolio framing
  ROADMAP.md             ← session roadmap (S1–S9) + Phase 3 scope
  PROGRESS.md            ← recent session log (Phase 3 spine + docs pass)
  PROGRESS_ARCHIVE.md    ← S1–S8 + Phase 0–2 history
  ML_THEORY.md           ← ML/stats theory reference (textbook-level)
  ML_TOOLING.md          ← Windows/environment gotchas
ML_LEARNING_LOG.md       ← ML gotchas and decisions log (pointers to above docs)
tests/                   ← 61 pytest unit tests, all green
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
