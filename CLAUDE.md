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

## Learning Goals (read this before writing any ML code)

**This project's primary purpose is for Guilherme to learn and practice hands-on ML, not just
produce a working portfolio artifact.** The portfolio is the by-product; the understanding is the
point. This changes how Claude Code should work in this repo:

- **Narrate the "why" behind every modelling decision, not just the "what."** Why this train/test
  split, why this metric, why this model before that one. A working notebook with no explained
  reasoning fails the actual goal even if it runs clean.
- **Surface tradeoffs and negative results honestly** rather than smoothing them into a clean
  narrative. "I tried X, it didn't beat the baseline, here's why" is a more valuable learning
  moment than quietly picking whichever model number looks best.
- **Flag real ML/stats gotchas when they come up** (e.g. dummy-variable collinearity, the
  bias-variance tradeoff showing up as a train/test gap) — these are exactly the things that are
  hard to learn from reading alone and are the reason this project exists.
- **When Guilherme asks "why" or seems unsure, slow down and explain conceptually before writing
  more code.** Don't treat clarifying questions as a detour from progress — they're the actual work.

### The two-module ML curriculum this project covers

| Module | ML paradigm | Core skills being practiced |
|---|---|---|
| **A — xG model** | Supervised, binary classification | Feature engineering from raw event data, baseline-before-complexity methodology, calibration vs. discrimination metrics, train/test design under distribution shift, honest model comparison |
| **B — Player similarity** | Unsupervised, clustering + dimensionality reduction | Feature scaling, K-means, PCA, judging cluster quality without ground-truth labels |

### Concepts already exercised (S2–S4)
- Feature engineering from domain knowledge (shot distance/angle/assist type from raw JSON)
- Deliberate non-random train/test split to test distribution shift (league → tournament), not just in-sample memorisation
- Calibration (Brier score, log loss) evaluated separately from ranking quality (ROC-AUC) — a model can rank well but still be miscalibrated
- Bias-variance tradeoff observed directly: default gradient boosting overfit (train AUC 0.825 vs test 0.794); tuning it down still didn't beat the simpler logistic baseline — a real example of complexity not paying for itself on limited data
- Dummy-variable collinearity: one-hot encoding all categories of `assist_type` without dropping a reference category produced individually unreliable coefficients — fixed via `drop_first`-style encoding
- A real Python gotcha with ML relevance: `bool(float('nan'))` is `True`, which silently corrupted a categorical feature until caught

### Coming up (S5+)
- Feature scaling (K-means is distance-based — unlike the tree/linear models used so far, raw feature scale will matter)
- Clustering without labels — a different mental model for "is this working" (elbow method, cluster cohesion, does the grouping make football sense) versus a clean metric like ROC-AUC
- PCA for dimensionality reduction and what it trades away (interpretability of individual components) for what it gains

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
| **S1** | Scaffold + data exploration | Folder structure, requirements.txt, .gitignore, `data_loader.py` for StatsBomb + SkillCorner, notebook 01 running end-to-end | ✅ Done |
| **S2** | xG feature engineering | `features.py` with distance, angle, body part, assist type, game state features using EURO 2024 + Leverkusen data; feature validation in notebook 02 | ✅ Done |
| **S3** | xG model — baseline | Logistic regression in `models.py`, ROC-AUC + calibration evaluation, shot map visualisation | ✅ Done |
| **S4** | xG model — upgrade + visuals | Gradient boosting, feature importance, player xG rankings, overperformer/underperformer table; PL 2015/16 as era benchmark | ✅ Done |
| **S5** | Player similarity — features | Per-90 metrics per player/position from event data + SkillCorner physical metrics (speed, sprints, acceleration), `similarity.py` skeleton | ✅ Done |
| **S6** | Player similarity — clustering | K-means, PCA, elbow method, player archetype labelling, notebook 03 | ✅ Done |
| **S7** | Radar charts + visuals | Radar chart per player (event + physical metrics combined), PCA scatter plot, "players like X" function output | ⬜ Not started |
| **S8** | README + polish | Full README narrative, outputs committed, repo clean, links ready for CV/LinkedIn | ⬜ Not started |

### Next Session (S7) — Checklist
- [x] S1: folder structure, requirements.txt, .gitignore, `data_loader.py`, notebook 01 (incl. bonus mplsoccer shot map) — runs clean
- [x] S2: `src/features.py` — distance, angle, body part, first-time, under-pressure, penalty/free-kick flags,
  assist type (Cross/Through Ball/Cut Back/Standard Pass/None), game-state score diff, `build_training_dataset()`
- [x] S3: `src/models.py` (logistic regression baseline, ROC-AUC/log-loss/Brier eval, calibration curve),
  `src/visualisation.py` (`plot_shot_map`, `plot_calibration_curve`), notebook 02 trained on
  Leverkusen 2023/24 + PL 2015/16, evaluated on EURO 2024 — ROC-AUC 0.786 train / 0.798 test
