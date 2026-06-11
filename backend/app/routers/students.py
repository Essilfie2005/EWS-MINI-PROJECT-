"""
Students router – CRUD endpoints for student records.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Student
from app.models.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentListResponse,
)
from app.utils.anonymise import hash_student_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/students", tags=["Students"])


@router.get("/", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    risk_band: Optional[str] = Query(None, pattern=r"^(LOW|MEDIUM|HIGH)$"),
    is_flagged: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List students with pagination, filtering, and search."""
    query = select(Student)

    if risk_band:
        query = query.where(Student.risk_band == risk_band)
    if is_flagged is not None:
        query = query.where(Student.is_flagged == is_flagged)
    if search:
        query = query.where(Student.original_id.contains(search))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    students = result.scalars().all()

    return StudentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        students=[StudentResponse.model_validate(s) for s in students],
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single student by database ID."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    return StudentResponse.model_validate(student)


@router.get("/anon/{anon_id}", response_model=StudentResponse)
async def get_student_by_anon_id(anon_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single student by anonymised ID."""
    result = await db.execute(select(Student).where(Student.anon_id == anon_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student with anon_id {anon_id} not found")
    return StudentResponse.model_validate(student)


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(body: StudentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new student record."""
    raw_id = body.original_id or f"manual-{hash_student_id(str(id(body)))[:12]}"
    anon_id = hash_student_id(raw_id)

    # Check for duplicate
    existing = await db.execute(select(Student).where(Student.anon_id == anon_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student with this ID already exists")

    student = Student(
        anon_id=anon_id,
        original_id=raw_id,
        attendance_rate=body.attendance_rate,
        quiz_average=body.quiz_average,
        assignment_submission_rate=body.assignment_submission_rate,
        mobile_engagement_freq=body.mobile_engagement_freq,
        financial_aid_status=body.financial_aid_status,
        dropout_label=body.dropout_label,
    )
    db.add(student)
    await db.flush()
    await db.refresh(student)
    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a student's features or flagged status."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(student, key, val)

    await db.flush()
    await db.refresh(student)
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}", status_code=204)
async def delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a student record."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    await db.delete(student)


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV file to ingest students via ETL pipeline."""
    import tempfile
    from pathlib import Path
    from app.services.etl_pipeline import ingest_csv
    from app.config import RAW_DIR

    # Save uploaded file
    save_path = RAW_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    # Run ETL
    result = await ingest_csv(save_path, db)
    return result


@router.get("/stats/summary")
async def student_stats(db: AsyncSession = Depends(get_db)):
    """Quick student count statistics."""
    total = (await db.execute(select(func.count(Student.id)))).scalar_one()
    flagged = (await db.execute(
        select(func.count(Student.id)).where(Student.is_flagged == True)
    )).scalar_one()
    with_labels = (await db.execute(
        select(func.count(Student.id)).where(Student.dropout_label.isnot(None))
    )).scalar_one()

    return {
        "total_students": total,
        "flagged_students": flagged,
        "labelled_students": with_labels,
    }
