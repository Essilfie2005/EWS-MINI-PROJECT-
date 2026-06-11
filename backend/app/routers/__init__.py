from app.routers.students import router as students_router
from app.routers.predictions import router as predictions_router
from app.routers.dashboard import router as dashboard_router
from app.routers.alerts import router as alerts_router
from app.routers.interventions import router as interventions_router
from app.routers.system import router as system_router

__all__ = [
    "students_router",
    "predictions_router",
    "dashboard_router",
    "alerts_router",
    "interventions_router",
    "system_router",
]
