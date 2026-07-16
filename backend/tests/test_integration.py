"""End-to-end integration tests — auth flow and role-based permissions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app import create_app
from core.database import SessionLocal

app = create_app()
client = TestClient(app)

E2E_USER = "e2e_test_user"
E2E_KADMIN = "e2e_test_kadmin"


@pytest.fixture(autouse=True)
def cleanup():
    """Remove test users created during integration tests before each run."""
    from models import User

    db = SessionLocal()
    db.query(User).filter(User.username.in_([E2E_USER, E2E_KADMIN])).delete()
    db.commit()
    db.close()
    yield


def test_full_auth_flow():
    """End-to-end auth flow: register -> login -> /me -> list sessions -> 403 on admin.

    Verifies the complete lifecycle for a regular user including that
    unprivileged users are denied access to admin-only endpoints.
    """
    # 1. Register a new regular user
    resp = client.post("/api/v1/auth/register", json={
        "username": E2E_USER,
        "password": "pass123",
    })
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["username"] == E2E_USER
    assert data["data"]["role"] == "user"
    assert data["data"]["access_token"] is not None

    # 2. Login with the same credentials
    resp = client.post("/api/v1/auth/login", json={
        "username": E2E_USER,
        "password": "pass123",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert data["code"] == 0
    token = data["data"]["access_token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Get current user info
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200, f"/me failed: {resp.text}"
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["username"] == E2E_USER
    assert data["data"]["role"] == "user"

    # 4. List sessions (expected to succeed, empty or populated)
    resp = client.get("/api/v1/chat/sessions", headers=headers)
    assert resp.status_code == 200, f"List sessions failed: {resp.text}"
    sessions_data = resp.json()
    assert "sessions" in sessions_data
    assert isinstance(sessions_data["sessions"], list)

    # 5. Regular user cannot access admin endpoints
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403, (
        f"Expected 403 for regular user on /admin/users, got {resp.status_code}: {resp.text}"
    )


def test_knowledge_admin_permissions():
    """Register knowledge_admin via invite code and verify permission boundaries.

    - knowledge_admin can access knowledge endpoints
    - knowledge_admin cannot access super_admin-only endpoints
    """
    import core.security

    # Set the invite code on the already-imported module so resolve_role() picks it up
    original_code = core.security.ADMIN_INVITE_CODE
    core.security.ADMIN_INVITE_CODE = "test_invite_2024"

    try:
        # 1. Register as knowledge_admin with the correct invite code
        resp = client.post("/api/v1/auth/register", json={
            "username": E2E_KADMIN,
            "password": "pass123",
            "role": "knowledge_admin",
            "admin_code": "test_invite_2024",
        })
        assert resp.status_code == 200, f"Register kadmin failed: {resp.text}"
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["role"] == "knowledge_admin", (
            f"Expected knowledge_admin role, got {data['data'].get('role')}"
        )
        token = data["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. knowledge_admin can access knowledge document list
        resp = client.get("/api/v1/knowledge/documents", headers=headers)
        assert resp.status_code == 200, (
            f"kadmin should access /knowledge/documents, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data["code"] == 0

        # 3. knowledge_admin can access knowledge categories
        resp = client.get("/api/v1/knowledge/categories", headers=headers)
        assert resp.status_code == 200, (
            f"kadmin should access /knowledge/categories, got {resp.status_code}: {resp.text}"
        )

        # 4. knowledge_admin can access dashboard stats (require_knowledge_admin)
        resp = client.get("/api/v1/admin/dashboard/stats", headers=headers)
        assert resp.status_code == 200, (
            f"kadmin should access /admin/dashboard/stats, got {resp.status_code}: {resp.text}"
        )

        # 5. knowledge_admin cannot access super_admin-only endpoints
        resp = client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403, (
            f"Expected 403 for kadmin on /admin/users, got {resp.status_code}: {resp.text}"
        )

    finally:
        # Restore the original invite code so other tests aren't affected
        core.security.ADMIN_INVITE_CODE = original_code
