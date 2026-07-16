from datetime import datetime, timedelta
from sqlalchemy import func, text
from core.database import SessionLocal
from models import Document, UsageLog, User
from core.cache import cache


class AnalyticsService:

    CACHE_TTL = 300  # 5 分钟

    @staticmethod
    def get_dashboard_stats() -> dict:
        cached = cache.get_json("dashboard_stats")
        if cached:
            return cached

        db = SessionLocal()
        try:
            doc_count = db.query(Document).filter(Document.deleted_at.is_(None)).count()
            today = datetime.utcnow().date()
            today_upload = db.query(Document).filter(
                Document.deleted_at.is_(None),
                func.date(Document.created_at) == today,
            ).count()

            total_queries = db.query(UsageLog).count()

            # 近 7 天查询趋势
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            trend_rows = (
                db.query(
                    func.date(UsageLog.created_at).label("date"),
                    func.count().label("count"),
                )
                .filter(UsageLog.created_at >= seven_days_ago)
                .group_by(func.date(UsageLog.created_at))
                .order_by("date")
                .all()
            )
            query_trend = [{"date": str(r.date), "count": r.count} for r in trend_rows]

            # 热门搜索 TOP 5
            top_rows = (
                db.query(
                    func.left(UsageLog.query, 50).label("term"),
                    func.count().label("count"),
                )
                .group_by("term")
                .order_by(func.count().desc())
                .limit(5)
                .all()
            )
            top_queries = [{"term": r.term, "count": r.count} for r in top_rows]

            # 活跃用户
            active_rows = (
                db.query(
                    UsageLog.user_id,
                    func.count().label("qcount"),
                    func.max(UsageLog.created_at).label("last_active"),
                )
                .group_by(UsageLog.user_id)
                .order_by(func.count().desc())
                .limit(10)
                .all()
            )
            active_users_data = []
            for r in active_rows:
                u = db.query(User).filter(User.id == r.user_id).first()
                active_users_data.append({
                    "username": u.username if u else str(r.user_id),
                    "query_count": r.qcount,
                    "last_active": str(r.last_active),
                })

            result = {
                "document_count": doc_count,
                "today_upload_count": today_upload,
                "total_queries": total_queries,
                "query_trend": query_trend,
                "top_queries": top_queries,
                "active_users": active_users_data,
            }
            cache.set_json("dashboard_stats", result, AnalyticsService.CACHE_TTL)
            return result
        finally:
            db.close()
