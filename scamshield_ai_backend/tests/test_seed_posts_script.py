import pytest
import json
from unittest.mock import patch, mock_open, AsyncMock, MagicMock
import httpx # For MagicMock spec for response
import os # For path operations

# Assuming SCRIPT_PATH and DUMMY_POSTS_FOR_SCRIPT_TEST_PATH are defined correctly
# This requires 'scripts' to be discoverable.
# If running tests with `pytest` from project root, and scripts is a dir in root,
# then `from scripts import seed_posts` should work if `scamshield_ai_backend` is in PYTHONPATH
# or if `scamshield_ai_backend/scripts` is also in PYTHONPATH.
# For poetry, if the project is structured as a package, it should handle this.
# Let's assume the path is set up correctly for the test execution environment.
from scripts import seed_posts 

# Path for dummy posts file used by this test module
DUMMY_POSTS_FOR_SCRIPT_TEST_PATH = "tests/test_data/dummy_script_posts_for_test.jsonl"

@pytest.fixture(scope="module", autouse=True)
def setup_dummy_posts_for_script_module_level(): # Renamed to avoid conflict if other test files use similar fixture names
    # Ensure the test_data directory exists
    os.makedirs(os.path.dirname(DUMMY_POSTS_FOR_SCRIPT_TEST_PATH), exist_ok=True)
    
    dummy_data = [
        {"sid": "script_post_module_001", "text": "Post 1 for script test from module fixture", "metadata": {}},
        {"sid": "script_post_module_002", "text": "Post 2 for script test from module fixture", "metadata": {}},
    ]
    with open(DUMMY_POSTS_FOR_SCRIPT_TEST_PATH, "w") as f:
        for item in dummy_data:
            f.write(json.dumps(item) + '\n')
    yield
    # Teardown: remove the dummy file after all tests in this module run
    if os.path.exists(DUMMY_POSTS_FOR_SCRIPT_TEST_PATH):
        os.remove(DUMMY_POSTS_FOR_SCRIPT_TEST_PATH)

@pytest.mark.asyncio
@patch('scripts.seed_posts.httpx.AsyncClient') 
async def test_seed_posts_main_logic_with_actual_file_loading(MockAsyncClient):
    mock_post_method = AsyncMock()
    # Simulate a successful response from the API
    mock_post_method.return_value = MagicMock(spec=httpx.Response, status_code=200, json=lambda: {"job_id": "mock_job_123", "status": "pending"})
    
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = mock_post_method
    # __aenter__ is what's called when entering an 'async with' block
    MockAsyncClient.return_value.__aenter__.return_value = mock_async_client_instance

    # Patch the POSTS_FILE_PATH in seed_posts to use our test-specific dummy file
    # And also patch os.path.exists to control the dummy file creation logic within seed_posts.main
    with patch('scripts.seed_posts.POSTS_FILE_PATH', DUMMY_POSTS_FOR_SCRIPT_TEST_PATH), \
         patch('scripts.seed_posts.os.path.exists') as mock_path_exists:
        
        # Let's say the file *does* exist for this test run of main()
        mock_path_exists.return_value = True 
        
        await seed_posts.main() 

    # The dummy file created by setup_dummy_posts_for_script_module_level has 2 posts
    assert mock_post_method.call_count == 2 
    expected_url = f"{seed_posts.API_BASE_URL}/classify"
    
    # Check the first call's details as an example
    actual_call = mock_post_method.call_args_list[0]
    assert actual_call[0][0] == expected_url 
    sent_payload = actual_call[1]['json'] 
    assert sent_payload['post']['sid'] == "script_post_module_001"


@pytest.mark.asyncio
@patch('scripts.seed_posts.httpx.AsyncClient') 
@patch('scripts.seed_posts.os.makedirs') # Mock makedirs as it might be called
@patch('scripts.seed_posts.open', new_callable=mock_open) # Mock open to control file writing
async def test_seed_posts_main_logic_creates_dummy_file_if_not_exists(mock_file_open_for_write, mock_makedirs, MockAsyncClient):
    mock_post_method = AsyncMock()
    mock_post_method.return_value = MagicMock(spec=httpx.Response, status_code=200, json=lambda: {"job_id": "mock_job_dummy", "status": "pending"})
    
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = mock_post_method
    MockAsyncClient.return_value.__aenter__.return_value = mock_async_client_instance

    # Patch POSTS_FILE_PATH and os.path.exists to simulate file not existing
    with patch('scripts.seed_posts.POSTS_FILE_PATH', "data/non_existent_for_main_test.jsonl"), \
         patch('scripts.seed_posts.os.path.exists', return_value=False) as mock_path_exists:
        
        await seed_posts.main()

    # Check that os.path.exists was called to check for the file
    mock_path_exists.assert_called_with("data/non_existent_for_main_test.jsonl")
    # Check that os.makedirs was called for the 'data' directory
    mock_makedirs.assert_called_with(os.path.dirname("data/non_existent_for_main_test.jsonl"), exist_ok=True)
    # Check that 'open' was called to write the dummy posts
    mock_file_open_for_write.assert_called_with("data/non_existent_for_main_test.jsonl", "w", encoding="utf-8")
    
    # The dummy creation logic in seed_posts.py writes 2 posts
    assert mock_post_method.call_count == 2 
    sent_payload_1 = mock_post_method.call_args_list[0][1]['json']
    assert sent_payload_1['post']['sid'] == "post_dummy_001" # From seed_posts.py's internal dummy data


def test_load_posts_from_file_success_in_script_module():
    # Test the utility function from the script module directly
    # Patch 'open' within the context of the 'scripts.seed_posts' module
    m = mock_open(read_data='{"sid": "p1_script", "text": "t1_script"}\n{"sid": "p2_script", "text": "t2_script"}')
    with patch("scripts.seed_posts.open", m) as mock_file_open_func:
        posts = seed_posts.load_posts_from_file("dummy/path_in_script.jsonl")
        assert len(posts) == 2
        assert posts[0]['sid'] == "p1_script"
        mock_file_open_func.assert_called_once_with("dummy/path_in_script.jsonl", "r", encoding="utf-8")

def test_load_posts_from_file_not_found_in_script_module():
    # Patch 'open' specifically for the seed_posts module
    with patch("scripts.seed_posts.open", side_effect=FileNotFoundError) as mock_file_open_func:
        posts = seed_posts.load_posts_from_file("nonexistent/path_in_script.jsonl")
        assert len(posts) == 0
        mock_file_open_func.assert_called_once_with("nonexistent/path_in_script.jsonl", "r", encoding="utf-8")

def test_load_posts_from_file_json_decode_error_in_script_module():
    m = mock_open(read_data='{"sid": "p1_script", "text": "t1_script"\nMALFORMED_JSON') # Malformed line
    with patch("scripts.seed_posts.open", m) as mock_file_open_func:
        posts = seed_posts.load_posts_from_file("dummy/malformed.jsonl")
        assert len(posts) == 0 # Should return empty list on decode error
        mock_file_open_func.assert_called_once_with("dummy/malformed.jsonl", "r", encoding="utf-8")
