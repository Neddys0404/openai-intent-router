from fastapi import FastAPI
from ai_gateway.api.openai import router as openai_router
from ai_gateway.api.health import router as health_router

app = FastAPI(title="AI Gateway")

# Include routers
app.include_router(openai_router, prefix="/v1", tags=["OpenAI"])
app.include_router(health_router, prefix="/health", tags=["Health"])

@app.get("/")
async def root():
    return {"status": "AI Gateway is running"}
