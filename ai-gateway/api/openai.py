import httpx
from fastapi import APIRouter, Request, HTTPException
from ai_gateway.managers.model_manager import model_manager

router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model")
    
    if not model_name:
        raise HTTPException(status_code=400, detail="No model specified")

    try:
        endpoint = await model_manager.get_endpoint(model_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    async with httpx.AsyncClient() as client:
        # In a real scenario, we'd want to stream this response back.
        # For Phase 1, we will do a simple proxy of the JSON body.
        try:
            response = await client.post(endpoint, json=body, timeout=60.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Upstream error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models():
    return {"data": list(model_manager.models.keys())}
