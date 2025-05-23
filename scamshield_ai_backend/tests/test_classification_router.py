import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock 
import os # For file operations in fixture
import httpx # For the httpx.RequestError

from app.main import app 
from app.services import RAGCoreService # For dependency override
from app.models import RAGCoreJobCreationResponse, RAGCoreJobCreationErrorResponse, RAGCoreError, RAGCoreErrorDetail

client = TestClient(app)

DUMMY_FRAUD_SCENARIOS_PATH = "tests/test_data/dummy_fraud_scenarios_for_classify_route.jsonl"

@pytest.fixture(scope="function", autouse=True) # Changed to function scope for cleaner test isolation
def manage_dummy_fraud_scenarios_for_classify(request):
    # This fixture manages the dummy fraud scenarios file for tests in this module.
    # It also handles patching the path and clearing the cache in the router.
    
    # Ensure test_data directory exists
    os.makedirs(os.path.dirname(DUMMY_FRAUD_SCENARIOS_PATH), exist_ok=True)

    # Default: create a valid scenarios file
    create_scenarios = True
    if hasattr(request, 'param') and request.param == "no_scenarios_file":
        if os.path.exists(DUMMY_FRAUD_SCENARIOS_PATH): # Ensure it's not there
             os.remove(DUMMY_FRAUD_SCENARIOS_PATH)
        create_scenarios = False
    elif hasattr(request, 'param') and request.param == "empty_scenarios_file":
        with open(DUMMY_FRAUD_SCENARIOS_PATH, "w") as f: # create empty file
            pass
        create_scenarios = False # File created empty, no need to write defaults

    if create_scenarios:
        with open(DUMMY_FRAUD_SCENARIOS_PATH, "w") as f:
            f.write('{"sid": "fs_dummy_classify_01", "text": "Dummy scenario classify 1", "metadata": {}}\n')
            f.write('{"sid": "fs_dummy_classify_02", "text": "Dummy scenario classify 2", "metadata": {}}\n')

    # Patch the path and cache in the router module
    # The classification_router.py uses a global _fraud_scenarios_cache list.
    with patch('app.routes.classification_router.FRAUD_SCENARIOS_FILE_PATH', DUMMY_FRAUD_SCENARIOS_PATH), \
         patch('app.routes.classification_router._fraud_scenarios_cache', []):
        yield

    # Teardown: remove dummy file if it exists
    if os.path.exists(DUMMY_FRAUD_SCENARIOS_PATH):
        os.remove(DUMMY_FRAUD_SCENARIOS_PATH)
    # Note: Not removing tests/test_data directory in case other tests use it.

def test_classify_post_success():
    mock_rag_service_instance = AsyncMock(spec=RAGCoreService)
    mock_rag_service_instance.create_rag_task.return_value = RAGCoreJobCreationResponse(
        job_id="job_success_123", status="pending", created_at="2024-01-01T12:00:00Z"
    )
    
    # It's important to reset dependency_overrides after the test.
    # Using a try/finally or a context manager for this is safer.
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[RAGCoreService] = lambda: mock_rag_service_instance
    try:
        payload = {
            "post": {"sid": "test_sid_001", "text": "This is a test post.", "metadata": {"author": "pytest"}}
        }
        response = client.post("/api/v1/classification/classify", json=payload)
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["job_id"] == "job_success_123"
    finally:
        app.dependency_overrides = original_overrides


def test_classify_post_rag_service_returns_error():
    mock_rag_service_instance = AsyncMock(spec=RAGCoreService)
    mock_rag_service_instance.create_rag_task.return_value = RAGCoreJobCreationErrorResponse(
        success=False,
        error=RAGCoreError(code=4000, detail=RAGCoreErrorDetail(message="Test RAG Error", message_eng="Test RAG Error ENG"))
    )
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[RAGCoreService] = lambda: mock_rag_service_instance
    try:
        payload = {"post": {"sid": "test_sid_002", "text": "Another post.", "metadata": {}}}
        response = client.post("/api/v1/classification/classify", json=payload)

        assert response.status_code == 400 
        json_response = response.json()
        assert json_response["error"]["code"] == 4000
    finally:
        app.dependency_overrides = original_overrides

@pytest.mark.parametrize("manage_dummy_fraud_scenarios_for_classify", ["no_scenarios_file"], indirect=True)
def test_classify_post_missing_fraud_scenarios_file(manage_dummy_fraud_scenarios_for_classify):
    # The fixture will ensure the scenarios file does not exist for this test.
    payload = {"post": {"sid": "test_sid_003", "text": "Post needing scenarios.", "metadata": {}}}
    response = client.post("/api/v1/classification/classify", json=payload)
    assert response.status_code == 503 
    json_response = response.json()
    assert "Fraud scenarios could not be loaded" in json_response["detail"]["error"]["detail"]["message"]

@pytest.mark.parametrize("manage_dummy_fraud_scenarios_for_classify", ["empty_scenarios_file"], indirect=True)
def test_classify_post_empty_fraud_scenarios_file(manage_dummy_fraud_scenarios_for_classify):
    # The fixture will ensure the scenarios file is empty for this test.
    payload = {"post": {"sid": "test_sid_003b", "text": "Post needing scenarios from empty file.", "metadata": {}}}
    response = client.post("/api/v1/classification/classify", json=payload)
    # If file is empty, load_fraud_scenarios returns empty list, which also leads to 503
    assert response.status_code == 503 
    json_response = response.json()
    # The error message in the code is "No fraud scenarios loaded. Cannot proceed with classification."
    # The detail message in the HTTP response is "Fraud scenarios unavailable."
    assert "Fraud scenarios unavailable" in json_response["detail"]["error"]["detail"]["message_eng"]


def test_classify_post_invalid_payload():
    response = client.post("/api/v1/classification/classify", json={"text": "wrong payload"}) # Missing 'post' field
    assert response.status_code == 422 

# Patching the RAGCoreService dependency directly for this specific test case
# This avoids global state modification of app.dependency_overrides if not careful
@patch('app.routes.classification_router.get_rag_core_service')
def test_classify_post_rag_service_raises_httpx_request_error(mock_get_service):
    mock_service_instance = AsyncMock(spec=RAGCoreService)
    mock_service_instance.create_rag_task.side_effect = httpx.RequestError("Simulated network error", request=None)
    mock_service_instance.close = AsyncMock() # ensure close is also an async mock
    
    # Make the dependency injector return our mocked instance
    async def override_get_rag_core_service():
        try:
            yield mock_service_instance
        finally:
            await mock_service_instance.close()

    app.dependency_overrides[app.routes.classification_router.get_rag_core_service] = override_get_rag_core_service
    
    try:
        payload = {"post": {"sid": "test_sid_004", "text": "A post that will trigger network error.", "metadata": {}}}
        response = client.post("/api/v1/classification/classify", json=payload)
        
        assert response.status_code == 503
        json_response = response.json()
        assert "RAG service communication failed" in json_response["detail"]["error"]["detail"]["message_eng"]
    finally:
        app.dependency_overrides.pop(app.routes.classification_router.get_rag_core_service, None)
