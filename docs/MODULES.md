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

**Generalisation beyond EURO 2024 (Phase 4c, men's 2026-07-09, women's 2026-10-01):** the same
`TRAIN_SETS`-fitted logistic model is scored separately (not pooled) against five more held-out
tournaments via `config.GENERALISATION_TEST_SETS`/`models.evaluate_by_competition`:

- men's: FIFA World Cup 2022 (0.808), Africa Cup of Nations 2023 (0.807), Copa América 2024
  (0.763, smallest men's sample at 751 shots);
- women's (`gender="female"`): FIFA Women's World Cup 2023 (0.777), UEFA Women's EURO 2025 (0.763).

The ranking holds across all six (0.76–0.81). **Correction (2026-10-01):** docs had called EURO 2024's
0.765 "the floor of the four". Copa América's 0.763 was always lower, so EURO 2024 is near the
bottom, not the floor, and the 0.002 gap is noise. Calibration-in-the-large (goals ÷ summed xG)
ranges 0.83–1.04. Women's EURO 2025 is 0.98, so there is no women's-specific under-prediction.
Its Brier (0.092) is the worst of the six mostly because its base goal rate is the highest
(11.8%): Brier isn't comparable across populations with different base rates (see
ML_LEARNING_LOG.md). See `metrics.json`'s `xg_generalisation` section and
`outputs/xg_generalisation_by_tournament.png`. `config.TEST_SETS` (`[EURO_2024]`) is unchanged.
This is additional evidence, not a replacement for the headline test set.

**Planned upgrades** (see [ROADMAP.md](ROADMAP.md)): uncertainty on goals−xG + hierarchical/empirical-Bayes finishing model, header/foot interaction, calibration by stratum → **Phase 5**; 360-context features + post-shot xGOT → **Phase 7**.

---

## Module B — Player Similarity & Recruitment Tool

**Question:** without relying on reputation or scout notes, who plays like this player, and what archetype are they?

**Data (notebook/pipeline, unchanged):** PL 2015/16, 300 outfield players clearing 900-min floor. Position groups (Phase 2 minutes-weighted): Defender 119 / Midfielder 106 / Forward 75. This is what `metrics.json`/notebook 03/`pipeline.py` describe — kept to one competition on purpose, since it's the teaching example (see CLAUDE.md's learning mandate).

**Data (app pool, Phase 4b, 2026-07-05):** the Streamlit app's player pool is wider — every dataset in `config.SIMILARITY_SETS` (Premier League, La Liga, Serie A, Ligue 1, all 2015/16, plus Frauen Bundesliga and FA WSL, both 2023/24), clustered together per position group rather than per competition (`src/app_data.py::_build_combined_similarity_table`). **Cross-league normalisation (2026-07-13):** per-90 rates are no longer compared directly across leagues — `similarity.normalize_within_competition` first expresses each stat as standard deviations above/below the player's own competition's average, and clustering/`find_similar_players` both run on those league-adjusted (`_lz`-suffixed) features rather than the raw pooled ones. Still a *relative*, data-only fix, not a true competitiveness rating (no external league-strength index exists in this project's data) — a cross-league "similar player" match now compares relative standing rather than a raw rate, but still assumes each league's stat distribution has a broadly comparable shape. Radar axes, percentiles, and signature stats stay on the raw per-90 rates on purpose (real-unit displays, not a similarity computation). **Honest ceiling:** StatsBomb's free open data has no recent men's top-flight season at all — 2015/16 is the newest full men's-league season available for any of these four leagues; the women's leagues (2023/24) are the newest full-season data this project has anywhere. A live/current-season pool isn't achievable on this data source without a paid licence, which is why "wider" rather than "newer" is the honest description of what changed for the men's side.

**Per-90 features:** non-penalty goals, shots, key passes (excluding assists: StatsBomb flags the two separately and they never overlap), assists, progressive passes, dribbles completed, pressures, interceptions, tackles, clearances, blocks. Clearances/blocks added 2026-07-05 for defender-facing "sofascore-like" stats — StatsBomb's `Clearance` event has no last-ditch/goal-line sub-classification (checked the real schema before adding this, see ML_LEARNING_LOG.md), so a plain clearance count is the closest honest proxy for that kind of defending, not a more specific stat mislabelled as one. `build_player_per90_features` returns the raw season-total count alongside every rate (2026-07-06) — clustering/percentiles still key off the `_p90` rate, but the app leads with the whole-number total since that's what reads as an actual season, not a decimal.

