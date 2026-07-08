"""xG model training and evaluation.

Built out in Session S3 (logistic regression baseline) and Session S4
(gradient boosting upgrade, feature importance, player xG rankings).
"""

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

NUMERIC_FEATURES = ["distance_to_goal", "angle_to_goal", "game_state_score_diff"]
BOOLEAN_FEATURES = ["is_header", "is_first_time", "under_pressure", "is_penalty", "is_free_kick"]

# Fixed category list so train and test always produce the same one-hot
# columns in the same order, even if a category is absent from one of them
# (e.g. no cut-backs in a given sample). "None" (no assist/solo action) is
# the dropped reference category: every assist_* coefficient is then read
# as "vs. an unassisted shot" instead of sitting in an unidentifiable,
# always-sums-to-1 block of dummies alongside the intercept.
ASSIST_TYPES = ["None", "Standard Pass", "Cross", "Through Ball", "Cut Back"]


def build_feature_matrix(shots):
    """Turn engineered shot features into a numeric model matrix.

    Args:
        shots (pandas.DataFrame): output of `features.extract_shot_features`
            or `features.build_training_dataset`.

    Returns:
        tuple[pandas.DataFrame, pandas.Series]: feature matrix `X` and
            binary target `y` (1 = goal).
    """
    assist_dummies = pd.get_dummies(shots["assist_type"], prefix="assist")
    assist_dummies = assist_dummies.reindex(
        columns=[f"assist_{a}" for a in ASSIST_TYPES[1:]], fill_value=0
    )

    X = pd.concat(
        [
            shots[NUMERIC_FEATURES].reset_index(drop=True),
            shots[BOOLEAN_FEATURES].astype(int).reset_index(drop=True),
            assist_dummies.reset_index(drop=True),
        ],
        axis=1,
    )
    y = shots["is_goal"].astype(int).reset_index(drop=True)
    return X, y


def build_logistic_pipeline(numeric_features=NUMERIC_FEATURES):
    """Assemble the (unfitted) scaled-logistic xG pipeline.

    The continuous features are standardised before the logistic regression;
    the boolean/one-hot features are passed through untouched. Two reasons
    scaling matters here even though it didn't for the raw S3 model:

    1. **Fair regularization.** L2 (sklearn's default) penalises every
       coefficient by the same amount. On raw features, `distance_to_goal`
       (0–100+) and `angle_to_goal` (0–180) carry tiny coefficients purely
       because of their units, so the penalty barely touches them while it
       leans hard on the binary flags. Standardising the continuous features
       puts every coefficient on a comparable footing, so the penalty is
       applied for the right reason (predictive value), not unit size.
    2. **Convergence.** The old `max_iter=1000` was papering over a solver
       struggling on wildly different feature scales; on standardised inputs
       it converges comfortably.

    The binary 0/1 features are deliberately *not* scaled — they're already on
    a bounded, comparable scale, and leaving them raw keeps each `assist_*` /
    boolean coefficient readable as a clean "vs. the reference shot" log-odds
    shift (the S4 interpretability win), rather than a per-standard-deviation
    quantity that means little for a 0/1 column.

    Args:
        numeric_features (list[str]): continuous columns to standardise. Pass
            a subset (e.g. geometry only) to build a reduced baseline model;
            the column list must match the columns present in `X`.

    Returns:
        sklearn.pipeline.Pipeline: unfitted scaler+logistic pipeline. Use
            `train_logistic_regression` for the fitted full-feature model, or
            pass this to `cross_validate_model` for an unbiased CV estimate
            (the scaler is refit inside each fold, avoiding train/test leakage).
    """
    preprocessor = ColumnTransformer(
        transformers=[("scale", StandardScaler(), list(numeric_features))],
        remainder="passthrough",  # booleans + assist dummies pass through unscaled
    )
    return Pipeline([
        ("preprocess", preprocessor),
        ("logreg", LogisticRegression(max_iter=1000)),
    ])


