"""Document service — CRUD for documents, categories, and tags with soft delete and audit logging."""
import uuid
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from core.database import SessionLocal
from models import Document, Category, Tag, DocumentTag, AuditLog, User
from core.milvus_client import MilvusManager
from core.embedding import embedding_service
from milvus_writer import MilvusWriter
from document_loader import DocumentLoader
from parent_chunk_store import ParentChunkStore

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "documents"

loader = DocumentLoader()
parent_chunk_store = ParentChunkStore()
milvus_manager = MilvusManager()
milvus_writer = MilvusWriter(embedding_service=embedding_service, milvus_manager=milvus_manager)


def _write_audit(db: Session, user_id: int, action: str, target_type: str, target_id: str, detail: dict, ip: str | None):
    log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip,
    )
    db.add(log)


class DocumentService:
    """Document management service with soft-delete, categories, tags, and audit logging."""

    # ── Documents ──────────────────────────────────────────────────────────

    @staticmethod
    def list_documents(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        category_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        q = db.query(Document).filter(Document.deleted_at.is_(None))
        if search:
            q = q.filter(Document.filename.ilike(f"%{search}%"))
        if category_id:
            q = q.filter(Document.category_id == category_id)
        if status:
            q = q.filter(Document.status == status)
        total = q.count()
        items = q.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def create_document_record(db: Session, filename: str, file_path: str, file_size: int, file_type: str, uploaded_by: int, category_id: str | None = None) -> Document:
        doc = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            status="processing",
            uploaded_by=uploaded_by,
            category_id=category_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def update_document_status(db: Session, doc_id: str, status: str, char_count: int = 0, chunk_count: int = 0, error_message: str | None = None):
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = status
            doc.char_count = char_count
            doc.chunk_count = chunk_count
            doc.error_message = error_message
            db.commit()

    @staticmethod
    def process_document_async(doc_id: str, file_path: str, filename: str, category_id: str | None = None):
        """FastAPI BackgroundTasks calls this to process a document after upload."""
        db = SessionLocal()
        try:
            milvus_manager.init_collection()
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            new_docs = loader.load_document(file_path, filename)
            parent_docs = [d for d in new_docs if int(d.get("chunk_level", 0) or 0) in (1, 2)]
            leaf_docs = [d for d in new_docs if int(d.get("chunk_level", 0) or 0) == 3]

            if not leaf_docs:
                DocumentService.update_document_status(db, doc_id, "error", error_message="未生成可检索叶子分块")
                return

            # 将 category_id 写入每个 chunk 的 metadata，供后续按分类检索
            if category_id:
                for d in leaf_docs:
                    d["category_id"] = category_id
                for d in parent_docs:
                    d["category_id"] = category_id

            parent_chunk_store.upsert_documents(parent_docs)
            milvus_writer.write_documents(leaf_docs)

            full_text = "\n".join(d.get("text", "") for d in new_docs)
            DocumentService.update_document_status(
                db, doc_id, "ready",
                char_count=len(full_text),
                chunk_count=len(leaf_docs),
            )
        except Exception as e:
            DocumentService.update_document_status(db, doc_id, "error", error_message=str(e))
        finally:
            db.close()

    @staticmethod
    def soft_delete_document(db: Session, doc_id: str, user_id: int, ip: str | None = None):
        doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.is_(None)).first()
        if not doc:
            return None
        doc.deleted_at = datetime.utcnow()
        _write_audit(db, user_id, "document.delete", "document", doc_id, {"filename": doc.filename}, ip)
        db.commit()
        return doc

    @staticmethod
    def restore_document(db: Session, doc_id: str):
        doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.isnot(None)).first()
        if doc:
            doc.deleted_at = None
            db.commit()
        return doc

    # ── Categories ─────────────────────────────────────────────────────────

    @staticmethod
    def list_categories(db: Session) -> list[Category]:
        return db.query(Category).filter(Category.deleted_at.is_(None)).order_by(Category.sort_order).all()

    @staticmethod
    def create_category(db: Session, name: str, parent_id: str | None, sort_order: int, user_id: int, ip: str | None = None) -> Category:
        cat = Category(id=str(uuid.uuid4()), name=name, parent_id=parent_id, sort_order=sort_order)
        db.add(cat)
        _write_audit(db, user_id, "category.create", "category", cat.id, {"name": name}, ip)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def update_category(db: Session, cat_id: str, name: str | None, parent_id: str | None, sort_order: int | None, user_id: int, ip: str | None = None):
        cat = db.query(Category).filter(Category.id == cat_id, Category.deleted_at.is_(None)).first()
        if not cat:
            return None
        if name is not None:
            cat.name = name
        if parent_id is not None:
            cat.parent_id = parent_id
        if sort_order is not None:
            cat.sort_order = sort_order
        _write_audit(db, user_id, "category.update", "category", cat_id, {"name": name}, ip)
        db.commit()
        return cat

    @staticmethod
    def soft_delete_category(db: Session, cat_id: str, user_id: int, ip: str | None = None):
        cat = db.query(Category).filter(Category.id == cat_id, Category.deleted_at.is_(None)).first()
        if cat:
            cat.deleted_at = datetime.utcnow()
            _write_audit(db, user_id, "category.delete", "category", cat_id, {"name": cat.name}, ip)
            db.commit()
        return cat

    # ── Tags ───────────────────────────────────────────────────────────────

    @staticmethod
    def list_tags(db: Session) -> list[Tag]:
        return db.query(Tag).filter(Tag.deleted_at.is_(None)).all()

    @staticmethod
    def create_tag(db: Session, name: str, color: str, user_id: int, ip: str | None = None) -> Tag:
        tag = Tag(id=str(uuid.uuid4()), name=name, color=color)
        db.add(tag)
        _write_audit(db, user_id, "tag.create", "tag", tag.id, {"name": name}, ip)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def soft_delete_tag(db: Session, tag_id: str, user_id: int, ip: str | None = None):
        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.deleted_at.is_(None)).first()
        if tag:
            tag.deleted_at = datetime.utcnow()
            _write_audit(db, user_id, "tag.delete", "tag", tag_id, {"name": tag.name}, ip)
            db.commit()
        return tag
