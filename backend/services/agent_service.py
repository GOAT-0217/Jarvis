"""Agent service — post-processing helpers for chat flows."""
import uuid

from core.database import SessionLocal
from models import UsageLog


def _log_usage(user_id: int, session_id: str, query: str, has_attachment: bool, tokens_used: int):
    """写入 usage_logs 埋点记录。

    在流式响应完成后调用，记录本次对话的用量信息。
    """
    db = SessionLocal()
    try:
        log = UsageLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            query=query[:200],
            has_attachment=has_attachment,
            tokens_used=tokens_used,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()
