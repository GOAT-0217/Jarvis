"""Knowledge routes — document upload, list, delete."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.embedding import embedding_service
from core.milvus_client import MilvusManager
from core.security import require_knowledge_admin
from document_loader import DocumentLoader
from milvus_writer import MilvusWriter
from parent_chunk_store import ParentChunkStore
from schemas import (
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data"
UPLOAD_DIR = DATA_DIR / "documents"

loader = DocumentLoader()
parent_chunk_store = ParentChunkStore()
milvus_manager = MilvusManager()
milvus_writer = MilvusWriter(embedding_service=embedding_service, milvus_manager=milvus_manager)


def _remove_bm25_stats_for_filename(filename: str) -> None:
    """删除 Milvus 中该文件对应 chunk 前，先从持久化 BM25 统计中扣减。"""
    rows = milvus_manager.query_all(
        filter_expr=f'filename == "{filename}"',
        output_fields=["text"],
    )
    texts = [r.get("text") or "" for r in rows]
    embedding_service.increment_remove_documents(texts)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(_=Depends(require_knowledge_admin)):
    """获取已上传的文档列表（管理员）
        该接口为管理员获取文档列表。
            1.首先初始化Milvus集合并查询文件名及类型；
            2.随后遍历结果，按文件名聚合统计切片数量；
            3.最后构建文档信息对象并返回响应。若出错则抛出500异常。
    """
    try:
        milvus_manager.init_collection()     # 1

        results = milvus_manager.query(
            output_fields=["filename", "file_type"],
            limit=10000,
        )

        file_stats = {}
        # 2
        for item in results:
            filename = item.get("filename", "")
            file_type = item.get("file_type", "")
            if filename not in file_stats:
                file_stats[filename] = {
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_count": 0,
                }
            file_stats[filename]["chunk_count"] += 1
        # 3
        documents = [DocumentInfo(**stats) for stats in file_stats.values()]
        return DocumentListResponse(documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), _=Depends(require_knowledge_admin)):
    """上传文档并进行 embedding（管理员）
        实现管理员上传文档功能：
            校验文件类型后，先清理旧数据（含BM25统计、Milvus向量及父分块），
            保存文件、解析内容并分级存储。
            最终返回处理结果，确保数据一致性与检索有效性。
    """
    try:
        filename = file.filename or ""
        file_lower = filename.lower()
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        if not (
            file_lower.endswith(".pdf")
            or file_lower.endswith((".docx", ".doc"))
            or file_lower.endswith((".xlsx", ".xls"))
        ):
            raise HTTPException(status_code=400, detail="仅支持 PDF、Word 和 Excel 文档")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        milvus_manager.init_collection()

        delete_expr = f'filename == "{filename}"'
        try:
            _remove_bm25_stats_for_filename(filename)
        except Exception:
            pass
        try:
            milvus_manager.delete(delete_expr)
        except Exception:
            pass
        try:
            parent_chunk_store.delete_by_filename(filename)
        except Exception:
            pass

        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            new_docs = loader.load_document(str(file_path), filename)
        except Exception as doc_err:
            raise HTTPException(status_code=500, detail=f"文档处理失败: {doc_err}")

        if not new_docs:
            raise HTTPException(status_code=500, detail="文档处理失败，未能提取内容")

        parent_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) in (1, 2)]
        leaf_docs = [doc for doc in new_docs if int(doc.get("chunk_level", 0) or 0) == 3]
        if not leaf_docs:
            raise HTTPException(status_code=500, detail="文档处理失败，未生成可检索叶子分块")

        parent_chunk_store.upsert_documents(parent_docs)
        milvus_writer.write_documents(leaf_docs)

        return DocumentUploadResponse(
            filename=filename,
            chunks_processed=len(leaf_docs),
            message=(
                f"成功上传并处理 {filename}，叶子分块 {len(leaf_docs)} 个，"
                f"父级分块 {len(parent_docs)} 个（存入 PostgreSQL）"
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.delete("/documents/{filename}", response_model=DocumentDeleteResponse)
async def delete_document(filename: str, _=Depends(require_knowledge_admin)):
    """删除文档在 Milvus 中的向量（保留本地文件，管理员）"""
    try:
        milvus_manager.init_collection()

        delete_expr = f'filename == "{filename}"'
        _remove_bm25_stats_for_filename(filename)
        result = milvus_manager.delete(delete_expr)
        parent_chunk_store.delete_by_filename(filename)

        return DocumentDeleteResponse(
            filename=filename,
            chunks_deleted=result.get("delete_count", 0) if isinstance(result, dict) else 0,
            message=f"成功删除文档 {filename} 的向量数据（本地文件已保留）",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")
