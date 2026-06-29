# Football Analytics Portfolio — CLAUDE.md

This file is the source of truth for Claude Code working on this project.
Read it fully at the start of every session before touching any file.

---

## Project Goal

Build a football analytics portfolio project to support a career pivot into football data roles
at Premier League, La Liga, and Bundesliga clubs, as well as data providers (StatsBomb, Opta,
Football Radar, Hudl). The project must demonstrate both technical depth (ML, data engineering)
and football domain knowledge.

Target audience for the portfolio: sporting directors, analytics leads, and technical recruiters
at football clubs and data providers. The README must be readable by non-technical people.
The code must be clean enough to be reviewed by senior data scientists.

---

## Owner

**Guilherme Padinha**
- Data Engineer / Consultant, ~3 years experience, based in Lisbon
- Stack: Python, SQL, Scala, Databricks, Hadoop, HBase, Git, CI/CD
- Strong in pipeline engineering and ETL; solid theoretical ML, limited hands-on ML practice
- Semi-professional football background (forward/winger, 2008–2018); currently active in amateur league
- Applying to: Premier League clubs, La Liga clubs, Bundesliga clubs, Football Radar, StatsBomb, Opta

---

## What We Are Building

Two interconnected analyses on StatsBomb open data (La Liga, Messi-era seasons):

### Module A — xG Model
- Predict goal probability per shot using event-level features
- Model: logistic regression as baseline, gradient boosting as final
- Features: distance, angle, body part, assist type, game state, shot technique
- Output: xG per shot, per player, per team; overperformers vs underperformers vs xG
- Visualisations: shot maps on pitch (mplsoccer), xG timeline per match, player xG ranking

### Module B — Player Similarity / Recruitment Tool
- Cluster players by position using per-90 performance metrics derived from event data
- Methods: K-means clustering, PCA for dimensionality reduction
- Output: player archetypes per position, "players like X" lookup, radar charts per player
- Framing: presented as a lightweight recruitment scouting tool

These two modules together form a "Player Evaluation Framework" — the same framing used by
Football Radar in their Club Services team job descriptions.

---

## Repository Structure

```
football-analytics-portfolio/
│
├── CLAUDE.md                  ← this file
├── README.md                  ← project narrative (written for non-technical audience)
├── requirements.txt           ← all Python dependencies
│
├── data/
│   └── .gitkeep               ← raw StatsBomb JSON ignored via .gitignore
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_xg_model.ipynb
│   └── 03_player_similarity.ipynb
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py         ← StatsBomb data ingestion via statsbombpy
│   ├── features.py            ← feature engineering for xG and clustering
│   ├── models.py              ← xG model training and evaluation
│   ├── similarity.py          ← clustering and PCA logic
│   └── visualisation.py       ← all pitch plots and charts (mplsoccer)
│
└── outputs/
    └── .gitkeep               ← saved plots, model artifacts
```

---

## Data Sources

### StatsBomb Open Data (primary)
- Library: `statsbombpy` (pulls data programmatically, no manual download needed)
- No API key required for open data
- Data volume: ~1–2 GB uncompressed locally; well within free GitHub limits

**Avoid the Messi-era La Liga as primary dataset** — overdone in public portfolios, weak differentiation.
Use it only for specific player benchmarks if needed.
Ronaldo and Messi as obviously outliers. Worth mentioning and entertainting to compare with. This La Liga period was really good which makes their feats even more absurd. 

**xG Model — data split strategy:**

Tournament football (World Cups, Euros) and league football have structurally different shot profiles:
tournament format means fewer games, higher stakes, more conservative tactics, different shot risk profiles.
This is a legitimate modelling consideration — we treat them as separate contexts intentionally.

- **Training data (league context):** Leverkusen 2023/24 full season + PL 2015/16 — high volume,
  consistent pressure dynamics, chronic rather than acute stakes
- **Test/validation data (tournament context):** UEFA EURO 2024 — deliberately out-of-distribution,
  tests whether a league-trained xG model generalises to tournament football
- **Narrative:** "I separated training and test contexts because tournament and league football have
  structurally different shot profiles" — this is the kind of analytical decision to highlight in interviews

**Priority datasets:**

| Dataset | Coverage | Role |
|---|---|---|
| Bayer Leverkusen 2023/24 | 34 matches, events + 360 | xG training (league) — tactically unique unbeaten season |
| Premier League 2015/16 | 380 matches, events | xG training (league) — volume + era benchmark |
| UEFA EURO 2024 | 51 matches, events + 360 | xG test/validation (tournament) — out-of-distribution test |
| Copa América 2024 | 32 matches, events | Optional extension if EURO 2024 test is interesting |
| SkillCorner 2024/25 | 10 matches, physical tracking | Physical layer for player similarity (Module B) |
| Messi-era La Liga | Multiple seasons | Reference/benchmarks only if needed |