**Goalkeepers (2026-07-05, wired into the app 2026-07-13):** excluded from the outfield clustering above on purpose — a keeper's tackles/progressive-passes rate is meaningless, so reusing the same columns would just rediscover "this is a goalkeeper" rather than distinguish between keepers. `build_goalkeeper_per90_features` (`src/similarity.py`) gives them their own feature set instead — saves, goals conceded (penalties included), claims, punches, sweeper actions per 90 (raw season totals kept alongside, same "keep both" reasoning as the outfield builder), plus `save_pct` = saves ÷ (saves + goals conceded), the share of on-target shots stopped. A keeper's shots count only when on target (2026-10-03, Guilherme's call): there is no all-shots total, and a save of a shot that was going wide ("Shot Saved Off Target") isn't a save, since StatsBomb's own shot outcome calls that shot off target. **Fixed 2026-10-02:** StatsBomb logs one keeper event per shot, and its "Shot Faced" type is only the remainder (off target, blocked, post), not every shot faced. The July caveat here suspected the denominator but had it backwards: `save_pct` had been saves ÷ "Shot Faced", median 38% instead of ~70%, and goals conceded had left out penalties. Checked on 150 matches: keeper events equal the shot count every time.

**App wiring (2026-07-13):** `src/app_data.py`'s `_build_combined_tables` builds goalkeepers from the same `config.SIMILARITY_SETS` pool alongside the outfield table and concatenates them — **123 goalkeepers** across the 6-competition pool, a 4th `app.py` position filter alongside Defender/Midfielder/Forward, with their own signature stats, radar axes, and "players like X" ranking. A real bug caught by Streamlit's `AppTest` harness during wiring, not by reading the code: `build_goalkeeper_per90_features` originally returned only the `_p90` rate columns, not the raw season totals the signature-stat cards need (unlike the outfield builder, which always kept both) — fixed by adding `GK_ACTION_COLUMNS` to its `keep_columns` (see ML_LEARNING_LOG.md).

**Goalkeeper clustering (2026-07-13, same-day follow-up):** goalkeepers went from wired-but-unclustered to a real silhouette-informed K, using the same method as the outfield groups but checked against the actual pool that gets clustered (the app's 123-keeper, league-normalised, 6-competition pool — there is no single-league goalkeeper table to match the outfield notebook's narrower scope against). Silhouette peaks at K=2 (0.238 on the corrected, on-target-only keeper stats of 2026-10-03, the same soft-continuum shape every outfield group shows); K=4 is kept anyway for archetype granularity, the same call as the outfield groups, at a comparable silhouette value (0.187 vs. their 0.130–0.150 on the same pool). `src/app_data.py::_cluster_position_groups` generalises the old outfield-only `_add_cluster_labels` to cover both — same normalise-then-cluster recipe, parameterised by which groups and which feature columns — so goalkeepers now share the app's Style archetype panel with outfield players.

**Market value + comparison view (Phase 9, 2026-07-14):** `src/market_value.py` matches each player onto an external Transfermarkt valuation by name (no shared ID exists between the two data sources — see DATA.md's Transfermarkt section for the full entity-resolution account, including two real matching bugs found and fixed against actual data), shown on a player's own page, in the "players like X" table, and on the Leaderboard — directly answering Module B's original "similar profile, cheaper" pitch (see FRAMEWORK.md). Men's competitions only (~99% match rate on the four 2015/16 leagues, 1,327 of 1,347 players: StatsBomb's nickname finds the popular name Transfermarkt uses, and a club check confirms identity and tells namesakes apart); the two women's leagues have zero coverage in this data source, verified directly rather than assumed. A new **Compare players** view puts two players side by side (any two, any position) — market value and Finishing always compare directly; signature stats, an overlaid radar (`visualisation.plot_player_radar_comparison`, mplsoccer's native two-radar `draw_radar_compare`), and a percentile table only render when both players share a position group, since that's the only case where the same per-90 feature set applies to both.

**Position assignment:** `resolve_season_positions` — total season minutes per group, not modal per-match position. Reclassified 10 borderline hybrids in Phase 2. Michail Antonio stays a Defender (920 min RB/wing-back vs 761 wing — genuinely the plurality).

**Pipeline:**
- `StandardScaler` → `fit_kmeans` (K=4 per group)
- `compute_silhouette_scores`: peaked K=2 at ~0.22–0.26 (soft continuum) → K=4 (~0.15–0.17) kept deliberately for archetype granularity
- `run_pca` + `plot_pca_clusters` for 2D scatter visualisation
- `find_similar_players` — Euclidean distance in standardised space, within position group (continuous ranking)
- `plot_player_radar` — mplsoccer Radar, axes at 5th-95th percentile (avoids Antonio outlier distortion)

**Validated against** (11-feature set, re-checked 2026-10-01): Kanté → Tioté/Gueye/Kirchhoff/Yacob/Cork; Cresswell → Brunt/Davies/Sagna/Bertrand/Naughton; Kane → Ighalo/Vardy/Giroud/Costa/Walcott. Michail Antonio is still the most extreme defender (nearest neighbour 6.3 standardised units away, 2–3× a typical match) but is no longer a one-man cluster — K-means now spends that cluster on ball-playing centre-backs and absorbs him into the attacking full-backs (see notebook 03).

**SkillCorner physical layer:** `build_physical_per90_features` — distance/HSR/sprints per 90 from A-League tracking data. Standalone capability demo only (no player overlap with StatsBomb datasets).

**Planned upgrades** (see [ROADMAP.md](ROADMAP.md)): multi-competition pool + cross-league normalisation → **Phase 4** (done 2026-07-13); Mahalanobis distance, possession-adjusted actions, GMM soft membership, richer creative features (xA/progressive-pass-distance) → **Phase 6**.

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
