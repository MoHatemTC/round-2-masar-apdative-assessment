from fastapi.testclient import TestClient
from app.main import app 
from app.routes import admin  # <-- We import your admin file directly!
import uuid

# --- FAKE DATABASE FOR CI TESTING ---
class DummyDB:
    def __init__(self):
        self.current_table = None
        self.is_failure_test = False 
        
    def table(self, name):
        self.current_table = name
        return self
        
    def select(self, *args): return self
    def eq(self, *args): return self
    def in_(self, *args): return self
    def insert(self, *args): return self
    
    async def execute(self):
        class Response: pass
        res = Response()
        
        if self.current_table == "question_set_items":
            # Return empty list if we are testing the failure path, otherwise return a fake question
            res.data = [] if self.is_failure_test else [{"question_id": "q123"}]
            
        elif self.current_table == "question_bank":
            res.data = [{"competency_id": "fake-competency-123"}]
            
        elif self.current_table == "assessments":
            # Return the fake assessment row
            res.data = [{
                "id": str(uuid.uuid4()), 
                "question_set_id": str(uuid.uuid4()),
                "competency_ids": ["fake-competency-123"],
                "time_limit_min": 30
            }]
        else:
            res.data = []
            
        return res

fake_db = DummyDB()

async def override_get_db():
    return fake_db

# THE MAGIC FIX: We forcefully overwrite the get_db function inside the admin file
admin.get_db = override_get_db

# --- SINGLE TEST SESSION ---
def test_all_admin_routes():
    """Run all tests in one session so the async event loop stays perfectly open."""
    with TestClient(app) as client:
        
        # 1. Test GET route
        get_res = client.get("/admin/assessments")
        assert get_res.status_code == 200
        
        # 2. Test POST route (Failure Path: 404)
        fake_db.is_failure_test = True # Flip the switch to test the error
        fail_payload = {"title": "Bad Assessment", "question_set_id": str(uuid.uuid4()), "time_limit_min": 45}
        fail_res = client.post("/admin/assessments", json=fail_payload)
        assert fail_res.status_code == 404
        
        # 3. Test POST route (Success Path: 200)
        fake_db.is_failure_test = False # Flip the switch back for a success
        success_payload = {"title": "Good Assessment", "question_set_id": str(uuid.uuid4()), "time_limit_min": 30}
        success_res = client.post("/admin/assessments", json=success_payload)
        
        assert success_res.status_code == 200
        assert "fake-competency-123" in success_res.json()["competency_ids"]