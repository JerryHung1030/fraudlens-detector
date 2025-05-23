from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()

class IngestPayload(BaseModel):
    source: str
    data: Dict[str, Any] # Example: can be a list of posts or scenarios

class IngestResponse(BaseModel):
    message: str
    received_source: str
    data_summary: Dict[str, Any]

@router.post("/ingest", 
             status_code=status.HTTP_501_NOT_IMPLEMENTED,
             response_model=IngestResponse)
async def ingest_data(payload: IngestPayload):
    # For Week 1, this is a placeholder.
    # It does not interact with RAGCore-X for ingestion as reference data is passed with each task.
    # Future functionality might involve managing the fraud_scenarios.jsonl file or other data sources.
    
    # Log the received payload for now to show it's being called
    # import logging
    # logging.info(f"Received ingestion request from source: {payload.source} with data: {payload.data}")

    return IngestResponse(
        message="Ingestion endpoint is a placeholder for Week 1. No data was actively ingested into RAGCore-X. Future versions may support managing reference data like fraud scenarios.",
        received_source=payload.source,
        data_summary={"content_keys": list(payload.data.keys()), "num_items": len(payload.data) if isinstance(payload.data, list) else 1}
    )
