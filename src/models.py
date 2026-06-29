"""xG model training and evaluation.

Built out in Session S3 (logistic regression baseline) and Session S4
(gradient boosting upgrade, feature importance, player xG rankings).
"""

import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

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


def train_logistic_regression(X_train, y_train):
    """Fit the xG baseline model.

    Logistic regression is the deliberate baseline here: it's well
    calibrated by construction (unlike most tree ensembles, which need
    extra calibration), which matters for an xG model whose whole purpose
    is producing probabilities, not just rankings.

    Args:
        X_train (pandas.DataFrame): feature matrix from `build_feature_matrix`.
        y_train (pandas.Series): binary goal/no-goal target.

    Returns:
        sklearn.linear_model.LogisticRegression: fitted model.
    """
    model = LogisticRegression(max_iter=1000)
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