def train_logistic_regression(X_train, y_train, numeric_features=NUMERIC_FEATURES):
    """Fit the xG baseline model: standardised-continuous logistic regression.

    Logistic regression is the deliberate baseline here: it's well
    calibrated by construction (unlike most tree ensembles, which need
    extra calibration), which matters for an xG model whose whole purpose
    is producing probabilities, not just rankings. See `build_logistic_pipeline`
    for why the continuous features are standardised first.

    Args:
        X_train (pandas.DataFrame): feature matrix from `build_feature_matrix`.
        y_train (pandas.Series): binary goal/no-goal target.
        numeric_features (list[str]): continuous columns to standardise;
            must be present in `X_train`.

    Returns:
        sklearn.pipeline.Pipeline: fitted scaler+logistic pipeline. Exposes
            `predict_proba` like a bare estimator, so `evaluate_model` and
            `model.predict_proba(...)` work unchanged; coefficients are read
            via `get_coefficients` (the scaler reorders columns internally).
    """
    model = build_logistic_pipeline(numeric_features)
    model.fit(X_train, y_train)
    return model


def get_coefficients(model):
    """Extract logistic coefficients as a name-indexed Series.

    The scaling pipeline (`ColumnTransformer`) reorders columns — scaled
    features first, passed-through features after — and prefixes their names
    (`scale__`, `remainder__`), so `model.coef_` no longer lines up with the
    original `X` column order. This recovers the mapping and strips the
    prefixes, so the result reads like the old `zip(X.columns, model.coef_)`.

    Note the units differ from the raw S3 model: continuous-feature
    coefficients are now per-standard-deviation (a one-SD increase in the
    feature, ~13m for distance), which makes their magnitudes directly
    comparable to each other; the unscaled boolean/dummy coefficients remain
    raw log-odds shifts vs. the reference category.

    Args:
        model (sklearn.pipeline.Pipeline): fitted output of
            `train_logistic_regression`.

    Returns:
        pandas.Series: coefficient per feature, indexed by clean feature name,
            sorted descending.
    """
    feature_names = model.named_steps["preprocess"].get_feature_names_out()
    clean_names = [name.split("__", 1)[-1] for name in feature_names]
    coefficients = model.named_steps["logreg"].coef_[0]
    return pd.Series(coefficients, index=clean_names).sort_values(ascending=False)


def cross_validate_model(estimator, X, y, cv=5, scorings=("roc_auc", "neg_brier_score")):
    """Cross-validate an *unfitted* estimator and return per-fold scores.

    A single train-once/evaluate-once number is one draw from a noisy process —
    it can't tell a genuine difference between two models from fold-to-fold
    wobble. k-fold CV refits the model on each of `cv` train/validation splits
    and reports the spread, so "model A beats model B" can be judged against
    how much the score moves just by reshuffling the data.

    Folds are stratified by default (sklearn does this automatically for a
    classifier + integer `cv`), which matters at ~10% goals — an unstratified
    fold could land with a badly skewed goal rate. Pass an *unfitted*
    estimator (e.g. `build_logistic_pipeline()`); `cross_validate` clones and
    refits it per fold, so any scaler is fit on each fold's training portion
    only — no leakage from validation rows into the scaling.

    Important scope note: this estimates *in-distribution* stability (folds are
    random slices of the league training data). It is a different question from
    the held-out EURO 2024 test, which measures *out-of-distribution*
    generalisation to tournament football. Both are reported; neither replaces
    the other.

    Args:
        estimator: unfitted sklearn estimator/pipeline.
        X (pandas.DataFrame): feature matrix.
        y (pandas.Series): binary goal/no-goal target.
        cv (int): number of folds.
        scorings (tuple[str]): sklearn scorer names. `neg_brier_score` is
            negated by convention (higher = better) — flip the sign to read it
            as a normal Brier score.

    Returns:
        dict[str, numpy.ndarray]: scorer name -> array of per-fold scores.
    """
    results = cross_validate(estimator, X, y, cv=cv, scoring=list(scorings))
    return {scorer: results[f"test_{scorer}"] for scorer in scorings}


