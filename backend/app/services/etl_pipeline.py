"""
ETL Pipeline – Ingest CSV files, anonymise IDs, engineer features,
and upsert students into the database.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, PROCESSED_DIR
from app.models.db_models import Student
from app.utils.anonymise import hash_student_id

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
]


def validate_csv(df: pd.DataFrame) -> list[str]:
    """
    Validate that a CSV DataFrame contains required columns.
    Returns a list of warnings (empty = all good).
    """
    warnings: list[str] = []
    # At minimum we need some identifier
    if "student_id" not in df.columns and "id_student" not in df.columns and "anon_id" not in df.columns:
        warnings.append("Missing student identifier column (student_id, id_student, or anon_id).")

    for col in FEATURE_COLS:
        if col not in df.columns:
            warnings.append(f"Missing feature column: {col}")

    return warnings


def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Apply median imputation for all feature columns."""
    df = df.copy()
    for col in FEATURE_COLS:
        if col in df.columns:
            median_val = df[col].median()
            if pd.isna(median_val):
                median_val = 0.0
            df[col] = df[col].fillna(median_val)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all 5 feature columns exist and are properly typed.
    Clips values to valid ranges.
    """
    df = df.copy()

    for col in ["attendance_rate", "quiz_average", "assignment_submission_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").clip(0, 100)

    if "mobile_engagement_freq" in df.columns:
        df["mobile_engagement_freq"] = pd.to_numeric(df["mobile_engagement_freq"], errors="coerce").clip(0, None)

    if "financial_aid_status" in df.columns:
        df["financial_aid_status"] = pd.to_numeric(df["financial_aid_status"], errors="coerce").clip(0, None)

    return df


async def ingest_csv(
    file_path: str | Path,
    session: AsyncSession,
    has_header: bool = True,
    id_column: str = "student_id",
) -> dict:
    """
    Full ETL pipeline for a CSV file:
      1. Load → 2. Validate → 3. Engineer → 4. Impute → 5. Anonymise → 6. Upsert

    Returns summary dict with counts and warnings.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    # 1. Load
    df = pd.read_csv(file_path, header=0 if has_header else None)
    logger.info("Loaded %d rows from %s", len(df), file_path)

    # 2. Validate
    warnings = validate_csv(df)
    if any("Missing student identifier" in w for w in warnings):
        return {"inserted": 0, "updated": 0, "warnings": warnings, "errors": ["No student ID column found."]}

    # 3. Engineer features
    df = engineer_features(df)

    # 4. Impute
    df = impute_missing(df)

    # Determine id column
    actual_id_col = id_column
    if actual_id_col not in df.columns:
        for candidate in ["student_id", "id_student", "anon_id"]:
            if candidate in df.columns:
                actual_id_col = candidate
                break

    # 5. Anonymise & 6. Upsert
    inserted = 0
    updated = 0
    settings = get_settings()

    for _, row in df.iterrows():
        raw_id = str(row[actual_id_col])
        anon_id = hash_student_id(raw_id)

        # Check if student exists
        result = await session.execute(
            select(Student).where(Student.anon_id == anon_id)
        )
        existing = result.scalar_one_or_none()

        feature_data = {
            col: float(row[col]) if col in row.index and not pd.isna(row[col]) else 0.0
            for col in FEATURE_COLS
        }

        # Check for phone number
        phone_number = None
        if "phone_number" in row.index and not pd.isna(row["phone_number"]):
            phone_number = str(row["phone_number"])
        elif "phone" in row.index and not pd.isna(row["phone"]):
            phone_number = str(row["phone"])

        if existing:
            for key, val in feature_data.items():
                setattr(existing, key, val)
            if "dropout_label" in row.index and not pd.isna(row.get("dropout_label")):
                existing.dropout_label = int(row["dropout_label"])
            if phone_number is not None:
                existing.phone_number = phone_number
            updated += 1
        else:
            student = Student(
                anon_id=anon_id,
                original_id=raw_id,
                **feature_data,
                phone_number=phone_number,
                dropout_label=int(row["dropout_label"]) if "dropout_label" in row.index and not pd.isna(row.get("dropout_label")) else None,
            )
            session.add(student)
            inserted += 1

    await session.commit()

    # Save processed version
    processed_path = PROCESSED_DIR / f"processed_{file_path.stem}.csv"
    df.to_csv(processed_path, index=False)

    summary = {
        "inserted": inserted,
        "updated": updated,
        "total_rows": len(df),
        "warnings": warnings,
        "processed_file": str(processed_path),
    }
    logger.info("ETL complete: %s", summary)
    return summary


async def get_feature_matrix(session: AsyncSession) -> pd.DataFrame:
    """Pull all student features from DB into a DataFrame for ML."""
    result = await session.execute(
        select(
            Student.id,
            Student.anon_id,
            Student.attendance_rate,
            Student.quiz_average,
            Student.assignment_submission_rate,
            Student.mobile_engagement_freq,
            Student.financial_aid_status,
            Student.dropout_label,
        )
    )
    rows = result.all()
    return pd.DataFrame(rows, columns=[
        "id", "anon_id", *FEATURE_COLS, "dropout_label",
    ])
