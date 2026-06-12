"""
Application configuration via pydantic-settings.
Reads from environment variables and/or a .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Resolve project paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
PLOTS_DIR = BASE_DIR / "plots"
SAVED_MODELS_DIR = BASE_DIR / "saved_models"

# Ensure directories exist
for _d in (RAW_DIR, PROCESSED_DIR, SYNTHETIC_DIR, PLOTS_DIR, SAVED_MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Central configuration object – populated from env / .env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────
    APP_NAME: str = "Dropout Early-Warning System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'dropout.db'}"

    # ── Security / anonymisation ──────────────────────────────────────────
    HASH_SALT: str = "ghana-foundation-2024-salt"

    # ── OULAD dataset ─────────────────────────────────────────────────────
    OULAD_URL: str = "https://analyse.kmi.open.ac.uk/open_dataset/download"
    OULAD_ZIP: str = str(RAW_DIR / "oulad.zip")

    # ── ML pipeline ───────────────────────────────────────────────────────
    MODEL_PATH: str = str(SAVED_MODELS_DIR / "xgb_model.joblib")
    SCALER_PATH: str = str(SAVED_MODELS_DIR / "scaler.joblib")
    OPTUNA_TRIALS: int = 100
    OPTUNA_CV_FOLDS: int = 5
    XGB_N_ESTIMATORS: int = 300
    XGB_MAX_DEPTH: int = 6
    XGB_LEARNING_RATE: float = 0.05
    XGB_SUBSAMPLE: float = 0.8
    XGB_COLSAMPLE_BYTREE: float = 0.8
    XGB_SCALE_POS_WEIGHT: float = 3.0
    XGB_EARLY_STOPPING: int = 20
    TRAIN_RATIO: float = 0.70
    VAL_RATIO: float = 0.15
    TEST_RATIO: float = 0.15
    RISK_THRESHOLD: float = 0.5

    # ── CTGAN ─────────────────────────────────────────────────────────────
    CTGAN_EPOCHS: int = 300
    CTGAN_BATCH_SIZE: int = 500
    CTGAN_GENERATOR_DIM: tuple[int, int] = (256, 256)
    CTGAN_DISCRIMINATOR_DIM: tuple[int, int] = (256, 256)
    CTGAN_SYNTHETIC_N: int = 500



    # ── Scheduler ─────────────────────────────────────────────────────────
    SCHEDULER_HOUR: int = 18  # 18:00 GMT
    SCHEDULER_MINUTE: int = 0

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", 
        "http://localhost:3000",
        "https://dropout-early-warning.vercel.app",
        "*"
    ]


@lru_cache()
def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    return Settings()
