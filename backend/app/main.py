"""
FastAPI application entry point.

Lifespan events handle:
  • Database initialisation (create tables)
  • OULAD dataset download & seeding
  • ML model loading
  • Scheduler startup/shutdown
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings, PLOTS_DIR
from app.database import init_db, dispose_engine
from app.routers import (
    students_router,
    predictions_router,
    dashboard_router,
    alerts_router,
    interventions_router,
    system_router,
)
from app.routers.auth import router as auth_router

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    settings = get_settings()

    # 1. Create DB tables
    logger.info("Initialising database …")
    await init_db()

    # 2. Seed OULAD data (downloads on first run)
    logger.info("Checking OULAD data seed …")
    try:
        from app.utils.seed_data import seed_from_oulad
        count = await seed_from_oulad()
        logger.info("Database has %d students.", count)
    except Exception as e:
        logger.error("OULAD seed failed: %s (system will run but without pre-loaded data)", e)

    # 3. Load ML model if available
    from app.services.sync import sync_models_from_db
    logger.info("Syncing ML models from database...")
    await sync_models_from_db()
    
    from app.services.ml_pipeline import reload_model
    if reload_model():
        logger.info("ML model loaded successfully.")
    else:
        logger.warning("No pre-trained model found. Train via POST /api/predictions/train")

    # 4. Start scheduler
    from app.services.scheduler import start_scheduler, stop_scheduler
    try:
        start_scheduler()
    except Exception as e:
        logger.error("Scheduler start failed: %s", e)

    logger.info("═══ %s v%s started ═══", settings.APP_NAME, settings.APP_VERSION)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Shutting down …")
    try:
        stop_scheduler()
    except Exception:
        pass
    await dispose_engine()
    logger.info("═══ Shutdown complete ═══")


# ── App factory ───────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Lightweight Dropout Prediction and Early Warning System "
            "with Explainable AI for University Foundation Programs in Ghana. "
            "Powered by XGBoost, SHAP, and CTGAN."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Static files (SHAP plots) ────────────────────────────────────────
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static/plots", StaticFiles(directory=str(PLOTS_DIR)), name="plots")

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(students_router)
    app.include_router(predictions_router)
    app.include_router(dashboard_router)
    app.include_router(alerts_router)
    app.include_router(interventions_router)
    app.include_router(system_router)
    app.include_router(auth_router)

    # ── Root endpoint ─────────────────────────────────────────────────────
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/dashboard/health",
        }

    return app


app = create_app()
