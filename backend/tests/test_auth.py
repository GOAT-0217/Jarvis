import sys
from pathlib import Path

# Ensure the backend package is on sys.path so that imports work whether
# pytest is invoked from the repo root or from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import create_app
from core.database import SessionLocal
from core.security import get_password_hash
from models import User

app = create_app()
client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    db.query(User).filter(User.username.in_(["test_user", "test_kadmin", "test_sadmin"])).delete()
    db.commit()
    db.close()
    yield

def _create_user(username: str, role: str):
    db = SessionLocal()
    user = User(username=username, password_hash=get_password_hash("test123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

def _login(client, username: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": "test123"})

def test_login_success():
    _create_user("test_user", "user")
    resp = _login(client, "test_user")
    assert resp.status_code == 200
    assert resp.json()["access_token"] is not None

def test_login_wrong_password():
    _create_user("test_user", "user")
    resp = client.post("/api/v1/auth/login", json={"username": "test_user", "password": "wrong"})
    assert resp.status_code == 401

def test_me_requires_auth():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)

def test_knowledge_admin_access():
    _create_user("test_kadmin", "knowledge_admin")
    token = _login(client, "test_kadmin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "knowledge_admin"

def test_user_cannot_access_admin():
    _create_user("test_user", "user")
    token = _login(client, "test_user").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403
