import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app import app

client = TestClient(app)


def test_teacher_login_and_role():
    response = client.post("/login", json={"username": "teacher", "password": "teacher123"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "teacher"
    assert body["username"] == "teacher"


def test_student_signup_requires_authentication():
    response = client.post("/activities/Chess Club/signup?email=student1@mergington.edu")
    assert response.status_code == 401


def test_teacher_can_unregister_student():
    teacher_login = client.post("/login", json={"username": "teacher", "password": "teacher123"})
    token = teacher_login.json()["token"]
    email = "teacher-managed-student@mergington.edu"

    signup = client.post(
        f"/activities/Chess Club/signup?email={email}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert signup.status_code == 200

    unregister = client.delete(
        f"/activities/Chess Club/unregister?email={email}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unregister.status_code == 200
    assert email not in client.get("/activities").json()["Chess Club"]["participants"]
