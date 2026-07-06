# ML Learning Log

Companion to CLAUDE.md. Running record of ML/stats concepts exercised, gotchas hit, and ideas parked. Read this before starting a new module or before an interview — it's the "why", not the "what."

→ Theory reference: [docs/ML_THEORY.md](docs/ML_THEORY.md) | Environment gotchas: [docs/ML_TOOLING.md](docs/ML_TOOLING.md)

---

## Module A — xG Model (supervised, binary classification)

Key gotchas and lessons — most recent first:

- **A shapeless empty Series can corrupt a `pd.concat` even when every other column is fine**
  (2026-07-05, `similarity.py`'s `extract_player_match_actions`). Adding `clearances`/`blocks`
  columns (for defender-facing stats requested in the app) meant writing a zero-Pass-events
  synthetic test — and it broke `.set_index(["player", "team"])` on the *output*, not on
  anything clearance/block related. Root cause: the pre-existing `progressive_passes` fallback
  for "zero completed passes" was `pd.Series(name=..., dtype=int)` — a plain default
  `RangeIndex`, not the empty 2-level `(player, team)` `MultiIndex` every other action's
  `.groupby(["player", "team"]).size()` produces even with zero rows. `pd.concat(axis=1)`
  mixing one differently-shaped empty index among several correctly-shaped ones silently
  produced a malformed combined index — invisible until something tried to actually use
  `player`/`team` as columns downstream. Fixed by deriving the empty case the same way as
  everywhere else (`completed_passes.groupby(["player", "team"]).size()`, safe even at zero
  rows since `player`/`team` always exist) instead of hand-building a differently-shaped
  empty Series. Unreachable with real data — StatsBomb matches always have pass events — but
  the general lesson holds beyond this one function: **when a code path fabricates its own
  "nothing here" placeholder instead of deriving it the same way as the non-empty case, check
  that the placeholder's *shape* actually matches**, not just its values.
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

- **A library can silently override rcParams theming — verified by rendering and reading actual
  pixels, not by re-reading the code** (2026-07-06). Guilherme screenshotted the running app: the
  dark theme worked everywhere except the radar chart, which stayed white. Root cause:
  `visualisation.py`'s `plot_player_radar` called `radar.setup_axis(ax=ax)` without passing
  `facecolor` — mplsoccer's `Radar._setup_axis` defaults that to `'#FFFFFF'` and calls
  `ax.set_facecolor()` itself, which runs *after* the axes already existed with the correct
  rcParams-derived dark background, silently stomping it. Fixed by threading the app's
  `circle_facecolor` param through to `setup_axis(facecolor=...)` too, not just `draw_circles`.
  Verified the fix by actually rendering a synthetic radar and reading pixel RGB values from the
  saved PNG (not just re-reading the diff) — confirms `#12181a` at the axes region, not assumed.
  General lesson: a plotting library that exposes its own `facecolor`/background parameters is
  telling you it does NOT reliably inherit global theming — every one of its own background-setting
  calls needs the override passed explicitly, not just the ones a first pass happened to touch.
- **A percentile column formatted to a string before sorting sorts wrong** (2026-07-06, `app.py`'s
  "All per-90 stats" table). `.sort_values("Percentile")` ran on strings like `"98th"`/`"9th"` —
  lexical comparison puts `"9th"` after `"89th"` (since `'8' < '9'` character-by-character), which
  silently misorders any single-digit-vs-double-digit percentile pair. Not something a quick look
  would catch (the table still "looks sorted" for most rows) — found while restructuring this
  exact table for an unrelated reason (adding a "Total" column) and noticing the sort key was a
  formatted string. Fixed by sorting on the numeric percentile first, formatting to a display
  string only after. Lesson: format-for-display and sort-key must never be the same column when
  the format isn't already lexically monotone (e.g. zero-padded) with the underlying value.
- **Raw season totals matter as much as per-90 rates — different jobs, different audiences**
  (2026-07-06). `build_player_per90_features` divided every action count by minutes and kept only
  the rate — correct for clustering/percentiles (comparing players with different minutes fairly),
  but the wrong number for a human headline ("0.80" reads as noise; "29" reads as a season). Now
  keeps both: `ACTION_COLUMNS` (raw totals) alongside the existing `<col>_p90` rates, in the same
  table, no separate rebuild path. Sanity-checked against a real number before trusting it:
  Cristiano Ronaldo's 2015/16 La Liga non-penalty-goal total came out to 29 (his real season had
  35 total including penalties) — the arithmetic and the football both check out.
- **Widening the app's player pool exposed a real, hard data-recency ceiling, not just a config
  change** (Phase 4b real wiring, 2026-07-05). Asked "why only PL 2015/16 — I want it as
  updated as possible," the honest answer had to be checked, not assumed: StatsBomb's *free*
  open data simply has no recent men's top-flight season at all, for any league already in this
  project (PL/La Liga/Serie A/Ligue 1 all cap out at 2015/16 — that's the newest full-season
  men's data StatsBomb gives away, not a gap this project's pulling can close). The genuine lever
  available was breadth + the two 2023/24 women's leagues (the newest full-season data this
  project has anywhere), so `config.SIMILARITY_SETS` now spans 6 competitions instead of 1
  (`app.py`/`app_data.py`), clustered together per position group rather than per league. Said
  the ceiling plainly in the app itself (`Under the hood` methodology expander) instead of
  quietly widening the pool and letting "more data" imply "more recent than it actually is."
  **Deliberately still no cross-league normalisation** — per-90 rates are compared raw across
  leagues of different competitiveness, so a cross-league "similar player" match is flagged in
  the UI as a coarser signal than a same-league one, matching Phase 4b's original open item
  rather than quietly resolving it by fiat.
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
- **"Goal-line clearance" isn't a real StatsBomb sub-type** (2026-07-05). Asked to surface
  defenders' goal-line clearances specifically, checked the real schema first (same habit as
  the goalkeeper feature work below) rather than assuming a field existed: `Clearance` events
  only carry body-part/aerial-won sub-fields, no last-ditch/goal-line classification at all —
  that granularity is an Opta-style stat, not a StatsBomb one. Added a plain `clearances` count
  (plus `blocks`, the same situation) as the closest honest proxy, and said so explicitly in the
  app rather than quietly labelling a generic clearance count as something more specific than
  it is.
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
