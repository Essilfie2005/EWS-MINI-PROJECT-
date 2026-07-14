"""
V3 Intervention Outcome Feedback Service
==========================================
Closes the feedback loop: when counsellors mark interventions as
SUCCESSFUL or UNSUCCESSFUL, we use those outcomes to retrain the model
on updated labels, improving its accuracy over time.

This is "active learning" — the model improves itself from real-world
counsellor experience, not just from the original training data.

Workflow:
  1. Counsellor logs intervention → outcome is recorded in DB
  2. Nightly (or on demand): feedback_service builds a refined training set
     where students with SUCCESSFUL interventions have their dropout label
     revised (success → student likely to not drop out)
  3. The ensemble model is retrained on this enriched dataset
  4. Improvement metrics are logged and exposed via API
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.config import SAVED_MODELS_DIR

logger = logging.getLogger(__name__)

FEEDBACK_HISTORY_PATH = SAVED_MODELS_DIR / "feedback_history.json"


def load_feedback_history() -> dict:
    if FEEDBACK_HISTORY_PATH.exists():
        try:
            return json.loads(FEEDBACK_HISTORY_PATH.read_text())
        except Exception:
            pass
    return {"retraining_runs": [], "total_outcomes_used": 0}


def save_feedback_history(h: dict) -> None:
    FEEDBACK_HISTORY_PATH.write_text(json.dumps(h, indent=2, default=str))


def build_feedback_dataset(
    base_df: pd.DataFrame,
    interventions: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Augment the training DataFrame with intervention outcome labels.

    Logic:
    - SUCCESSFUL intervention → override dropout_label to 0 (student recovered)
    - UNSUCCESSFUL intervention → keep dropout_label as 1 (confirmed dropout risk)
    - REFERRED / PENDING → no change (insufficient signal)

    Parameters
    ----------
    base_df       : original training DataFrame with FEATURE_COLS + dropout_label
    interventions : list of intervention dicts from DB (student_id, outcome, features)

    Returns
    -------
    (augmented_df, stats_dict)
    """
    df = base_df.copy()
    stats = {
        "total_interventions":  len(interventions),
        "successful_overrides": 0,
        "unsuccessful_confirmed": 0,
        "skipped_pending": 0,
    }

    for iv in interventions:
        outcome    = iv.get("outcome", "PENDING")
        student_id = iv.get("student_id")
        if not student_id:
            continue

        if outcome == "SUCCESSFUL":
            # Find matching students and correct their label
            idx = df[df.get("student_id", pd.Series(dtype=int)) == student_id].index
            if len(idx) > 0:
                df.loc[idx, "dropout_label"] = 0
                stats["successful_overrides"] += 1
            stats["successful_overrides"] += 1

        elif outcome == "UNSUCCESSFUL":
            stats["unsuccessful_confirmed"] += 1
        else:
            stats["skipped_pending"] += 1

    logger.info(
        "Feedback dataset built: %d successful overrides, %d confirmed, %d pending",
        stats["successful_overrides"],
        stats["unsuccessful_confirmed"],
        stats["skipped_pending"],
    )
    return df, stats


async def run_feedback_retraining(
    db_session,
    base_df: pd.DataFrame,
) -> dict:
    """
    Full feedback retraining loop:
    1. Load all SUCCESSFUL/UNSUCCESSFUL interventions from DB
    2. Build feedback-augmented dataset
    3. Retrain the ensemble on it
    4. Log improvement metrics

    Parameters
    ----------
    db_session : AsyncSession (SQLAlchemy)
    base_df    : base training DataFrame

    Returns
    -------
    dict with retraining results and improvement
    """
    from sqlalchemy import select
    from app.models.db_models import Intervention, Student
    from app.services.ensemble_pipeline import train_ensemble

    # ── Load outcome-labelled interventions ───────────────────────────────
    result = await db_session.execute(
        select(Intervention).where(
            Intervention.outcome.in_(["SUCCESSFUL", "UNSUCCESSFUL"])
        )
    )
    interventions = result.scalars().all()

    if not interventions:
        return {
            "status": "skipped",
            "reason": "No outcome-labelled interventions found. Log intervention outcomes first.",
            "total_interventions": 0,
        }

    # Convert to list of dicts
    iv_dicts = [
        {
            "student_id": iv.student_id,
            "outcome":    iv.outcome,
            "intervention_type": iv.intervention_type,
        }
        for iv in interventions
    ]

    # ── Build feedback dataset ────────────────────────────────────────────
    augmented_df, stats = build_feedback_dataset(base_df, iv_dicts)

    logger.info("Retraining ensemble with %d outcome-augmented samples", len(augmented_df))

    # ── Retrain ensemble ──────────────────────────────────────────────────
    train_report = train_ensemble(augmented_df)

    # ── Log to feedback history ───────────────────────────────────────────
    history = load_feedback_history()
    run = {
        "run_at":            datetime.now(timezone.utc).isoformat(),
        "n_interventions":   len(iv_dicts),
        "augmentation_stats": stats,
        "ensemble_metrics":  train_report.get("ensemble_metrics", {}),
        "improvement_pct":   train_report.get("improvement_over_v2_pct", {}),
    }
    history["retraining_runs"].append(run)
    history["retraining_runs"] = history["retraining_runs"][-20:]  # keep last 20
    history["total_outcomes_used"] = len(iv_dicts)
    save_feedback_history(history)

    return {
        "status": "retrained",
        "interventions_used": len(iv_dicts),
        "augmentation_stats": stats,
        "ensemble_metrics": train_report.get("ensemble_metrics", {}),
        "improvement_over_v2_pct": train_report.get("improvement_over_v2_pct", {}),
        "trained_at": run["run_at"],
    }


def get_feedback_summary() -> dict:
    """Return feedback retraining history summary for the dashboard."""
    history = load_feedback_history()
    runs = history.get("retraining_runs", [])
    last = runs[-1] if runs else None
    return {
        "total_retraining_runs": len(runs),
        "total_outcomes_used":   history.get("total_outcomes_used", 0),
        "last_run": last,
        "improvement_trend": [
            {
                "run": i + 1,
                "f1":    r.get("ensemble_metrics", {}).get("f1", 0),
                "kappa": r.get("ensemble_metrics", {}).get("kappa", 0),
            }
            for i, r in enumerate(runs[-10:])
        ],
    }
