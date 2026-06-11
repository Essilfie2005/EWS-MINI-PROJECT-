"""
CTGAN Synthetic Data Generation Service.

Uses the SDV library's CTGAN to generate synthetic at-risk student records.
Validates output with SDV's diagnostic and quality reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, SYNTHETIC_DIR
from app.models.db_models import SyntheticStudent

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "attendance_rate",
    "quiz_average",
    "assignment_submission_rate",
    "mobile_engagement_freq",
    "financial_aid_status",
    "dropout_label",
]


def train_ctgan_and_generate(
    real_data: pd.DataFrame,
    n_samples: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Train a CTGAN model on real student data and generate synthetic records.

    Parameters
    ----------
    real_data : DataFrame with FEATURE_COLS columns
    n_samples : number of synthetic records to generate (default from settings)

    Returns
    -------
    (synthetic_df, report_dict)
    """
    from sdv.single_table import CTGANSynthesizer
    from sdv.metadata import SingleTableMetadata
    from sdv.evaluation.single_table import run_diagnostic, evaluate_quality

    settings = get_settings()
    n_samples = n_samples or settings.CTGAN_SYNTHETIC_N

    # Prepare real data subset
    df = real_data[FEATURE_COLS].copy()
    df["dropout_label"] = df["dropout_label"].astype(int)

    # ── Build SDV metadata ────────────────────────────────────────────────
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(df)

    # Override column types for precision
    metadata.update_column(column_name="dropout_label", sdtype="categorical")
    for col in FEATURE_COLS[:-1]:  # all except dropout_label
        metadata.update_column(column_name=col, sdtype="numerical")

    # ── Train CTGAN ───────────────────────────────────────────────────────
    logger.info(
        "Training CTGAN: epochs=%d, batch_size=%d, gen_dim=%s, disc_dim=%s, n_samples=%d",
        settings.CTGAN_EPOCHS, settings.CTGAN_BATCH_SIZE,
        settings.CTGAN_GENERATOR_DIM, settings.CTGAN_DISCRIMINATOR_DIM, n_samples,
    )

    synthesizer = CTGANSynthesizer(
        metadata,
        epochs=settings.CTGAN_EPOCHS,
        batch_size=settings.CTGAN_BATCH_SIZE,
        generator_dim=list(settings.CTGAN_GENERATOR_DIM),
        discriminator_dim=list(settings.CTGAN_DISCRIMINATOR_DIM),
        verbose=True,
    )
    synthesizer.fit(df)

    # ── Generate synthetic data ───────────────────────────────────────────
    synthetic_df = synthesizer.sample(num_rows=n_samples)

    # Clip to valid ranges
    synthetic_df["attendance_rate"] = synthetic_df["attendance_rate"].clip(0, 100).round(2)
    synthetic_df["quiz_average"] = synthetic_df["quiz_average"].clip(0, 100).round(2)
    synthetic_df["assignment_submission_rate"] = synthetic_df["assignment_submission_rate"].clip(0, 100).round(2)
    synthetic_df["mobile_engagement_freq"] = synthetic_df["mobile_engagement_freq"].clip(0, 100).round(2)
    synthetic_df["financial_aid_status"] = synthetic_df["financial_aid_status"].clip(1, 10).round(0)
    synthetic_df["dropout_label"] = synthetic_df["dropout_label"].astype(int).clip(0, 1)

    # ── Save to CSV ───────────────────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = SYNTHETIC_DIR / f"ctgan_synthetic_{timestamp}.csv"
    synthetic_df.to_csv(csv_path, index=False)
    logger.info("Synthetic data saved → %s (%d rows)", csv_path, len(synthetic_df))

    # ── Validate with SDV reports ─────────────────────────────────────────
    report_dict = {}
    try:
        diagnostic = run_diagnostic(real_data=df, synthetic_data=synthetic_df, metadata=metadata)
        report_dict["diagnostic_score"] = diagnostic.get_score()
        logger.info("SDV Diagnostic score: %s", report_dict["diagnostic_score"])
    except Exception as e:
        logger.warning("SDV diagnostic failed: %s", e)
        report_dict["diagnostic_score"] = None

    try:
        quality = evaluate_quality(real_data=df, synthetic_data=synthetic_df, metadata=metadata)
        report_dict["quality_score"] = quality.get_score()
        logger.info("SDV Quality score: %s", report_dict["quality_score"])
    except Exception as e:
        logger.warning("SDV quality eval failed: %s", e)
        report_dict["quality_score"] = None

    report_dict["n_generated"] = len(synthetic_df)
    report_dict["csv_path"] = str(csv_path)
    report_dict["dropout_rate_synthetic"] = float(synthetic_df["dropout_label"].mean())
    report_dict["dropout_rate_real"] = float(df["dropout_label"].mean())

    # Save CTGAN model
    model_path = SYNTHETIC_DIR / f"ctgan_model_{timestamp}.pkl"
    synthesizer.save(str(model_path))
    report_dict["model_path"] = str(model_path)

    return synthetic_df, report_dict


async def save_synthetic_to_db(
    synthetic_df: pd.DataFrame,
    session: AsyncSession,
    batch_label: str | None = None,
) -> int:
    """Insert synthetic records into the synthetic_students table."""
    batch_label = batch_label or datetime.now(timezone.utc).strftime("batch_%Y%m%d_%H%M%S")
    count = 0

    for _, row in synthetic_df.iterrows():
        record = SyntheticStudent(
            attendance_rate=float(row["attendance_rate"]),
            quiz_average=float(row["quiz_average"]),
            assignment_submission_rate=float(row["assignment_submission_rate"]),
            mobile_engagement_freq=float(row["mobile_engagement_freq"]),
            financial_aid_status=float(row["financial_aid_status"]),
            dropout_label=int(row["dropout_label"]),
            generation_batch=batch_label,
        )
        session.add(record)
        count += 1

    await session.commit()
    logger.info("Inserted %d synthetic records (batch: %s)", count, batch_label)
    return count
