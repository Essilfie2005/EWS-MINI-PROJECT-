from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StudentBase(BaseModel):
    attendance_rate: Optional[float] = None
    quiz_average: Optional[float] = None
    assignment_submission_rate: Optional[float] = None
    financial_aid_status: Optional[bool] = None


class StudentCreate(StudentBase):
    student_id: str
    dropout_status: Optional[int] = None
    phone_number: Optional[str] = None


class StudentUpdate(StudentBase):
    attendance_rate: Optional[float] = None
    quiz_average: Optional[float] = None
    assignment_submission_rate: Optional[float] = None
    financial_aid_status: Optional[float] = None
    is_flagged: Optional[bool] = None


class StudentResponse(StudentBase):
    id: int
    anon_id: str
    original_id: Optional[str] = None
    phone_number: Optional[str] = None
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    is_flagged: bool = False
    dropout_label: Optional[int] = None
    created_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class StudentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    students: list[StudentResponse]
