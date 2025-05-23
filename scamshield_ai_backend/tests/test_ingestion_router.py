from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)

def test_ingest_data_placeholder():
    payload = {
        "source": "test_source",
        "data": {"key": "value", "items": [1, 2, 3]}
    }
    response = client.post("/api/v1/ingestion/ingest", json=payload)
    
    assert response.status_code == 501 
    json_response = response.json()
    assert "Ingestion endpoint is a placeholder" in json_response["message"]
    assert json_response["received_source"] == "test_source"
