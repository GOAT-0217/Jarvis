import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from models import User, AuditLog


class UserService:

    @staticmethod
    def list_users(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        q = db.query(User)
        total = q.count()
        items = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def update_user(
        db: Session, user_id: int, role: str | None, is_active: bool | None,
        operator_id: int, ip: str | None = None,
    ) -> User | None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        detail = {}
        if role is not None and role in ("user", "knowledge_admin", "super_admin"):
            detail["role"] = {"old": user.role, "new": role}
            user.role = role
        if is_active is not None:
            detail["is_active"] = {"old": user.role, "new": is_active}
            if not is_active:
                user.role = "user"  # 停用时降级为普通用户
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=operator_id,
            action="user.update",
            target_type="user",
            target_id=str(user_id),
            detail=detail,
            ip_address=ip,
        )
        db.add(log)
        db.commit()
        return user
