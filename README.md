# Football Analytics Portfolio — Player Evaluation Framework

A two-part analytics project built on public StatsBomb and SkillCorner data, designed to answer
two questions a recruitment or performance analysis team actually asks:

1. **Was that shot a good chance, or did the player just finish well?** (Module A — Expected Goals)
2. **Who plays like this player, and what type of player are they?** (Module B — Player Similarity)

Together these form a lightweight **Player Evaluation Framework** — the same kind of question set
used by recruitment and analytics teams at top-level clubs and data providers.

Built by **Guilherme Padinha** — Data Engineer with a semi-professional football background,
pivoting into football analytics.

---

## Module A — Expected Goals (xG) Model

**Question:** given where a shot was taken from, how it was taken, and what led to it — what's the
probability it results in a goal?

**Why it matters:** raw goal counts reward and punish players for finishing variance, not shot
quality. A striker scoring from good chances and a striker scoring from speculative long-range
efforts can have identical goal tallies and completely different underlying output. xG separates
the two.

### Approach
- Trained on **10,824 shots** from Bayer Leverkusen 2023/24 (a tactically distinctive unbeaten
  season) and Premier League 2015/16 (high shot volume, a well-known season as a sanity-check
  benchmark).
- Tested on **1,340 shots** from EURO 2024 — deliberately a different context (tournament
  football: fewer games, higher stakes, more conservative shot selection) to check whether a
  league-trained model actually generalises rather than just memorising one competition's shot
  profile.
- Features: distance and angle to goal (computed from real shot geometry, not approximated), body
  part, assist type (cross / through ball / cut back / standard pass / none), first-time finish,
  under pressure, penalty/free-kick, and live game-state score difference.
- Two models compared honestly: logistic regression (the baseline) and gradient boosting (the
  "should be better" candidate).

### Result

| Model | Train ROC-AUC | Test ROC-AUC (EURO 2024) | Train Brier | Test Brier |
|---|---|---|---|---|
| Logistic regression | 0.786 | **0.798** | 0.077 | **0.067** |
| Gradient boosting (tuned) | 0.796 | 0.793 | — | — |

Gradient boosting did **not** clearly beat the simpler model here, even after a tuning sweep —
logistic regression is the recommended model. Reporting that honestly matters more than picking
whichever number looks better: a model that's harder to explain to a coaching staff needs to earn
that cost with a real performance gain, and this one didn't.

The model also **generalises league → tournament without retraining** — test performance on
EURO 2024 was as good as or better than training performance, evidence the model is learning real
shot-quality signal rather than something specific to one competition.

![Calibration curve](outputs/calibration_curve.png)
![Feature importance](outputs/feature_importance.png)

### What it's used for

**Shot maps** — every shot on a pitch, sized by predicted quality, coloured by outcome:

![EURO 2024 shot map](outputs/euro2024_shot_map.png)

**Overperformer / underperformer ranking** — goals scored minus expected goals, the "is this
player finishing better or worse than their chances deserve" question a recruitment team asks
before paying a transfer fee for a hot scoring streak:

![PL 2015/16 xG ranking](outputs/pl_2015_16_xg_ranking.png)

Sergio Agüero, Riyad Mahrez, and Harry Kane top the overperformer list for PL 2015/16 — consistent
with how that title-race season is actually remembered, a useful sanity check that the model isn't
producing noise.

---

## Module B — Player Similarity & Recruitment Tool

**Question:** without relying on reputation or scout notes, what type of player is this, and who
else plays the same way?

**Why it matters:** this is the recruitment use case — find statistically similar alternatives to
a target player (for budget reasons, for a like-for-like replacement, for scouting an unfamiliar
league) using their actual on-pitch output rather than name recognition.

### Approach
- Per-90 event metrics (goals, shots, key passes, assists, progressive passes, dribbles,
  pressures, interceptions, tackles) built from StatsBomb event data, **Premier League 2015/16**,
  300 players clearing a 900-minute appearance floor.
- Clustering run **separately within each position group** (Defender / Midfielder / Forward,
  goalkeepers excluded) — clustering everyone together would mostly just rediscover position
  itself rather than find play-style differences within a position, which is the actually useful
  signal for recruitment.
- K-means (K=4 per group, chosen via the elbow method) plus PCA for visualisation.
- A separate, finer-grained **nearest-neighbour lookup** ("players like X") on top of the
  clustering — two players in the same cluster aren't necessarily equally similar, so this ranks
  by actual distance rather than just shared cluster membership.

