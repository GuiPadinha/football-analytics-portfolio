# ML Learning Log

Companion to CLAUDE.md. CLAUDE.md is the project's operating manual (goals, structure, roadmap);
this file is the running record of **ML/stats concepts actually exercised**, gotchas hit, and
ideas parked for later. Update this any time a session produces a real learning moment — a
gotcha, a tradeoff, a metric choice, a result that didn't go the way the cleaner narrative would
want. Keep entries dated and tied to the session that produced them.

This file is the one to reread before starting a new module, or before an interview — it's the
"why," not the "what" (the "what" is in the code).

---

## Module A — xG model (supervised, binary classification)

### Concepts exercised

- **Baseline-before-complexity.** Logistic regression first, gradient boosting second, explicitly
  to test whether added model complexity earns its keep — not because logistic regression was
  assumed sufficient. (S3, S4)
- **Train/test split under deliberate distribution shift.** League data (Leverkusen 2023/24 + PL
  2015/16) → train; tournament data (EURO 2024) → test. Not a random split — the point was testing
  generalisation to a structurally different shot-risk context, not just in-sample memorisation.
  (S3)
- **Calibration vs. discrimination are different questions.** ROC-AUC answers "does the model rank
  true goals above non-goals" (discrimination). Brier score / log loss answer "do predicted
  probabilities match observed frequencies" (calibration). A model can be good at one and bad at
  the other — for xG specifically, calibration matters more than usual because the model's whole
  output *is* a probability, not just a ranking. (S3)
- **Bias-variance tradeoff, observed directly, not just described.** Default
  `GradientBoostingClassifier` settings overfit: train ROC-AUC 0.825 vs test 0.794. Tuned it down
  (shallow trees, low learning rate, subsampling) and the gap shrank, but the tuned model (train
  0.796/test 0.793) still didn't clearly beat the simpler logistic baseline (train 0.786/test
  0.798). **Real negative result, reported honestly rather than forced into a "boosting wins"
  narrative** — added model complexity didn't pay for itself on this dataset size. Logistic
  regression remained the recommended model. (S4)
- **Dummy-variable collinearity.** One-hot encoding all 5 categories of `assist_type` with no
  dropped reference category meant the dummies always summed to 1 — sklearn's L2 regularization
  still produced an answer, but individual coefficients weren't cleanly interpretable in isolation.
  Fixed by dropping "None" (unassisted shot) as the reference category; every remaining coefficient
  now reads as "vs. an unassisted shot." (S3 flagged it, S4 fixed it)
- **A genuine Python gotcha with ML consequences.** `bool(float('nan'))` evaluates to `True` in
  Python. StatsBomb's pass-flag columns (`pass_cross`, `pass_through_ball`, `pass_cut_back`) hold
  `True`/`NaN`, not `True`/`False` — a plain truthy check on these silently misclassified ~72% of
  assists as crosses. Fixed with explicit `is True` checks. Lesson generalises: never trust a
  truthy check on a column you haven't confirmed is actually boolean-typed. (S2)
- **Feature choice over feature volume.** `angle_to_goal` (degrees subtended by the goalposts) was
  added specifically because `distance_to_goal` alone can't distinguish a shot dead-center from one
  on the byline at the same distance — angle captures "how much of the goal is reachable," which
  distance can't. (S2)
- **ROC-AUC is inflated by trivially-rankable cases — a data-integrity lesson with a number on it.**
  The EURO 2024 test set silently included penalty-shootout attempts (period 5): ~75% converters,
  all flagged `is_penalty`, which the model ranked confidently and correctly. They aren't open/
  in-game shots, so they shouldn't be graded by an xG model at all — and dropping them *lowered*
  test ROC-AUC from 0.798 to 0.765. Removing easy, correct rankings makes the metric look worse
  precisely because they were padding it. The 0.765 is the honest measure of ranking on real
  in-play shots; the 0.798 was flattered. General lesson: a discrimination metric is only as
  meaningful as the population it's computed over — deciding *which cases belong in the evaluation
  set* is itself a modelling decision, not a given. (Hardening Phase 1, 2026-06-30)

