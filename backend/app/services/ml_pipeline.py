"""
XGBoost ML Pipeline with Optuna hyper-parameter optimisation.

Responsibilities:
  • Train / retrain an XGBoost classifier with Optuna HPO
  • Stratified 70/15/15 split
  • Early stopping on validation AUC
  • Serialize model + scaler to disk
  • Predict risk scores for individual students or batches
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

from app.config import get_settings, SAVED_MODELS_DIR
from app.utils.metrics import compute_all_metrics, assign_risk_band

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]

# Two Ghana-calibrated engineered features added on top of the originals
ENGINEERED_FEATURE_COLS = FEATURE_COLS + [
    "academic_performance_index",
    "financial_academic_risk",
]

# Youden's J optimal threshold (calibrated from engineering evaluation)
# Overrides the config RISK_THRESHOLD for classification; AUC is threshold-free.
YOUDEN_THRESHOLD = 0.4432


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add two domain-calibrated composite features.

    Academic Performance Index (API)
    ---------------------------------
    Weighted average of the three academic signals, reflecting SHAP-derived
    relative importances from the baseline model:
      - Attendance  40 %  (highest SHAP contribution)
      - Quiz        40 %
      - Assignment  20 %
    Scaled 0-100, same range as the input features.

    Financial-Academic Risk Interaction (FARI)
    ------------------------------------------
    Captures the compounding effect of financial vulnerability AND low assignment
    submission. Students with *both* low financial aid AND low submission rate
    are at disproportionately higher risk in Ghanaian foundation programmes.
    Range: 0 (low risk) -> 1 (high risk).
    """
    df = df.copy()
    df["academic_performance_index"] = (
        0.40 * df["attendance_rate"]
        + 0.40 * df["quiz_average"]
        + 0.20 * df["assignment_submission_rate"]
    )
    df["financial_academic_risk"] = (
        (1.0 - df["financial_aid_status"] / 10.0)
        * (1.0 - df["assignment_submission_rate"] / 100.0)
    ).clip(0, 1)
    return df

# Module-level cache for loaded model
_model_cache: dict[str, Any] = {}


def _get_cached_model():
    """Return cached (model, scaler) or load from disk."""
    settings = get_settings()
    if "model" not in _model_cache:
        model_path = Path(settings.MODEL_PATH)
        scaler_path = Path(settings.SCALER_PATH)
        if model_path.exists() and scaler_path.exists():
            _model_cache["model"] = joblib.load(model_path)
            _model_cache["scaler"] = joblib.load(scaler_path)
            logger.info("Loaded model from %s", model_path)
        else:
            return None, None
    return _model_cache.get("model"), _model_cache.get("scaler")


def is_model_loaded() -> bool:
    """Check if a trained model is available."""
    model, scaler = _get_cached_model()
    return model is not None and scaler is not None


def reload_model() -> bool:
    """Force reload model from disk."""
    _model_cache.clear()
    model, _ = _get_cached_model()
    return model is not None


