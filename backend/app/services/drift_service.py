"""
Model Drift Detection Service
==============================
Detects when the distribution of model predictions has shifted significantly
compared to a baseline, alerting operators to potential data drift.

Called by the nightly scheduler and exposed via the dashboard endpoint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

SAVED_MODELS = Path(__file__).parent.parent.parent / "saved_models"
DRIFT_HISTORY_FILE = SAVED_MODELS / "drift_history.json"

# Thresholds
KS_DRIFT_THRESHOLD = 0.10    # KS statistic above this = drift detected
PSI_DRIFT_THRESHOLD = 0.20   # PSI above 0.2 = significant drift
PSI_WARNING_THRESHOLD = 0.10  # PSI 0.1-0.2 = minor drift warning


def _population_stability_index(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """
    Compute Population Stability Index (PSI) between two distributions.
    PSI < 0.1: No significant change
    PSI 0.1-0.2: Minor change (monitor)
    PSI > 0.2: Significant drift (retrain)
    """
    bins = np.linspace(0, 1, n_bins + 1)

    def safe_hist(arr):
        counts, _ = np.histogram(arr, bins=bins)
        pct = counts / len(arr)
        pct = np.where(pct == 0, 1e-4, pct)  # avoid log(0)
        return pct

    e = safe_hist(expected)
    a = safe_hist(actual)
    psi = np.sum((a - e) * np.log(a / e))
    return float(psi)


def load_drift_history() -> dict:
    """Load the drift history file or return empty structure."""
    if DRIFT_HISTORY_FILE.exists():
        try:
            return json.loads(DRIFT_HISTORY_FILE.read_text())
        except Exception:
            pass
    return {
        "baseline": None,
        "checks": [],
        "last_check": None,
        "current_status": "no_baseline",
    }


def save_drift_history(history: dict) -> None:
    DRIFT_HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))


def set_baseline(risk_scores: list[float]) -> dict:
    """
    Set the current risk score distribution as the baseline.
    Call this after training a new model or at the start of a semester.
    """
    history = load_drift_history()
    baseline = {
        "set_at": datetime.now(timezone.utc).isoformat(),
        "n_students": len(risk_scores),
        "mean": round(float(np.mean(risk_scores)), 4),
        "std": round(float(np.std(risk_scores)), 4),
        "percentiles": {
            "p10": round(float(np.percentile(risk_scores, 10)), 4),
            "p25": round(float(np.percentile(risk_scores, 25)), 4),
            "p50": round(float(np.percentile(risk_scores, 50)), 4),
            "p75": round(float(np.percentile(risk_scores, 75)), 4),
            "p90": round(float(np.percentile(risk_scores, 90)), 4),
        },
        "scores_sample": [round(float(s), 4) for s in risk_scores[:500]],  # store sample
    }
    history["baseline"] = baseline
    history["current_status"] = "baseline_set"
    save_drift_history(history)
    logger.info("Drift baseline set: n=%d, mean=%.4f", len(risk_scores), np.mean(risk_scores))
    return baseline


def check_drift(current_scores: list[float]) -> dict:
    """
    Compare current score distribution to the baseline.
    Returns drift status and metrics.
    """
    history = load_drift_history()

    if not history.get("baseline"):
        return {
            "status": "no_baseline",
            "message": "No baseline set. Train the model first or call /api/dashboard/drift/set-baseline.",
            "drift_detected": False,
        }

    baseline_scores = history["baseline"]["scores_sample"]
    baseline_arr = np.array(baseline_scores, dtype=float)
    current_arr  = np.array(current_scores, dtype=float)

    # KS test
    ks_stat, ks_p = stats.ks_2samp(baseline_arr, current_arr)

    # PSI
    psi = _population_stability_index(baseline_arr, current_arr)

    # Mean shift
    mean_shift = float(np.mean(current_arr)) - float(np.mean(baseline_arr))
    mean_shift_pct = round(abs(mean_shift) / max(float(np.mean(baseline_arr)), 0.01) * 100, 1)

    # Drift classification
    if psi > PSI_DRIFT_THRESHOLD or ks_stat > KS_DRIFT_THRESHOLD:
        drift_level = "SIGNIFICANT"
        recommendation = "Model retraining recommended. Risk score distribution has shifted materially."
    elif psi > PSI_WARNING_THRESHOLD:
        drift_level = "MINOR"
        recommendation = "Monitor closely. Minor distribution shift detected — may need retraining soon."
    else:
        drift_level = "NONE"
        recommendation = "Model is stable. Distribution matches baseline within acceptable limits."

    check_result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "n_current": len(current_scores),
        "n_baseline": len(baseline_scores),
        "ks_statistic": round(float(ks_stat), 4),
        "ks_p_value": round(float(ks_p), 4),
        "psi": round(psi, 4),
        "mean_baseline": round(float(np.mean(baseline_arr)), 4),
        "mean_current": round(float(np.mean(current_arr)), 4),
        "mean_shift_pct": mean_shift_pct,
        "drift_level": drift_level,
        "drift_detected": drift_level != "NONE",
        "recommendation": recommendation,
        "thresholds": {
            "ks_threshold": KS_DRIFT_THRESHOLD,
            "psi_warning": PSI_WARNING_THRESHOLD,
            "psi_significant": PSI_DRIFT_THRESHOLD,
        },
    }

    # Update history
    history["last_check"] = check_result["checked_at"]
    history["current_status"] = drift_level.lower()
    history["checks"] = history.get("checks", [])
    history["checks"].append({k: v for k, v in check_result.items() if k != "thresholds"})
    history["checks"] = history["checks"][-30:]  # keep last 30 checks
    save_drift_history(history)

    logger.info(
        "Drift check: PSI=%.4f, KS=%.4f, level=%s",
        psi, ks_stat, drift_level
    )
    return check_result


def get_drift_summary() -> dict:
    """Return a summary of the current drift status for the dashboard."""
    history = load_drift_history()
    recent_checks = history.get("checks", [])
    last_check = recent_checks[-1] if recent_checks else None

    return {
        "current_status": history.get("current_status", "no_baseline"),
        "baseline_set_at": history["baseline"]["set_at"] if history.get("baseline") else None,
        "last_check_at": history.get("last_check"),
        "last_result": last_check,
        "check_count": len(recent_checks),
        "history": recent_checks[-10:],  # last 10 for sparkline
    }