### Module C (candidate) — "PUP" (Performance Under Pressure), recovered and scoped 2026-06-29

This was originally discussed in an earlier session, lost to a context clear, and recovered from
Guilherme's recollection this session. Writing it down properly now so it survives the next clear
too — **not started**, this is a spec for a future session, not a description of working code.

**Hypothesis:** certain league moments (title-race fixtures, relegation six-pointers, derbies,
must-win games) carry a pressure profile comparable to tournament moments (World Cup/Euro,
especially knockout stage). A player who performs well in high-pressure league moments should be
expected to perform comparably well under tournament pressure — PUP is the KPI meant to capture
that "performs well under pressure" trait at the league level, to then check against tournament
output.

**Definition decision (clarified 2026-06-29):** pressure is defined at the **match level**
(title race / relegation / derby / must-win status), not from in-match proxies like score state or
the existing `under_pressure` shot flag. This is richer and matches the original framing, but it's
also the hard part — StatsBomb has no league-table, rivalry, or fixture-stakes metadata, so this
needs external sourcing (see future-session steps below).

**Key finding — real transfer validation is possible, not just parallel methodology.** Checked
player overlap between the existing cached league data (`data/shots_train.pkl`: Leverkusen 2023/24
+ PL 2015/16) and tournament data (`data/shots_test.pkl`: EURO 2024):

| Source competition | Players | Overlap with EURO 2024 | Overlap rate |
|---|---|---|---|
| Premier League 2015/16 | 456 | 20 | ~4% |
| Bayer Leverkusen 2023/24 | 179 | 34 | ~19% |
| **Total unique overlap** | — | **51** | — |

This is the opposite situation to Module B's StatsBomb/SkillCorner split (zero overlap, forced into
a parallel-demo framing). Here there's a real, non-trivial group of players — concentrated in the
Leverkusen 2023/24 → EURO 2024 link (Wirtz, Xhaka, Frimpong, Tah, Andrich, etc., since that roster
is largely the same group of players a few months apart) — who can be directly compared: league PUP
score vs. actual tournament performance. Still a small sample (fewer once filtered to enough
high-pressure-match minutes in both contexts) — frame any result as a correlation-level check, not
a trained predictive model.

**Confound to name up front, every time this is written about:** tournament squads are themselves
selection-biased — only good/in-form players get picked at all. Any observed link between league
PUP and tournament performance is confounded by that selection, not a clean causal test. State this
explicitly in any future write-up, the same way the S4 boosting result and the S6 Antonio cluster
were reported as real limitations rather than smoothed over.

**Future-session plan, when this gets picked up:**
1. **New data needed (the actual hard part).** Match-level importance labels for the training
   competitions: final league table position/movement at time of match (title race / relegation
   framing, joined from an external football-data source by date + teams), a small hand-curated
   derby/rivalry list. For EURO 2024, knockout-stage vs. group-stage is already derivable from
   existing match metadata — no external sourcing needed there.
2. **Feature reuse.** `src/similarity.py`'s per-90 architecture
   (`extract_player_match_actions`, the per-90 division pattern) is directly reusable — same
   per-player action counts, just split into "high pressure" vs. "normal" match buckets per player
   instead of summed across a whole season.
3. **PUP score (starting proposal, to be revisited, not final):** a per-player delta — performance
   rate (goals/key actions per-90, or `xg_diff` from the existing xG model) in labelled
   high-pressure league matches minus the same rate in normal league matches. Conceptually reuses
   `build_player_xg_table`'s overperformance logic rather than inventing a new metric from scratch.
