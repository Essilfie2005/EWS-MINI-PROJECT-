from __future__ import annotations

import base64
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.db_models import SystemState
from app.config import SAVED_MODELS_DIR

logger = logging.getLogger(__name__)

FILES_TO_SYNC = [
    "xgb_model.joblib",
    "scaler.joblib",
    "model_meta.json"
]

async def sync_models_to_db() -> None:
    """
    Reads the trained model files from the local disk, converts them to base64,
    and stores them in the SystemState database table.
    This protects the models from ephemeral disk wipes.
    """
    async with async_session_factory() as db:
        try:
            for filename in FILES_TO_SYNC:
                filepath = SAVED_MODELS_DIR / filename
                if filepath.exists():
                    with open(filepath, "rb") as f:
                        file_data = f.read()
                        b64_data = base64.b64encode(file_data).decode("utf-8")
                        
                        # Upsert into SystemState
                        stmt = select(SystemState).where(SystemState.key == f"model_file_{filename}")
                        result = await db.execute(stmt)
                        state_obj = result.scalars().first()
                        
                        if state_obj:
                            state_obj.value = b64_data
                        else:
                            state_obj = SystemState(key=f"model_file_{filename}", value=b64_data)
                            db.add(state_obj)
                            
            await db.commit()
            logger.info("Successfully synced local ML models to PostgreSQL.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to sync models to DB: {e}")

async def sync_models_from_db() -> None:
    """
    Retrieves the trained model files from the SystemState database table,
    decodes them from base64, and writes them to the local disk.
    This restores the models after an ephemeral disk wipe.
    """
    async with async_session_factory() as db:
        try:
            restored_count = 0
            for filename in FILES_TO_SYNC:
                stmt = select(SystemState).where(SystemState.key == f"model_file_{filename}")
                result = await db.execute(stmt)
                state_obj = result.scalars().first()
                
                if state_obj:
                    filepath = SAVED_MODELS_DIR / filename
                    file_data = base64.b64decode(state_obj.value)
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    restored_count += 1
            
            if restored_count > 0:
                logger.info(f"Successfully restored {restored_count} ML model files from PostgreSQL.")
        except Exception as e:
            logger.error(f"Failed to restore models from DB: {e}")
