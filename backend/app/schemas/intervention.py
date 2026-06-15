from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InterventionCreate(BaseModel):
    student_id: str
    intervention_type: str
    handled_by: Optional[str] = None
    created_at: datetime


class InterventionUpdate(BaseModel):
    intervention_type: Optional[str] = None
    handled_by: Optional[str] = None


class InterventionResponse(BaseModel):
    student_id: str
    intervention_type: str
    handled_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
