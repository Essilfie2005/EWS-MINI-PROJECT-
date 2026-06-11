"""
APScheduler-based task scheduler.

Runs a nightly cron job (default 18:00 GMT) to:
  1. Re-score all students
  2. Flag new high-risk students
  3. Generate alerts
  4. Batch-send SMS for newly flagged students
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from app.config import get_settings
from app.database import async_session_factory
from app.models.db_models import Student, Prediction, Alert
from app.services import ml_pipeline, shap_service, sms_service
from app.utils.metrics import assign_risk_band

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def nightly_risk_assessment():
    """
    Nightly batch job:
      1. Pull all students from DB
      2. Re-predict risk scores
      3. Update student records
      4. Create alerts for new HIGH-risk students
      5. Batch-send SMS (via mock/real AT)
    """
    logger.info("═══ Starting nightly risk assessment ═══")
    settings = get_settings()

    if not ml_pipeline.is_model_loaded():
        logger.warning("No ML model available – skipping nightly assessment.")
        return

    async with async_session_factory() as session:
        # 1. Pull all students
        result = await session.execute(select(Student))
        students = result.scalars().all()

        if not students:
            logger.info("No students in database – nothing to process.")
            return

        newly_flagged = []

        for student in students:
            features = {
                "attendance_rate": student.attendance_rate,
                "quiz_average": student.quiz_average,
                "assignment_submission_rate": student.assignment_submission_rate,
                "mobile_engagement_freq": student.mobile_engagement_freq,
                "financial_aid_status": student.financial_aid_status,
            }

            try:
                pred = ml_pipeline.predict_single(features)
            except Exception as e:
                logger.error("Prediction failed for student %d: %s", student.id, e)
                continue

            risk_score = pred["risk_score"]
            risk_band = pred["risk_band"]
            was_flagged = student.is_flagged

            # 2. Update student record
            student.risk_score = risk_score
            student.risk_band = risk_band
            student.is_flagged = (risk_band == "HIGH")

            # 3. Create prediction record
            try:
                shap_result = shap_service.compute_shap_values(features)
                top_factors = shap_service.get_top_risk_factors(features, top_n=3)
            except Exception:
                shap_result = None
                top_factors = []

            import json
            prediction = Prediction(
                student_id=student.id,
                anon_id=student.anon_id,
                risk_score=risk_score,
                risk_band=risk_band,
                model_version=pred["model_version"],
                shap_values=json.dumps(shap_result["shap_values"]) if shap_result else None,
                top_factors=json.dumps(top_factors) if top_factors else None,
            )
            session.add(prediction)

            # 4. Create alert for newly flagged students
            if risk_band == "HIGH" and not was_flagged:
                alert = Alert(
                    student_id=student.id,
                    anon_id=student.anon_id,
                    alert_type="RISK_HIGH",
                    message=f"Student {student.anon_id[:8]}… has been flagged as HIGH risk "
                            f"(score: {risk_score:.2%}). Top factors: {', '.join(top_factors[:2])}",
                )
                session.add(alert)
                newly_flagged.append((student, top_factors))

        await session.commit()

        # 5. Batch SMS for newly flagged (logged in mock mode)
        for student, factors in newly_flagged:
            sms_service.send_alert_sms(
                phone_number="+233000000000",  # placeholder; real phone from student profile
                student_anon_id=student.anon_id,
                risk_score=student.risk_score,
                risk_band=student.risk_band,
                top_factors=factors,
            )

        logger.info(
            "═══ Nightly assessment complete: %d students processed, %d newly flagged ═══",
            len(students), len(newly_flagged),
        )


def start_scheduler():
    """Start the APScheduler with the nightly cron job."""
    settings = get_settings()

    if scheduler.running:
        logger.info("Scheduler already running.")
        return

    scheduler.add_job(
        nightly_risk_assessment,
        trigger=CronTrigger(hour=settings.SCHEDULER_HOUR, minute=settings.SCHEDULER_MINUTE),
        id="nightly_risk_assessment",
        name="Nightly Dropout Risk Assessment",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started – nightly job at %02d:%02d UTC",
        settings.SCHEDULER_HOUR, settings.SCHEDULER_MINUTE,
    )


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
