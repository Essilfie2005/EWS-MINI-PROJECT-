"""
V3 Cross-Validation and PDP Service
=====================================
Generates:
  1. 5-fold stratified cross-validation report with confidence intervals
  2. Partial Dependence Plots (PDP) — how each feature affects predicted risk
  3. Learning curve — how model performance scales with training data size
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import SAVED_MODELS_DIR
from app.services.ml_pipeline import engineer_features, ENGINEERED_FEATURE_COLS, YOUDEN_THRESHOLD

logger = logging.getLogger(__name__)

CV_REPORT_PATH    = SAVED_MODELS_DIR / "cv_report.json"
PDP_REPORT_PATH   = SAVED_MODELS_DIR / "pdp_report.json"
LC_REPORT_PATH    = SAVED_MODELS_DIR / "learning_curve.json"


# ── Cross-Validation Report ──────────────────────────────────────────────────

def compute_cv_report(df: pd.DataFrame, n_splits: int = 5) -> dict:
    """
    Run stratified K-fold CV on the full dataset and return per-fold + summary metrics.
    Uses the ensemble stacking model if available, otherwise XGBoost.
    """
    import xgboost as xgb
    from sklearn.model_selection import StratifiedKFold, cross_validate
    from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    logger.info("Computing %d-fold cross-validation report", n_splits)

    df = engineer_features(df)
    X = df[ENGINEERED_FEATURE_COLS].values.astype(float)
    y = df["dropout_label"].values.astype(int)

    clf = xgb.XGBClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="auc",
        random_state=42, n_jobs=-1, verbosity=0,
    )

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_aucs, fold_f1s, fold_precs, fold_recs = [], [], [], []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        scaler = StandardScaler()
        X_tr_s  = scaler.fit_transform(X_tr)
        X_val_s = scaler.transform(X_val)

        clf.fit(X_tr_s, y_tr)
        y_prob = clf.predict_proba(X_val_s)[:, 1]          # always 1D
        y_pred = (y_prob >= YOUDEN_THRESHOLD).astype(int)

        fold_aucs.append(float(roc_auc_score(y_val, y_prob)))
        fold_f1s.append(float(f1_score(y_val, y_pred, zero_division=0)))
        fold_precs.append(float(precision_score(y_val, y_pred, zero_division=0)))
        fold_recs.append(float(recall_score(y_val, y_pred, zero_division=0)))
        logger.debug("Fold %d: AUC=%.4f F1=%.4f", fold + 1, fold_aucs[-1], fold_f1s[-1])

    def summarize(vals):
        arr = np.array(vals)
        mean, std = float(np.mean(arr)), float(np.std(arr))
        return {
            "mean":     round(mean, 4),
            "std":      round(std,  4),
            "min":      round(float(np.min(arr)), 4),
            "max":      round(float(np.max(arr)), 4),
            "ci_lower": round(max(0.0, mean - 1.96 * std), 4),
            "ci_upper": round(min(1.0, mean + 1.96 * std), 4),
            "per_fold": [round(v, 4) for v in vals],
        }

    report = {
        "n_folds":   n_splits,
        "n_samples": int(len(df)),
        "metrics": {
            "auc":       summarize(fold_aucs),
            "f1":        summarize(fold_f1s),
            "precision": summarize(fold_precs),
            "recall":    summarize(fold_recs),
        },
        "feature_cols": ENGINEERED_FEATURE_COLS,
    }

    CV_REPORT_PATH.write_text(json.dumps(report, indent=2))
    logger.info("CV report: AUC=%.4f±%.4f, F1=%.4f±%.4f",
                report["metrics"]["auc"]["mean"],  report["metrics"]["auc"]["std"],
                report["metrics"]["f1"]["mean"],   report["metrics"]["f1"]["std"])
    return report


# ── Partial Dependence Plots (PDP) ───────────────────────────────────────────

def compute_pdp(df: pd.DataFrame, grid_points: int = 20) -> dict:
    """
    Compute partial dependence of risk score on each feature, holding all other
    features at their median values.

    Returns a dict mapping feature_name → list of {x, y} points for charting.
    """
    import joblib

    logger.info("Computing Partial Dependence Plots for %d features", len(ENGINEERED_FEATURE_COLS))

    df = engineer_features(df)
    X = df[ENGINEERED_FEATURE_COLS].values.astype(float)

    # Load trained model + scaler
    model_path  = SAVED_MODELS_DIR / "xgb_model.joblib"
    scaler_path = SAVED_MODELS_DIR / "scaler.joblib"
    if not model_path.exists():
        raise FileNotFoundError("No trained model found for PDP. Train the model first.")

    model  = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    median_row = np.median(X, axis=0)
    pdp_results = {}

    for feat_idx, feat_name in enumerate(ENGINEERED_FEATURE_COLS):
        feat_min = float(np.percentile(X[:, feat_idx], 2))
        feat_max = float(np.percentile(X[:, feat_idx], 98))
        grid = np.linspace(feat_min, feat_max, grid_points)

        pdp_y = []
        for val in grid:
            row = median_row.copy()
            row[feat_idx] = val
            row_s = scaler.transform(row.reshape(1, -1))
            prob = float(model.predict_proba(row_s)[0, 1])
            pdp_y.append(round(prob, 4))

        pdp_results[feat_name] = {
            "x": [round(float(v), 4) for v in grid],
            "y": pdp_y,
            "feature_min": round(feat_min, 4),
            "feature_max": round(feat_max, 4),
            "feature_median": round(float(median_row[feat_idx]), 4),
        }

    PDP_REPORT_PATH.write_text(json.dumps({"features": pdp_results}, indent=2))
    logger.info("PDP computed for %d features", len(ENGINEERED_FEATURE_COLS))
    return {"features": pdp_results}


# ── Learning Curve ───────────────────────────────────────────────────────────

def compute_learning_curve(df: pd.DataFrame) -> dict:
    """
    Compute how model AUC and F1 improve as training set size increases.
    Uses 10 evenly-spaced sample sizes from 10% to 100% of the training data.
    """
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, f1_score
    from sklearn.preprocessing import StandardScaler

    logger.info("Computing learning curve on %d samples", len(df))

    df = engineer_features(df)
    X = df[ENGINEERED_FEATURE_COLS].values.astype(float)
    y = df["dropout_label"].values.astype(int)

    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    scaler = StandardScaler().fit(X_train_full)
    X_test_s = scaler.transform(X_test)

    # Sample sizes to evaluate (10% → 100% of training data)
    sizes = np.linspace(0.10, 1.0, 10)
    curve_points = []

    for frac in sizes:
        n = max(50, int(len(X_train_full) * frac))
        idx = np.random.RandomState(42).choice(len(X_train_full), size=n, replace=False)
        Xtr = scaler.transform(X_train_full[idx])
        ytr = y_train_full[idx]

        clf = xgb.XGBClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=4,
            use_label_encoder=False, eval_metric="auc",
            random_state=42, n_jobs=-1, verbosity=0,
        )
        clf.fit(Xtr, ytr)
        prob = clf.predict_proba(X_test_s)[:, 1]
        pred = (prob >= YOUDEN_THRESHOLD).astype(int)

        curve_points.append({
            "train_size":   n,
            "train_pct":    round(float(frac) * 100, 1),
            "test_auc":     round(float(roc_auc_score(y_test, prob)), 4),
            "test_f1":      round(float(f1_score(y_test, pred)), 4),
        })
        logger.debug("Learning curve n=%d: AUC=%.4f", n, curve_points[-1]["test_auc"])

    result = {"n_total": len(df), "curve": curve_points}
    LC_REPORT_PATH.write_text(json.dumps(result, indent=2))
    return result


# ── Load cached reports ───────────────────────────────────────────────────────

def get_cv_report() -> dict | None:
    if CV_REPORT_PATH.exists():
        try:
            return json.loads(CV_REPORT_PATH.read_text())
        except Exception:
            return None
    return None


def get_pdp_report() -> dict | None:
    if PDP_REPORT_PATH.exists():
        try:
            return json.loads(PDP_REPORT_PATH.read_text())
        except Exception:
            return None
    return None


def get_learning_curve() -> dict | None:
    if LC_REPORT_PATH.exists():
        try:
            return json.loads(LC_REPORT_PATH.read_text())
        except Exception:
            return None
    return None
