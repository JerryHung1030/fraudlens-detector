from fastapi import FastAPI
from app.routes import classification_router, ingestion_router # Add ingestion_router

app = FastAPI(
    title="ScamShield AI Backend",
    version="0.1.0",
    description="API for ScamShield AI operations, including post classification and ingestion.",
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to ScamShield AI Backend"}

# Include routers
app.include_router(classification_router, prefix="/api/v1/classification", tags=["Classification"])
app.include_router(ingestion_router, prefix="/api/v1/ingestion", tags=["Ingestion"]) # Add this line
