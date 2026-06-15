import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SMSStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"

    from pydantic import BaseModel, Field


class SMSSendRequest(BaseModel):
    student_id: int

    phone_number: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=20
    )

    message: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=500
    )

    priority: Optional[str] = "MEDIUM"


class SMSResponse(BaseModel):
    id: int

    student_id: int

    phone_number: str

    message: str

    status: SMSStatus

    success: bool

    sms_provider_id: Optional[str] = None

    error_message: Optional[str] = None

    sent_at: Optional[datetime.datetime] = None

    delivered_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}