Key StatsBomb data objects we use:
- `competitions` — list of available competitions
- `matches` — match metadata per competition/season
- `events` — granular event data (shots, passes, dribbles, pressures, 3400+ events/match) per match
- `lineups` — player lineups per match
- `three-sixty` — freeze frame: position of every visible player at moment of each event (selected matches)

### SkillCorner Open Data (physical layer)
- Repo: `github.com/SkillCorner/opendata`
- Contains: broadcast tracking data (X/Y coordinates at 10fps) for 10 matches, 2024/25 A-League
- Physical metrics: speed zones, sprint distance, acceleration, high-speed running, off-ball runs
- This is the closest publicly available equivalent to the "sensitive" GPS/biometric data clubs use internally
- Heart rate and true biometric data (HRV, sleep, hydration) are never released publicly — legally and
  contractually protected by clubs. Physical tracking is the public-facing equivalent.
- Combining StatsBomb event data with SkillCorner physical data in one portfolio is rare and differentiating

### On biometric data
True biometric data (heart rate variability, sleep cycles, muscle recovery) is collected by clubs via
STATSports, Catapult, and similar wearables but is classified as sensitive health data and never released.
No league or federation makes this public. Do not pursue this angle — SkillCorner physical tracking data
is the realistic and still impressive substitute.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core language |
| statsbombpy | StatsBomb open data ingestion |
| kloppy | Unified loader for multiple tracking/event data providers incl. SkillCorner |
| pandas | Data manipulation |
| numpy | Numerical operations |
| scikit-learn | ML models (logistic regression, K-means, PCA) |
| mplsoccer | Football pitch visualisations |
| matplotlib / seaborn | Supporting charts |
| plotly | Interactive charts (optional, for README visuals) |
| jupyter | Exploratory notebooks |
| git | Version control |

IDE: VS Code with Claude Code extension + GitHub Copilot Free (inline autocomplete)

---

## Coding Standards

- **Language**: English only — all code, comments, docstrings, commit messages
- **Style**: PEP8, meaningful variable names, no magic numbers
- **Notebooks**: each notebook must be runnable top-to-bottom without errors
- **Functions**: all functions in `src/` must have docstrings
- **No hardcoded paths**: use relative paths or config constants
- **Commits**: small and descriptive — one logical change per commit
- **No data files in git**: raw StatsBomb JSON goes in `data/` which is gitignored
- **Comments**: always include inline comments in code — explain the "why", not just the "what"
- **Small decisions**: do not stop to ask for confirmation on minor implementation choices
  (variable names, minor structure, param defaults) — use best judgement and move on

---

## Session Workflow

At the start of every Claude Code session:
1. Read this CLAUDE.md fully
2. Check `git status` and `git log --oneline -10` to understand current state
3. Give a 2-line summary of where we are and what you plan to do this session
4. Ask Guilherme what we are working on today if not specified
5. Never modify files outside the repo without explicit instruction

At the end of every session:
1. Ensure all new code is saved
2. Give a 3-line summary of what was done and what is unresolved
3. Suggest a commit message for the work done
4. Update the Progress Log section of this file

### Communication Style
- **Planning**: one short sentence on what you are about to do before doing it
- **After doing**: one short sentence confirming what was done and any side effect worth knowing
- **No long preambles, no summaries that restate the code** — assume Guilherme can read it
- **Errors**: explain what failed and the fix in plain language, not a wall of stack trace commentary

---

## Model Selection Guide

Use the right model for the right task to maximise output quality per credit spent:

| Model | Use for | When to switch |
|---|---|---|
| **Sonnet** (default, ~90% of work) | Writing code, debugging, feature engineering, visualisations, notebook work, most tasks | Start here always |
| **Opus** (sparingly) | Architecture decisions, repeated Sonnet failures, complex modelling trade-offs, README narrative | Only if Sonnet fails 2–3 times on the same problem |
| **Haiku** (quick tasks) | Simple lookups, quick syntax questions, minor reformatting | Use in Claude.ai chat sidebar, not Claude Code |

**Rule**: never open Opus for a task Sonnet can handle. Never use Claude Code for a task
Copilot Free resolves inline in 2 seconds (boilerplate, autocomplete, trivial syntax).

### Token efficiency tips
- Use `/compact` in Claude Code when the session history gets long — compresses context, keeps essentials
- Use `/clear` when switching between modules (e.g. done with xG model, starting clustering)
- Keep sessions to 45–60 min with a clear goal — long unfocused sessions waste context budget
- Point Claude Code to files directly rather than pasting code into chat

