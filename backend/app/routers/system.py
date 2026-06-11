from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["System"])

@router.delete("/factory-reset")
async def factory_reset(db: AsyncSession = Depends(get_db)):
    """
    Purge all operational data (Students, Predictions, Alerts, Interventions)
    but preserve the core Settings configuration.
    """
    logger.warning("Initiating Factory Reset: Purging all operational data.")
    try:
        # SQLite doesn't support TRUNCATE, so we use DELETE
        await db.execute(text("DELETE FROM interventions;"))
        await db.execute(text("DELETE FROM alerts;"))
        await db.execute(text("DELETE FROM predictions;"))
        await db.execute(text("DELETE FROM students;"))
        
        await db.commit()
        logger.info("Factory Reset completed successfully.")
        return {"status": "success", "message": "All student and operational data has been purged."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Factory Reset failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to purge data.")
