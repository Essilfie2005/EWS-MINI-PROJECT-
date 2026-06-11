"""
SQLAlchemy ORM models for the dropout early-warning system.
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Student(Base):
    """Core student table – stores anonymised profile + academic features."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anon_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    original_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Academic / behavioural features ───────────────────────────────────
    attendance_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quiz_average: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assignment_submission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mobile_engagement_freq: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    financial_aid_status: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Risk fields ───────────────────────────────────────────────────────
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_band: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # LOW / MEDIUM / HIGH
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Ground truth ──────────────────────────────────────────────────────
    dropout_label: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1 = dropped, 0 = retained

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class Prediction(Base):
    """Per-student prediction log."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    anon_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")

    # ── SHAP values (JSON blob) ───────────────────────────────────────────
    shap_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    top_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Intervention(Base):
    """Records of interventions taken for flagged students."""

    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    anon_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    intervention_type: Mapped[str] = mapped_column(String(64), nullable=False)  # SMS, EMAIL, COUNSELLING, TUTORING
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")  # PENDING, SENT, COMPLETED, FAILED
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Alert(Base):
    """System alerts generated when students cross risk thresholds."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    anon_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)  # RISK_HIGH, RISK_MEDIUM, ATTENDANCE_DROP
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SyntheticStudent(Base):
    """CTGAN-generated synthetic student records."""

    __tablename__ = "synthetic_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attendance_rate: Mapped[float] = mapped_column(Float, nullable=False)
    quiz_average: Mapped[float] = mapped_column(Float, nullable=False)
    assignment_submission_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mobile_engagement_freq: Mapped[float] = mapped_column(Float, nullable=False)
    financial_aid_status: Mapped[float] = mapped_column(Float, nullable=False)
    dropout_label: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generation_batch: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SystemState(Base):
    """Key-value store for system-wide configuration and serialized ML models."""

    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