- [x] S4: gradient boosting model + tuning sweep in `models.py`, feature importance,
  `build_player_xg_table()` (overperformer/underperformer table), `plot_player_xg_ranking()`,
  PL 2015/16 era benchmark in notebook 02 — logistic regression confirmed as recommended model
- [x] Switched `assist_type` one-hot encoding to drop "None" as reference category (was flagged as
  dummy-variable collinearity in S3) — coefficients now read cleanly as "vs. an unassisted shot"
- [x] S5: `src/similarity.py` — minutes-played + position from StatsBomb `lineups` endpoint,
  per-90 event metrics (goals/shots/key passes/assists/progressive passes/dribbles/pressures/
  interceptions/tackles) for PL 2015/16 (300 qualifying players), SkillCorner physical per-90
  metrics (distance/HSR/sprints) for the 10 A-League sample matches (22 qualifying players)
- [x] S6: `scale_features`/`compute_elbow_scores`/`fit_kmeans`/`profile_clusters`/`run_pca` in
  `similarity.py`, `plot_elbow_curve`/`plot_pca_clusters` in `visualisation.py`, notebook 03 —
  K=4 clustering per position group (Defender/Midfielder/Forward) on PL 2015/16
- [ ] S7: radar charts per player (event-based per-90s; SkillCorner physical layer presented
  separately, see Learning Goals note on zero player overlap), PCA scatter as standalone
  deliverable, "players like X" lookup function
- [ ] Commit S5+S6 work (S1–S4 committed 2026-06-29; S5/S6 are new uncommitted work)

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
- **2026-06-29** — Closed out S1 (notebook 01 ran clean; added a bonus mplsoccer shot map for the
  sample EURO 2024 match, with outcomes Goal/Saved/Blocked/Off T/Wayward all explicitly coloured
  and legended — first version silently lumped "Off T"/"Wayward" into an unlabelled grey). Built S2
  (`src/features.py`): distance/angle computed from goalpost geometry (StatsBomb pitch, posts at
  y=36/44), assist type derived by joining each shot's `shot_key_pass_id` to its source pass event.
  Hit and fixed a real bug here — `pass_cross`/`pass_through_ball`/`pass_cut_back` columns hold
  `True`/`NaN`, and `bool(float('nan'))` is `True` in Python, so a plain truthy check classified
  ~72% of assists as crosses; fixed with explicit `is True` checks. Built S3 (`src/models.py`,
  `src/visualisation.py`, notebook 02): logistic regression trained on Leverkusen 2023/24 + PL
  2015/16 (10,824 shots, 10.1% conversion), evaluated on EURO 2024 (1,340 shots, 9.4% conversion) —
  ROC-AUC 0.786 train / 0.798 test, Brier 0.077 / 0.067, generalises cleanly league→tournament.
  Cached the StatsBomb pulls to `data/shots_train.pkl` / `shots_test.pkl` (gitignored, ~8 min to
  rebuild via `build_training_dataset()` — pyarrow isn't installed so pickle, not parquet).
  Coefficient review surfaced a real modelling caveat: `assist_type` is one-hot encoded across all
  5 categories with no dropped reference, which is a classic dummy-variable collinearity setup —
  sklearn's L2 regularization still produces an answer, but individual coefficients aren't cleanly
  interpretable in isolation, only relative differences between them are. Flagged for `drop_first=True`
  in S4. Nothing committed to git yet — S1 through S3 are all uncommitted local work.
- **2026-06-29 (cont.)** — Closed out S4. Fixed the assist-type collinearity flagged above by
  switching `build_feature_matrix` to drop "None" as the reference category (`ASSIST_TYPES[1:]`),
  so each assist coefficient now reads cleanly as "vs. an unassisted shot." Added
  `train_gradient_boosting()` to `src/models.py`: ran a small tuning sweep (default params
  overfit — train ROC-AUC 0.825 vs test 0.794) and landed on shallow trees (max_depth=2),
  learning_rate=0.05, subsample=0.8. Even tuned, GBM (train 0.796/test 0.793) did not clearly beat
  the logistic baseline (train 0.786/test 0.798) — reported this honestly in notebook 02 rather
  than forcing a "boosting wins" narrative; **logistic regression stays the recommended model**.
  Added `get_feature_importance()`, `build_player_xg_table()` (goals minus cumulative xG, the
  overperformer/underperformer lens), and `plot_player_xg_ranking()` to visualisation.py. Rebuilt
  the cached `data/shots_train.pkl` once more to add a `competition_id` column (needed to isolate
  PL 2015/16 shots from Leverkusen shots for the era-benchmark ranking — both were previously
  tagged identically as `league_context='league'`). PL 2015/16 ranking output passes the sniff
  test: Agüero/Mahrez/Kane top overperformers, Mitrović/Bony/Jerome top underperformers, both
  consistent with how that season is actually remembered. Notebook 02 now covers S3+S4 end-to-end,
  runs clean. Also added a project-level "Learning Goals" section to this file (right after
  Owner) — this project's purpose is Guilherme practicing hands-on ML, not just shipping a
  portfolio artifact, so future sessions should narrate the "why" behind modelling decisions,
  report negative/mixed results honestly, and slow down to explain when asked rather than racing
  to more code. S1 through S4 committed to git this session.
- **2026-06-29 (cont. 2)** — Closed out S5 (`src/similarity.py`). Minutes-played and position are
  pulled from StatsBomb's `lineups` endpoint (per-player on-pitch stints with from/to clock times
  and position, including in-match "Tactical Shift" position changes) rather than reconstructed
  from Starting XI + Substitution events — `lineups` already tracks exactly this, more reliably.
  Built per-90 event metrics (non-penalty goals, shots, key passes, assists, progressive passes,
  dribbles completed, pressures, interceptions, tackles) for PL 2015/16 — 300 players qualify at
  the 900-minute floor (118 Defenders / 104 Midfielders / 78 Forwards; goalkeepers excluded from
  clustering entirely, per `POSITION_GROUPS`). Hit another sparse-column gotcha like the S2 one:
  statsbombpy only includes a column in a match's events DataFrame if at least one event in that
  match has it set, so `pass_goal_assist` was missing entirely from matches with zero assists,
  crashing the full-season build partway through — fixed with `_safe_bool_column`/`_safe_column`
  helpers that substitute a default Series when the column doesn't exist, rather than assuming
  every match's schema is identical.
  Built `build_physical_per90_features()` for SkillCorner: speed/distance columns in `to_df()`
  output are entirely null, so they're derived from frame-to-frame position deltas (rescaled from
  normalised 0-1 coordinates to metres using the match's real pitch dimensions, 105×68m here).
  First pass extrapolated short tracked windows up to a full "per 90" rate assuming uniform
  intensity — one player tracked for only ~10 minutes got blown up 9x to reach his per-90 figure,
  which is not a number to build a scouting decision on. Raised `min_observed_minutes` to 30 (caps
  the extrapolation factor at 3x) — 22 of the original 32 tracked players survive, with the
  remaining figures (9,000-13,000m per 90 for outfield players, ~4,400m for what are almost
  certainly the two goalkeepers) landing in a believable range. Documented this as a real
  reliability gap between the StatsBomb event-based per-90s and the SkillCorner physical per-90s,
  not glossed over.
  **Confirmed explicitly (see Learning Goals section) that StatsBomb (PL/Bundesliga/Euro) and
  SkillCorner (Australian A-League) share zero players** — S7's "event + physical combined" radar
  chart will be two standalone capability demos, not one fused per-player profile. Cached
  `data/player_per90_pl_2015_16.pkl` and `data/physical_per90_skillcorner_sample.pkl`. S1-S4
  committed to git this session; S5 was committed separately right after.
