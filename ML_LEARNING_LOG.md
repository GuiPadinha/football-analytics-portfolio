# ML Learning Log

Companion to CLAUDE.md. Running record of ML/stats concepts exercised, gotchas hit, and ideas parked. Read this before starting a new module or before an interview — it's the "why", not the "what."

→ Theory reference: [docs/ML_THEORY.md](docs/ML_THEORY.md) | Environment gotchas: [docs/ML_TOOLING.md](docs/ML_TOOLING.md)

---

## Module A — xG Model (supervised, binary classification)

Key gotchas and lessons — most recent first:

- **Sparse-column bug had three more instances, found by writing the edge case rather than
  hitting it in production** (Phase 4, follow-up). Adding a zero-shots-match test for
  `extract_shot_features` (no `pytest.raises` intended — meant to be a boring pass) surfaced that
  `shot_body_part`/`shot_type`/`shot_outcome`/`shot_key_pass_id` were still bare column accesses,
  same crash shape as the `shot_first_time`/`under_pressure` fix above but one level sparser
  (missing because a match has *zero shots at all*, not just zero shots with one flag set). Fixed
  the same way — routed through `safe_column`. Unlike the Barcelona 2020/21 case this wasn't hit by
  real data yet (StatsBomb matches basically always have >=1 shot), but at ~2,400 newly-cached
  Phase 4 matches the odds of a true zero-shot match stop being negligible, and the fix was free
  once the gap was visible. Lesson: writing the deliberately-adversarial test found the bug before
  the data did, not after.
- **More league volume didn't close the tournament generalisation gap** (Phase 4, quick smoke test,
  not yet the real Phase 4b wiring). Retrained the same logistic pipeline on baseline (10,824 shots)
  vs +La Liga/Serie A/Ligue 1 2015/16 (38,804) vs +all 16 Barcelona seasons too (50,789), same
  untouched EURO 2024 test set throughout. Test ROC-AUC crept 0.765→0.766→0.768 — smaller than the
  ±0.009 fold-to-fold noise the Phase 2 CV already measured, so not distinguishable from noise — while
  test Brier got marginally *worse* (0.0651→0.0656→0.0659) even as train ROC-AUC rose more
  (0.786→0.804→0.803). Reads as confirmation of the CV finding, not a new one: the league→tournament
  shift is structural (different shot profile), not a sample-size problem, so naively pooling more
  league shots mostly overfits the training distribution rather than transferring. Caveat: no
  cross-league normalisation in this quick test — the real Phase 4b pass needs that before this is
  a final verdict.
- **Sparse-column crash on a genuinely new competition** (Phase 4). `extract_shot_features` read
  `shot_first_time`/`under_pressure` with a bare column access; statsbombpy drops a flag column
  entirely from a match's events if zero shots in that match have it set (same pattern `similarity.py`
  already handled for pass/dribble/duel columns). Worked by luck across Leverkusen/PL2015/16/EURO2024
  — broke for real the moment Phase 4 added Barcelona 2020/21, where one of 35 matches had zero
  first-time shots. Fixed by moving `similarity.py`'s `_safe_bool_column`/`_safe_column` up to
  `data_loader.py` (shared, public) and using them in `features.py` too — the kind of bug that only
  shows up when you actually add data diversity, not when you re-run the same three datasets.
- **Calibrated GBM didn't rescue it** (Phase 2). Brier 0.0661→0.0659. S4 tuned-shallow GBM wasn't pathologically miscalibrated to begin with. "Logistic stays" survives a harder test.
- **Baseline ladder** (Phase 2). Geometry-only 0.712 → full 0.765. ~80% of discrimination is pure shot geometry.
- **5-fold CV as variance estimate** (Phase 2). In-distribution 0.783 ± 0.009; EURO test 0.765 at bottom edge → real ~1.7-pt league→tournament cost. CV ≠ substitute for OOD test.
- **Scaling a logistic model — the non-movement is the lesson** (Phase 2). Test ROC-AUC barely moved; the win is clean convergence and coefficient comparability (`distance_to_goal` −0.10 raw → −0.84 per-SD).
- **ROC-AUC inflated by trivially-rankable cases** (Phase 1). Penalty-shootout shots (period 5) padded test ROC-AUC 0.798 → 0.765 after removal. Evaluation population is itself a modelling decision.
- **Python NaN gotcha with ML consequences** (S2). `bool(float('nan'))` is `True` — `pass_cross`/`pass_through_ball`/`pass_cut_back` columns hold `True`/`NaN`, so ~72% of assists misclassified as crosses. Fixed with explicit `is True` checks.
- **Dummy-variable trap in practice** (S3 flagged, S4 fixed). All 5 `assist_type` categories encoded with no dropped reference. Fixed by dropping "None" as reference.
- **Observed bias-variance tradeoff** (S4). Default GBM: train 0.825 vs test 0.794. Tuned: 0.796/0.793. Logistic still won: 0.786/0.798. Real negative result, reported honestly.
- **Calibration ≠ discrimination** (S3). ROC-AUC answers ranking; Brier answers probability accuracy. For xG, calibration matters more — the output *is* a probability.
- **Train/test under deliberate distribution shift** (S3). League → train; tournament → test. Not a random split — testing generalisation to a structurally different shot context.
- **Baseline-before-complexity** (S3–S4). Logistic first, GBM second. GBM didn't beat logistic even tuned — reported honestly. Logistic regression stays.

