from pydantic import BaseModel, Field, model_validator
from typing import Optional
from enum import Enum
import datetime


class RiskBand(str, Enum):
    LOW = "Low Risk"
    MEDIUM = "Medium Risk"
    HIGH = "High Risk"


class PredictionStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class PredictionRequest(BaseModel):
    student_id: Optional[int] = None
    anon_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_identifiers(self,):
        if self.student_id is None and self.anon_id is None:
            raise ValueError("Either student_id or anon_id must be provided.")
        return self


class PredictionBatchRequest(BaseModel):
    student_ids: Optional[list[int]] = Field(
        default=None, description="List of student IDs for batch prediction")


class SHAPValue(BaseModel):
    feature: str
    value: float
    contribution: float
    direction: str = Field(
        ..., description="Indicates whether the feature contributes to higher or lower risk")


class PredictionResponse(BaseModel):
    id: int
    student_id: int
    anon_id: str
    risk_score: float
    confidence_score: Optional[float] = None
    risk_band: RiskBand
    status: PredictionStatus
    model_version: str
    explanation: Optional[str] = None
    shap_values: Optional[list[SHAPValue]] = None
    top_factors: Optional[list[str]] = None
    recommendations: Optional[list[str]] = None
    waterfall_plot_url: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    total: int
    page: int
    page_size: int

    predictions: list[PredictionResponse]
