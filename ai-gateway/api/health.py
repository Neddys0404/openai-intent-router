from fastapi import APIRouter
from managers.model_manager import model_manager

router = APIRouter()

@router.get("")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", **model_manager.health()}

@router.get("/metrics")
async def metrics():
    state = model_manager.health()
    return {"requests_total": state["requests"], "uptime_seconds": state["uptime_seconds"]}
