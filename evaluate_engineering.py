"""
Model Engineering Evaluation Script
=====================================
Compares three configurations:
  1. BASELINE  — original 5 features, threshold = 0.5
  2. YOUDEN    — original 5 features, threshold = Youden's J optimal
  3. ENGINEERED — 7 features (5 original + 2 new), threshold = Youden's J

Engineered features added:
  - academic_performance_index  : weighted academic composite (Ghana-calibrated)
  - financial_academic_risk     : interaction between financial stress and non-submission

Prints a side-by-side improvement table.
"""

import json
import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score,
    precision_score, recall_score, roc_curve, cohen_kappa_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# ── paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
DB   = BASE / "backend" / "dropout.db"
MODEL_DIR = BASE / "backend" / "saved_models"

optuna.logging.set_verbosity(optuna.logging.WARNING)

ORIGINAL_FEATURES = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]

# ── helpers ────────────────────────────────────────────────────────────────

def load_data():
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT attendance_rate, quiz_average, assignment_submission_rate, "
        "mobile_engagement_freq, financial_aid_status, dropout_label "
        "FROM students WHERE dropout_label IS NOT NULL",
        conn,
    )
    conn.close()
    print(f"  Loaded {len(df)} labelled students  "
          f"(dropout={df.dropout_label.sum()}, retained={len(df)-df.dropout_label.sum()})")
    return df


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Two Ghana-calibrated composite features:

    1. Academic Performance Index (API)
       Weighted combination of the three academic signals.
       Weights reflect the relative predictive importance from SHAP analysis:
         attendance  → 40 %  (highest SHAP importance)
         quiz        → 40 %
         assignment  → 20 %
       Scaled to 0–100.

    2. Financial-Academic Risk Interaction (FARI)
       Captures the compounding effect of financial stress AND low submission rate.
       Students with low financial aid AND low assignment submission are at highest risk.
       Formula: (1 - financial_aid_status/10) * (1 - assignment_submission_rate/100)
       Range: 0 (low risk) → 1 (high risk)
    """
    df = df.copy()
    df["academic_performance_index"] = (
        0.40 * df["attendance_rate"] +
        0.40 * df["quiz_average"] +
        0.20 * df["assignment_submission_rate"]
    )
    df["financial_academic_risk"] = (
        (1.0 - df["financial_aid_status"] / 10.0) *
        (1.0 - df["assignment_submission_rate"] / 100.0)
    ).clip(0, 1)
    return df


def youden_threshold(y_true, y_prob):
    """Return the threshold that maximises Youden's J = Sensitivity + Specificity - 1."""
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    j = tpr - fpr
    best_idx = np.argmax(j)
    return float(thresholds[best_idx])


def train_xgb(X_train, y_train, X_val, y_val, n_trials=40):
    """Train XGBoost with Optuna HPO. Returns fitted model."""
    def objective(trial):
        params = {
            "n_estimators":      trial.suggest_int("n_estimators", 100, 500),
            "max_depth":         trial.suggest_int("max_depth", 3, 8),
            "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample":         trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "scale_pos_weight":  trial.suggest_float("scale_pos_weight", 1.0, 5.0),
            "use_label_encoder": False,
            "eval_metric":       "auc",
            "random_state":      42,
        }
        m = xgb.XGBClassifier(**params)
        m.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        return roc_auc_score(y_val, m.predict_proba(X_val)[:, 1])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    best = study.best_params
    best.update({"use_label_encoder": False, "eval_metric": "auc", "random_state": 42})
    model = xgb.XGBClassifier(**best)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def evaluate(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "auc_roc":   round(roc_auc_score(y_true, y_prob), 4),
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "kappa":     round(cohen_kappa_score(y_true, y_pred), 4),
        "threshold": round(threshold, 4),
    }


def pct_change(old, new):
    if old == 0:
        return "N/A"
    delta = (new - old) / old * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f}%"


def print_table(configs: dict):
    metrics = ["auc_roc", "f1", "accuracy", "recall", "precision", "kappa", "threshold"]
    labels  = ["AUC-ROC", "F1 Score", "Accuracy", "Recall", "Precision", "Cohen κ", "Threshold"]
    names   = list(configs.keys())

    col_w = 16
    header = f"{'Metric':<14}" + "".join(f"{n:>{col_w}}" for n in names)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    baseline_vals = configs[names[0]]
    for m, lab in zip(metrics, labels):
        row = f"{lab:<14}"
        for i, name in enumerate(names):
            val = configs[name][m]
            cell = f"{val:.4f}" if isinstance(val, float) else str(val)
            if i > 0 and m != "threshold":
                change = pct_change(baseline_vals[m], configs[name][m])
                cell = f"{val:.4f} ({change})"
            row += f"{cell:>{col_w}}"
        print(row)
    print("=" * len(header))


