# ML/Stats Theory Reference

Textbook-level theory behind every concept used in this project. Read when the goal is understanding the concept itself, not just what was decided here.

→ Project decisions + gotchas: [../ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md) | Env gotchas: [ML_TOOLING.md](ML_TOOLING.md)

---

## Supervised Learning (Module A)

**Logistic regression.** Computes a weighted sum of features and passes it through the sigmoid function (`1 / (1 + e^-x)`) to produce a 0–1 probability. Fit by maximum likelihood (minimizing log loss). Tends to be well-calibrated out of the box — *why* it's the xG baseline, not just convention.

**Gradient boosting.** Ensemble: fits a sequence of shallow decision trees, each predicting the *residual error* of the trees before it (gradient descent in function space). More trees / deeper trees = more capacity to fit noise. Hyperparameters that control this: `max_depth`, `learning_rate`, `subsample`. Default settings overfit on this project — tuning down shrank the gap without beating the simpler model.

**Maximum likelihood vs. least squares.** Linear regression minimizes squared error; logistic/GBM classifiers minimize log loss (cross-entropy). Log loss penalizes confident wrong predictions far more harshly — the correct loss function for probability outputs.

**Bias-variance tradeoff.** Simpler model: higher bias (fixed linear shape), lower variance. Flexible model: lower bias, higher variance. Textbook signature of high variance: big train/test gap. Fixes: simplify the model, add regularization, or add more data.

**Train/test split and distribution shift.** A random split only tests memorisation. A *structured* split (league train, tournament test) tests whether the model works when the underlying distribution shifts — closer to real deployment risk than a random split reveals.

**Cross-validation (k-fold).** k-fold: train on k−1 partitions, validate on the held-out one, rotate through all k, report mean and spread. The spread shows whether a performance difference is real or fold-to-fold noise. **Stratified** k-fold keeps each fold's class balance matched to the whole (essential at ~10% goals). Two leakage traps to avoid: (1) preprocessing must be refit *inside* each fold — sklearn Pipeline + `cross_validate` does this automatically; (2) CV measures in-distribution stability — it is *not* a substitute for a genuinely held-out OOD test set when the real question is out-of-distribution generalisation.

**Probability calibration.** `CalibratedClassifierCV` learns a monotonic map from the model's raw score to observed frequency. **Platt scaling** (`method="sigmoid"`) — single logistic curve, robust, low data cost. **Isotonic** (`method="isotonic"`) — free-form monotonic step function, more flexible, needs more data. Calibration never changes ROC-AUC (ranking is preserved) — it can only improve probability accuracy. Tree ensembles are notorious for poor calibration without this fix; logistic regression isn't.

**ROC-AUC.** Probability that for a random goal/non-goal pair, the model ranks the goal higher. Ranges 0.5 (coin-flip) to 1.0 (perfect). Threshold-independent and scale-independent — a model outputting garbled probabilities (always between 0.01 and 0.02) can still get a perfect ROC-AUC if the relative ordering is right. **Inflated by easy, unambiguous cases** — removing penalty-shootout shots lowered xG test AUC from 0.798 to 0.765. The headline number is only meaningful relative to the population it's computed over.

**Brier score / calibration curve.** Brier = mean squared error between predicted probability and actual outcome. Calibration curve: bins predictions, plots predicted vs. observed rate per bin. Points on the diagonal = perfect calibration. Directly penalizes miscalibration — the metric to watch for an xG model, where the output *is* a probability, not just a ranking.

**One-hot encoding and the dummy-variable trap.** Encoding all categories with no dropped reference makes them perfectly collinear with the intercept (they always sum to 1). Standard fix: drop one category as the reference. Every remaining coefficient reads as "effect of this category relative to the reference." Applied here: dropped "None" (unassisted shot) as the reference for `assist_type`.

**Feature engineering from domain geometry.** `angle_to_goal` (degrees subtended by the goalposts, law of cosines) captures "how much of the goal is reachable" in one number a linear model can use directly — versus needing x, y, and interaction/polynomial terms to approximate the same from raw coordinates.

---

## Unsupervised Learning (Module B)

**K-means clustering.** Iteratively: (1) assign each point to its nearest centroid; (2) recompute each centroid as the mean of its assigned points. Requires K in advance. Sensitive to feature scale — "nearest" is Euclidean distance, so mandatory `StandardScaler` before clustering.

**Why scale-sensitivity differs between model families.** Linear/logistic/tree models fit a coefficient or split point *per feature* — they adapt to scale internally. Distance-based methods (K-means, k-NN) compute one combined distance across all features — whichever feature has the largest numeric range dominates, regardless of predictive relevance. This is the general principle; the S6 scaling note is one instance of it.

**Elbow method.** Inertia (within-cluster sum of squared distances) falls monotonically as K grows. The elbow is where the rate of decrease flattens. Read by eye — no single correct answer; fundamentally different from a supervised metric since there is no ground truth.

**Silhouette score.** For each point: `a` = mean distance to same-cluster points (cohesion); `b` = mean distance to nearest-other-cluster points (separation). Score = `(b − a) / max(a, b)`. Range −1 to 1: near 1 = well-clustered; near 0 = on the boundary; negative = probably wrong cluster. Unlike inertia, does **not** improve monotonically — has a genuine interior maximum usable to *recommend* a K. Two caveats: (1) geometric bias toward convex, equal-sized, well-separated blobs; (2) absolute level matters as much as argmax — a peak of 0.25 diagnoses soft structure in the data, not just identifies K.

**Cluster validation without ground truth.** `profile_clusters` z-score approach: cluster mean per feature expressed as standard deviations from population mean. A human can read "interceptions +0.85, tackles +0.97" as "ball-winning destroyer" — the most common practical substitute for a clean accuracy number in unsupervised work.

**Standardization (z-scores).** `(x - mean) / std`. Two distinct uses in this project: (1) preprocessing before K-means so all features are on comparable scales; (2) cluster profiling in `profile_clusters` to describe how unusual a cluster's average is. Same math, different purpose.

**PCA.** Finds new axes (principal components) as linear combinations of original features, ordered by variance captured. First component = most variance in one direction; second = most remaining variance orthogonal to first. Keeping 2 for plotting is lossy compression — `explained_variance_ratio_` reports what survives. Tradeoff: visualisability at the cost of individual-feature interpretability.

**Per-90 normalization.** Comparing raw counts across units with different exposure (minutes played) is a rate-vs-total problem. Per-90: divide by (minutes / 90). The general fix for comparing "how good" vs. "how much total output" — same idea as epidemiology's per-100,000 or finance's per-share.
