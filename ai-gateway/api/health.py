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

@router.get("/readiness")
async def readiness_check():
    """Return 200 OK if the gateway is ready to serve requests.

    The readiness probe checks that the classifier model (if configured) is
    running and that the image generation backend is correctly configured.
    It does **not** check the health of every individual model; those are
    covered by the normal ``/health`` endpoint.
    """
    # Check classifier readiness
    classifier_name = model_manager.config.get("gateway", {}).get("classifier_model")
    if classifier_name:
        try:
            running = await model_manager.is_running(classifier_name)
        except Exception as exc:  # pragma: no cover - defensive
            return HTTPException(status_code=503, detail=f"Classifier health check failed: {exc}")
        if not running:
            return HTTPException(status_code=503, detail="Classifier model is not running")

    # Check image backend readiness
    try:
        # Import lazily to avoid circular imports at module load time.
        from tools.image_tools import ImageGenerator
        image_generator = ImageGenerator(model_manager.config.get("image_generation", {}))
        image_generator.validate_configuration()
    except Exception as exc:  # pragma: no cover - defensive
        return HTTPException(status_code=503, detail=f"Image backend not ready: {exc}")

    return {"status": "ready"}
