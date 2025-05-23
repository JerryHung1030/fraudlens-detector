import json
import httpx # Using httpx for consistency, can also use requests if preferred for sync script
import asyncio # Required if using httpx.AsyncClient, or use synchronous httpx.Client
import logging
from typing import List, Dict, Any, Optional

# Assuming data_models.py is in app.models and accessible for Post structure
# If scripts are run as a module (e.g. python -m scripts.seed_posts),
# then app.models should be importable if PYTHONPATH is set correctly or if scamshield_ai_backend is installed.
# For simplicity in a standalone script, we might duplicate or simplify the Post model,
# or ensure the script is run in an environment where 'app' is discoverable.
# Let's try to import it assuming the script is run from the project root.
try:
    from app.models import Post, RAGCoreScenario # RAGCoreScenario for potential scenario options
    from pydantic import BaseModel # Required for the fallback Post model
except ImportError:
    # Fallback if 'app' is not in PYTHONPATH - define a simplified local model for the script's purpose
    # This is not ideal but can work for a standalone script.
    # Better: Ensure the script is run as part of the package or PYTHONPATH is set.
    # For now, the subtask should try to make the import work as if run from project root with `python -m scripts.seed_posts`
    # or `poetry run python scripts/seed_posts.py`
    logging.warning("Could not import Post from app.models. Using a local simplified definition if needed. Ensure PYTHONPATH is set or run with 'python -m'.")
    # Pydantic is a dependency of the main app, so it should be available if running in the same venv
    try:
        from pydantic import BaseModel
        class Post(BaseModel): # Requires pydantic to be available
            sid: str
            text: str
            metadata: Dict[str, Any] = {}

        class RAGCoreScenario(BaseModel): # Placeholder if import fails
            pass
    except ImportError:
        logging.error("Pydantic not found. Cannot define fallback models. Please ensure Pydantic is installed.")
        # If pydantic is not found, the script will likely fail later.
        # Define dummy classes to prevent immediate NameError
        class Post: pass
        class RAGCoreScenario: pass


# Configuration
API_BASE_URL = "http://localhost:8000/api/v1/classification" # Assuming default FastAPI port
# The POSTS_FILE_PATH should be relative to the project root, where the 'data' directory is.
# If running 'python scripts/seed_posts.py' from project root, 'data/example_posts_300.jsonl' is correct.
# If running 'python scamshield_ai_backend/scripts/seed_posts.py' from project root, then also correct.
# If running from within the 'scripts' directory, it would need to be '../data/...'
# Standard practice is to run scripts from project root.
POSTS_FILE_PATH = "data/example_posts_300.jsonl" 
# Fraud scenarios are loaded by the /classify endpoint, not directly by the seeder script.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_posts_from_file(path: str) -> List[Dict[str, Any]]:
    posts_data = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    posts_data.append(json.loads(line))
        logger.info(f"Successfully loaded {len(posts_data)} posts from {path}")
        return posts_data
    except FileNotFoundError:
        logger.error(f"Posts file not found: {path}. Please create it in the 'data' directory relative to the project root.")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from posts file: {path}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred loading posts: {e}")
        return []

async def send_post_to_classify_api(client: httpx.AsyncClient, post_data: Dict[str, Any], scenario_options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    # Construct the payload for the /api/v1/classification/classify endpoint
    # which expects {"post": Post, "scenario_options": RAGCoreScenario (optional)}
    
    payload = {
        "post": post_data 
    }
    if scenario_options:
        payload["scenario_options"] = scenario_options
        
    classify_url = f"{API_BASE_URL}/classify"
    logger.debug(f"Sending post SID {post_data.get('sid')} to {classify_url}")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = await client.post(classify_url, json=payload, timeout=60.0) # Increased timeout
        
        if response.status_code == 200: # Successful job creation by /classify
            logger.info(f"Successfully submitted post SID {post_data.get('sid')}. Response: {response.json()}")
            return response.json()
        else:
            logger.error(f"Error submitting post SID {post_data.get('sid')}. Status: {response.status_code}, Response: {response.text}")
            try:
                logger.error(f"Error details: {response.json()}") 
            except json.JSONDecodeError:
                pass 
            return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTPStatusError for post SID {post_data.get('sid')}: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e: # Covers network errors, timeouts etc.
        logger.error(f"RequestError for post SID {post_data.get('sid')}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending post SID {post_data.get('sid')}: {e}")
        return None

async def main():
    logger.info("Starting CLI Seeder Script...")
    
    import os
    # Ensure POSTS_FILE_PATH is interpreted from project root.
    # If script is in scamshield_ai_backend/scripts/ and data is in scamshield_ai_backend/data/
    # and CWD is scamshield_ai_backend/, then "data/example_posts_300.jsonl" is fine.
    
    # Check if the dummy file needs creation. This path is relative to where the script is run.
    # If running `python scripts/seed_posts.py` from project root, this path is correct.
    if not os.path.exists(POSTS_FILE_PATH):
        logger.warning(f"{POSTS_FILE_PATH} not found. Creating a dummy file for seeder execution.")
        # Ensure the 'data' directory exists relative to the project root.
        # os.path.dirname("data/example_posts_300.jsonl") is "data"
        os.makedirs(os.path.dirname(POSTS_FILE_PATH), exist_ok=True)
        dummy_posts = [
            {"sid": "post_dummy_001", "text": "This is a dummy post for seeder testing from script.", "metadata": {"author": "seeder_script", "timestamp": "2024-01-01T00:00:00Z", "source": "dummy_file"}},
            {"sid": "post_dummy_002", "text": "Another dummy post here, for testing.", "metadata": {"author": "seeder_script", "timestamp": "2024-01-01T00:01:00Z", "source": "dummy_file"}}
        ]
        with open(POSTS_FILE_PATH, "w", encoding="utf-8") as f:
            for post in dummy_posts:
                f.write(json.dumps(post) + "\n")
        logger.info(f"Created dummy posts file at {POSTS_FILE_PATH}")

    posts_to_seed = load_posts_from_file(POSTS_FILE_PATH)
    
    if not posts_to_seed:
        logger.warning("No posts loaded. Exiting seeder script.")
        return

    successful_submissions = 0
    failed_submissions = 0

    common_scenario_options = None 

    async with httpx.AsyncClient() as client:
        tasks = []
        for post_data in posts_to_seed:
            tasks.append(send_post_to_classify_api(client, post_data, scenario_options=common_scenario_options))
        
        results = await asyncio.gather(*tasks, return_exceptions=True) # Handle potential exceptions from send_post_to_classify_api
        
        for i, res_or_exc in enumerate(results):
            if isinstance(res_or_exc, Exception):
                logger.error(f"Task for post {posts_to_seed[i].get('sid', 'unknown_sid')} failed with exception: {res_or_exc}")
                failed_submissions +=1
            elif res_or_exc: # If it's not an exception, it's the response dict from the function
                successful_submissions += 1
            else: # If it's None (which send_post_to_classify_api returns on API error)
                failed_submissions += 1


    logger.info("Seeder script finished.")
    logger.info(f"Successful submissions: {successful_submissions}")
    logger.info(f"Failed submissions: {failed_submissions}")

if __name__ == "__main__":
    asyncio.run(main())
