"""Admin routes — user management (stub for permission tests)."""
from fastapi import APIRouter, Depends

from core.security import get_current_user, require_super_admin
from models import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/users")
async def list_users(current_user: User = Depends(require_super_admin)):
    """List all users (requires super_admin)."""
    return {"users": []}