---

## Module B — Player Similarity (unsupervised, clustering + PCA)

Key gotchas and lessons — most recent first:

- **Goalkeepers need their own feature set, not a branch of the outfield one** (2026-07-05).
  Investigated StatsBomb's `Goal Keeper` event type before writing anything (`goalkeeper_type`
  values across 15 real matches: Shot Faced, Shot Saved [+3 rarer synonym labels], Goal Conceded,
  Collected, Punch, Keeper Sweeper) rather than guessing what fields exist. Confirms the existing
  "cluster per position group" lesson (S6) one step further: mixing GKs into the outfield
  `ACTION_COLUMNS` wouldn't just blur the clusters, it'd be measuring almost-always-zero tackles/
  passes for every keeper — no signal at all, not just weak signal. `build_goalkeeper_per90_features`
  mirrors the outfield builder's shape (counts summed over a season, converted to per-90, same
  900-minute floor) with a goalkeeper-appropriate column set instead. Verified on real PL 2015/16
  data before trusting it: 27 keepers clear the floor, and the ranking is recognisable (Čech, de
  Gea, Lloris, Courtois, Schmeichel all present). One caveat surfaced by looking at the actual
  numbers rather than assuming they were right: `save_pct` came out lower (~25-51%) than the
  broadcast "save %" stat football fans expect (usually quoted 65-75%) — most likely because
  StatsBomb's `Shot Faced` count includes shots the keeper faced but wasn't necessarily the one
  who touched (e.g. off-target attempts still logged as a facing event), so the denominator isn't
  exactly "shots on target." Documented as an open caveat in MODULES.md rather than either hiding
  the low numbers or asserting they're the standard stat without checking further.
- **Percentile-bounded radar axes** (S7). 5th-95th percentile scales to avoid outlier distortion (Antonio). General technique: any shared visual scale with a single extreme outlier.
- **Nearest-neighbour vs. cluster membership** (S7). `find_similar_players` ranks by Euclidean distance within the standardised space — two players in the same cluster can be at very different distances. The ranking is the recruitment-useful shape.
- **Minutes-weighted position assignment** (Phase 2). `resolve_season_positions` totals minutes per group, not modal match slot — reclassified 10 borderline hybrids. Did **not** move Michail Antonio (920 min at RB/wing-back vs 761 at wing — genuinely defensive). The S6 "primarily a winger" claim was simply wrong.
- **Silhouette score — peaked at K=2 with low absolute values (~0.25)** (Phase 2). That low level is the finding: play-styles within a position are a soft **continuum**, not crisp blobs. K=4 kept deliberately against the metric for archetype utility.
- **Sparse StatsBomb schema** (S5). StatsBombpy only includes a column if at least one event in a match uses it — `pass_goal_assist` absent from zero-assist matches. Fixed with `_safe_bool_column`/`_safe_column` helpers.
- **PCA's tradeoff** (S6). 2D scatter is lossy; `explained_variance_ratio_` quantifies what survives. Individual-feature interpretability traded away for visualisability.
- **No ground truth changes the success criterion** (S6). Used elbow method (eyeballed) + z-score cluster profiling (does it read as a recognisable football role?) as substitutes for accuracy.
- **Cluster per position group** (S6). Clustering all outfield players together just rediscovers position. Run within each group for style sub-archetypes.
- **Feature scaling matters here, not for Module A** (S6). K-means uses Euclidean distance. `StandardScaler` before clustering, not before the xG models.

---

## Module C (candidate) — "PUP" (Performance Under Pressure)

**Status: scoped only, not started.** Full spec in [docs/MODULES.md](docs/MODULES.md).

Core idea: players performing well in high-pressure league moments (title race, relegation, derby, must-win) should perform well in tournaments. PUP = per-player delta (high-pressure vs. normal league performance).

**51-player overlap** between league training data and EURO 2024 makes real transfer validation possible (34 via Leverkusen roster). **Always name the confound:** tournament squads are selection-biased — only good/in-form players get picked.

What's needed: external match-importance labels (StatsBomb has no league-table or rivalry metadata). Scalar per-player PUP score. Scatter validation against EURO 2024 knockout performance for the 51 overlap players.

---

## How to use this file

- After any session producing a real "why" moment — add an entry here, dated, under the relevant module.
- Before an interview — this is the list of decisions worth explaining.
- If an idea isn't built yet, write it here (as Module C shows) — the cost is near zero; losing it across a context clear means full re-derivation.
- New ML/stats theory → add to [docs/ML_THEORY.md](docs/ML_THEORY.md) (that file is the complete textbook primer).
- New environment/tooling gotcha → add to [docs/ML_TOOLING.md](docs/ML_TOOLING.md).