4. **Validation.** For the ~51 overlapping players, plot league PUP score against EURO 2024
   knockout-stage performance. Given the small N, this is a scatter-plot/correlation-level check,
   not a model to be trained and deployed.

---

## Module B — Player similarity (unsupervised, clustering + PCA)

### Concepts exercised

- **Feature scaling matters here in a way it didn't for Module A.** Logistic regression and
  gradient boosting fit a coefficient/split per feature, so raw scale barely matters. K-means
  measures literal Euclidean distance between points, so an unscaled `progressive_passes_p90`
  (tens) would dominate `non_penalty_goals_p90` (usually under 1) purely on units, not football
  relevance. `StandardScaler` (mean 0, std 1) applied before clustering, not before the xG models.
  (S6)
- **No ground truth changes what "is this working" means.** The xG model has `is_goal` to check
  against; clustering has nothing equivalent. Two substitutes used instead:
  - **Elbow method** (`compute_elbow_scores`) — inertia always decreases as K grows, so there's no
    single "correct" K the way a classification metric gives one right answer. Read by eye, not
    computed.
  - **Cluster profiling via z-scores** (`profile_clusters`) — express each cluster's mean feature
    values as standard deviations from the population mean, so a human can judge "does this
    grouping make football sense" (e.g. interceptions +0.85, tackles +0.97 z-score reads directly
    as "ball-winning destroyer role"). (S6)
- **Clustering per position group, not across all outfield players.** Clustering everyone together
  would mostly just rediscover position itself (defenders cluster away from forwards trivially)
  rather than find play-style sub-archetypes *within* a position, which is the actually useful
  output for a recruitment framing. (S6)
- **PCA's explicit tradeoff.** Reducing to 2D for a scatter plot makes clusters visualisable but
  each resulting axis is a blend of original features — `explained_variance_ratio_` quantifies how
  much signal survives the squeeze, and individual-feature interpretability is deliberately given
  up in the 2D plot (still recovered via `profile_clusters`, which works in the original feature
  space, not the PCA-reduced one). (S6)
- **A cluster result that exposed a real labelling limitation, not a clustering bug.** A one-player
  defender cluster turned out to be Michail Antonio — primarily a winger that season, but `position`
  is the *modal* (most common) position across the season, and a handful of defensive appearances
  won that vote despite his attacking output dominating. K-means correctly found he doesn't resemble
  real defenders; the bug, if there is one, is in "most common position across a season" as an
  assignment rule for versatile/misused players. Documented rather than hidden. (S6)

### Data-quality caveats actively tracked (not glossed over)

- **StatsBomb event-based per-90s vs. SkillCorner physical per-90s have different reliability.**
  Event per-90s are summed over a full season (large sample). Physical per-90s are extrapolated
  from a single match's *observed* tracking window (broadcast camera visibility, not true playing
  time), capped at a 3x extrapolation factor (`min_observed_minutes=30`) after an early version
  blew up a 10-minute window 9x to reach a per-90 figure. (S5)
- **Zero player overlap between the two data sources used in Module B.** StatsBomb (PL/Bundesliga/
  Euro) and SkillCorner (Australian A-League broadcast tracking) share no players. The event-based
  clustering and the physical-tracking layer are two standalone capability demonstrations, not one
  fused per-player profile — this needs to stay explicit in any README/portfolio framing of S7's
  output, or it will read as an oversight rather than a deliberate scope boundary. (S5)
- **Nearest-neighbour lookup vs. cluster membership are different similarity questions.**
  `find_similar_players` (S7) reuses the same standardised feature space as K-means but answers a
  different question: K-means gives a coarse in/out label (same cluster or not), while raw
  Euclidean distance gives a continuous, rankable "most to least similar." For a "players like X"
  tool the ranking is the actually useful shape — two players can be in the same cluster but at
  very different distances from each other, which a cluster label alone can't distinguish. Sanity
  check came back clean: nearest neighbours for Kanté, Cresswell, and Kane were all recognisable
  same-role players (Gana Gueye/Tioté/Coquelin for Kanté; other attacking full-backs for Cresswell;
  Vardy/Defoe/Agüero for Kane). (S7)
