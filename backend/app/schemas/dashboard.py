
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RiskDistribution(BaseModel):
    low_count: int
    medium_count: int
    high_count: int

    low_percentage: float
    medium_percentage: float
    high_percentage: float


class FeatureStats(BaseModel):
    feature: str
    mean: float
    median: float
    std: float
    min: float
    max: float
    missing_values: int


class DashboardSummary(BaseModel):
    total_students: int

    flagged_students: int

    high_risk_students: int

    risk_distribution: RiskDistribution

    average_risk_score: Optional[float] = None

    dropout_rate: Optional[float] = None

    intervention_success_rate: Optional[float] = None

    risk_trend: Optional[str] = None

    feature_stats: list[FeatureStats]

    recent_alerts_count: int

    resolved_alerts_count: int

    pending_interventions_count: int


class ModelMetrics(BaseModel):
    auc_roc: Optional[float] = None
    f1_score: Optional[float] = None
    pr_auc: Optional[float] = None
    cohen_kappa: Optional[float] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    training_samples: Optional[int] = None
    validation_samples: Optional[int] = None
    training_date: Optional[datetime.datetime] = None


class TrainResponse(BaseModel):
    message: str
    model_version: str
    metrics: Optional[ModelMetrics] = None
    training_duration_seconds: Optional[float] = None

    trained_at: Optional[datetime.datetime] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    api_status: bool
    database_ok: bool
    model_loaded: bool
    sms_service_ok: bool
    storage_ok: bool
