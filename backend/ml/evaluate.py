"""
Model evaluation script.

Usage:
    python -m ml.evaluate

Loads the trained XGBoost model and all baselines, evaluates them on the
test set, runs DeLong's test, and generates comparison plots.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings, SAVED_MODELS_DIR, PLOTS_DIR
from app.services.ml_pipeline import FEATURE_COLS
from app.utils.metrics import compute_all_metrics, delong_test
from app.utils.seed_data import load_processed_csv
from ml.baseline import train_logistic_regression, rule_based_predict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("ml.evaluate")


def main():
    """Full evaluation pipeline: XGBoost vs LR vs Rule-based."""
    settings = get_settings()
    logger.info("═══ Model Evaluation Pipeline ═══")

    # Load data
    try:
        df = load_processed_csv()
    except FileNotFoundError:
        logger.error("No processed data. Run the server or training first.")
        sys.exit(1)

    df = df.dropna(subset=["dropout_label"]).copy()
    df["dropout_label"] = df["dropout_label"].astype(int)

    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df["dropout_label"].values.astype(int)

    # Same split as training
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=settings.TEST_RATIO, stratify=y, random_state=42
    )
    val_ratio_adjusted = settings.VAL_RATIO / (settings.TRAIN_RATIO + settings.VAL_RATIO)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_ratio_adjusted, stratify=y_train_val, random_state=42
    )

    logger.info("Test set: %d samples (%.1f%% positive)", len(X_test), y_test.mean() * 100)

    # ── 1. XGBoost ────────────────────────────────────────────────────────
    model_path = Path(settings.MODEL_PATH)
    scaler_path = Path(settings.SCALER_PATH)

    if not model_path.exists():
        logger.error("No trained XGBoost model. Run ml.train first.")
        sys.exit(1)

    xgb_model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    X_test_scaled = scaler.transform(X_test)
    xgb_prob = xgb_model.predict_proba(X_test_scaled)[:, 1]
    xgb_pred = (xgb_prob >= settings.RISK_THRESHOLD).astype(int)
    xgb_metrics = compute_all_metrics(y_test, xgb_pred, xgb_prob)
    logger.info("XGBoost metrics: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in xgb_metrics.items()})

    # ── 2. Logistic Regression ────────────────────────────────────────────
    lr_model, lr_scaler = train_logistic_regression(X_train, y_train)
    X_test_lr_scaled = lr_scaler.transform(X_test)
    lr_prob = lr_model.predict_proba(X_test_lr_scaled)[:, 1]
    lr_pred = (lr_prob >= settings.RISK_THRESHOLD).astype(int)
    lr_metrics = compute_all_metrics(y_test, lr_pred, lr_prob)
    logger.info("Logistic Regression metrics: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in lr_metrics.items()})

    # ── 3. Rule-based ─────────────────────────────────────────────────────
    test_df = pd.DataFrame(X_test, columns=FEATURE_COLS)
    rule_pred, rule_prob = rule_based_predict(test_df)
    rule_metrics = compute_all_metrics(y_test, rule_pred, rule_prob)
    logger.info("Rule-based metrics: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in rule_metrics.items()})

    # ── 4. DeLong's test (XGBoost vs LR) ──────────────────────────────────
    delong = delong_test(y_test, xgb_prob, lr_prob)
    logger.info(
        "DeLong's test (XGB vs LR): z=%.4f, p=%.6f, AUC_XGB=%.4f, AUC_LR=%.4f",
        delong["z_statistic"], delong["p_value"], delong["auc_a"], delong["auc_b"],
    )

    # ── 5. ROC Curve Plot ─────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 6))

    for name, probs, metrics in [
        ("XGBoost", xgb_prob, xgb_metrics),
        ("Logistic Regression", lr_prob, lr_metrics),
        ("Rule-based", rule_prob, rule_metrics),
    ]:
        fpr, tpr, _ = roc_curve(y_test, probs)
        ax.plot(fpr, tpr, label=f"{name} (AUC={metrics['auc_roc']:.3f})")

    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves – Dropout Prediction")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    plt.tight_layout()

    roc_path = PLOTS_DIR / "roc_comparison.png"
    plt.savefig(roc_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("ROC curve saved → %s", roc_path)

    # ── 6. Confusion Matrix Plot (XGBoost) ────────────────────────────────
    from sklearn.metrics import ConfusionMatrixDisplay

    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(
        y_test, xgb_pred, display_labels=["Retained", "Dropout"],
        cmap="Blues", ax=ax,
    )
    ax.set_title("XGBoost Confusion Matrix")
    plt.tight_layout()

    cm_path = PLOTS_DIR / "confusion_matrix_xgb.png"
    plt.savefig(cm_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Confusion matrix saved → %s", cm_path)

    # ── 7. Save evaluation report ─────────────────────────────────────────
    report = {
        "xgboost": {k: v for k, v in xgb_metrics.items()},
        "logistic_regression": {k: v for k, v in lr_metrics.items()},
        "rule_based": {k: v for k, v in rule_metrics.items()},
        "delong_test": delong,
        "test_set_size": len(X_test),
        "positive_rate": float(y_test.mean()),
    }

    report_path = SAVED_MODELS_DIR / "evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Evaluation report saved → %s", report_path)

    logger.info("═══ Evaluation Complete ═══")


if __name__ == "__main__":
    main()
