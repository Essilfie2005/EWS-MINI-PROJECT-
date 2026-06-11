"""
Alerts router – CRUD for system alerts.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Alert, Student
from app.models.schemas import AlertCreate, AlertResponse, AlertListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    is_read: Optional[bool] = None,
    alert_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List alerts with pagination and filtering."""
    query = select(Alert).order_by(Alert.created_at.desc())

    if is_read is not None:
        query = query.where(Alert.is_read == is_read)
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Unread count
    unread = (await db.execute(
        select(func.count(Alert.id)).where(Alert.is_read == False)
    )).scalar_one()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        total=total,
        unread_count=unread,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return AlertResponse.model_validate(alert)


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(body: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert."""
    # Verify student exists
    student_result = await db.execute(select(Student).where(Student.id == body.student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {body.student_id} not found")

    alert = Alert(
        student_id=student.id,
        anon_id=student.anon_id,
        alert_type=body.alert_type,
        message=body.message,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as read."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    alert.is_read = True
    await db.flush()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Dismiss an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    alert.is_dismissed = True
    alert.is_read = True
    await db.flush()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post("/mark-all-read")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    """Mark all alerts as read."""
    await db.execute(
        update(Alert).where(Alert.is_read == False).values(is_read=True)
    )
    return {"message": "All alerts marked as read"}


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    await db.delete(alert)


@router.get("/student/{student_id}", response_model=AlertListResponse)
async def get_alerts_for_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all alerts for a specific student."""
    result = await db.execute(
        select(Alert).where(Alert.student_id == student_id).order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()

    unread = sum(1 for a in alerts if not a.is_read)

    return AlertListResponse(
        total=len(alerts),
        unread_count=unread,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
    )
