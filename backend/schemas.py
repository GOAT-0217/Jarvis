from pydantic import BaseModel
from typing import Optional, List


class RegisterRequest(BaseModel):
    """注册请求。"""
    username: str
    password: str
    role: Optional[str] = "user"
    admin_code: Optional[str] = None


class LoginRequest(BaseModel):
    """用于验证登录请求数据结构"""
    username: str
    password: str


class AuthResponse(BaseModel):
    """规范认证响应结构"""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class CurrentUserResponse(BaseModel):
    """标准化当前用户信息的响应结构"""
    username: str
    role: str


class AttachmentItem(BaseModel):
    """聊天附件（文档文本或图片 base64）"""
    type: str            # "text" | "image"
    content: str         # 文本内容 或 data:image/...;base64,... URI
    filename: str
    mime_type: Optional[str] = None


class ChatRequest(BaseModel):
    """用于规范聊天请求的数据结构及类型校验"""
    message: str
    session_id: Optional[str] = "default_session"
    attachments: Optional[List[AttachmentItem]] = None


class RetrievedChunk(BaseModel):
    """用于结构化存储检索到的文本片段信息"""
    filename: str
    page_number: Optional[str | int] = None
    text: Optional[str] = None
    score: Optional[float] = None
    rrf_rank: Optional[int] = None
    rerank_score: Optional[float] = None


class RagTrace(BaseModel):
    """结构化记录RAG系统的完整执行轨迹"""
    tool_used: bool
    tool_name: str
    query: Optional[str] = None
    expanded_query: Optional[str] = None
    step_back_question: Optional[str] = None
    step_back_answer: Optional[str] = None
    expansion_type: Optional[str] = None
    hypothetical_doc: Optional[str] = None
    retrieval_stage: Optional[str] = None
    grade_score: Optional[str] = None
    grade_route: Optional[str] = None
    rewrite_needed: Optional[bool] = None
    rewrite_strategy: Optional[str] = None
    rewrite_query: Optional[str] = None
    rerank_enabled: Optional[bool] = None
    rerank_applied: Optional[bool] = None
    rerank_model: Optional[str] = None
    rerank_endpoint: Optional[str] = None
    rerank_error: Optional[str] = None
    retrieval_mode: Optional[str] = None
    candidate_k: Optional[int] = None
    leaf_retrieve_level: Optional[int] = None
    auto_merge_enabled: Optional[bool] = None
    auto_merge_applied: Optional[bool] = None
    auto_merge_threshold: Optional[int] = None
    auto_merge_replaced_chunks: Optional[int] = None
    auto_merge_steps: Optional[int] = None
    retrieved_chunks: Optional[List[RetrievedChunk]] = None
    initial_retrieved_chunks: Optional[List[RetrievedChunk]] = None
    expanded_retrieved_chunks: Optional[List[RetrievedChunk]] = None


class ChatResponse(BaseModel):
    """用于结构化聊天响应"""
    response: str
    rag_trace: Optional[RagTrace] = None


class MessageInfo(BaseModel):
    """结构化消息信息"""
    type: str
    content: str
    timestamp: str
    rag_trace: Optional[RagTrace] = None


class SessionMessagesResponse(BaseModel):
    """结构化地表示会话中的多条消息响应数据"""
    messages: List[MessageInfo]


class SessionInfo(BaseModel):
    """结构化存储会话相关信息"""
    session_id: str
    updated_at: str
    message_count: int


class SessionListResponse(BaseModel):
    """结构化地表示会话列表响应数据，通常用于 API 接口的数据序列化与验证"""
    sessions: List[SessionInfo]


class SessionDeleteResponse(BaseModel):
    """用于 API 响应中结构化删除会话的结果数据"""
    session_id: str
    message: str


class DocumentInfo(BaseModel):
    """结构化文档元数据"""
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    """结构化地表示文档列表响应数据，通常配合 Pydantic 进行数据验证和序列化"""
    documents: List[DocumentInfo]


class DocumentUploadResponse(BaseModel):
    """用于结构化文档上传的响应结果"""
    filename: str
    chunks_processed: int
    message: str


class DocumentDeleteResponse(BaseModel):
    """用于结构化文档删除操作的响应数据。"""
    filename: str
    chunks_deleted: int
    message: str


# ── Unified API response models ──────────────────────────────────────────────

from typing import Generic, TypeVar
from pydantic import BaseModel as PydanticBaseModel

T = TypeVar("T")


class APIResponse(PydanticBaseModel, Generic[T]):
    """统一成功响应。"""
    code: int = 0
    message: str = "success"
    data: T | None = None


class PaginatedData(PydanticBaseModel, Generic[T]):
    """分页数据结构。"""
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorResponse(PydanticBaseModel):
    """统一错误响应。"""
    code: int
    message: str
    data: None = None