def train_model(df: pd.DataFrame) -> dict:
    """
    Full training pipeline:
      1. Stratified split (70/15/15)
      2. Optuna HPO with 5-fold CV
      3. Final model training with early stopping
      4. Evaluation on test set
      5. Serialization

    Parameters
    ----------
    df : DataFrame with FEATURE_COLS + "dropout_label"

    Returns
    -------
    dict with model_version, metrics, model_path
    """
    settings = get_settings()

    X_raw = df[FEATURE_COLS].values.astype(np.float32)
    y = df["dropout_label"].values.astype(int)

    # ── Feature engineering ───────────────────────────────────────────────
    df_eng = engineer_features(df[FEATURE_COLS])
    X = df_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)

    # ── Stratified split: 70 / 15 / 15 ───────────────────────────────────
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=settings.TEST_RATIO, stratify=y, random_state=42
    )
    val_ratio_adjusted = settings.VAL_RATIO / (settings.TRAIN_RATIO + settings.VAL_RATIO)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_ratio_adjusted, stratify=y_train_val, random_state=42
    )

    logger.info(
        "Split sizes – train: %d, val: %d, test: %d (positive rate: %.1f%%)",
        len(X_train), len(X_val), len(X_test), y.mean() * 100,
    )

    # ── Scale features ────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # ── Optuna HPO ────────────────────────────────────────────────────────
    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 10.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }

        cv_folds = StratifiedKFold(n_splits=settings.OPTUNA_CV_FOLDS, shuffle=True, random_state=42)
        auc_scores = []

        for train_idx, val_idx in cv_folds.split(X_train_scaled, y_train):
            X_fold_train, X_fold_val = X_train_scaled[train_idx], X_train_scaled[val_idx]
            y_fold_train, y_fold_val = y_train[train_idx], y_train[val_idx]

            clf = xgb.XGBClassifier(
                **params,
                objective="binary:logistic",
                eval_metric="auc",
                use_label_encoder=False,
                random_state=42,
                early_stopping_rounds=settings.XGB_EARLY_STOPPING,
            )
            clf.fit(
                X_fold_train, y_fold_train,
                eval_set=[(X_fold_val, y_fold_val)],
                verbose=False,
            )
            y_prob = clf.predict_proba(X_fold_val)[:, 1]
            from sklearn.metrics import roc_auc_score
            auc_scores.append(roc_auc_score(y_fold_val, y_prob))

        return np.mean(auc_scores)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", study_name="xgb_dropout")
    study.optimize(objective, n_trials=settings.OPTUNA_TRIALS, show_progress_bar=True)

    logger.info("Best Optuna trial: AUC=%.4f, params=%s", study.best_value, study.best_params)

    # ── Train final model with best params ────────────────────────────────
    best_params = study.best_params
    final_model = xgb.XGBClassifier(
        **best_params,
        objective="binary:logistic",
        eval_metric="auc",
        use_label_encoder=False,
        random_state=42,
        early_stopping_rounds=settings.XGB_EARLY_STOPPING,
    )
    final_model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=False,
    )

    # ── Evaluate on test set ──────────────────────────────────────────────
    y_prob_test = final_model.predict_proba(X_test_scaled)[:, 1]

    # ── Youden's J threshold calibration ─────────────────────────────────
    from sklearn.metrics import roc_curve
    val_probs = final_model.predict_proba(X_val_scaled)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, val_probs)
    j_scores = tpr - fpr
    youden_tau = float(thresholds[np.argmax(j_scores)])
    logger.info("Youden's J optimal threshold: %.4f", youden_tau)

    y_pred_test = (y_prob_test >= youden_tau).astype(int)
    metrics = compute_all_metrics(y_test, y_pred_test, y_prob_test)

    logger.info("Test metrics: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items()})

    # ── Serialize ─────────────────────────────────────────────────────────
    model_version = datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M%S")
    model_path = SAVED_MODELS_DIR / "xgb_model.joblib"
    scaler_path = SAVED_MODELS_DIR / "scaler.joblib"
    meta_path = SAVED_MODELS_DIR / "model_meta.json"

    joblib.dump(final_model, model_path)
    joblib.dump(scaler, scaler_path)

    meta = {
        "model_version": model_version,
        "best_params": best_params,
        "optuna_best_auc": study.best_value,
        "test_metrics": {k: v for k, v in metrics.items() if k != "confusion_matrix"},
        "confusion_matrix": metrics["confusion_matrix"],
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "feature_cols": ENGINEERED_FEATURE_COLS,
        "youden_threshold": youden_tau,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str))

    # Refresh cache
    _model_cache.clear()
    _model_cache["model"] = final_model
    _model_cache["scaler"] = scaler

    logger.info("Model saved → %s (version: %s)", model_path, model_version)

    return {
        "model_version": model_version,
        "model_path": str(model_path),
        "metrics": metrics,
        "best_params": best_params,
    }


def predict_single(features: dict[str, float]) -> dict:
    """
    Predict dropout risk for a single student.

    Parameters
    ----------
    features : dict with keys matching FEATURE_COLS

    Returns
    -------
    dict with risk_score, risk_band, model_version
    """
    model, scaler = _get_cached_model()
    if model is None:
        raise RuntimeError("No trained model available. Train the model first.")

    # Build a single-row DataFrame so engineer_features() can compute derived cols
    row_df = pd.DataFrame([{col: features.get(col, 0.0) for col in FEATURE_COLS}])
    row_eng = engineer_features(row_df)
    x = row_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)
    x_scaled = scaler.transform(x)

    prob = float(model.predict_proba(x_scaled)[0, 1])

    # Use Youden threshold from metadata if available, else module default
    meta_path = SAVED_MODELS_DIR / "model_meta.json"
    tau = YOUDEN_THRESHOLD
    model_version = "v1"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        model_version = meta.get("model_version", "v1")
        tau = meta.get("youden_threshold", YOUDEN_THRESHOLD)

    band = assign_risk_band(prob, tau)

    return {
        "risk_score": round(prob, 4),
        "risk_band": band,
        "model_version": model_version,
    }


def predict_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Predict dropout risk for a batch of students.

    Parameters
    ----------
    df : DataFrame with FEATURE_COLS

    Returns
    -------
    DataFrame with added columns: risk_score, risk_band
    """
    model, scaler = _get_cached_model()
    if model is None:
        raise RuntimeError("No trained model available. Train the model first.")

    df_eng = engineer_features(df[FEATURE_COLS])
    X = df_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)
    X_scaled = scaler.transform(X)

    probs = model.predict_proba(X_scaled)[:, 1]

    # Use Youden threshold from saved metadata
    meta_path = SAVED_MODELS_DIR / "model_meta.json"
    tau = YOUDEN_THRESHOLD
    if meta_path.exists():
        meta_json = json.loads(meta_path.read_text())
        tau = meta_json.get("youden_threshold", YOUDEN_THRESHOLD)

    result = df.copy()
    result["risk_score"] = np.round(probs, 4)
    result["risk_band"] = [assign_risk_band(p, tau) for p in probs]

    return result


def get_model_metadata() -> dict | None:
    """Load model metadata from disk."""
    meta_path = SAVED_MODELS_DIR / "model_meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return None
