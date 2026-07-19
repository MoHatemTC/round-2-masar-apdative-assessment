from fastapi.testclient import TestClient
from app.main import app
from app.routes import admin
import uuid


SUB_ID = "550e8400-e29b-41d4-a716-446655440000"
TRACK_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


class DummyDB:
    def __init__(self):
        self.current_table = None
        self.is_failure_test = False
        self.inserted = None

    def table(self, name):
        self.current_table = name
        return self

    def select(self, *args):
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

        if self.current_table == "question_set_items":
            res.data = (
                []
                if self.is_failure_test
                else [{"question_id": "q123"}]
            )

        elif self.current_table == "question_bank":
            res.data = [
                {"competency_id": SUB_ID}
            ]

        elif self.current_table == "competencies":
            res.data = [
                {"parent_id": TRACK_ID}
            ]

        elif self.current_table == "assessments":
            res.data = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Good Assessment",
                    "question_set_id": str(uuid.uuid4()),
                    "competency_ids": [TRACK_ID],
                    "time_limit_min": 30,
                }
            ]

        else:
            res.data = []

        return res


fake_db = DummyDB()


async def override_get_db():
    return fake_db


admin.get_db = override_get_db


def test_all_admin_routes():
    """Run all admin route tests in one session."""

    with TestClient(app) as client:

        # 1. Test GET /admin/assessments
        get_res = client.get("/admin/assessments")
        assert get_res.status_code == 200

        # 2. Test POST /admin/assessments - failure path
        fake_db.is_failure_test = True

        fail_payload = {
            "title": "Bad Assessment",
            "question_set_id": str(uuid.uuid4()),
            "time_limit_min": 45,
        }

        fail_res = client.post(
            "/admin/assessments",
            json=fail_payload,
        )

        assert fail_res.status_code == 404

        # 3. Test POST /admin/assessments - success path
        fake_db.is_failure_test = False

        success_payload = {
            "title": "Good Assessment",
            "question_set_id": str(uuid.uuid4()),
            "time_limit_min": 30,
        }

        success_res = client.post(
            "/admin/assessments",
            json=success_payload,
        )

        assert success_res.status_code == 200
        assert fake_db.inserted["title"] == "Good Assessment"
        assert TRACK_ID in success_res.json()["competency_ids"]
