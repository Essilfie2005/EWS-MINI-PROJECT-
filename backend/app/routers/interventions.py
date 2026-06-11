"""
Interventions router – CRUD for student interventions + SMS trigger.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Intervention, Student
from app.models.schemas import (
    InterventionCreate,
    InterventionUpdate,
    InterventionResponse,
    InterventionListResponse,
    SMSSendRequest,
    SMSResponse,
)
from app.services import sms_service, whatsapp_service, shap_service, ml_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interventions", tags=["Interventions"])

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]


@router.get("/", response_model=InterventionListResponse)
async def list_interventions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    intervention_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List interventions with pagination and filtering."""
    query = select(Intervention).order_by(Intervention.created_at.desc())

    if status:
        query = query.where(Intervention.status == status)
    if intervention_type:
        query = query.where(Intervention.intervention_type == intervention_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    interventions = result.scalars().all()

    return InterventionListResponse(
        total=total,
        interventions=[InterventionResponse.model_validate(i) for i in interventions],
    )


@router.get("/{intervention_id}", response_model=InterventionResponse)
async def get_intervention(intervention_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single intervention by ID."""
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail=f"Intervention {intervention_id} not found")
    return InterventionResponse.model_validate(intervention)


@router.post("/", response_model=InterventionResponse, status_code=201)
async def create_intervention(
    body: InterventionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new intervention record."""
    # Verify student
    student_result = await db.execute(select(Student).where(Student.id == body.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {body.student_id} not found")

    intervention = Intervention(
        student_id=student.id,
        anon_id=student.anon_id,
        intervention_type=body.intervention_type,
        description=body.description,
        status="PENDING",
    )
    db.add(intervention)
    await db.flush()
    await db.refresh(intervention)
    return InterventionResponse.model_validate(intervention)


@router.put("/{intervention_id}", response_model=InterventionResponse)
async def update_intervention(
    intervention_id: int,
    body: InterventionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an intervention's status or outcome."""
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail=f"Intervention {intervention_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(intervention, key, val)

    if body.status == "COMPLETED":
        intervention.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(intervention)
    return InterventionResponse.model_validate(intervention)


@router.delete("/{intervention_id}", status_code=204)
async def delete_intervention(intervention_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an intervention record."""
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail=f"Intervention {intervention_id} not found")
    await db.delete(intervention)


@router.get("/student/{student_id}", response_model=InterventionListResponse)
async def get_interventions_for_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all interventions for a specific student."""
    result = await db.execute(
        select(Intervention)
        .where(Intervention.student_id == student_id)
        .order_by(Intervention.created_at.desc())
    )
    interventions = result.scalars().all()

    return InterventionListResponse(
        total=len(interventions),
        interventions=[InterventionResponse.model_validate(i) for i in interventions],
    )


@router.post("/send-sms", response_model=SMSResponse)
async def send_sms_intervention(
    body: SMSSendRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send an SMS alert for a specific student.
    Creates an intervention record and sends the SMS.
    """
    # Find student
    student_result = await db.execute(select(Student).where(Student.id == body.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {body.student_id} not found")

    target_phone = body.phone_number or student.phone_number
    if not target_phone:
        raise HTTPException(status_code=400, detail="Phone number is required. Please provide it or update the student profile.")

    # Save the phone number to the student if they didn't have one
    if body.phone_number and not student.phone_number:
        student.phone_number = body.phone_number
        await db.commit()

    # Get risk factors
    features = {col: getattr(student, col) for col in FEATURE_COLS}
    top_factors = []
    try:
        if ml_pipeline.is_model_loaded():
            top_factors = shap_service.get_top_risk_factors(features, top_n=3)
    except Exception as e:
        logger.warning("Could not compute SHAP factors for SMS: %s", e)

    # Build and send SMS
    if body.custom_message:
        message = body.custom_message
    else:
        message = sms_service.build_alert_message(
            student_anon_id=student.anon_id,
            risk_score=student.risk_score or 0.0,
            risk_band=student.risk_band or "UNKNOWN",
            top_factors=top_factors,
        )

    sms_result = sms_service.send_sms(target_phone, message)

    # Create intervention record
    intervention = Intervention(
        student_id=student.id,
        anon_id=student.anon_id,
        intervention_type="SMS",
        description=f"SMS sent to {target_phone}: {message[:100]}…",
        status="SENT" if sms_result["success"] else "FAILED",
    )
    db.add(intervention)

    return SMSResponse(
        success=sms_result["success"],
        message=sms_result["message"],
        sms_id=sms_result.get("sms_id"),
    )

@router.post("/send-whatsapp", response_model=SMSResponse)
async def send_whatsapp_intervention(
    body: SMSSendRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a WhatsApp alert for a specific student.
    Creates an intervention record and sends the WhatsApp message via Twilio.
    """
    # Find student
    student_result = await db.execute(select(Student).where(Student.id == body.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {body.student_id} not found")

    target_phone = body.phone_number or student.phone_number
    if not target_phone:
        raise HTTPException(status_code=400, detail="Phone number is required. Please provide it or update the student profile.")

    # Save the phone number to the student if they didn't have one
    if body.phone_number and not student.phone_number:
        student.phone_number = body.phone_number
        await db.commit()

    # Get risk factors
    features = {col: getattr(student, col) for col in FEATURE_COLS}
    top_factors = []
    try:
        if ml_pipeline.is_model_loaded():
            top_factors = shap_service.get_top_risk_factors(features, top_n=3)
    except Exception as e:
        logger.warning("Could not compute SHAP factors for WhatsApp: %s", e)

    # Build and send WhatsApp
    if body.custom_message:
        message = body.custom_message
    else:
        # We reuse the SMS build message function since WhatsApp requires the same text constraints
        message = sms_service.build_alert_message(
            student_anon_id=student.anon_id,
            risk_score=student.risk_score or 0.0,
            risk_band=student.risk_band or "UNKNOWN",
            top_factors=top_factors,
        )

    wa_result = whatsapp_service.send_whatsapp(target_phone, message)

    # Create intervention record
    intervention = Intervention(
        student_id=student.id,
        anon_id=student.anon_id,
        intervention_type="OTHER", # Mapping WhatsApp to OTHER due to DB enum
        description=f"WhatsApp sent to {target_phone}: {message[:100]}…",
        status="COMPLETED" if wa_result["success"] else "FAILED",
    )
    db.add(intervention)

    return SMSResponse(
        success=wa_result["success"],
        message=wa_result["message"],
        sms_id=wa_result.get("whatsapp_id"),
    )
