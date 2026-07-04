# Module Specs

→ [CLAUDE.md](../CLAUDE.md) | Product purpose: [FRAMEWORK.md](FRAMEWORK.md)

---

## Module A — Expected Goals (xG) Model

**Question:** given where a shot was taken from, how it was taken, and what led to it — what's the probability it results in a goal?

**Features:**
- `distance_to_goal` — from shot location to goal centre (StatsBomb pitch, posts at y=36/44)
- `angle_to_goal` — degrees subtended by the goalposts (law of cosines)
- `body_part_*` — head / foot / other (one-hot)
- `assist_type_*` — Cross / Through Ball / Cut Back / Standard Pass (one-hot, "None" dropped as reference; each coefficient reads as "vs. unassisted shot")
- `first_time`, `under_pressure`, `is_penalty`, `is_free_kick` — situation flags
- `score_diff` — live game-state score difference

**Models (Phase 2 honest comparison):**
- Logistic regression (scaled pipeline): train 0.786, test **0.765** ROC-AUC — **recommended model**
- Gradient boosting (tuned, max_depth=2, lr=0.05, subsample=0.8): 0.796/0.760 — did not clearly beat logistic
- Calibrated GBM (isotonic): Brier 0.0661→0.0659 — third honest non-win

**Phase 2 additions:** `build_logistic_pipeline` (Pipeline/ColumnTransformer), `get_coefficients`, `cross_validate_model` (0.783 ± 0.009 in-distribution), `train_baseline_classifier` (geometry-only 0.712), `train_calibrated_gbm`.

**Output:** xG per shot/player/team; overperformer/underperformer table (`build_player_xg_table`); shot maps; calibration curves.

**Planned upgrades** (see [ROADMAP.md](ROADMAP.md)): uncertainty on goals−xG + hierarchical/empirical-Bayes finishing model, header/foot interaction, calibration by stratum → **Phase 5**; 360-context features + post-shot xGOT → **Phase 7**.

---

## Module B — Player Similarity & Recruitment Tool

**Question:** without relying on reputation or scout notes, who plays like this player, and what archetype are they?

**Data:** PL 2015/16, 300 outfield players clearing 900-min floor. Position groups (Phase 2 minutes-weighted): Defender 119 / Midfielder 106 / Forward 75.

**Per-90 features:** non-penalty goals, shots, key passes, assists, progressive passes, dribbles completed, pressures, interceptions, tackles.

**Goalkeepers (2026-07-05, built not yet wired in):** excluded from the outfield clustering above on purpose — a keeper's tackles/progressive-passes rate is meaningless, so reusing the same columns would just rediscover "this is a goalkeeper" rather than distinguish between keepers. `build_goalkeeper_per90_features` (`src/similarity.py`) gives them their own feature set instead — shots faced, saves, goals conceded, claims, punches, sweeper actions per 90, plus `save_pct` (saves ÷ shots faced) — verified against real PL 2015/16 data (27 keepers clearing the minutes floor, recognisable names: Čech, de Gea, Lloris, Courtois, Schmeichel). One honest caveat: `save_pct` divides by StatsBomb's own "Shot Faced" GK-event count, which may include some off-target/blocked shots a keeper never had to save — it isn't necessarily the broadcast "saves ÷ shots on target" stat, and cross-referencing the linked `Shot` event's outcome would tighten that up if this becomes user-facing. Not yet wired into `config.py`/clustering/the app — that's a separate integration decision (own K? own silhouette check? added to the app's position filter?), deliberately left open rather than rushed.

**Position assignment:** `resolve_season_positions` — total season minutes per group, not modal per-match position. Reclassified 10 borderline hybrids in Phase 2. Michail Antonio stays a Defender (920 min RB/wing-back vs 761 wing — genuinely the plurality).

**Pipeline:**
- `StandardScaler` → `fit_kmeans` (K=4 per group)
- `compute_silhouette_scores`: peaked K=2 at ~0.25 (soft continuum) → K=4 kept deliberately for archetype granularity
- `run_pca` + `plot_pca_clusters` for 2D scatter visualisation
- `find_similar_players` — Euclidean distance in standardised space, within position group (continuous ranking)
- `plot_player_radar` — mplsoccer Radar, axes at 5th-95th percentile (avoids Antonio outlier distortion)

**Validated against:** Kanté → Gueye/Tioté/Coquelin/Fernando; Cresswell → Brunt/Davies/Sagna/Bertrand; Kane → Vardy/Carroll/Ighalo/Defoe/Agüero

**SkillCorner physical layer:** `build_physical_per90_features` — distance/HSR/sprints per 90 from A-League tracking data. Standalone capability demo only (no player overlap with StatsBomb datasets).

**Planned upgrades** (see [ROADMAP.md](ROADMAP.md)): multi-competition pool + cross-league normalisation → **Phase 4**; Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features (xA/progressive-pass-distance) → **Phase 6**.

---

## Module C — "PUP" (Performance Under Pressure)

**Status: scoped only, not started (now Phase 9 — opportunistic). Do not assume any code exists for this.** Phase 5's hierarchical finishing model delivers most of PUP's "skill vs. luck" payoff with cleaner stats and none of the selection-bias confound, so PUP is deprioritised behind it.

**Hypothesis:** players who perform well in high-pressure league moments (title race, relegation six-pointer, derby, must-win) should perform comparably in tournaments. PUP = the per-player KPI measuring that at league level, validated against tournament output.

**Key finding enabling this:** 51-player overlap between league training data (34 from Leverkusen 2023/24 roster, who largely also played EURO 2024) and EURO 2024 test data. Real transfer validation possible — frame as correlation-level check, not a trained predictive model.

**Confound to always name:** tournament squads are selection-biased. Any observed link is confounded by that selection — not a clean causal test.

**What's needed when picked up:**
1. External match-importance labels (StatsBomb has no league-table or rivalry metadata) — a scraped
   SofaScore/FlashScore standings table is a candidate source, see
   [DATA.md](DATA.md#candidate-alternative--supplementary-data-sources-not-yet-used)
2. Per-player PUP score: delta between high-pressure and normal league performance rates
3. Scatter validation: league PUP vs. EURO 2024 knockout-stage performance for the 51-overlap players
4. `src/similarity.py`'s per-90 architecture is directly reusable — same action-count pattern, split into "high pressure" vs. "normal" buckets
