"""
SHAP Explainability Service.

Provides:
  • Per-student waterfall chart (800×600 PNG)
  • Cohort beeswarm summary plot
  • JSON SHAP values export
  • Top-N risk factor extraction (for SMS text)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from app.config import get_settings, PLOTS_DIR, SAVED_MODELS_DIR
from app.services.ml_pipeline import engineer_features, FEATURE_COLS, ENGINEERED_FEATURE_COLS

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    "attendance_rate":            "Attendance Rate",
    "quiz_average":               "Quiz Average",
    "assignment_submission_rate": "Assignment Submission Rate",
    "mobile_engagement_freq":     "Mobile Engagement",
    "financial_aid_status":       "Financial Aid Status (IMD)",
    "academic_performance_index": "Academic Performance Index",
    "financial_academic_risk":    "Financial-Academic Risk",
}


def _load_model_and_scaler():
    """Load the trained XGBoost model and scaler from disk."""
    settings = get_settings()
    model_path = Path(settings.MODEL_PATH)
    scaler_path = Path(settings.SCALER_PATH)
    if not model_path.exists() or not scaler_path.exists():
        raise RuntimeError("No trained model found. Train the model first.")
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    return model, scaler


def safe_float(val: Any) -> float:
    try:
        if isinstance(val, (list, tuple, np.ndarray)):
            return float(val[0])
        return float(val)
    except Exception:
        s = str(val).replace('[', '').replace(']', '').replace("'", "").replace('"', '').strip()
        try:
            return float(s)
        except Exception:
            return 0.0

def compute_shap_values(features: dict[str, float]) -> dict[str, Any]:
    """
    Compute SHAP values for a single student.

    Returns dict with:
      - shap_values: list of {feature, value, contribution}
      - base_value: expected model output
      - prediction: risk score
    """
    model, scaler = _load_model_and_scaler()

    # Build engineered feature row (5 raw + 2 derived = 7 total)
    row_df = pd.DataFrame([{col: safe_float(features.get(col, 0.0)) for col in FEATURE_COLS}])
    row_eng = engineer_features(row_df)
    x = row_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)
    x_scaled = scaler.transform(x)

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(x_scaled)

    # shap_vals shape: (1, n_features) for binary
    sv = shap_vals[0] if isinstance(shap_vals, list) else shap_vals[0]

    # Safely extract expected_value which can be a scalar, list, or array
    ev = explainer.expected_value
    if isinstance(ev, (list, tuple, np.ndarray)):
        base = safe_float(ev[0])
    else:
        base = safe_float(ev)

    prob = safe_float(model.predict_proba(x_scaled)[0, 1])

    # Engineered features are derived, so show their raw inputs for display
    display_values = {**features}
    display_values["academic_performance_index"] = safe_float(row_eng["academic_performance_index"].iloc[0])
    display_values["financial_academic_risk"]    = safe_float(row_eng["financial_academic_risk"].iloc[0])

    result = {
        "shap_values": [
            {
                "feature":     FEATURE_LABELS.get(col, col),
                "feature_key": col,
                "value":       safe_float(display_values.get(col, 0.0)),
                "contribution": safe_float(sv[i]),
            }
            for i, col in enumerate(ENGINEERED_FEATURE_COLS)
        ],
        "base_value": base,
        "prediction": prob,
    }

    return result


def get_top_risk_factors(features: dict[str, float], top_n: int = 3) -> list[str]:
    """
    Extract the top N risk factors driving a student's risk score.
    Returns human-readable strings suitable for SMS messages.
    """
    shap_result = compute_shap_values(features)
    shap_items = shap_result["shap_values"]

    # Sort by absolute contribution (descending)
    sorted_items = sorted(shap_items, key=lambda x: abs(x["contribution"]), reverse=True)

    factors = []
    for item in sorted_items[:top_n]:
        direction = "high" if item["contribution"] > 0 else "low"
        if direction == "high":
            # Positive SHAP = pushes toward dropout
            factors.append(f"{item['feature']} ({item['value']:.1f}) increasing risk")
        else:
            factors.append(f"{item['feature']} ({item['value']:.1f}) mitigating risk")

    return factors


def generate_waterfall_plot(
    features: dict[str, float],
    student_id: str,
    save_dir: Path | None = None,
) -> str:
    """
    Generate a SHAP waterfall chart for a single student.
    Saves as 800×600 PNG and returns the file path.
    """
    model, scaler = _load_model_and_scaler()

    row_df = pd.DataFrame([{col: safe_float(features.get(col, 0.0)) for col in FEATURE_COLS}])
    row_eng = engineer_features(row_df)
    x = row_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)
    x_scaled = scaler.transform(x)

    explainer = shap.TreeExplainer(model)
    explanation = explainer(x_scaled)

    # Use human-readable feature names for all 7 features
    explanation.feature_names = [FEATURE_LABELS.get(c, c) for c in ENGINEERED_FEATURE_COLS]

    save_dir = save_dir or PLOTS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    plot_path = save_dir / f"waterfall_{student_id}.png"

    fig, ax = plt.subplots(figsize=(10, 7.5))
    shap.plots.waterfall(explanation[0], show=False)

    plt.title(f"Risk Factor Analysis - Student {student_id[:12]}...", fontsize=12)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=80, bbox_inches="tight")  # approx 800x600
    plt.close("all")

    logger.info("Waterfall plot saved -> %s", plot_path)
    return str(plot_path)


def generate_beeswarm_plot(df: pd.DataFrame, save_dir: Path | None = None) -> str:
    """
    Generate a cohort-level SHAP beeswarm summary plot.
    Expects df with FEATURE_COLS columns (raw feature values).
    """
    model, scaler = _load_model_and_scaler()

    df_eng = engineer_features(df[FEATURE_COLS])
    X = df_eng[ENGINEERED_FEATURE_COLS].values.astype(np.float32)
    X_scaled = scaler.transform(X)

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_scaled)

    # For binary classification, shap_vals may be a list
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]

    save_dir = save_dir or PLOTS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    plot_path = save_dir / "beeswarm_summary.png"

    plt.figure(figsize=(10, 7.5))
    shap.summary_plot(
        shap_vals,
        X_scaled,
        feature_names=[FEATURE_LABELS.get(c, c) for c in ENGINEERED_FEATURE_COLS],
        show=False,
    )
    plt.title("Cohort SHAP Summary - Dropout Risk Factors", fontsize=12)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=80, bbox_inches="tight")
    plt.close("all")

    logger.info("Beeswarm plot saved -> %s", plot_path)
    return str(plot_path)


def export_shap_json(features: dict[str, float], student_id: str) -> str:
    """
    Export SHAP values as a JSON file and return the path.
    """
    shap_result = compute_shap_values(features)

    save_path = PLOTS_DIR / f"shap_{student_id}.json"
    save_path.write_text(json.dumps(shap_result, indent=2, default=str))

    logger.info("SHAP JSON exported → %s", save_path)
    return str(save_path)
