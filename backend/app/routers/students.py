from __future__ import annotations

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
)
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.students import Student
from app.models.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentListResponse,
)
from app.utils.anonymise import hash_student_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/students",
    tags=["Students"],
)


@router.get("/", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),

    risk_band: Optional[str] = Query(
        None,
        pattern=r"^(LOW|MEDIUM|HIGH)$"
    ),

    is_flagged: Optional[bool] = None,

    search: Optional[str] = None,

    min_risk_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
    ),

    max_risk_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
    ),

    sort_by: str = Query(
        "created_at",
        pattern=r"^(created_at|risk_score|attendance_rate|quiz_average)$"
    ),

    sort_order: str = Query(
        "desc",
        pattern=r"^(asc|desc)$"
    ),

    db: AsyncSession = Depends(get_db),
):
    """
    List students with:
    - Pagination
    - Search
    - Risk filtering
    - Sorting
    """

    query = select(Student)

    if risk_band:
        query = query.where(Student.risk_band == risk_band)

    if is_flagged is not None:
        query = query.where(Student.is_flagged == is_flagged)

    if search:
        query = query.where(
            Student.original_id.contains(search)
        )

    if min_risk_score is not None:
        query = query.where(
            Student.risk_score >= min_risk_score
        )

    if max_risk_score is not None:
        query = query.where(
            Student.risk_score <= max_risk_score
        )

    count_query = select(
        func.count()
    ).select_from(
        query.subquery()
    )

    total_result = await db.execute(count_query)

    total = total_result.scalar_one()

    sort_column = getattr(Student, sort_by)

    if sort_order == "asc":
        query = query.order_by(
            asc(sort_column)
        )
    else:
        query = query.order_by(
            desc(sort_column)
        )

    query = query.offset(
        (page - 1) * page_size
    ).limit(page_size)

    result = await db.execute(query)

    students = result.scalars().all()

    return StudentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        students=[
            StudentResponse.model_validate(student)
            for student in students
        ],
    )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(
            Student.id == student_id
        )
    )

    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student {student_id} not found",
        )

    return StudentResponse.model_validate(student)


@router.get(
    "/anon/{anon_id}",
    response_model=StudentResponse,
)
async def get_student_by_anon_id(
    anon_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(
            Student.anon_id == anon_id
        )
    )

    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student {anon_id} not found",
        )

    return StudentResponse.model_validate(student)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=201,
)
async def create_student(
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
):
    try:

        raw_id = (
            body.original_id
            or f"manual-{hash_student_id(str(id(body)))[:12]}"
        )

        anon_id = hash_student_id(raw_id)

        existing = await db.execute(
            select(Student).where(
                Student.anon_id == anon_id
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Student already exists",
            )

        student = Student(
            anon_id=anon_id,
            original_id=raw_id,

            attendance_rate=body.attendance_rate,
            quiz_average=body.quiz_average,
            assignment_submission_rate=body.assignment_submission_rate,
            mobile_engagement_freq=body.mobile_engagement_freq,
            financial_aid_status=body.financial_aid_status,

            phone_number=body.phone_number,

            dropout_label=body.dropout_label,
        )

        db.add(student)

        await db.commit()

        await db.refresh(student)

        return StudentResponse.model_validate(student)

    except Exception as e:

        await db.rollback()

        logger.exception(e)

        raise


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
)
async def update_student(
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(
            Student.id == student_id
        )
    )

    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student {student_id} not found",
        )

    try:

        update_data = body.model_dump(
            exclude_unset=True
        )

        for field, value in update_data.items():
            setattr(student, field, value)

        await db.commit()

        await db.refresh(student)

        return StudentResponse.model_validate(student)

    except Exception as e:

        await db.rollback()

        logger.exception(e)

        raise


@router.delete(
    "/{student_id}",
    status_code=204,
)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(
            Student.id == student_id
        )
    )

    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student {student_id} not found",
        )

    try:

        await db.delete(student)

        await db.commit()

    except Exception as e:

        await db.rollback()

        logger.exception(e)

        raise


@router.get("/stats/summary")
async def student_stats(
    db: AsyncSession = Depends(get_db),
):
    total_students = (
        await db.execute(
            select(
                func.count(Student.id)
            )
        )
    ).scalar_one()

    flagged_students = (
        await db.execute(
            select(
                func.count(Student.id)
            ).where(
                Student.is_flagged == True
            )
        )
    ).scalar_one()

    labelled_students = (
        await db.execute(
            select(
                func.count(Student.id)
            ).where(
                Student.dropout_label.is_not(None)
            )
        )
    ).scalar_one()

    high_risk_students = (
        await db.execute(
            select(
                func.count(Student.id)
            ).where(
                Student.risk_band == "HIGH"
            )
        )
    ).scalar_one()

    avg_risk_score = (
        await db.execute(
            select(
                func.avg(Student.risk_score)
            )
        )
    ).scalar()

    return {
        "total_students": total_students,
        "flagged_students": flagged_students,
        "labelled_students": labelled_students,
        "high_risk_students": high_risk_students,
        "average_risk_score": avg_risk_score,
    }
