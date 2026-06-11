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

        try:
            top_factors = shap_service.get_top_risk_factors(features, top_n=3)
        except Exception:
            top_factors = []

        prediction = Prediction(
            student_id=student.id,
            anon_id=student.anon_id,
            risk_score=pred["risk_score"],
            risk_band=pred["risk_band"],
            model_version=pred["model_version"],
            top_factors=json.dumps(top_factors) if top_factors else None,
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
            top_factors=top_factors,
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