- **Percentile-bounded radar axes vs. true min/max.** `plot_player_radar` (S7) scales each axis to
  the 5th-95th percentile of the comparison population rather than the true min/max — directly
  motivated by the S6 Antonio outlier: a true-range axis would let one extreme value compress every
  other player's chart toward the centre, on every feature, not just the one Antonio is unusual in.
  This is a general technique, not radar-specific: any time a single extreme outlier could distort a
  shared visual scale, percentile clipping is the standard fix, traded against slightly
  understating how extreme the true outlier actually is.

---

## Tooling / environment gotchas (Windows-specific, not ML theory)

Not modelling lessons, but real friction hit while building this project on Windows — worth a
home so they don't get silently re-solved (or re-broken) every few sessions.

- **`python`/`pip` not recognized in a fresh PowerShell terminal.** The real Python 3.10 install
  lives at `C:\Users\guilh\AppData\Local\Programs\Python\Python310\` and is on the *User* PATH —
  but each newly opened terminal in this environment sometimes doesn't pick it up (and the
  Windows Store "App execution alias" stub shadows it if it does try to resolve `python`). Fix:
  call the interpreter by full path
  (`& "C:\Users\guilh\AppData\Local\Programs\Python\Python310\python.exe" ...`) when a bare
  `python` command fails, rather than re-debugging PATH each time. Original PATH fix from S1 is in
  the Progress Log below if this needs revisiting properly.
- **`UnicodeEncodeError: 'charmap' codec can't encode character...` when printing accented names.**
  Windows PowerShell's default console codepage is cp1252, which can't represent many characters
  StatsBomb player names contain (Kramarić, Šeško, Šeško, Þór Sigurðsson, etc.). Printing these
  directly crashes. Fix: `chcp 65001` (UTF-8 codepage) and/or setting `$env:PYTHONUTF8 = "1"`
  before running the Python process, and `sys.stdout.reconfigure(encoding='utf-8')` inside the
  script if printing directly rather than through a notebook.
- **`jupyter nbconvert --execute` silently corrupting a literal apostrophe-name in cell source.**
  Hit when a notebook cell contained `"N'Golo Kanté"` — the executed cell came back with `Kant�`
  and the player lookup failed. Same root cause as the codepage issue above: the nbconvert
  subprocess inherits the console's cp1252 codepage unless told otherwise. Fix: set
  `$env:PYTHONUTF8 = "1"` in the PowerShell session before invoking `nbconvert`. Unrelated to this
  fix, but found at the same time: the StatsBomb data for this player is actually stored as
  `N''Golo Kanté` with a **doubled apostrophe** — not a typo introduced anywhere in this project,
  a genuine quirk in StatsBomb's source data. Any future lookup by this exact name needs the
  double apostrophe, confirmed via `df[df['player'].str.contains('Kant')]` directly against the
  cached pickle.
- **mplsoccer's `Radar.setup_axis` raising `KeyError: 'bottom'` on a manually-created polar axes.**
  Passed `plt.subplots(subplot_kw={"polar": True})` expecting `Radar` to draw onto a polar
  projection, since radar charts are visually polar plots. Wrong assumption: `Radar` expects a
  **plain rectangular** `Axes` and configures the polar-like projection internally — handing it an
  already-polar axes breaks its internal spine-visibility logic (polar axes don't have
  `'bottom'`/`'top'`/`'left'`/`'right'` spines the way rectangular ones do). Fix: create plain
  `plt.subplots()` axes with no `subplot_kw`, let `Radar.setup_axis(ax=ax)` handle the projection.
  General lesson: check a plotting library's actual expected input type from its own usage
  examples/docstring rather than inferring it from what the output visually looks like.
