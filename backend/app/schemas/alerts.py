from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class AlertType(str, Enum):
    HIGH_RISK = "High Risk"
    LOW_ATTENDANCE = "Low Attendance"
    LOW_QUIZ_Score = "Low Quiz Score"
    LOW_ASSIGNMENT_SUBMISSION = "Low Assignment Submission"
    FINANCIAL_AID_RISK = "Financial Aid risk"
    DROPOUT_RISK = "Dropout Risk"


class AlertPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    CRITICAL = "Critical"


class AlertStatus(str, Enum):
    PENDING = "Pending"
    RESOLVED = "Resolved"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"
    OPEN = "Open"


class AlertCreate(BaseModel):
    student_code: str
    alert_type: AlertType
    priority: AlertPriority
    message: str
    created_at: datetime


class AlertUpdate(BaseModel):
    message: Optional[str] = None
    is_read: Optional[bool] = None
    status: Optional[AlertStatus] = None
    handled_at: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    student_id: str
    anon_id: str
    alert_type: AlertType
    priority: AlertPriority
    status: AlertStatus
    is_read: bool
    message: str
    prediction_id: Optional[int] = None
    handled_by: Optional[str] = None
    created_at: datetime.datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int
    unread_count: int
    alerts: list[AlertResponse]
