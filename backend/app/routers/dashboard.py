"""
Dashboard router – analytics and summary endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Student, Prediction, Alert, Intervention
from app.models.schemas import (
    DashboardSummary,
    RiskDistribution,
    FeatureStats,
    HealthResponse,
    ModelMetrics,
)
from app.services import ml_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Get a comprehensive dashboard summary with risk distribution and feature stats."""

    # Total students
    total_result = await db.execute(select(func.count(Student.id)))
    total_students = total_result.scalar_one()

    # Flagged students
    flagged_result = await db.execute(
        select(func.count(Student.id)).where(Student.is_flagged == True)
    )
    flagged_students = flagged_result.scalar_one()

    # Risk distribution
    low_result = await db.execute(
        select(func.count(Student.id)).where(Student.risk_band == "LOW")
    )
    medium_result = await db.execute(
        select(func.count(Student.id)).where(Student.risk_band == "MEDIUM")
    )
    high_result = await db.execute(
        select(func.count(Student.id)).where(Student.risk_band == "HIGH")
    )

    risk_dist = RiskDistribution(
        low=low_result.scalar_one(),
        medium=medium_result.scalar_one(),
        high=high_result.scalar_one(),
    )

    # Average risk score
    avg_risk_result = await db.execute(
        select(func.avg(Student.risk_score)).where(Student.risk_score.isnot(None))
    )
    avg_risk = avg_risk_result.scalar_one()

    # Dropout rate (from labelled data)
    dropout_count = await db.execute(
        select(func.count(Student.id)).where(Student.dropout_label == 1)
    )
    labelled_count = await db.execute(
        select(func.count(Student.id)).where(Student.dropout_label.isnot(None))
    )
    dc = dropout_count.scalar_one()
    lc = labelled_count.scalar_one()
    dropout_rate = (dc / lc * 100) if lc > 0 else None

    # Feature statistics - single query to avoid N+1
    feature_stats = []
    students_res = await db.execute(select(Student))
    students = students_res.scalars().all()
    
    for col in FEATURE_COLS:
        vals = [getattr(s, col) for s in students if getattr(s, col) is not None]
        if vals:
            feature_stats.append(FeatureStats(
                feature=col,
                mean=round(float(np.mean(vals)), 2),
                median=round(float(np.median(vals)), 2),
                std=round(float(np.std(vals)), 2),
                min=round(float(np.min(vals)), 2),
                max=round(float(np.max(vals)), 2),
            ))
        else:
            feature_stats.append(FeatureStats(
                feature=col, mean=0.0, median=0.0, std=0.0, min=0.0, max=0.0
            ))

    # Recent alerts count (last 24h)
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    alerts_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= since)
    )
    recent_alerts = alerts_result.scalar_one()

    # Pending interventions
    pending_result = await db.execute(
        select(func.count(Intervention.id)).where(Intervention.status == "PENDING")
    )
    pending_interventions = pending_result.scalar_one()

    return DashboardSummary(
        total_students=total_students,
        flagged_students=flagged_students,
        risk_distribution=risk_dist,
        average_risk_score=round(avg_risk, 4) if avg_risk else None,
        dropout_rate=round(dropout_rate, 2) if dropout_rate else None,
        feature_stats=feature_stats,
        recent_alerts_count=recent_alerts,
        pending_interventions_count=pending_interventions,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check."""
    # Check DB
    db_ok = True
    try:
        await db.execute(select(func.count(Student.id)))
    except Exception:
        db_ok = False

    from app.config import get_settings
    settings = get_settings()

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=settings.APP_VERSION,
        model_loaded=ml_pipeline.is_model_loaded(),
        database_ok=db_ok,
    )


@router.get("/model-metrics", response_model=Optional[ModelMetrics])
async def get_model_metrics():
    """Get the latest model evaluation metrics."""
    meta = ml_pipeline.get_model_metadata()
    if not meta:
        raise HTTPException(status_code=404, detail="No model trained yet")

    test_metrics = meta.get("test_metrics", {})
    return ModelMetrics(
        auc_roc=test_metrics.get("auc_roc"),
        f1_score=test_metrics.get("f1_score"),
        pr_auc=test_metrics.get("pr_auc"),
        cohen_kappa=test_metrics.get("cohen_kappa"),
        accuracy=test_metrics.get("accuracy"),
        precision=test_metrics.get("precision"),
        recall=test_metrics.get("recall"),
    )


@router.get("/risk-distribution")
async def get_risk_distribution(db: AsyncSession = Depends(get_db)):
    """Detailed risk distribution breakdown."""
    result = await db.execute(
        select(
            Student.risk_band,
            func.count(Student.id).label("count"),
            func.avg(Student.risk_score).label("avg_score"),
        )
        .where(Student.risk_band.isnot(None))
        .group_by(Student.risk_band)
    )
    rows = result.all()

    distribution = {}
    for row in rows:
        distribution[row[0]] = {
            "count": row[1],
            "avg_score": round(float(row[2]), 4) if row[2] else None,
        }

    return {"risk_distribution": distribution}


@router.get("/feature-importance")
async def get_feature_importance():
    """Get XGBoost feature importance scores."""
    meta = ml_pipeline.get_model_metadata()
    if not meta:
        raise HTTPException(status_code=404, detail="No model trained yet")

    model, _ = ml_pipeline._get_cached_model()
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    importance = model.get_booster().get_score(importance_type="gain")

    # Map f0, f1, ... to feature names
    feature_cols = meta.get("feature_cols", FEATURE_COLS)
    named_importance = {}
    for key, val in importance.items():
        idx = int(key.replace("f", ""))
        if idx < len(feature_cols):
            named_importance[feature_cols[idx]] = round(val, 4)

    # Sort descending
    sorted_importance = dict(sorted(named_importance.items(), key=lambda x: x[1], reverse=True))

    return {"feature_importance": sorted_importance}
