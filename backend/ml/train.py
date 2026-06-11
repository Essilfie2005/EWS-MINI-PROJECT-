"""
Standalone ML training script.

Usage:
    python -m ml.train

Loads OULAD data from the processed CSV (or DB), trains an XGBoost model
with Optuna HPO, evaluates on the test set, and serializes to disk.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure the backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings, SAVED_MODELS_DIR, PROCESSED_DIR
from app.services.ml_pipeline import train_model, FEATURE_COLS
from app.utils.seed_data import load_processed_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("ml.train")


def main():
    """Main training entry point."""
    logger.info("═══ ML Training Pipeline ═══")

    # Load data
    try:
        df = load_processed_csv()
        logger.info("Loaded processed CSV: %d rows", len(df))
    except FileNotFoundError:
        logger.error(
            "No processed data found at %s. "
            "Start the FastAPI server first to download & process OULAD, "
            "or run the seed script.",
            PROCESSED_DIR / "oulad_processed.csv",
        )
        sys.exit(1)

    # Ensure dropout_label column exists
    if "dropout_label" not in df.columns:
        logger.error("'dropout_label' column not found in data.")
        sys.exit(1)

    # Filter to labelled data only
    df = df.dropna(subset=["dropout_label"]).copy()
    df["dropout_label"] = df["dropout_label"].astype(int)

    logger.info(
        "Training data: %d samples, %.1f%% dropout rate",
        len(df), df["dropout_label"].mean() * 100,
    )

    # Train
    result = train_model(df)

    # Report
    logger.info("═══ Training Complete ═══")
    logger.info("Model version: %s", result["model_version"])
    logger.info("Model path: %s", result["model_path"])
    logger.info("Best Optuna params: %s", json.dumps(result["best_params"], indent=2))
    logger.info("Test metrics:")
    for key, val in result["metrics"].items():
        if key == "confusion_matrix":
            logger.info("  %s: %s", key, val)
        else:
            logger.info("  %s: %.4f", key, val)


if __name__ == "__main__":
    main()
