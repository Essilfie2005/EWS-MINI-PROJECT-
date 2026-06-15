"""
Pydantic schemas (request / response models) for the FastAPI endpoints.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# Student
# ═══════════════════════════════════════════════════════════════════════════

class StudentBase(BaseModel):
    attendance_rate: float = Field(..., ge=0.0, le=100.0)
    quiz_average: float = Field(..., ge=0.0, le=100.0)
    assignment_submission_rate: float = Field(..., ge=0.0, le=100.0)
    mobile_engagement_freq: float = Field(..., ge=0.0)
    financial_aid_status: float = Field(..., ge=0.0)


class StudentCreate(StudentBase):
    original_id: Optional[str] = None
    dropout_label: Optional[int] = None
    phone_number: Optional[str] = None


class StudentUpdate(BaseModel):
    attendance_rate: Optional[float] = None
    quiz_average: Optional[float] = None
    assignment_submission_rate: Optional[float] = None
    mobile_engagement_freq: Optional[float] = None
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


# ═══════════════════════════════════════════════════════════════════════════
# Prediction
# ═══════════════════════════════════════════════════════════════════════════

class PredictionRequest(BaseModel):
    student_id: Optional[int] = None
    anon_id: Optional[str] = None


class PredictionBatchRequest(BaseModel):
    student_id: Optional[list[int]] = None


class SHAPValue(BaseModel):
    feature: str
    value: float
    contribution: float


class PredictionResponse(BaseModel):
    id: int
    student_id: int
    anon_id: str
    risk_score: float
    risk_band: str
    model_version: str
    shap_values: Optional[list[SHAPValue]] = None
    top_factors: Optional[list[str]] = None
    waterfall_plot_url: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    total: int
    predictions: list[PredictionResponse]


# ═══════════════════════════════════════════════════════════════════════════
# Intervention
# ═══════════════════════════════════════════════════════════════════════════

class InterventionCreate(BaseModel):
    student_id: int
    intervention_type: str = Field(...,
                                   pattern=r"^(SMS|EMAIL|COUNSELLING|TUTORING|OTHER)$")
    description: Optional[str] = None


class InterventionUpdate(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None


class InterventionResponse(BaseModel):
    id: int
    student_id: int
    anon_id: str
    intervention_type: str
    description: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class InterventionListResponse(BaseModel):
    total: int
    interventions: list[InterventionResponse]


# ═══════════════════════════════════════════════════════════════════════════
# Alert
# ═══════════════════════════════════════════════════════════════════════════

class AlertCreate(BaseModel):
    student_id: int
    alert_type: str
    message: str


class AlertResponse(BaseModel):
    id: int
    student_id: int
    anon_id: str
    alert_type: str
    message: str
    is_read: bool
    is_dismissed: bool
    created_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int
    unread_count: int
    alerts: list[AlertResponse]


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard / Analytics
# ═══════════════════════════════════════════════════════════════════════════

class RiskDistribution(BaseModel):
    low: int
    medium: int
    high: int


class FeatureStats(BaseModel):
    feature: str
    mean: float
    median: float
    std: float
    min: float
    max: float


class DashboardSummary(BaseModel):
    total_students: int
    flagged_students: int
    risk_distribution: RiskDistribution
    average_risk_score: Optional[float] = None
    dropout_rate: Optional[float] = None
    feature_stats: list[FeatureStats]
    recent_alerts_count: int
    pending_interventions_count: int


class ModelMetrics(BaseModel):
    auc_roc: Optional[float] = None
    f1_score: Optional[float] = None
    pr_auc: Optional[float] = None
    cohen_kappa: Optional[float] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None


class TrainResponse(BaseModel):
    message: str
    model_version: str
    metrics: Optional[ModelMetrics] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    database_ok: bool


# ═══════════════════════════════════════════════════════════════════════════
# CTGAN / Synthetic
# ═══════════════════════════════════════════════════════════════════════════

class SyntheticGenerateRequest(BaseModel):
    n_samples: int = 500


class SyntheticResponse(BaseModel):
    generated: int
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# SMS
# ═══════════════════════════════════════════════════════════════════════════
