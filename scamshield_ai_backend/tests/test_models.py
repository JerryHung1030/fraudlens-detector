import pytest
from pydantic import ValidationError

from app.models import (
    Post, PostMetadata, FraudScenario, FraudScenarioMetadata,
    RAGCoreRequest, RAGCoreLevelData, RAGCoreDataItem, RAGCoreScenario,
    RAGCoreJobCreationResponse, RAGCoreJobStatusResponse, RAGCorePrediction, RAGCoreResultDetail
)

def test_post_creation():
    data = {"sid": "post1", "text": "Hello world", "metadata": {"author": "test"}}
    post = Post(**data)
    assert post.sid == "post1"
    assert post.text == "Hello world"
    assert post.metadata.author == "test"
    assert post.model_dump()["metadata"]["author"] == "test"

def test_fraud_scenario_creation():
    data = {"sid": "fs1", "text": "Fraud text", "metadata": {"scenario": "phishing"}}
    fs = FraudScenario(**data)
    assert fs.sid == "fs1"
    assert fs.metadata.scenario == "phishing"

def test_rag_core_request_creation():
    req_data = {
        "project_id": "proj1",
        "input_data": {"level1": [{"sid": "in1", "text": "input"}]},
        "reference_data": {"level1": [{"sid": "ref1", "text": "reference"}]}
    }
    req = RAGCoreRequest(**req_data)
    assert req.project_id == "proj1"
    assert req.input_data.level1[0].sid == "in1"
    assert req.scenario.direction == "both" # Check default

def test_rag_core_job_creation_response():
    data = {"job_id": "job123", "status": "pending", "created_at": "2024-01-01T00:00:00Z"}
    resp = RAGCoreJobCreationResponse(**data)
    assert resp.job_id == "job123"
    assert resp.status == "pending"

def test_rag_core_job_status_response_completed():
    data = {
        "job_id": "job123", "project_id": "proj1", "status": "completed", "progress": 100.0,
        "results": [[{
            "direction": "both", "root_uid": "input-abc", "model": "openai", "rag_k": 1, "cof_threshold": 0.5,
            "predictions": [{
                "input_uid": "user_query", "input_text": "text_in", "ref_uid": "ref_query", "ref_text": "text_ref",
                "evidences": ["evidence"], "start_end_idx": [[0,1]], "confidence": 0.9, "similarity_score": 0.89
            }]
        }]],
        "error": None, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:01:00Z",
        "completed_at": "2024-01-01T00:01:00Z"
    }
    resp = RAGCoreJobStatusResponse(**data)
    assert resp.status == "completed"
    assert resp.results[0][0].predictions[0].confidence == 0.9

# Example of a validation test (if Post had a required field without default that is not 'sid')
# def test_post_missing_required_field():
#     with pytest.raises(ValidationError):
#         Post(sid="post_sid_only") # Assuming 'text' is required and has no default