![Elbow curves](outputs/similarity_elbow_curves.png)
![PCA clusters](outputs/similarity_pca_clusters.png)

### Result — real football archetypes, not statistical noise

- A midfielder cluster of **N'Golo Kanté, Yann M'Vila, Idrissa Gueye, Danny Drinkwater** — the
  ball-winning destroyer role, anchored by Kanté's title-winning Leicester season.
- A separate midfielder cluster of **Mesut Özil, Cesc Fàbregas, Adam Lallana** — the creative
  playmaker role, anchored by Özil's record-assist season.
- A defender cluster of **Aaron Cresswell, Ben Daniels, Héctor Bellerín, Patrick van Aanholt** —
  attacking, overlapping full-backs, distinct from the more conventional "stopper" defender
  cluster.

**Radar charts** make a player's profile legible at a glance against their position group's range:

![Player radar charts](outputs/player_radar_examples.png)

**Nearest-neighbour lookup**, validated against players whose style is well known:

| Target | Nearest neighbours |
|---|---|
| N'Golo Kanté | Idrissa Gana Gueye, Cheick Tioté, Francis Coquelin, Fernando |
| Aaron Cresswell | Chris Brunt, Ben Davies, Bacary Sagna, Ryan Bertrand, Ben Daniels |
| Harry Kane | Jamie Vardy, Andy Carroll, Odion Ighalo, Jermain Defoe, Sergio Agüero |

All five lists read as genuine stylistic matches, not statistical coincidence — the qualitative
check used throughout this project wherever there's no ground-truth label to validate against.

### An honest data-quality caveat

One defender cluster contains a single player, **Michail Antonio**, with extreme z-scores driven
by attacking output that doesn't belong in a defensive cluster at all. He was primarily a winger
that season who occasionally filled in at the back — his *modal* match position landed on
"defender," which is a real limitation of using "most common position across a season" to classify
versatile or misused players. K-means didn't make a mistake here; it correctly found he's nothing
like the other defenders. The mistake, if there is one, is upstream in how position is assigned.
Noted here rather than quietly excluded, because this is exactly the kind of edge case a real
recruitment tool needs a human in the loop for.

---

## Why two separate data sources, and why they don't overlap

StatsBomb (event data: passes, shots, pressures) and SkillCorner (broadcast tracking: speed,
sprints, distance covered) are genuinely different data layers — one tells you *what* a player
did, the other tells you *how physically demanding* doing it was. They are demonstrated separately
here (StatsBomb on Premier League / Bundesliga / EURO 2024; SkillCorner on its own public
A-League sample) because the two datasets share zero players — there is no single match in both.
Combining them at the player level would need a club's internal data, where both layers exist for
the same roster. Treat this as two capability demos of a methodology that *would* fuse into one
profile, given that data.

---

## Repository Structure

```
football-analytics-portfolio/
├── README.md
├── CLAUDE.md                  ← full project log, ML reasoning, session-by-session decisions
├── ML_LEARNING_LOG.md         ← theory reference + concepts exercised + tooling gotchas
├── requirements.txt
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_xg_model.ipynb
│   └── 03_player_similarity.ipynb
├── src/
│   ├── data_loader.py          ← StatsBomb + SkillCorner ingestion
│   ├── features.py             ← xG feature engineering
│   ├── models.py                ← xG model training and evaluation
│   ├── similarity.py            ← clustering, PCA, nearest-neighbour lookup
│   └── visualisation.py         ← pitch plots, radar charts, all chart functions
└── outputs/                    ← saved plots (shown above)
```

## Tech Stack

Python · `statsbombpy` · `kloppy` · pandas · numpy · scikit-learn · `mplsoccer` · matplotlib

## Running it

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01_data_exploration.ipynb
```

Notebooks run top-to-bottom with no manual data download — `statsbombpy` pulls StatsBomb's open
data directly; no API key required.

---

## What's next

Two directions are scoped but not yet built:

- **Module C — Performance Under Pressure (PUP):** a per-player KPI comparing performance in
  high-stakes league moments (title race, relegation, derby) against tournament performance, for
  the 51 players who appear in both this project's league and tournament datasets. Fully scoped in
  `ML_LEARNING_LOG.md`, not started.
- **A browsable front-end** for the player lookup and radar charts, so these results don't only
  live inside notebooks.
