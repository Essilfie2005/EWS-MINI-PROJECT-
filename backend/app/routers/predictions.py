"""
Predictions router – ML prediction endpoints, SHAP explanations, model training.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Student, Prediction
from app.models.schemas import (
    PredictionRequest,
    PredictionBatchRequest,
    PredictionResponse,
    PredictionListResponse,
    SHAPValue,
    TrainResponse,
    ModelMetrics,
    SyntheticGenerateRequest,
    SyntheticResponse,
)
from app.services import ml_pipeline, shap_service, ctgan_service
from app.utils.seed_data import get_training_dataframe, load_processed_csv

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/predictions", tags=["Predictions"])

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]


@router.post("/predict", response_model=PredictionResponse)
async def predict_student(
    body: PredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Predict dropout risk for a single student."""
    if not ml_pipeline.is_model_loaded():
        raise HTTPException(status_code=503, detail="No trained model available. Train the model first via POST /api/predictions/train")

    # Find student
    query = select(Student)
    if body.student_id:
        query = query.where(Student.id == body.student_id)
    elif body.anon_id:
        query = query.where(Student.anon_id == body.anon_id)
    else:
        raise HTTPException(status_code=400, detail="Provide student_id or anon_id")

    try:
        result = await db.execute(query)
    except Exception as e:
        logger.error("Database query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    features = {col: getattr(student, col) for col in FEATURE_COLS}

    # Predict
    pred = ml_pipeline.predict_single(features)

    # SHAP
    try:
        shap_result = shap_service.compute_shap_values(features)
        top_factors = shap_service.get_top_risk_factors(features, top_n=3)
        shap_values_list = [
            SHAPValue(feature=sv["feature"], value=sv["value"], contribution=sv["contribution"])
            for sv in shap_result["shap_values"]
        ]
    except Exception as e:
        logger.exception("SHAP computation failed: %s", e)
        # Expose the error to the frontend for debugging
        raise HTTPException(status_code=500, detail=f"SHAP computation failed: {str(e)}")

    # Generate waterfall plot
    waterfall_url = None
    try:
        plot_path = shap_service.generate_waterfall_plot(features, student.anon_id)
        filename = Path(plot_path).name
        waterfall_url = f"/static/plots/{filename}"
    except Exception as e:
        logger.warning("Waterfall plot generation failed: %s", e)

    # Save prediction to DB
    prediction = Prediction(
        student_id=student.id,
        anon_id=student.anon_id,
        risk_score=pred["risk_score"],
        risk_band=pred["risk_band"],
        model_version=pred["model_version"],
        shap_values=json.dumps([sv.model_dump() for sv in shap_values_list]) if shap_values_list else None,
        top_factors=json.dumps(top_factors) if top_factors else None,
    )
    db.add(prediction)

    # Update student risk fields
    student.risk_score = pred["risk_score"]
    student.risk_band = pred["risk_band"]
    student.is_flagged = (pred["risk_band"] == "HIGH")

    await db.flush()
    await db.refresh(prediction)

    return PredictionResponse(
        id=prediction.id,
        student_id=student.id,
        anon_id=student.anon_id,
        risk_score=pred["risk_score"],
        risk_band=pred["risk_band"],
        model_version=pred["model_version"],
        shap_values=shap_values_list,
        top_factors=top_factors,
        waterfall_plot_url=waterfall_url,
        created_at=prediction.created_at,
    )


@router.post("/predict-batch", response_model=PredictionListResponse)
async def predict_batch(
    body: PredictionBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Predict dropout risk for a batch of students."""
    if not ml_pipeline.is_model_loaded():
        raise HTTPException(status_code=503, detail="No trained model available")

    query = select(Student)
    if body.student_ids:
        query = query.where(Student.id.in_(body.student_ids))

    result = await db.execute(query)
    students = result.scalars().all()

    if not students:
        raise HTTPException(status_code=404, detail="No students found")

    predictions = []
    for student in students:
        features = {col: getattr(student, col) for col in FEATURE_COLS}
        pred = ml_pipeline.predict_single(features)

        prediction = Prediction(
            student_id=student.id,
            anon_id=student.anon_id,
            risk_score=pred["risk_score"],
            risk_band=pred["risk_band"],
            model_version=pred["model_version"],
            top_factors=None,
        )
        db.add(prediction)

        student.risk_score = pred["risk_score"]
        student.risk_band = pred["risk_band"]
        student.is_flagged = (pred["risk_band"] == "HIGH")

        predictions.append(PredictionResponse(
            id=0,  # will be set after flush
            student_id=student.id,
            anon_id=student.anon_id,
            risk_score=pred["risk_score"],
            risk_band=pred["risk_band"],
            model_version=pred["model_version"],
            top_factors=[],
        ))

    await db.flush()

    return PredictionListResponse(total=len(predictions), predictions=predictions)


@router.get("/history/{student_id}", response_model=PredictionListResponse)
async def get_prediction_history(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get prediction history for a student."""
    result = await db.execute(
        select(Prediction).where(Prediction.student_id == student_id).order_by(Prediction.created_at.desc())
    )
    predictions = result.scalars().all()

    response_list = []
    for p in predictions:
        shap_vals = None
        if p.shap_values:
            try:
                raw = json.loads(p.shap_values)
                shap_vals = [SHAPValue(**sv) for sv in raw]
            except Exception:
                pass

        top_facs = None
        if p.top_factors:
            try:
                top_facs = json.loads(p.top_factors)
            except Exception:
                pass

        response_list.append(PredictionResponse(
            id=p.id,
            student_id=p.student_id,
            anon_id=p.anon_id,
            risk_score=p.risk_score,
            risk_band=p.risk_band,
            model_version=p.model_version,
            shap_values=shap_vals,
            top_factors=top_facs,
            created_at=p.created_at,
        ))

    return PredictionListResponse(total=len(response_list), predictions=response_list)


@router.post("/train", response_model=TrainResponse)
async def train_model_endpoint(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Train (or retrain) the XGBoost model using all labelled students in the DB.
    Training runs synchronously for now (takes ~2-10 min depending on data size).
    """
    try:
        df = await get_training_dataframe()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("Training model with %d labelled students …", len(df))
    result = ml_pipeline.train_model(df)
    
    # Sync trained model to DB to protect against ephemeral wipes
    from app.services.sync import sync_models_to_db
    background_tasks.add_task(sync_models_to_db)

    metrics = ModelMetrics(
        auc_roc=result["metrics"].get("auc_roc"),
        f1_score=result["metrics"].get("f1_score"),
        pr_auc=result["metrics"].get("pr_auc"),
        cohen_kappa=result["metrics"].get("cohen_kappa"),
        accuracy=result["metrics"].get("accuracy"),
        precision=result["metrics"].get("precision"),
        recall=result["metrics"].get("recall"),
    )

    return TrainResponse(
        message="Model trained successfully",
        model_version=result["model_version"],
        metrics=metrics,
    )


@router.get("/model-info")
async def model_info():
    """Get info about the currently loaded model."""
    meta = ml_pipeline.get_model_metadata()
    if not meta:
        raise HTTPException(status_code=404, detail="No model metadata found")
    return meta


@router.post("/generate-synthetic", response_model=SyntheticResponse)
async def generate_synthetic(
    body: SyntheticGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate synthetic student records using CTGAN."""
    try:
        df = await get_training_dataframe()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    synthetic_df, report = ctgan_service.train_ctgan_and_generate(df, n_samples=body.n_samples)
    count = await ctgan_service.save_synthetic_to_db(synthetic_df, db)

    return SyntheticResponse(
        generated=count,
        message=f"Generated {count} synthetic records. Quality score: {report.get('quality_score', 'N/A')}",
    )


@router.post("/generate-beeswarm")
async def generate_beeswarm(db: AsyncSession = Depends(get_db)):
    """Generate a cohort SHAP beeswarm summary plot."""
    if not ml_pipeline.is_model_loaded():
        raise HTTPException(status_code=503, detail="No trained model available")

    try:
        df = await get_training_dataframe()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plot_path = shap_service.generate_beeswarm_plot(df)
    filename = Path(plot_path).name

    return {"message": "Beeswarm plot generated", "plot_url": f"/static/plots/{filename}"}


async def _run_shap_batch(student_ids: list[int]) -> None:
    """
    Background task: compute and store SHAP values for a list of student IDs.

    Fetches each student from its own DB session, computes SHAP, then upserts
    the result into the Prediction table (latest prediction row for that student).
    Students are processed in chunks of 100 to avoid holding large result sets
    in memory.
    """
    from app.database import async_session_factory  # avoid circular import at module level

    BATCH_SIZE = 100
    total = len(student_ids)
    logger.info("SHAP batch: processing %d students in chunks of %d", total, BATCH_SIZE)

    for batch_start in range(0, total, BATCH_SIZE):
        chunk_ids = student_ids[batch_start : batch_start + BATCH_SIZE]

        async with async_session_factory() as db:
            try:
                result = await db.execute(
                    select(Student).where(Student.id.in_(chunk_ids))
                )
                students = result.scalars().all()

                for student in students:
                    features = {col: getattr(student, col) for col in FEATURE_COLS}

                    try:
                        shap_result = shap_service.compute_shap_values(features)
                        top_factors = shap_service.get_top_risk_factors(features, top_n=3)
                    except Exception as exc:
                        logger.warning(
                            "SHAP computation failed for student %s: %s",
                            student.anon_id,
                            exc,
                        )
                        continue

                    # Build the same list-of-dicts format used by predict_student
                    shap_values_json = json.dumps(
                        [
                            {
                                "feature": sv["feature"],
                                "value": sv["value"],
                                "contribution": sv["contribution"],
                            }
                            for sv in shap_result["shap_values"]
                        ]
                    )
                    top_factors_json = json.dumps(top_factors) if top_factors else None

                    # Upsert: update the most-recent Prediction row if it exists,
                    # otherwise insert a new one.
                    pred_result = await db.execute(
                        select(Prediction)
                        .where(Prediction.student_id == student.id)
                        .order_by(Prediction.created_at.desc())
                        .limit(1)
                    )
                    existing = pred_result.scalar_one_or_none()

                    if existing is not None:
                        existing.shap_values = shap_values_json
                        existing.top_factors = top_factors_json
                    else:
                        # No prediction row yet – create a minimal one carrying
                        # only the SHAP payload (risk fields come from the Student).
                        new_pred = Prediction(
                            student_id=student.id,
                            anon_id=student.anon_id,
                            risk_score=student.risk_score if student.risk_score is not None else 0.0,
                            risk_band=student.risk_band if student.risk_band is not None else "LOW",
                            model_version=ml_pipeline.get_model_metadata().get("model_version", "v1")
                            if ml_pipeline.get_model_metadata()
                            else "v1",
                            shap_values=shap_values_json,
                            top_factors=top_factors_json,
                        )
                        db.add(new_pred)

                await db.flush()
                logger.info(
                    "SHAP batch: committed chunk %d-%d",
                    batch_start + 1,
                    batch_start + len(students),
                )
            except Exception as exc:
                logger.error("SHAP batch chunk failed (start=%d): %s", batch_start, exc)
                await db.rollback()

    logger.info("SHAP batch complete – processed %d students", total)


@router.post("/generate-shap-batch")
async def generate_shap_batch(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger background SHAP computation for all batch-predicted students.

    Fetches every student that already has a risk_score (i.e. has gone through
    batch prediction), then launches a background task to compute and store
    SHAP values in the Prediction table.  Returns immediately with a count of
    students queued.
    """
    if not ml_pipeline.is_model_loaded():
        raise HTTPException(status_code=503, detail="No trained model available. Train the model first via POST /api/predictions/train")

    result = await db.execute(
        select(Student.id).where(Student.risk_score.isnot(None))
    )
    student_ids: list[int] = list(result.scalars().all())

    if not student_ids:
        return {"status": "no_op", "total": 0, "message": "No batch-predicted students found."}

    background_tasks.add_task(_run_shap_batch, student_ids)

    logger.info("generate-shap-batch: queued %d students for SHAP computation", len(student_ids))
    return {"status": "started", "total": len(student_ids)}


# ── V2 endpoints ────────────────────────────────────────────────────────────

@router.get("/trajectory/{student_id}")
async def get_risk_trajectory(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    Return weekly risk score history for a student.
    If multiple predictions exist, returns them ordered by created_at.
    Fills in synthetic earlier weeks based on current score trend.
    """
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Load prediction history ordered by time
    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.created_at.asc())
    )
    predictions = pred_result.scalars().all()

    current_score = float(student.risk_score or 0.5)

    if predictions and len(predictions) >= 2:
        # Use real history
        trajectory = [
            {
                "week": f"Wk {i+1}",
                "risk_score": round(float(p.risk_score), 4),
                "real": True,
            }
            for i, p in enumerate(predictions[-8:])  # last 8 readings
        ]
    else:
        # Synthesise a plausible 6-week trajectory ending at current score
        import random
        import math
        random.seed(student_id)
        weeks = 6
        # Start higher if high risk (student was deteriorating), lower if safe
        start_offset = random.uniform(0.05, 0.20)
        if current_score > 0.5:
            start = max(0.1, current_score - start_offset)
        else:
            start = min(0.9, current_score + start_offset)
        trajectory = []
        for w in range(weeks):
            t = w / (weeks - 1)
            # Ease from start to current
            score = start + (current_score - start) * (t ** 1.5)
            # Small noise
            score += random.uniform(-0.02, 0.02)
            score = round(max(0.0, min(1.0, score)), 4)
            trajectory.append({"week": f"Wk {w+1}", "risk_score": score, "real": False})

    return {
        "student_id": student_id,
        "current_risk_score": current_score,
        "trajectory": trajectory,
        "youden_threshold": 0.4432,
    }


@router.get("/count-at-threshold")
async def count_students_at_threshold(
    tau: float = 0.5,
    db: AsyncSession = Depends(get_db),
):
    """Count how many students would be flagged at a given threshold tau."""
    if not (0.0 <= tau <= 1.0):
        raise HTTPException(status_code=422, detail="tau must be between 0 and 1")

    result = await db.execute(
        select(func.count(Student.id)).where(Student.risk_score.isnot(None))
    )
    total = result.scalar() or 0

    flagged_result = await db.execute(
        select(func.count(Student.id)).where(
            Student.risk_score.isnot(None),
            Student.risk_score >= tau,
        )
    )
    flagged = flagged_result.scalar() or 0

    return {
        "tau": round(tau, 4),
        "flagged": int(flagged),
        "total": int(total),
        "pct_flagged": round(flagged / total * 100, 1) if total > 0 else 0.0,
        "youden_tau": 0.4432,
    }


@router.get("/pdf/{student_id}")
async def download_pdf_brief(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    Generate and return a PDF risk brief for a single student.
    Returns a binary PDF with student risk score, top SHAP factors, and recommended actions.
    """
    from fastapi.responses import StreamingResponse
    import io

    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    features = {col: getattr(student, col) for col in FEATURE_COLS}
    risk_score = float(student.risk_score or 0.0)
    risk_band = student.risk_band or "UNKNOWN"

    # Get SHAP values for top factors
    try:
        shap_result = shap_service.compute_shap_values(features)
        shap_items = sorted(shap_result["shap_values"], key=lambda x: abs(x["contribution"]), reverse=True)
        top3 = shap_items[:3]
    except Exception:
        top3 = []

    # Build PDF using reportlab (fallback to plain text if not installed)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                                leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=6, alignment=TA_CENTER)
        story.append(Paragraph("EWS — Student Risk Brief", title_style))
        story.append(Paragraph("Confidential — For Counsellor Use Only", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Risk band colour
        band_color = {"CRITICAL": colors.red, "HIGH": colors.orangered,
                      "MEDIUM": colors.orange, "LOW": colors.green}.get(risk_band, colors.gray)

        # Summary table
        data = [
            ["Student ID", f"#{student_id}  (Anon: {student.anon_id or 'N/A'})"],
            ["Risk Score", f"{risk_score:.2%}"],
            ["Risk Band", risk_band],
            ["Attendance", f"{float(student.attendance_rate or 0):.1f}%"],
            ["Quiz Average", f"{float(student.quiz_average or 0):.1f}%"],
            ["Assignment Submission", f"{float(student.assignment_submission_rate or 0):.1f}%"],
        ]
        tbl = Table(data, colWidths=[6*cm, 10*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a0f1e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (1, 2), (1, 2), band_color),
            ("TEXTCOLOR", (1, 2), (1, 2), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # Top risk factors
        story.append(Paragraph("Top Risk Factors (SHAP Analysis)", styles["Heading2"]))
        if top3:
            for item in top3:
                direction = "increases" if item["contribution"] > 0 else "decreases"
                arrow = "+" if item["contribution"] > 0 else ""
                story.append(Paragraph(
                    f"• <b>{item['feature']}</b> = {item['value']:.1f} "
                    f"(SHAP: {arrow}{item['contribution']:.4f} — {direction} dropout risk)",
                    styles["Normal"]
                ))
        else:
            story.append(Paragraph("SHAP data not yet computed for this student.", styles["Normal"]))

        story.append(Spacer(1, 0.4*cm))

        # Recommended actions
        story.append(Paragraph("Recommended Actions", styles["Heading2"]))
        actions = []
        if float(student.attendance_rate or 100) < 60:
            actions.append("Schedule an attendance review meeting within 3 days.")
        if float(student.quiz_average or 100) < 40:
            actions.append("Refer to academic support / peer tutoring programme.")
        if float(student.financial_aid_status or 10) < 4:
            actions.append("Review financial aid eligibility — student may qualify for bursary.")
        if not actions:
            actions.append("Monitor student progress weekly. No urgent intervention required.")
        for a in actions:
            story.append(Paragraph(f"• {a}", styles["Normal"]))

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            "Generated by the EWS (Early Warning System) — Ghanaian University Foundation Programme. "
            "This document is anonymised and must not be shared outside the counselling team.",
            styles["Italic"]
        ))

        doc.build(story)
        buf.seek(0)
        content_type = "application/pdf"
        filename = f"risk_brief_{student_id}.pdf"

    except ImportError:
        # Fallback: plain text if reportlab not available
        text = (
            f"EWS Risk Brief — Student #{student_id}\n"
            f"Risk Score: {risk_score:.2%}\n"
            f"Risk Band: {risk_band}\n\n"
            + "\n".join(f"{item['feature']}: {item['contribution']:+.4f}" for item in top3)
            + "\n\nInstall reportlab for PDF output: pip install reportlab"
        )
        buf = io.BytesIO(text.encode())
        content_type = "text/plain"
        filename = f"risk_brief_{student_id}.txt"

    return StreamingResponse(
        buf,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
