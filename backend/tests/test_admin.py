from fastapi.testclient import TestClient
from app.main import app 
import uuid

def test_admin_routes():
    """Test both GET and POST routes in a single session to keep the async connection open."""
    
    # The 'with' block keeps the event loop alive for everything inside it!
    with TestClient(app) as client:
        
        # 1. Test the GET route
        get_response = client.get("/admin/assessments")
        assert get_response.status_code == 200
        assert isinstance(get_response.json(), list)

        # 2. Test the POST route (Not Found scenario)
        fake_id = str(uuid.uuid4())
        payload = {
            "question_set_id": fake_id,
            "time_limit_min": 45
        }
        
        post_response = client.post("/admin/assessments", json=payload)
        assert post_response.status_code == 404
        assert post_response.json()["detail"] == "Question set not found"