def train_baseline_classifier(X_train, y_train):
    """Fit the no-skill floor: predict the base goal rate for every shot.

    This is the reference every real model has to clear. A `DummyClassifier`
    that always predicts the training goal rate (~10%) has ROC-AUC 0.5 by
    construction (it ranks no shot above any other), but its Brier score is a
    meaningful *calibration* floor — a model that can't beat the base-rate
    Brier isn't earning its features. Reporting it stops "ROC-AUC 0.77" from
    sounding good in a vacuum: it only means something against this floor and
    against the geometry-only model (see notebook 02).

    Args:
        X_train (pandas.DataFrame): feature matrix (unused for prediction;
            kept for a uniform `fit`/`predict_proba` interface).
        y_train (pandas.Series): binary goal/no-goal target.

    Returns:
        sklearn.dummy.DummyClassifier: fitted base-rate predictor.
    """
    model = DummyClassifier(strategy="prior")
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X, y):
    """Score a fitted model on a feature matrix.

    Args:
        model: fitted classifier exposing `predict_proba`.
        X (pandas.DataFrame): feature matrix.
        y (pandas.Series): binary goal/no-goal target.

    Returns:
        dict: predicted probabilities plus ROC-AUC, log loss, and Brier
            score. ROC-AUC checks ranking quality (does the model rate
            real goals higher than non-goals); Brier/log loss check
            calibration (do predicted probabilities match observed
            frequencies) — both matter for an xG model.
    """
    predicted_xg = model.predict_proba(X)[:, 1]
    return {
        "predicted_xg": predicted_xg,
        "roc_auc": roc_auc_score(y, predicted_xg),
        "log_loss": log_loss(y, predicted_xg),
        "brier_score": brier_score_loss(y, predicted_xg),
    }


def get_calibration_curve(y, predicted_xg, n_bins=10):
    """Bin predictions and compare mean predicted xG to observed goal rate per bin.

    Args:
        y (pandas.Series): binary goal/no-goal target.
        predicted_xg (numpy.ndarray): model's predicted probabilities.
        n_bins (int): number of probability bins.

    Returns:
        tuple[numpy.ndarray, numpy.ndarray]: (mean predicted xG per bin,
            observed goal frequency per bin) — points on the diagonal mean
            the model is well calibrated.
    """
    observed_freq, mean_predicted = calibration_curve(y, predicted_xg, n_bins=n_bins, strategy="quantile")
    return mean_predicted, observed_freq


def train_gradient_boosting(X_train, y_train, random_state=42):
    """Fit a gradient boosting xG model, as a candidate upgrade to the logistic baseline.

    Defaults here (shallow trees, low learning rate, row subsampling) are
    the result of a small tuning sweep aimed at controlling overfitting —
    with ~10k training shots and a dozen features, the default
    `GradientBoostingClassifier` settings (max_depth=3, no subsampling)
    overfit the training set without improving held-out performance over
    the logistic baseline. Even tuned, this model does not clearly beat
    logistic regression out-of-sample on this dataset size (see notebook 02
    S4 section) — it's kept here as an honest comparison point and for its
    feature importance output, not because it's the recommended production
    model.

    Args:
        X_train (pandas.DataFrame): feature matrix from `build_feature_matrix`.
        y_train (pandas.Series): binary goal/no-goal target.
        random_state (int): seed for reproducibility.

    Returns:
        sklearn.ensemble.GradientBoostingClassifier: fitted model.
    """
    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8,
        random_state=random_state,
    )
    model.fit(X_train, y_train)
    return model


def train_calibrated_gbm(X_train, y_train, method="isotonic", cv=5, random_state=42):
    """Fit the gradient boosting model wrapped in probability calibration.

    The S4 finding was that gradient boosting *ranked* about as well as
    logistic regression but its raw probabilities were less trustworthy —
    tree ensembles optimise split purity, not probability accuracy, so their
    `predict_proba` outputs are notoriously pushed toward 0/1 (a real problem
    for xG, where the number *is* the product). This tests the obvious
    follow-up: was poor calibration the GBM's only real weakness?

    `CalibratedClassifierCV` learns a correction from predicted score to
    observed frequency on held-out folds (so the calibrator never sees the
    same rows the base model was fit on), then averages the per-fold
    calibrated models. `method="isotonic"` fits a free-form monotonic mapping
    — flexible and fine at this sample size (~10k shots, ~1k goals); switch to
    `"sigmoid"` (Platt scaling, a single logistic fit) if data is scarce and
    isotonic starts overfitting the calibration curve.

    Args:
        X_train (pandas.DataFrame): feature matrix from `build_feature_matrix`.
        y_train (pandas.Series): binary goal/no-goal target.
        method (str): "isotonic" or "sigmoid" calibration mapping.
        cv (int): folds used to fit the calibrator without leakage.
        random_state (int): seed for the underlying GBM.

    Returns:
        sklearn.calibration.CalibratedClassifierCV: fitted calibrated model.
            Compare its Brier score against the raw GBM and the logistic
            baseline — if it now matches logistic on calibration but still
            doesn't beat it on ROC-AUC, the S4 "logistic stays" call holds.
    """
    base_gbm = GradientBoostingClassifier(
        n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8,
        random_state=random_state,
    )
    model = CalibratedClassifierCV(estimator=base_gbm, method=method, cv=cv)
    model.fit(X_train, y_train)
    return model


