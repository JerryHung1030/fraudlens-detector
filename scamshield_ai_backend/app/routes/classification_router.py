import json
from fastapi import APIRouter, HTTPException, Depends, Body, status # Added status
from pydantic import BaseModel # Added BaseModel
from typing import List, Annotated, Optional # Added Optional
import logging 

from app.services import RAGCoreService 
from app.models import ( 
    Post, 
    FraudScenario,
    RAGCoreJobCreationResponse,
    RAGCoreJobCreationErrorResponse,
    RAGCoreScenario, 
)
import httpx # For catching httpx specific errors

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__) 


router = APIRouter()

_fraud_scenarios_cache: List[FraudScenario] = []
FRAUD_SCENARIOS_FILE_PATH = "data/fraud_scenarios.jsonl" 

def load_fraud_scenarios(path: str = FRAUD_SCENARIOS_FILE_PATH) -> List[FraudScenario]:
    global _fraud_scenarios_cache
    # In a real app, consider thread-safety for cache or load at startup.
    # For this PoC, this basic cache is fine.
    if _fraud_scenarios_cache: 
        logger.info("Returning cached fraud scenarios.")
        return _fraud_scenarios_cache
    
    scenarios = []
    try:
        logger.info(f"Loading fraud scenarios from: {path}")
        # Ensure path is relative to the project root where 'data' dir is expected.
        # FastAPI's CWD is usually the project root when run with uvicorn from there.
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                scenarios.append(FraudScenario(**data))
        _fraud_scenarios_cache = scenarios
        logger.info(f"Successfully loaded and cached {len(scenarios)} fraud scenarios.")
        return scenarios
    except FileNotFoundError:
        logger.error(f"Fraud scenarios file not found at {path}. Please create it in the 'data' directory at the project root.")
        _fraud_scenarios_cache = [] 
        return [] 
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from fraud scenarios file: {path}")
        _fraud_scenarios_cache = []
        return []
    except Exception as e: 
        logger.error(f"An unexpected error occurred loading fraud scenarios: {e}")
        _fraud_scenarios_cache = []
        return []

async def get_rag_core_service():
    service = RAGCoreService()
    try:
        yield service
    finally:
        await service.close()

class ClassifyRequest(BaseModel): # Ensure BaseModel is imported
    post: Post
    scenario_options: Optional[RAGCoreScenario] = None


@router.post("/classify", 
             response_model=RAGCoreJobCreationResponse, 
             responses={
                 status.HTTP_400_BAD_REQUEST: {"model": RAGCoreJobCreationErrorResponse, "description": "Bad Request (e.g., RAG Core API error, invalid input)"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": RAGCoreJobCreationErrorResponse, "description": "Internal Server Error"},
                 status.HTTP_503_SERVICE_UNAVAILABLE: {"model": RAGCoreJobCreationErrorResponse, "description": "External service unavailable"}
             })
async def classify_post(
    payload: Annotated[ClassifyRequest, Body(...)],
    rag_service: Annotated[RAGCoreService, Depends(get_rag_core_service)]
):
    logger.info(f"Received classification request for post SID: {payload.post.sid}")

    fraud_scenarios = load_fraud_scenarios()
    if not fraud_scenarios:
        logger.error("No fraud scenarios loaded. Cannot proceed with classification.")
        # Return a RAGCoreJobCreationErrorResponse-like structure for consistency if possible
        # Or a more generic error. For now, use HTTPException directly.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail={"success": False, "error": {"code": 5030, "detail": {"message": "Fraud scenarios could not be loaded.", "message_eng": "Fraud scenarios unavailable."}}}
        )

    try:
        logger.info(f"Calling RAGCoreService to create task for post SID: {payload.post.sid} with {len(fraud_scenarios)} reference scenarios.")
        result = await rag_service.create_rag_task(
            post_data=payload.post, 
            reference_scenarios=fraud_scenarios,
            scenario_options=payload.scenario_options
        )
        logger.info(f"RAGCoreService response for SID {payload.post.sid}: {result}")

        if isinstance(result, RAGCoreJobCreationResponse):
            return result
        elif isinstance(result, RAGCoreJobCreationErrorResponse):
            http_status_code = status.HTTP_400_BAD_REQUEST # Default for client-type errors from RAG
            if result.error:
                # As per RAGCore-X spec: 4000 for format issues, 5000 for resource issues, 3000 for general system issues
                if result.error.code == 4000: # Bad request format to RAG
                    http_status_code = status.HTTP_400_BAD_REQUEST
                elif result.error.code == 5000: # RAG system resource issue
                    http_status_code = status.HTTP_503_SERVICE_UNAVAILABLE # Or 500, depends on desired semantics
                elif result.error.code == 3000: # RAG general system error
                    http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            logger.error(f"Error from RAGCoreService for SID {payload.post.sid}: {result.model_dump_json()}")
            raise HTTPException(status_code=http_status_code, detail=result.model_dump())
        else:
            logger.error(f"Unexpected response type from RAGCoreService for SID {payload.post.sid}: {type(result)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail={"success": False, "error": {"code": 5000, "detail": {"message": "Internal server error: Unexpected response from RAG service.", "message_eng": "Internal server error"}}}
            )

    except httpx.HTTPStatusError as e: 
        logger.exception(f"HTTPStatusError during RAG task creation for post SID {payload.post.sid}: {e.response.text if e.response else str(e)}")
        # Try to return RAGCoreJobCreationErrorResponse if possible from e.response.json()
        # For now, a generic message.
        detail_error = {"success": False, "error": {"code": 5031, "detail": {"message": f"External RAG service error: {str(e)}", "message_eng": "External RAG service error."}}}
        if e.response:
            try:
                detail_error = e.response.json()
            except json.JSONDecodeError: # If RAG error response is not JSON
                pass # Keep the generic message
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail_error)
    except httpx.RequestError as e: # Covers network errors, timeouts etc.
        logger.exception(f"httpx.RequestError during RAG task creation for post SID {payload.post.sid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail={"success": False, "error": {"code": 5032, "detail": {"message": f"External RAG service communication failed: {str(e)}", "message_eng": "RAG service communication failed."}}}
        )
    except Exception as e:
        logger.exception(f"Unexpected error during classification of post SID {payload.post.sid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"success": False, "error": {"code": 5001, "detail": {"message": f"An unexpected error occurred: {str(e)}", "message_eng": "Unexpected internal error."}}}
        )