- **VS Code ran notebooks on the wrong interpreter (conda base 3.9.12), not the project's 3.10 env.**
  Cells failed with *"Running cells with 'base (Python 3.9.12)' requires the ipykernel package"*
  even though the workspace interpreter was pinned to 3.10 in `.vscode/settings.json`. Root cause:
  the Jupyter **kernel** is chosen and remembered separately from the Python **interpreter**, and
  the `.ipynb` files had a `base` kernelspec baked into their metadata, so VS Code kept reselecting
  conda base. Two-part fix: (1) `jupyter.kernels.filter` in `.vscode/settings.json` to hide the
  conda-base interpreter from the kernel picker; (2) normalize every notebook's
  `metadata.kernelspec` to the portable `python3` (via `nbformat`). Separately, to execute a
  notebook *headless* on a chosen interpreter, register it as a kernel
  (`python -m ipykernel install --user --name ...`) and pass `--ExecutePreprocessor.kernel_name=...`
  to `nbconvert` — otherwise nbconvert inherits the notebook's stale kernelspec and runs on the
  wrong env. (Hardening Phase 1, 2026-06-30)
- **Parquet vs. pickle for caching depends on whether the columns are nested.** The processed shot
  tables are flat (scalars only) → Parquet round-trips cleanly, is faster, and is portable. The
  *raw* per-match StatsBomb events carry nested list/dict columns (locations, 360 freeze-frames) →
  those do **not** round-trip through columnar Parquet, so the per-match `data_loader` cache stays
  pickle. Same project, two cache layers, two different correct serialization choices for a concrete
  structural reason — not a blanket "always use Parquet." (Hardening Phase 1, 2026-06-30)

---

## Theoretical Concepts Reference

The sections above are project-specific decisions and gotchas. This section is the underlying
**textbook theory** behind them — written for a self-taught ML learner, not just a project log.
Each entry: the concept in general, then exactly where it shows up in this repo. Read this section
when the goal is understanding the concept itself, not just what was decided here.

### Supervised learning (Module A)

- **Logistic regression.** A linear model for binary outcomes: it computes a weighted sum of the
  features (like linear regression) and passes it through the *sigmoid* function
  (`1 / (1 + e^-x)`) to squeeze the result into a 0–1 probability. The weights are fit by maximum
  likelihood (equivalently, minimizing log loss), not least-squares like plain linear regression.
  Because the model is fit by directly optimizing a probability-based loss, its outputs tend to be
  well-calibrated out of the box — this is *why* it was chosen as the xG baseline, not just
  convention. See `train_logistic_regression` in `src/models.py`.
