"""Chat routes — chat, streaming, sessions, attachment extraction."""
import json
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, UnstructuredExcelLoader
from pydantic import BaseModel as PydanticBaseModel

from agent import chat_with_agent, chat_with_agent_stream, storage
from services.agent_service import _log_usage
from core.security import get_current_user
from models import User
from schemas import (
    AttachmentItem,
    ChatRequest,
    ChatResponse,
    MessageInfo,
    SessionDeleteResponse,
    SessionInfo,
    SessionListResponse,
    SessionMessagesResponse,
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class AttachmentExtractResponse(PydanticBaseModel):
    filename: str
    text: str
    char_count: int


MAX_ATTACHMENTS = 5
MAX_IMAGE_BASE64_SIZE = 20 * 1024 * 1024  # 20 MB per image base64 string


def _validate_attachments(attachments: list | None) -> None:
    """服务端校验附件数量与图片大小。"""
    if not attachments:
        return
    if len(attachments) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"附件数量超过上限（最多 {MAX_ATTACHMENTS} 个）",
        )
    for att in attachments:
        if att.type == "image" and len(att.content) > MAX_IMAGE_BASE64_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"图片 {att.filename} 过大（最大 20MB base64）",
            )


@router.post("/attachments/extract", response_model=AttachmentExtractResponse)
async def extract_attachment_text(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """提取上传文件的全文（不分块、不入库、不向量化）。

    支持 PDF / Word (.docx) / Excel。文件写入临时路径供加载器使用，提取后立即删除。
    """
    filename = file.filename or ""
    file_lower = filename.lower()

    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not (
        file_lower.endswith(".pdf")
        or file_lower.endswith(".docx")
        or file_lower.endswith((".xlsx", ".xls"))
    ):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持：PDF、Word (.docx)、Excel (.xlsx/.xls)",
        )

    # 文件大小检查（50MB 上限）
    MAX_EXTRACT_SIZE = 50 * 1024 * 1024  # 50 MB
    if hasattr(file, "size") and file.size is not None and file.size > MAX_EXTRACT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{file.size} bytes），附件提取上限为 50MB",
        )

    # 写入临时文件供加载器使用
    suffix = Path(filename).suffix or ".tmp"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            # 分块读取，避免大文件占用过多内存，同时检查大小
            total_read = 0
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > MAX_EXTRACT_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件过大（超过 {MAX_EXTRACT_SIZE // (1024*1024)}MB），附件提取上限为 50MB",
                    )
                tmp.write(chunk)
            tmp_path = tmp.name

        # 根据类型选择加载器
        if file_lower.endswith(".pdf"):
            doc_loader = PyPDFLoader(tmp_path)
        elif file_lower.endswith(".docx"):
            doc_loader = Docx2txtLoader(tmp_path)
        else:
            doc_loader = UnstructuredExcelLoader(tmp_path)

        docs = doc_loader.load()
        # 拼接所有页面文本为全文
        full_text = "\n\n".join(
            (doc.page_content or "").strip() for doc in docs if (doc.page_content or "").strip()
        )

        return AttachmentExtractResponse(
            filename=filename,
            text=full_text,
            char_count=len(full_text),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件提取失败: {str(e)}")
    finally:
        # 清理临时文件（无论成功或失败都会执行）
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.get("/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str, current_user: User = Depends(get_current_user)):
    """获取指定会话的所有消息"""
    try:
        messages = [
            MessageInfo(
                type=msg["type"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                rag_trace=msg.get("rag_trace"),
            )
            for msg in storage.get_session_messages(current_user.username, session_id)
        ]
        return SessionMessagesResponse(messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: User = Depends(get_current_user)):
    """获取当前用户的所有会话列表"""
    try:
        sessions = [SessionInfo(**item) for item in storage.list_session_infos(current_user.username)]
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return SessionListResponse(sessions=sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    """删除当前用户的指定会话"""
    try:
        deleted = storage.delete_session(current_user.username, session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="会话不存在")
        return SessionDeleteResponse(session_id=session_id, message="成功删除会话")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    该接口处理聊天请求：
    获取会话ID并调用代理生成回复，封装为ChatResponse返回。
    若异常，解析错误码：429提示限流，401/403及其他代码抛出对应HTTP异常，未匹配则报500错误，实现统一错误处理。
    """
    try:
        session_id = request.session_id or "default_session"
        _validate_attachments(request.attachments)
        resp = chat_with_agent(request.message, current_user.username, session_id, attachments=request.attachments)
        if isinstance(resp, dict):
            return ChatResponse(**resp)
        return ChatResponse(response=resp)
    except Exception as e:
        message = str(e)
        match = re.search(r"Error code:\s*(\d{3})", message)
        if match:
            code = int(match.group(1))
            if code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "上游模型服务触发限流/额度限制（429）。请检查账号额度/模型状态。\n"
                        f"原始错误：{message}"
                    ),
                )
            if code in (401, 403):
                raise HTTPException(status_code=code, detail=message)
            raise HTTPException(status_code=code, detail=message)
        raise HTTPException(status_code=500, detail=message)


@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """跟 Agent 对话 (流式)
        该函数实现流式聊天接口。
        它定义异步生成器，调用chat_with_agent_stream逐块yield对话内容，
        异常时返回错误JSON。
        最终通过StreamingResponse以SSE格式返回数据，并设置禁用缓存和缓冲的头信息，确保实时推送
    """

    async def event_generator():
        try:
            session_id = request.session_id or "default_session"
            _validate_attachments(request.attachments)
            async for chunk in chat_with_agent_stream(request.message, current_user.username, session_id, attachments=request.attachments):
                yield chunk
            _log_usage(current_user.id, session_id, request.message, bool(request.attachments), 0)
        except Exception as e:
            error_data = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
