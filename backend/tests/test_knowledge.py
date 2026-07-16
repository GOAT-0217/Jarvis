"""Tests for knowledge management APIs — documents, categories, tags."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app import create_app
from core.database import SessionLocal
from core.security import get_password_hash
from models import User, Category, Tag, Document, AuditLog

app = create_app()
client = TestClient(app)

TEST_USER = "test_knowledge_user"
TEST_USER_REGULAR = "test_knowledge_regular"
TEST_PW = "test123"


@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    # Delete audit logs for test users first (FK references)
    for username in (TEST_USER, TEST_USER_REGULAR):
        user = db.query(User).filter(User.username == username).first()
        if user:
            db.query(AuditLog).filter(AuditLog.user_id == user.id).delete()
    # Now delete test documents, categories, tags
    db.query(Document).filter(Document.filename.like("test_%")).delete()
    db.query(Category).filter(Category.name.like("test_%")).delete()
    db.query(Tag).filter(Tag.name.like("test_%")).delete()
    # Finally delete test users
    db.query(User).filter(User.username.in_([TEST_USER, TEST_USER_REGULAR])).delete()
    db.commit()
    db.close()
    yield


def _ensure_user() -> str:
    """Create a knowledge_admin user and return the auth token."""
    db = SessionLocal()
    existing = db.query(User).filter(User.username == TEST_USER).first()
    if not existing:
        user = User(username=TEST_USER, password_hash=get_password_hash(TEST_PW), role="knowledge_admin")
        db.add(user)
        db.commit()
    db.close()
    resp = client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": TEST_PW})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _headers() -> dict:
    token = _ensure_user()
    return {"Authorization": f"Bearer {token}"}


# ── Categories ────────────────────────────────────────────────────────────────

def test_list_categories_empty():
    resp = client.get("/api/v1/knowledge/categories", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


def test_create_and_list_category():
    h = _headers()
    resp = client.post("/api/v1/knowledge/categories", json={"name": "test_cat_1", "sort_order": 1}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "test_cat_1"

    cat_id = data["data"]["id"]
    resp = client.get("/api/v1/knowledge/categories", headers=h)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["data"]]
    assert "test_cat_1" in names

    return cat_id


def test_update_category():
    cat_id = test_create_and_list_category()
    h = _headers()
    resp = client.put(f"/api/v1/knowledge/categories/{cat_id}", json={"name": "test_cat_updated"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "test_cat_updated"


def test_delete_category():
    cat_id = test_create_and_list_category()
    h = _headers()
    resp = client.delete(f"/api/v1/knowledge/categories/{cat_id}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ── Tags ──────────────────────────────────────────────────────────────────────

def test_list_tags_empty():
    resp = client.get("/api/v1/knowledge/tags", headers=_headers())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_create_and_list_tag():
    h = _headers()
    resp = client.post("/api/v1/knowledge/tags", json={"name": "test_tag_1", "color": "#FF0000"}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "test_tag_1"
    assert data["data"]["color"] == "#FF0000"

    tag_id = data["data"]["id"]
    resp = client.get("/api/v1/knowledge/tags", headers=h)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()["data"]]
    assert "test_tag_1" in names

    return tag_id


def test_delete_tag():
    tag_id = test_create_and_list_tag()
    h = _headers()
    resp = client.delete(f"/api/v1/knowledge/tags/{tag_id}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ── Documents ─────────────────────────────────────────────────────────────────

def test_list_documents_empty():
    resp = client.get("/api/v1/knowledge/documents", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "items" in data["data"]


def test_upload_rejects_empty_filename():
    resp = client.post(
        "/api/v1/knowledge/documents/upload",
        headers=_headers(),
        files={"file": ("", b"content", "application/octet-stream")},
    )
    assert resp.status_code in (400, 422)  # 422 if FastAPI validation rejects empty filename first


def test_upload_rejects_unsupported_filetype():
    resp = client.post(
        "/api/v1/knowledge/documents/upload",
        headers=_headers(),
        files={"file": ("test.exe", b"malware", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_delete_nonexistent_document():
    resp = client.delete("/api/v1/knowledge/documents/nonexistent-id", headers=_headers())
    assert resp.status_code == 404


def test_reindex_nonexistent_document():
    resp = client.post("/api/v1/knowledge/documents/nonexistent-id/reindex", headers=_headers())
    assert resp.status_code == 404


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_requires_auth():
    resp = client.get("/api/v1/knowledge/documents")
    assert resp.status_code == 401


def test_requires_knowledge_admin():
    db = SessionLocal()
    user = User(username=TEST_USER_REGULAR, password_hash=get_password_hash(TEST_PW), role="user")
    db.add(user)
    db.commit()
    db.close()

    resp = client.post("/api/v1/auth/login", json={"username": TEST_USER_REGULAR, "password": TEST_PW})
    token = resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/knowledge/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