---

## Session Roadmap

Each session has a clear scope, deliverable, and done condition.
Update the status column at the end of each session.

| Session | Focus | Key deliverables | Status |
|---|---|---|---|
| **S1** | Scaffold + data exploration | Folder structure, requirements.txt, .gitignore, `data_loader.py` for StatsBomb + SkillCorner, notebook 01 running end-to-end | ⬜ Not started |
| **S2** | xG feature engineering | `features.py` with distance, angle, body part, assist type, game state features using EURO 2024 + Leverkusen data; feature validation in notebook 02 | ⬜ Not started |
| **S3** | xG model — baseline | Logistic regression in `models.py`, ROC-AUC + calibration evaluation, shot map visualisation | ⬜ Not started |
| **S4** | xG model — upgrade + visuals | Gradient boosting, feature importance, player xG rankings, overperformer/underperformer table; PL 2015/16 as era benchmark | ⬜ Not started |
| **S5** | Player similarity — features | Per-90 metrics per player/position from event data + SkillCorner physical metrics (speed, sprints, acceleration), `similarity.py` skeleton | ⬜ Not started |
| **S6** | Player similarity — clustering | K-means, PCA, elbow method, player archetype labelling, notebook 03 | ⬜ Not started |
| **S7** | Radar charts + visuals | Radar chart per player (event + physical metrics combined), PCA scatter plot, "players like X" function output | ⬜ Not started |
| **S8** | README + polish | Full README narrative, outputs committed, repo clean, links ready for CV/LinkedIn | ⬜ Not started |

### Next Session (S1) — Checklist
- [x] Create full folder structure
- [x] Write `requirements.txt` (include kloppy for SkillCorner loading)
- [x] Write `.gitignore` (ignore `data/`, `outputs/`, `.ipynb_checkpoints`, `__pycache__`)
- [x] Write `src/data_loader.py` with `load_competitions()`, `load_matches()`, `load_events()`, `load_skillcorner_tracking()`
- [ ] Write `notebooks/01_data_exploration.ipynb` — pull EURO 2024 data + SkillCorner sample, inspect shot events and physical metrics, basic EDA
- [ ] Confirm notebook runs top-to-bottom without errors
- [ ] Commit: `feat: project scaffold and data loader`

---

## Progress Log

Update this section at the end of every session.

- **2026-06-28** — Fixed local dev environment: `python`/`pip` weren't recognized in the VS Code
  terminal because the User PATH only contained the broken Windows Store "App execution alias" stub,
  not the real Python 3.10.7 install (`C:\Users\guilh\AppData\Local\Programs\Python\Python310\`).
  Added that install (+ its `Scripts\`) to the User PATH and pinned it as the workspace interpreter
  in `.vscode/settings.json`. Separately, `pip install` failed with `CERTIFICATE_VERIFY_FAILED`
  because Avast Antivirus intercepts HTTPS traffic for scanning and Python's bundled `certifi`
  didn't trust Avast's generated root cert — fixed by appending that root cert to both `certifi`
  cacert.pem files (the top-level `certifi` package and pip's vendored copy).
  `pip install -r requirements.txt` now succeeds. **New terminals only** — already-open terminals
  won't pick up the PATH change. S1 scaffold partially done (folders, `.gitignore`,
  `requirements.txt`, `src/data_loader.py` + module stubs) — `notebooks/01_data_exploration.ipynb`
  and the scaffold commit are still pending for next session.
- [ ] S1 — Scaffold + data loader
- [ ] S2 — xG feature engineering
- [ ] S3 — xG baseline model
- [ ] S4 — xG upgrade + visuals
- [ ] S5 — Player similarity features
- [ ] S6 — Clustering + PCA
- [ ] S7 — Radar charts
- [ ] S8 — README + polish

---

## Portfolio Framing

When writing README sections, docstrings, or any public-facing text:
- Frame Module A + B together as a "Player Evaluation Framework"
- Emphasise: data engineering rigour (clean pipelines, reproducibility) AND analytical insight
- Always include a "so what" — not just what the model does, but what decision it informs
- Avoid academic language; write as if explaining to a sporting director, not a reviewer

---

## Career Context (relevant for tailoring outputs)

Target roles being applied to in parallel:
- Data Engineer / Analytics Engineer at football clubs (PL, Bundesliga, La Liga)
- Data Scientist at Football Radar (London) — requires production ML experience
- Data Analyst at StatsBomb, Opta, Hudl

This project is the primary portfolio differentiator. Once complete, it will be linked on:
- GitHub (public repo)
- LinkedIn profile under Projects
- CV under a dedicated Projects section

Key gap this project addresses: no prior public football data work despite strong engineering
background and genuine football domain knowledge.