- **2026-06-29 (cont. 3)** — Closed out S6. Added clustering to `src/similarity.py`
  (`scale_features`, `compute_elbow_scores`, `fit_kmeans`, `profile_clusters`, `run_pca`) and
  plotting to `visualisation.py` (`plot_elbow_curve`, `plot_pca_clusters`). Key design decision:
  **clustering is run separately per position group** (Defender/Midfielder/Forward, goalkeepers
  excluded), not on all outfield players together — clustering everyone at once would mostly just
  rediscover position itself rather than find play-style sub-archetypes within a position, which
  is what's actually useful for a recruitment framing. Used K=4 for all three groups (none of the
  elbow curves showed one obviously "correct" K; 4 balances archetype granularity against group
  size). `profile_clusters` gives each cluster's z-score profile vs. its position group's own
  population — the substitute for a clean accuracy metric here, since clustering has no ground
  truth to check against the way the xG model has `is_goal`.
  Results read as genuine football archetypes, not noise: midfielder cluster of
  Kanté/M'Vila/Gueye/Drinkwater (interceptions +0.85, tackles +0.97 z-score) is the ball-winning
  destroyer role — Kanté's title-winning Leicester season, a strong validation; another midfielder
  cluster of Özil/Fàbregas/Lallana (key passes +1.69, assists +1.97) matches Özil's record-assist
  season; defender cluster of Cresswell/Daniels/Bellerín/van Aanholt (key passes +1.23, assists
  +1.37) reads as attacking/overlapping full-backs vs. the central "stopper" defender cluster.
  **Found and documented a real data-quality wrinkle rather than hiding it**: one defender cluster
  has exactly one player, Michail Antonio, with absurd z-scores (+5.95 goals/90). He was primarily
  a winger that season who filled in defensively a handful of times; `position` is the season's
  *modal* per-match position, and that vote landed on a defensive slot despite his attacking
  output dominating. Not a clustering bug — K-means correctly found he's nothing like the other
  defenders — but a real limitation of "most common position across the season" as an assignment
  rule for versatile/misused players, noted directly in notebook 03 rather than smoothed over.
  Notebook 03 runs clean end-to-end. S5 and S6 are both uncommitted local work as of this entry.
- [x] S1 — Scaffold + data loader
- [x] S2 — xG feature engineering
- [x] S3 — xG baseline model
- [x] S4 — xG upgrade + visuals
- [x] S5 — Player similarity features
- [x] S6 — Clustering + PCA
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
