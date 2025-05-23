import pytest
import httpx
from pytest_httpx import HTTPXMock

from app.services import RAGCoreService
from app.models import Post, FraudScenario, RAGCoreJobCreationResponse, RAGCoreJobStatusResponse, RAGCoreJobCreationErrorResponse, RAGCoreJobStatusErrorResponse

@pytest.fixture
def post_example():
    return Post(sid="post_test_01", text="This is a test post content.", metadata={"author": "test_user"})

@pytest.fixture
def fraud_scenario_example():
    return FraudScenario(sid="fraud_test_01", text="This is a test fraud scenario.", metadata={"scenario": "phishing"})

@pytest.mark.asyncio
async def test_create_rag_task_success(httpx_mock: HTTPXMock, post_example, fraud_scenario_example):
    service = RAGCoreService()
    expected_response_json = {"job_id": "job_123", "status": "pending", "created_at": "2024-07-15T10:00:00Z"}
    
    httpx_mock.add_response(
        method="POST",
        url=service.base_url, 
        json=expected_response_json,
        status_code=200 
    )

    result = await service.create_rag_task(post_example, [fraud_scenario_example])
    await service.close()

    assert isinstance(result, RAGCoreJobCreationResponse)
    assert result.job_id == "job_123"
    assert result.status == "pending"

@pytest.mark.asyncio
async def test_create_rag_task_rag_api_error(httpx_mock: HTTPXMock, post_example, fraud_scenario_example):
    service = RAGCoreService()
    error_response_json = {
        "success": False, 
        "error": {"code": 4000, "detail": {"message": "請求資料格式不符合", "message_eng": "System problem"}}
    }
    
    httpx_mock.add_response(
        method="POST",
        url=service.base_url,
        json=error_response_json,
        status_code=400 
    )

    result = await service.create_rag_task(post_example, [fraud_scenario_example])
    await service.close()
    
    assert isinstance(result, RAGCoreJobCreationErrorResponse)
    assert result.success is False
    assert result.error.code == 4000

@pytest.mark.asyncio
async def test_get_rag_task_status_success(httpx_mock: HTTPXMock):
    service = RAGCoreService()
    job_id = "job_123"
    expected_status_json = {
        "job_id": job_id, "project_id": "scamshield_project", "status": "completed", "progress": 100.0,
        "results": [], "error": None, "created_at": "2024-07-15T10:00:00Z", 
        "updated_at": "2024-07-15T10:01:00Z", "completed_at": "2024-07-15T10:01:00Z"
    }
    
    httpx_mock.add_response(
        method="GET",
        url=f"{service.base_url}/{job_id}/status",
        json=expected_status_json,
        status_code=200
    )

    result = await service.get_rag_task_status(job_id)
    await service.close()

    assert isinstance(result, RAGCoreJobStatusResponse)
    assert result.status == "completed"
    assert result.job_id == job_id

@pytest.mark.asyncio
async def test_get_rag_task_status_job_not_found(httpx_mock: HTTPXMock):
    service = RAGCoreService()
    job_id = "job_unknown"
    error_response_json = {
        "success": False,
        "error": {"code": 1002, "detail": {"message": "任務不存在", "message_eng": "Job not found"}}
    }
    httpx_mock.add_response(
        method="GET",
        url=f"{service.base_url}/{job_id}/status",
        json=error_response_json,
        status_code=400 
    )

    result = await service.get_rag_task_status(job_id)
    await service.close()

    assert isinstance(result, RAGCoreJobStatusErrorResponse)
    assert result.success is False
    assert result.error.code == 1002

@pytest.mark.asyncio
async def test_create_rag_task_http_request_error(httpx_mock: HTTPXMock, post_example, fraud_scenario_example):
    service = RAGCoreService()
    httpx_mock.add_exception(httpx.RequestError("Network error"))

    with pytest.raises(httpx.RequestError): 
        await service.create_rag_task(post_example, [fraud_scenario_example])
    await service.close()