# ── main ──────────────────────────────────────────────────────────────────

def main():
    print("\n[*] Model Engineering Evaluation")
    print("=" * 50)

    # ── 1. load data ──────────────────────────────────────────────────────
    print("\n[1/5] Loading data from database…")
    df = load_data()

    # ── 2. splits ─────────────────────────────────────────────────────────
    print("[2/5] Splitting 70/15/15 (stratified)…")
    X_orig = df[ORIGINAL_FEATURES].values
    y      = df["dropout_label"].values

    X_tmp, X_test, y_tmp, y_test = train_test_split(
        X_orig, y, test_size=0.15, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(
        X_tmp, y_tmp, test_size=0.15/(1-0.15), stratify=y_tmp, random_state=42)

    scaler_orig = StandardScaler()
    X_tr_s  = scaler_orig.fit_transform(X_train)
    X_val_s = scaler_orig.transform(X_val)
    X_te_s  = scaler_orig.transform(X_test)

    # ── 3. BASELINE — load existing trained model ─────────────────────────
    print("[3/5] Evaluating BASELINE (existing model, threshold=0.50)…")
    existing_model  = joblib.load(MODEL_DIR / "xgb_model.joblib")
    existing_scaler = joblib.load(MODEL_DIR / "scaler.joblib")

    X_test_existing = existing_scaler.transform(X_test)
    base_prob = existing_model.predict_proba(X_test_existing)[:, 1]
    baseline  = evaluate(y_test, base_prob, threshold=0.50)

    # ── 4. YOUDEN — same model, optimal threshold ─────────────────────────
    print("[4/5] Applying Youden's J threshold calibration…")
    # Calibrate on validation set
    X_val_existing = existing_scaler.transform(X_val)
    val_prob = existing_model.predict_proba(X_val_existing)[:, 1]
    tau = youden_threshold(y_val, val_prob)
    print(f"      Youden's J optimal threshold: {tau:.4f}  (was 0.5000)")
    youden = evaluate(y_test, base_prob, threshold=tau)

    # ── 5. ENGINEERED — new features + retrain ────────────────────────────
    print("[5/5] Adding engineered features and retraining (40 Optuna trials)…")
    df_eng = add_engineered_features(df)
    eng_features = ORIGINAL_FEATURES + ["academic_performance_index", "financial_academic_risk"]
    X_eng = df_eng[eng_features].values

    Xe_tmp, Xe_test, ye_tmp, ye_test = train_test_split(
        X_eng, y, test_size=0.15, stratify=y, random_state=42)
    Xe_train, Xe_val, ye_train, ye_val = train_test_split(
        Xe_tmp, ye_tmp, test_size=0.15/(1-0.15), stratify=ye_tmp, random_state=42)

    scaler_eng = StandardScaler()
    Xe_tr_s  = scaler_eng.fit_transform(Xe_train)
    Xe_val_s = scaler_eng.transform(Xe_val)
    Xe_te_s  = scaler_eng.transform(Xe_test)

    eng_model = train_xgb(Xe_tr_s, ye_train, Xe_val_s, ye_val, n_trials=40)
    eng_prob  = eng_model.predict_proba(Xe_te_s)[:, 1]
    tau_eng   = youden_threshold(ye_val, eng_model.predict_proba(Xe_val_s)[:, 1])
    print(f"      Engineered model Youden's J threshold: {tau_eng:.4f}")
    engineered = evaluate(ye_test, eng_prob, threshold=tau_eng)

    # ── print results ─────────────────────────────────────────────────────
    print_table({
        "BASELINE (0.50)": baseline,
        "YOUDEN τ":        youden,
        "ENGINEERED+τ":    engineered,
    })

    # ── save engineered artefacts ─────────────────────────────────────────
    print("\n📦  Saving engineered model + metadata…")
    joblib.dump(eng_model,   MODEL_DIR / "xgb_model_engineered.joblib")
    joblib.dump(scaler_eng,  MODEL_DIR / "scaler_engineered.joblib")

    meta = {
        "engineered_features": eng_features,
        "youden_threshold":    tau_eng,
        "baseline_threshold":  0.50,
        "baseline_metrics":    baseline,
        "youden_metrics":      youden,
        "engineered_metrics":  engineered,
    }
    (MODEL_DIR / "engineering_report.json").write_text(json.dumps(meta, indent=2))
    print(f"      Saved to {MODEL_DIR}/engineering_report.json")
    print("\n✅  Done.")


if __name__ == "__main__":
    main()
