import httpx
from typing import List, Union, Optional
from app.models import ( # Assuming models are accessible via app.models
    Post,
    FraudScenario,
    RAGCoreRequest,
    RAGCoreScenario,
    RAGCoreDataItem,
    RAGCoreLevelData,
    RAGCoreJobCreationResponse,
    RAGCoreJobCreationErrorResponse,
    RAGCoreJobStatusResponse,
    RAGCoreJobStatusErrorResponse,
)

# Configuration - In a real app, this would come from environment variables or a config file
RAG_CORE_API_BASE_URL = "http://localhost:8008/api/v1/rag" # Placeholder, real one TBD
RAG_CORE_PROJECT_ID = "scamshield_project" # Example project ID

class RAGCoreService:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.http_client = http_client if http_client else httpx.AsyncClient(timeout=30.0)
        self.base_url = RAG_CORE_API_BASE_URL
        self.project_id = RAG_CORE_PROJECT_ID

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> httpx.Response:
        try:
            response = await self.http_client.request(
                method, endpoint, json=json_data, params=params
            )
            response.raise_for_status() # Raise an exception for 4XX or 5XX status codes
            return response
        except httpx.HTTPStatusError as e:
            # Log error e.g., logging.error(f"HTTP error occurred: {e}")
            # For now, re-raise or return the error response to be handled by the caller
            if e.response:
                return e.response # Return the error response itself for parsing
            raise # Re-raise if there's no response object
        except httpx.RequestError as e:
            # Log error e.g., logging.error(f"Request error occurred: {e}")
            # Handle network errors, timeouts, etc.
            # For now, re-raise or create a custom error response
            raise # Re-raise for now

    async def create_rag_task(
        self, post_data: Post, reference_scenarios: List[FraudScenario], scenario_options: Optional[RAGCoreScenario] = None
    ) -> Union[RAGCoreJobCreationResponse, RAGCoreJobCreationErrorResponse]:
        
        input_items = [RAGCoreDataItem(sid=post_data.sid, text=post_data.text, metadata=post_data.metadata.model_dump(exclude_none=True))]
        reference_items = [
            RAGCoreDataItem(sid=scenario.sid, text=scenario.text, metadata=scenario.metadata.model_dump(exclude_none=True))
            for scenario in reference_scenarios
        ]

        rag_request_payload = RAGCoreRequest(
            project_id=self.project_id,
            scenario=scenario_options if scenario_options else RAGCoreScenario(), # Default scenario options
            input_data=RAGCoreLevelData(level1=input_items),
            reference_data=RAGCoreLevelData(level1=reference_items),
        )

        try:
            response = await self._make_request(
                method="POST",
                endpoint=self.base_url, # POST to /api/v1/rag
                json_data=rag_request_payload.model_dump(exclude_none=True),
            )

            if response.status_code == 200: # Assuming 200 for successful job submission based on spec's good case
                 # The spec shows 200 for job creation returning job_id, status, created_at.
                 # Let's assume the good case for POST /api/v1/rag is a 200 or 201 or 202.
                 # The provided spec for POST /api/v1/rag shows a response:
                 # { "job_id": "job_123", "status": "pending", "created_at": "..." }
                 # This implies a successful HTTP status (e.g. 200, 201, or 202).
                 # We will try to parse RAGCoreJobCreationResponse.
                return RAGCoreJobCreationResponse.model_validate(response.json())
            else:
                # Attempt to parse as a known error structure
                return RAGCoreJobCreationErrorResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e: # Raised by _make_request for 4xx/5xx if not handled there
             if e.response:
                return RAGCoreJobCreationErrorResponse.model_validate(e.response.json())
             # Handle cases where e.response might not be available or JSON is invalid
             # This part might need more robust error handling
             raise
        except Exception as e: # Catch-all for other errors like Pydantic validation, etc.
            # Log error: logging.error(f"Error creating RAG task: {e}")
            # Return a generic error or re-raise
            # For now, let's assume it might be a validation error if not HTTP error
            # This part needs to be more specific based on actual errors encountered
            raise


    async def get_rag_task_status(
        self, job_id: str
    ) -> Union[RAGCoreJobStatusResponse, RAGCoreJobStatusErrorResponse]:
        endpoint = f"{self.base_url}/{job_id}/status"
        try:
            response = await self._make_request(method="GET", endpoint=endpoint)

            if response.status_code == 200: # Assuming 200 for successful status retrieval
                return RAGCoreJobStatusResponse.model_validate(response.json())
            else:
                # Attempt to parse as a known error structure
                return RAGCoreJobStatusErrorResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response:
                 return RAGCoreJobStatusErrorResponse.model_validate(e.response.json())
            raise
        except Exception as e:
            # Log error
            raise

    async def close(self):
        await self.http_client.aclose()
