from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.security import get_current_user, get_db, require_super_admin, require_knowledge_admin
from models import User, AuditLog, SystemSetting
from services.analytics_service import AnalyticsService
from services.user_service import UserService
from schemas import APIResponse, PaginatedData

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard/stats", response_model=APIResponse[dict])
async def dashboard_stats(current_user: User = Depends(require_knowledge_admin)):
    stats = AnalyticsService.get_dashboard_stats()
    return APIResponse(data=stats)


@router.get("/users", response_model=APIResponse[PaginatedData[dict]])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    items, total = UserService.list_users(db, page, page_size)
    return APIResponse(data=PaginatedData(
        items=[{"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at.isoformat()} for u in items],
        total=total, page=page, page_size=page_size,
    ))


@router.put("/users/{user_id}", response_model=APIResponse[dict])
async def update_user(
    user_id: int,
    body: dict,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = UserService.update_user(db, user_id, body.get("role"), body.get("is_active"),
                                    current_user.id, request.client.host if request.client else None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return APIResponse(data={"message": "用户已更新"})


@router.get("/settings", response_model=APIResponse[list[dict]])
async def get_settings(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    settings = db.query(SystemSetting).all()
    return APIResponse(data=[{"key": s.key, "value": s.value} for s in settings])


@router.put("/settings", response_model=APIResponse[dict])
async def update_settings(
    body: dict,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    for key, value in body.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = __import__("datetime").datetime.utcnow()
        else:
            s = SystemSetting(key=key, value=str(value))
            db.add(s)
    db.commit()
    return APIResponse(data={"message": "设置已保存"})


@router.get("/audit-logs", response_model=APIResponse[PaginatedData[dict]])
async def list_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse(data=PaginatedData(
        items=[{
            "id": a.id, "user_id": a.user_id, "action": a.action,
            "target_type": a.target_type, "target_id": a.target_id,
            "detail": a.detail, "ip_address": a.ip_address,
            "created_at": a.created_at.isoformat(),
        } for a in items],
        total=total, page=page, page_size=page_size,
    ))
