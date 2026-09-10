"""
High School Management System API

A FastAPI app that allows students to view and sign up for extracurricular
activities at Mergington High School, while also supporting teacher/admin
access for managing registrations.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

BASE_DIR = Path(__file__).resolve().parent
AUTH_FILE = BASE_DIR / "teachers.json"


def _default_teachers() -> dict[str, Any]:
    return {
        "teachers": [
            {"username": "teacher", "password": "teacher123"},
            {"username": "admin", "password": "admin123"},
        ]
    }


def load_teachers() -> list[dict[str, str]]:
    if not AUTH_FILE.exists():
        AUTH_FILE.write_text(json.dumps(_default_teachers(), indent=2))

    try:
        data = json.loads(AUTH_FILE.read_text())
    except json.JSONDecodeError:
        data = _default_teachers()

    teachers = data.get("teachers", [])
    if not teachers:
        teachers = _default_teachers()["teachers"]
        AUTH_FILE.write_text(json.dumps({"teachers": teachers}, indent=2))
    return teachers


def is_teacher(username: str) -> bool:
    return any(t.get("username") == username for t in load_teachers())


def authenticate_user(username: str, password: str) -> str | None:
    username = (username or "").strip()
    password = (password or "").strip()

    for teacher in load_teachers():
        if teacher.get("username") == username and teacher.get("password") == password:
            return "teacher"

    if "@" in username and password == username:
        return "student"

    return None


SESSIONS: dict[str, str] = {}


def resolve_token(authorization: str | None = None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


class LoginRequest(BaseModel):
    username: str
    password: str


# Mount the static files directory
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(Path(__file__).parent, "static")),
    name="static",
)

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/login")
def login(payload: LoginRequest):
    role = authenticate_user(payload.username, payload.password)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(16)
    SESSIONS[token] = payload.username
    return {"token": token, "username": payload.username, "role": role}


@app.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    if token:
        SESSIONS.pop(token, None)
    return {"message": "Logged out successfully"}


@app.get("/auth/status")
def auth_status(authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    if not token:
        return {"authenticated": False, "role": "guest", "username": None}

    username = SESSIONS.get(token)
    if not username:
        return {"authenticated": False, "role": "guest", "username": None}

    role = "teacher" if is_teacher(username) else "student"
    return {"authenticated": True, "role": role, "username": username}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    authorization: str | None = Header(default=None),
):
    """Sign up a student for an activity."""
    token = resolve_token(authorization)
    if not token or SESSIONS.get(token) is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    username = SESSIONS[token]
    role = "teacher" if is_teacher(username) else "student"
    if role == "student" and username != email:
        raise HTTPException(status_code=403, detail="Students can only sign up themselves")

    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]
    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    authorization: str | None = Header(default=None),
):
    """Unregister a student from an activity."""
    token = resolve_token(authorization)
    if not token or SESSIONS.get(token) is None:
        raise HTTPException(status_code=403, detail="Only teachers can register and unregister students")

    username = SESSIONS[token]
    if not is_teacher(username):
        raise HTTPException(status_code=403, detail="Only teachers can register and unregister students")

    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]
    if email not in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
