# ===============================================================================
#     Module Name: main.py
#     Description: API for url and line id analysis, which calls the blacklist manager.
#     Author: Jerry, Ken, SJ
#     Last Updated: 2025-06-23
#     Version: 1.0.0
#     Notes: 無
# ===============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.managers.blacklist_manager import BlacklistManager

# Initialize the FastAPI app
app = FastAPI(
    title="Blacklist Analysis API",
    description="API to find suspicious line ids and urls in text",
    version="1.0.0"
)

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the blacklist manager class
manager = BlacklistManager()


# Define the request and response models
class AnalyzeRequest(BaseModel):
    description: str


class AnalyzeResponse(BaseModel):
    line_id_list: list[str]
    url_list: list[str]
    line_id_details: list[dict]
    url_details: list[dict]


# Define the API endpoint
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    try:
        result = manager.analyze(request.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
