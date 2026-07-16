"""Knowledge routes — document CRUD, categories, tags with unified APIResponse."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request, BackgroundTasks
from sqlalchemy.orm import Session

from core.security import get_current_user, get_db, require_knowledge_admin
from models import User, Document
from services.document_service import DocumentService, UPLOAD_DIR
from schemas import (
    APIResponse, PaginatedData,
    DocumentSchema, CategorySchema, CategoryCreate, CategoryUpdate,
    TagSchema, TagCreate, DocumentListQuery,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
service = DocumentService()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data"
UPLOAD_DIR_LOCAL = DATA_DIR / "documents"


@router.get("/documents", response_model=APIResponse[PaginatedData[DocumentSchema]])
async def list_documents(
    query: DocumentListQuery = Depends(),
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    items, total = service.list_documents(
        db, query.page, query.page_size, query.search, query.category_id, query.status
    )
    docs = [
        DocumentSchema(
            id=d.id, filename=d.filename, file_type=d.file_type, file_size=d.file_size,
            status=d.status, category_id=d.category_id,
            category_name=d.category.name if d.category else None,
            char_count=d.char_count,
            chunk_count=d.chunk_count, uploaded_by=str(d.uploaded_by) if d.uploaded_by else None,
            created_at=d.created_at.isoformat(),
            tags=[dt.tag.name for dt in d.tags_rel],
        )
        for d in items
    ]
    return APIResponse(data=PaginatedData(items=docs, total=total, page=query.page, page_size=query.page_size))


@router.post("/documents/upload", response_model=APIResponse[DocumentSchema])
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category_id: str | None = None,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""
    file_lower = filename.lower()
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if not file_lower.endswith((".pdf", ".docx", ".doc", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 PDF、Word 和 Excel 文档")

    file_type = file_lower.rsplit(".", 1)[-1]
    os.makedirs(UPLOAD_DIR_LOCAL, exist_ok=True)
    file_path = UPLOAD_DIR_LOCAL / filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = service.create_document_record(db, filename, str(file_path), len(content), file_type, current_user.id, category_id)

    background_tasks.add_task(service.process_document_async, doc.id, str(file_path), filename, category_id)

    return APIResponse(data=DocumentSchema(
        id=doc.id, filename=doc.filename, file_type=doc.file_type, file_size=doc.file_size,
        status=doc.status, char_count=0, chunk_count=0,
        uploaded_by=str(doc.uploaded_by) if doc.uploaded_by else None,
        created_at=doc.created_at.isoformat(), tags=[],
    ))


@router.put("/documents/{doc_id}/category", response_model=APIResponse[dict])
async def update_document_category(
    doc_id: str,
    body: dict,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    """修改文档分类"""
    category_id = (body.get("category_id") or "").strip() or None
    doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc.category_id = category_id
    db.commit()
    cat_name = doc.category.name if doc.category else None
    return APIResponse(data={"category_id": category_id, "category_name": cat_name})


@router.put("/documents/{doc_id}/tags", response_model=APIResponse[dict])
async def update_document_tags(
    doc_id: str,
    body: dict,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    """设置文档标签（最多 5 个）"""
    tag_ids = (body.get("tag_ids") or [])[:5]
    doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 清除旧标签关联
    from models import DocumentTag
    db.query(DocumentTag).filter(DocumentTag.document_id == doc_id).delete()

    # 添加新标签
    for tid in tag_ids:
        dt = DocumentTag(document_id=doc_id, tag_id=tid)
        db.add(dt)
    db.commit()

    tags = [dt.tag.name for dt in db.query(DocumentTag).filter(DocumentTag.document_id == doc_id).all()]
    return APIResponse(data={"tags": tags})


@router.delete("/documents/{doc_id}", response_model=APIResponse[dict])
async def delete_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    doc = service.soft_delete_document(db, doc_id, current_user.id, request.client.host if request.client else None)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return APIResponse(data={"message": f"文档 {doc.filename} 已删除"})


@router.post("/documents/{doc_id}/reindex", response_model=APIResponse[dict])
async def reindex_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc.status = "processing"
    db.commit()
    background_tasks.add_task(service.process_document_async, doc.id, doc.file_path, doc.filename)
    return APIResponse(data={"message": "已提交重新索引任务"})


@router.get("/categories", response_model=APIResponse[list[CategorySchema]])
async def list_categories(
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cats = service.list_categories(db)
    return APIResponse(data=[
        CategorySchema(id=c.id, name=c.name, parent_id=c.parent_id, sort_order=c.sort_order, children=[])
        for c in cats
    ])


@router.post("/categories", response_model=APIResponse[CategorySchema])
async def create_category(
    body: CategoryCreate,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cat = service.create_category(
        db, body.name, body.parent_id, body.sort_order,
        current_user.id, request.client.host if request.client else None,
    )
    return APIResponse(data=CategorySchema(
        id=cat.id, name=cat.name, parent_id=cat.parent_id, sort_order=cat.sort_order, children=[],
    ))


@router.put("/categories/{cat_id}", response_model=APIResponse[CategorySchema])
async def update_category(
    cat_id: str,
    body: CategoryUpdate,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cat = service.update_category(
        db, cat_id, body.name, body.parent_id, body.sort_order,
        current_user.id, request.client.host if request.client else None,
    )
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    return APIResponse(data=CategorySchema(
        id=cat.id, name=cat.name, parent_id=cat.parent_id, sort_order=cat.sort_order, children=[],
    ))


@router.delete("/categories/{cat_id}", response_model=APIResponse[dict])
async def delete_category(
    cat_id: str,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cat = service.soft_delete_category(db, cat_id, current_user.id, request.client.host if request.client else None)
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    return APIResponse(data={"message": f"分类 {cat.name} 已删除"})


@router.get("/tags", response_model=APIResponse[list[TagSchema]])
async def list_tags(
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    tags = service.list_tags(db)
    return APIResponse(data=[TagSchema(id=t.id, name=t.name, color=t.color) for t in tags])


@router.post("/tags", response_model=APIResponse[TagSchema])
async def create_tag(
    body: TagCreate,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    tag = service.create_tag(
        db, body.name, body.color,
        current_user.id, request.client.host if request.client else None,
    )
    return APIResponse(data=TagSchema(id=tag.id, name=tag.name, color=tag.color))


@router.delete("/tags/{tag_id}", response_model=APIResponse[dict])
async def delete_tag(
    tag_id: str,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    tag = service.soft_delete_tag(db, tag_id, current_user.id, request.client.host if request.client else None)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    return APIResponse(data={"message": f"标签 {tag.name} 已删除"})


@router.get("/documents/trash", response_model=APIResponse[PaginatedData[DocumentSchema]])
async def list_trash(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Document).filter(Document.deleted_at.isnot(None))
    total = q.count()
    items = q.order_by(Document.deleted_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    docs = [
        DocumentSchema(
            id=d.id, filename=d.filename, file_type=d.file_type, file_size=d.file_size,
            status=d.status, category_id=d.category_id, char_count=d.char_count,
            chunk_count=d.chunk_count, uploaded_by=str(d.uploaded_by),
            created_at=d.created_at.isoformat(), tags=[],
        )
        for d in items
    ]
    return APIResponse(data=PaginatedData(
        items=docs, total=total, page=page, page_size=page_size,
    ))


@router.post("/documents/{doc_id}/restore", response_model=APIResponse[dict])
async def restore_document(
    doc_id: str,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    doc = DocumentService.restore_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return APIResponse(data={"message": f"文档 {doc.filename} 已恢复"})
