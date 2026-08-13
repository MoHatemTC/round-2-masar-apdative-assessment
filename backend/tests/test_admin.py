from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
import uuid

SUB_ID = "550e8400-e29b-41d4-a716-446655440000"
TRACK_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

class DummyDB:
    def __init__(self):
        self.current_table = None
        self.is_failure_test = False
        self.inserted = None
        self.mock_invitations = []
        self.mock_sessions = []

    def table(self, name):
        self.current_table = name
        return self

    def select(self, *args, count: str = None, **kwargs):
        self.count = 100
        return self

    def limit(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def eq(self, *args):
        return self

    def in_(self, *args):
        return self

    def insert(self, data):
        self.inserted = data
        return self

    async def execute(self):
        class Response:
            pass

        res = Response()
        res.count = getattr(self, "count", None)

        if self.current_table == "question_set_items":
            res.data = [] if self.is_failure_test else [{"question_id": "q123"}]
        elif self.current_table == "question_bank":
            res.data = [{"competency_id": SUB_ID}]
        elif self.current_table == "competencies":
            res.data = [{"parent_id": TRACK_ID}]
        elif self.current_table == "assessments":
            if self.inserted is not None:
                res.data = [{"id": str(uuid.uuid4()), **self.inserted}]
            else:
                res.data = []
        elif self.current_table == "invitations":
            if self.inserted is not None:
                res.data = [{"id": str(uuid.uuid4()), **self.inserted}]
                self.inserted = None
            else:
                res.data = self.mock_invitations
        elif self.current_table == "sessions":
            res.data = self.mock_sessions
        else:
            res.data = []

        return res

fake_db = DummyDB()

async def override_get_db():
    return fake_db

def test_all_admin_routes():
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            get_res = client.get("/admin/assessments")
            assert get_res.status_code == 200

            fake_db.is_failure_test = True
            fail_payload = {
                "title": "Bad Assessment",
                "question_set_id": str(uuid.uuid4()),
                "time_limit_min": 45,
            }
            fail_res = client.post("/admin/assessments", json=fail_payload)
            assert fail_res.status_code == 404

            fake_db.is_failure_test = False
            success_payload = {
                "title": "Good Assessment",
                "question_set_id": str(uuid.uuid4()),
                "time_limit_min": 30,
            }
            success_res = client.post("/admin/assessments", json=success_payload)
            assert success_res.status_code == 200
            assert fake_db.inserted["title"] == "Good Assessment"
            assert SUB_ID in success_res.json()["competency_ids"]

            fake_db.inserted = None
            invalid_email_payload = {
                "assessment_id": str(uuid.uuid4()),
                "candidate_email": "not-an-email"
            }
            invalid_res = client.post("/admin/invitations", json=invalid_email_payload)
            assert invalid_res.status_code == 422

            assessment_id = str(uuid.uuid4())
            dup_email = "test@example.com"
            fake_db.mock_invitations = [{"id": str(uuid.uuid4()), "token": "existing-token", "candidate_email": dup_email, "assessment_id": assessment_id}]

            dup_payload = {
                "assessment_id": assessment_id,
                "candidate_email": dup_email
            }
            dup_res = client.post("/admin/invitations", json=dup_payload)
            assert dup_res.status_code == 200
            assert dup_res.json()["token"] == "existing-token"

            fake_db.mock_invitations = [
                {"id": "inv1", "candidate_email": "user1@example.com", "assessment_id": assessment_id},
                {"id": "inv2", "candidate_email": "user2@example.com", "assessment_id": assessment_id},
                {"id": "inv3", "candidate_email": "user3@example.com", "assessment_id": assessment_id}
            ]
            fake_db.mock_sessions = [
                {"id": "sess1", "candidate_email": "user2@example.com", "status": "in_progress"},
                {"id": "sess2", "candidate_email": "user3@example.com", "status": "completed"}
            ]
            fake_db.inserted = None
            list_res = client.get(f"/admin/assessments/{assessment_id}/invitations")
            assert list_res.status_code == 200
            items = list_res.json()["data"]
            assert len(items) == 3

            status_map = {item["candidate_email"]: item["status"] for item in items}
            assert status_map["user1@example.com"] == "not_taken"
            assert status_map["user2@example.com"] == "in_progress"
            assert status_map["user3@example.com"] == "taken"

            session_map = {item["candidate_email"]: item.get("session_id") for item in items}
            assert session_map["user1@example.com"] is None
            assert session_map["user2@example.com"] == "sess1"
            assert session_map["user3@example.com"] == "sess2"

    finally:
        app.dependency_overrides.pop(get_db, None)