- **Gradient boosting.** An ensemble method: fits a sequence of shallow decision trees, where each
  new tree is trained to predict the *residual error* of the trees fitted so far (gradient descent
  in function space, not parameter space). More trees / deeper trees = more capacity to fit
  patterns, including noise — which is exactly the overfitting this project hit with default
  settings (see Module A's bias-variance entry above). Hyperparameters that control this capacity:
  `max_depth` (tree complexity), `learning_rate` (how much each tree corrects the previous error,
  lower = more conservative), `subsample` (fraction of rows each tree sees, adds randomness to
  reduce overfitting, same idea as bagging).
- **Maximum likelihood vs. least squares.** Linear regression minimizes squared error; logistic
  regression and gradient boosting classifiers minimize log loss (cross-entropy) — the right loss
  function for the *type* of target matters, not just the model family. Squared error treats a
  prediction of 0.9 vs. actual 1 the same whether the true class is rare or common; log loss
  penalizes confident wrong predictions far more harshly, which is the correct behavior for
  probabilities.
- **Bias-variance tradeoff.** A simpler model (logistic regression: low variance, more bias — fixed
  linear shape it can't deviate from) vs. a more flexible model (gradient boosting: low bias, more
  variance — can fit almost any pattern, including noise). The textbook signature of high variance
  is exactly what was observed: a big gap between train and test performance (train AUC 0.825 vs
  test 0.794 for default GBM). The fix is always one of: simplify the model (shallower trees, here),
  add regularization, or add more data — tuning `max_depth`/`learning_rate`/`subsample` down was
  the first lever; the dataset (~10k shots) is the eventual ceiling on how much complexity is
  actually supportable.
- **Train/test split and distribution shift.** Standard ML practice holds out test data to estimate
  generalization, but a *random* split only tests whether the model memorized the training set's
  exact distribution. This project used a *structured* split (league train, tournament test)
  specifically to test a harder and more realistic question: does the model still work when the
  underlying data-generating process shifts? This is closer to genuine deployment risk (a model
  trained on one league being applied to a different competition) than a random split would reveal.
- **ROC-AUC.** The probability that, for a randomly chosen goal and a randomly chosen non-goal, the
  model assigns a higher score to the goal. Ranges 0.5 (no better than random) to 1.0 (perfect
  ranking). It is *threshold-independent* and *scale-independent* — a model could output garbled
  probabilities (e.g. always between 0.01 and 0.02) and still get a perfect ROC-AUC as long as the
  relative ordering is right. This is precisely why it doesn't tell you anything about calibration —
  a second, independent metric is needed for that (next entry). A practical corollary this project
  hit: ROC-AUC is also *inflated by easy, unambiguous cases* in the test set — penalty-shootout
  shots padded the xG test AUC to 0.798, and removing them (they aren't in-play shots) dropped it to
  an honest 0.765. The metric "got worse" by deleting trivially-correct rankings, a reminder that a
  headline AUC always has to be read together with *what population it was computed over*.
- **Calibration (Brier score, log loss, calibration curve).** A well-calibrated model's predicted
  probabilities match real-world frequencies: among all shots predicted at 0.10 xG, roughly 10%
  should actually be goals. Brier score is mean squared error between predicted probability and
  actual outcome (0 or 1) — directly penalizes miscalibration. The calibration curve
  (`get_calibration_curve` / `plot_calibration_curve`) bins predictions and plots predicted vs.
  observed rate per bin — points on the diagonal mean perfect calibration. Tree ensembles
  (gradient boosting, random forests) are notorious for being well-ranked but poorly calibrated
  without extra correction (e.g. Platt scaling / isotonic regression) — logistic regression doesn't
  have this problem by construction, which is the core reason it's preferred here even where ROC-AUC
  is similar.
- **One-hot encoding and the dummy-variable trap.** Converting a categorical feature (`assist_type`)
  into one binary column per category. If *all* categories get their own column, they are perfectly
  collinear with the intercept (they always sum to 1) — this is the dummy-variable trap, a specific
  case of multicollinearity. The standard fix is to drop one category as the "reference" — every
  remaining coefficient is then interpreted as "the effect of being in this category, relative to
  the reference category," which is both statistically cleaner and more interpretable. This project
  hit the problem concretely (S3) and fixed it (S4) by dropping `"None"` (unassisted shot) as the
  reference.
- **Feature engineering from domain geometry.** `angle_to_goal` is a clean example of encoding
  domain knowledge directly into a feature rather than hoping a model infers it from raw
  coordinates: the angle subtended by the goalposts, computed via the law of cosines on the vectors
  from the shot location to each post, captures "how much of the goal is reachable" in one number
  that a linear model can use directly — versus needing x, y, and several interaction/polynomial
  terms to approximate the same relationship from scratch.

### Unsupervised learning (Module B)

- **K-means clustering.** An algorithm that partitions points into *K* groups by iteratively (1)
  assigning each point to its nearest centroid and (2) recomputing each centroid as the mean of its
  assigned points, until assignments stop changing. It requires choosing *K* in advance (no
  built-in way to discover it) and is sensitive to feature scale, since "nearest" is plain Euclidean
  distance — hence the mandatory `StandardScaler` step before clustering that wasn't needed for
  Module A's models.
- **Why scale-sensitivity differs between model families.** Linear/logistic regression and tree
  ensembles fit a separate coefficient or split point *per feature*, so a feature's raw units don't
  affect how much it can contribute relative to others — the model adapts its own internal scale
  per feature. Distance-based methods (K-means, also k-NN) instead compute a single combined
  distance across all features at once, so whichever feature happens to have the largest numeric
  range dominates that distance regardless of its actual predictive relevance. This is the general
  principle behind the project's S6 scaling note, not just a one-off fact about this dataset.
- **The elbow method.** Inertia (within-cluster sum of squared distances to each point's assigned
  centroid) monotonically decreases as K increases — at the extreme, K = number of points gives
  zero inertia (every point is its own cluster, useless). The elbow method looks for the K where
  the rate of decrease flattens, trading off cluster tightness against meaningful grouping. It is a
  heuristic read by eye, not an optimization with one correct answer — fundamentally different from
  how a classification metric like ROC-AUC works, since there is no ground-truth label to compute
  inertia "against."
- **Cluster validation without ground truth.** Supervised learning always has a metric computable
  against a known answer. Unsupervised learning doesn't — `profile_clusters`' z-score approach
  (how many standard deviations is this cluster's mean above/below the overall population mean, per
  feature) is a general technique for this problem, not specific to football: it turns "is this
  cluster meaningful" into "can a domain expert read this cluster's feature profile and recognize a
  real-world category," which is the most common practical substitute for a clean accuracy number
  in unsupervised work.
- **Standardization (z-scores).** `(x - mean) / std`. Two distinct uses of the same formula appear
  in this project: (1) as a *preprocessing* step before K-means, so all features are on comparable
  scales before distance is computed; (2) as a *reporting/interpretation* tool in `profile_clusters`,
  describing how unusual a cluster's average is. Same math, different purpose — one feeds the
  algorithm, the other explains its output to a human.
- **Principal Component Analysis (PCA).** Finds new axes (principal components) that are linear
  combinations of the original features, ordered by how much variance in the data each one
  captures. The first component captures the most variance possible in a single direction, the
  second captures the most *remaining* variance orthogonal to the first, and so on. Keeping only
  the first 2 components for plotting is a deliberate lossy compression — `explained_variance_ratio_`
  reports exactly how much of the original variance survives the compression. The tradeoff is real:
  a high loading on PC1 doesn't map cleanly back to "this player has a lot of tackles" the way a
  raw feature would — that interpretability is what's traded away for the ability to plot
  high-dimensional data in 2D at all.
- **Per-90 normalization as a rate-vs-total problem.** A general statistics point beyond football:
  comparing raw counts (total tackles) across units with different exposure (minutes played) without
  normalizing is a basic but easy-to-miss error — it compares "how much total output" rather than
  "how good is this player at producing this output," which is almost always the actually interesting
  question. The general fix (per-90, per-capita, per-dollar, etc. — divide by exposure, then scale to
  a common reference) appears identically across fields; football's "per-90" is the same idea as
  epidemiology's "per 100,000" or finance's "per share."

---

## How to use this file going forward

- After any session that produces a real "why" moment (a tradeoff, a metric choice, a gotcha, a
  negative result) — add an entry here, dated, under the relevant module.
- Before writing README narrative in S8, this file is the source list of "interesting decisions to
  highlight in interviews" — it's already written in that voice.
- If an idea gets mentioned but not built (like PUP above), write it here immediately, even just as
  a one-line placeholder — the cost of writing it down is near zero; the cost of losing it across a
  context clear is a full re-derivation.
- When a new session introduces a genuinely new piece of ML/stats theory (not just a project
  decision), add it to the **Theoretical Concepts Reference** section too — that section should
  always be a complete, self-contained primer on every concept this project has actually used.