def get_feature_importance(model, feature_names):
    """Rank features by their contribution to the gradient boosting model.

    Args:
        model (sklearn.ensemble.GradientBoostingClassifier): fitted model.
        feature_names (list[str]): column names of the feature matrix used
            to fit `model`, in the same order.

    Returns:
        pandas.Series: feature name -> importance, sorted descending.
    """
    return pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)


def evaluate_by_competition(model, shots, datasets):
    """Score a fitted model separately on each competition present in a shot table.

    Phase 4c's generalisation check: pooling several held-out tournaments into one
    aggregate ROC-AUC would hide whether the model generalises evenly or does
    noticeably better/worse in a specific context (tournament size, tactical culture,
    women's vs. men's football). Scoring each `competition_id` slice on its own keeps
    that comparison honest and visible instead of averaging it away.

    Args:
        model: fitted classifier exposing `predict_proba` (e.g. from
            `train_logistic_regression`), trained on a *different* dataset than `shots`.
        shots (pandas.DataFrame): combined shot table (e.g. from
            `features.build_training_dataset`) covering one or more competitions, must
            carry a `competition_id` column.
        datasets (list[config.Dataset]): datasets to report on; only those whose
            `comp_id` actually appears in `shots` produce a row (skips silently
            otherwise, e.g. a dataset not yet cached/wired).

    Returns:
        dict[str, dict]: keyed by `str(dataset.comp_id)`, each value holding `label`,
            `n_shots`, `goal_rate`, `roc_auc`, and `brier_score` for that competition's
            shots scored by `model`.
    """
    out = {}
    for dataset in datasets:
        subset = shots[shots["competition_id"] == dataset.comp_id]
        if subset.empty:
            continue
        X, y = build_feature_matrix(subset)
        eval_ = evaluate_model(model, X, y)
        out[str(dataset.comp_id)] = {
            "label": dataset.label,
            "n_shots": int(len(y)),
            "goal_rate": round(float(y.mean()), 3),
            "roc_auc": round(float(eval_["roc_auc"]), 3),
            "brier_score": round(float(eval_["brier_score"]), 3),
        }
    return out


def build_player_xg_table(shots, predicted_xg):
    """Aggregate shot-level predictions into a per-player xG ranking.

    Args:
        shots (pandas.DataFrame): shot features, must contain `player`,
            `team`, and `is_goal`, same row order as `predicted_xg`.
        predicted_xg (numpy.ndarray): model's predicted probability per shot.

    Returns:
        pandas.DataFrame: one row per player, with shots taken, goals scored,
            cumulative xG, and `xg_diff` (goals minus xG — positive means
            outscoring the model's expectation, i.e. an overperformer;
            negative means underperforming it). This is the same lens
            used to spot finishing over/underperformance in real recruitment
            and performance-review work, not just a model diagnostic.
    """
    table = shots[["player", "team", "is_goal"]].copy()
    table["predicted_xg"] = predicted_xg

    ranking = table.groupby(["player", "team"]).agg(
        shots=("is_goal", "size"),
        goals=("is_goal", "sum"),
        total_xg=("predicted_xg", "sum"),
    )
    ranking["goals"] = ranking["goals"].astype(int)
    ranking["xg_diff"] = ranking["goals"] - ranking["total_xg"]
    return ranking.sort_values("xg_diff", ascending=False)
