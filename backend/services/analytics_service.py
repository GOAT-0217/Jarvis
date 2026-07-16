from datetime import datetime, timedelta
from sqlalchemy import func, text
from core.database import SessionLocal
from models import Document, UsageLog, User
from core.cache import cache


class AnalyticsService:

    CACHE_TTL = 60  # 1 分钟

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

            # 分类统计
            from models import Category, DocumentTag, Tag
            cat_rows = (
                db.query(Category.name, func.count(Document.id).label("cnt"))
                .outerjoin(Document, (Document.category_id == Category.id) & (Document.deleted_at.is_(None)))
                .filter(Category.deleted_at.is_(None))
                .group_by(Category.name)
                .order_by(func.count(Document.id).desc())
                .limit(10)
                .all()
            )
            category_distribution = [{"name": r.name, "count": r.cnt} for r in cat_rows if r.cnt > 0]

            # 标签统计
            tag_rows = (
                db.query(Tag.name, func.count(DocumentTag.document_id).label("cnt"))
                .join(DocumentTag, DocumentTag.tag_id == Tag.id)
                .join(Document, (Document.id == DocumentTag.document_id) & (Document.deleted_at.is_(None)))
                .filter(Tag.deleted_at.is_(None))
                .group_by(Tag.name)
                .order_by(func.count(DocumentTag.document_id).desc())
                .limit(10)
                .all()
            )
            tag_distribution = [{"name": r.name, "count": r.cnt} for r in tag_rows]

            # 近 30 天每日分类上传趋势
            from sqlalchemy import text as sa_text
            thirty_days = datetime.utcnow() - timedelta(days=30)
            cat_trend_rows = (
                db.query(
                    func.date(Document.created_at).label("dt"),
                    Category.name.label("cat"),
                    func.count().label("cnt"),
                )
                .join(Category, Category.id == Document.category_id)
                .filter(Document.created_at >= thirty_days, Document.deleted_at.is_(None), Category.deleted_at.is_(None))
                .group_by(func.date(Document.created_at), Category.name)
                .order_by("dt")
                .all()
            )
            dates = sorted(set(str(r.dt) for r in cat_trend_rows))
            cats = sorted(set(r.cat for r in cat_trend_rows))
            cat_index = {c: i for i, c in enumerate(cats)}
            def cat_empty_series(name: str) -> dict:
                return {"name": name, "type": "line", "stack": "cat", "data": [0] * len(dates)}
            cat_series = {c: cat_empty_series(c) for c in cats}
            for r in cat_trend_rows:
                di = dates.index(str(r.dt))
                cat_series[r.cat]["data"][di] = r.cnt
            category_trend = {"dates": dates, "series": list(cat_series.values())}

            # 近 30 天每日标签使用趋势
            tag_trend_rows = (
                db.query(
                    func.date(Document.created_at).label("dt"),
                    Tag.name.label("tag"),
                    func.count().label("cnt"),
                )
                .join(DocumentTag, DocumentTag.document_id == Document.id)
                .join(Tag, Tag.id == DocumentTag.tag_id)
                .filter(Document.created_at >= thirty_days, Document.deleted_at.is_(None), Tag.deleted_at.is_(None))
                .group_by(func.date(Document.created_at), Tag.name)
                .order_by("dt")
                .all()
            )
            tag_dates = sorted(set(str(r.dt) for r in tag_trend_rows))
            tag_names = sorted(set(r.tag for r in tag_trend_rows))
            def tag_empty_series(name: str) -> dict:
                return {"name": name, "type": "line", "stack": "tag", "data": [0] * len(tag_dates)}
            tag_series_map = {t: tag_empty_series(t) for t in tag_names}
            for r in tag_trend_rows:
                di = tag_dates.index(str(r.dt))
                tag_series_map[r.tag]["data"][di] = r.cnt
            tag_trend = {"dates": tag_dates, "series": list(tag_series_map.values())}

            result = {
                "document_count": doc_count,
                "today_upload_count": today_upload,
                "total_queries": total_queries,
                "query_trend": query_trend,
                "top_queries": top_queries,
                "active_users": active_users_data,
                "category_distribution": category_distribution,
                "tag_distribution": tag_distribution,
                "category_trend": category_trend,
                "tag_trend": tag_trend,
            }
            cache.set_json("dashboard_stats", result, AnalyticsService.CACHE_TTL)
            return result
        finally:
            db.close()
