from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

# --- RAGCore-X API Request Models ---

class RAGCoreScenario(BaseModel):
    direction: Optional[str] = "both"
    role_desc: Optional[str] = ""
    reference_desc: Optional[str] = ""
    input_desc: Optional[str] = ""
    rag_k: Optional[int] = 5
    rag_k_forward: Optional[int] = None
    rag_k_reverse: Optional[int] = None
    cof_threshold: Optional[float] = 0.5
    scoring_rule: Optional[str] = ""
    llm_name: Optional[str] = None
    # reference_depth, input_depth, chunk_size, max_prompt_tokens are omitted for now
    # as per initial project scope, but can be added if RAGCore-X requires them.

class RAGCoreDataItem(BaseModel):
    sid: str
    text: str
    metadata: Optional[Dict[str, Any]] = {}

class RAGCoreLevelData(BaseModel):
    level1: List[RAGCoreDataItem]

class RAGCoreRequest(BaseModel):
    project_id: str
    scenario: Optional[RAGCoreScenario] = Field(default_factory=RAGCoreScenario)
    input_data: RAGCoreLevelData
    reference_data: RAGCoreLevelData

# --- RAGCore-X API Response Models ---

class RAGCoreJobCreationResponse(BaseModel):
    job_id: str
    status: str # "pending", "successful", "fail" (based on spec, though "successful" seems unlikely for creation)
    created_at: str # Assuming ISO datetime string

class RAGCoreErrorDetail(BaseModel):
    message: str
    message_eng: str

class RAGCoreError(BaseModel):
    code: int
    detail: RAGCoreErrorDetail

class RAGCoreJobCreationErrorResponse(BaseModel):
    success: bool = False
    error: RAGCoreError

# Models for GET /api/v1/rag/{job_id}/status response
class RAGCorePrediction(BaseModel):
    input_uid: str
    input_text: str
    ref_uid: str
    ref_text: str
    evidences: List[str]
    start_end_idx: List[List[int]] # Assuming List of [start, end]
    confidence: float
    similarity_score: float

class RAGCoreResultDetail(BaseModel):
    direction: str
    root_uid: str
    model: str
    rag_k: int
    cof_threshold: float
    predictions: List[RAGCorePrediction]

class RAGCoreJobStatusResponse(BaseModel):
    job_id: str
    project_id: str
    status: str  # "pending", "completed", "fail"
    progress: float
    results: Optional[List[List[RAGCoreResultDetail]]] = None # Nested list structure from example
    error: Optional[Any] = None # Can be string or dict, use Any for now
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None

class RAGCoreJobStatusErrorResponse(BaseModel): # For errors like "Job not found"
    success: bool = False
    error: RAGCoreError

# Model for GET /api/v1/rag (list all tasks) - can reuse RAGCoreJobStatusResponse in a List
# For now, we are primarily concerned with single job status.
