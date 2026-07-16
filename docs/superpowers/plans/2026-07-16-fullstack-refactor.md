# 企业 AI 知识工坊 — 全栈重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Jarvis 从单页原型重构为 Vue 3 SPA + FastAPI 模块化后端的企业级 AI 知识工坊平台。

**Architecture:** FastAPI 三层架构（routers → services → core），Vue 3 SPA（Vite + TypeScript + Vue Router + Element Plus），PostgreSQL + Redis + Milvus 数据层，Vite build 产物由 FastAPI StaticFiles 一体化部署。

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy / Alembic / LangChain / Milvus / Redis / Vue 3 / TypeScript / Vite / Vue Router 4 / Element Plus / ECharts / Axios

## Global Constraints

- Python ≥ 3.12
- Vue 3 Composition API + `<script setup lang="ts">`
- 所有 API 路径以 `/api/v1/` 开头
- 统一响应格式 `{code: int, message: str, data: T | null}`
- 分页统一格式 `{items: [], total: int, page: int, page_size: int}`
- 三部角色: user / knowledge_admin / super_admin
- 软删除: documents、categories、tags 使用 `deleted_at` 字段
- 现有接口逻辑不重写，只拆分搬运
- 不做多租户、不做 SSO、不做移动端适配

---

## Phase 1: 基础设施

### Task 1.1: 初始化 Alembic 并生成初始迁移

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/001_initial.py`
- Modify: `backend/database.py`
- Modify: `backend/models.py`

**Interfaces:**
- Produces: Alembic 可用，`alembic upgrade head` 可建所有表

- [ ] **Step 1: 安装 Alembic 并初始化**

```bash
cd backend
uv run alembic init alembic
```

- [ ] **Step 2: 配置 alembic/env.py 指向 BASE 和 DATABASE_URL**

```python
# backend/alembic/env.py
from database import Base, DATABASE_URL
from models import *  # noqa: F401 — ensure all models are imported

target_metadata = Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
```

- [ ] **Step 3: 升级 models.py — 新增表 + 更新现有 User 模型**

在 `backend/models.py` 末尾追加以下模型（保留现有 User / ChatSession / ChatMessage / ParentChunk 不变）：

```python
# backend/models.py — 在现有文件末尾追加以下内容

import uuid
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

# === 新增: documents 表 ===
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("Category", back_populates="documents")
    uploader = relationship("User")
    tags_rel = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_status_deleted", "status", "deleted_at"),
        Index("ix_documents_category", "category_id"),
        Index("ix_documents_uploader", "uploaded_by"),
    )


# === 新增: categories 表 ===
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    documents = relationship("Document", back_populates="category")
    children = relationship("Category", backref="parent", remote_side="Category.id")


# === 新增: tags 表 ===
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#409EFF")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    documents_rel = relationship("DocumentTag", back_populates="tag", cascade="all, delete-orphan")


# === 新增: document_tags 关联表 ===
class DocumentTag(Base):
    __tablename__ = "document_tags"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(36), ForeignKey("tags.id"), primary_key=True)

    document = relationship("Document", back_populates="tags_rel")
    tag = relationship("Tag", back_populates="documents_rel")


# === 新增: system_settings 表 ===
class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# === 新增: usage_logs 表 ===
class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    has_attachment: Mapped[bool] = mapped_column(Boolean, default=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_usage_logs_created", "created_at"),
        Index("ix_usage_logs_user_created", "user_id", "created_at"),
    )


# === 新增: audit_logs 表 ===
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_logs_created", "created_at"),
        Index("ix_audit_logs_user", "user_id"),
    )


# === 更新 User 模型: role 字段扩展 ===
# 将现有的 role 字段注释掉，替换为:
# role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
# 无需修改数据库schema层面，只需在业务层校验枚举值
```

- [ ] **Step 4: 移除 database.py 中的 `init_db` 调用，仅保留定义**

确认 `backend/app.py` 中移除了对 `init_db()` 的调用（Alembic 接管建表）。

- [ ] **Step 5: 生成初始迁移并执行**

```bash
cd backend
uv run alembic revision --autogenerate -m "001_initial_fullstack"
uv run alembic upgrade head
```

- [ ] **Step 6: 提交**

```bash
git add backend/alembic.ini backend/alembic/ backend/models.py backend/database.py backend/app.py
git commit -m "feat: add Alembic migrations and new models (documents, categories, tags, settings, usage_logs, audit_logs)"
```

---

### Task 1.2: 创建后端目录结构和 __init__ 文件

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/services/__init__.py`
- Create: `backend/core/__init__.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p backend/routers backend/services backend/core
```

- [ ] **Step 2: 创建空的 __init__.py**

每个目录放一个空的 `__init__.py`。

- [ ] **Step 3: 提交**

```bash
git add backend/routers/ backend/services/ backend/core/
git commit -m "chore: create backend module directories (routers, services, core)"
```

---

### Task 1.3: 统一响应格式 — schemas.py 追加

**Files:**
- Modify: `backend/schemas.py`

**Interfaces:**
- Produces:
  - `APIResponse[T]` — 通用成功响应 `{code: 0, message: "success", data: T}`
  - `PaginatedData[T]` — 分页数据 `{items: T[], total: int, page: int, page_size: int}`
  - `ErrorResponse` — 错误响应 model

- [ ] **Step 1: 追加响应模型到 schemas.py**

```python
# backend/schemas.py — 在文件末尾追加

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
```

- [ ] **Step 2: 追加全局异常处理器到 app.py**

```python
# backend/app.py — 在 create_app() 中路由注册之前追加

from fastapi import Request
from fastapi.responses import JSONResponse
from schemas import ErrorResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.status_code, message=exc.detail).model_dump(),
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(code=50000, message=f"服务器内部错误: {str(exc)}").model_dump(),
    )
```

- [ ] **Step 3: 提交**

```bash
git add backend/schemas.py backend/app.py
git commit -m "feat: add unified API response format and global exception handlers"
```

---

### Task 1.4: 重构 core/ 目录 — 迁移基础设施文件

**Files:**
- Modify: `backend/core/database.py`（从 `backend/database.py` 移入）
- Modify: `backend/core/cache.py`（从 `backend/cache.py` 移入）
- Modify: `backend/core/milvus_client.py`（从 `backend/milvus_client.py` 移入）
- Modify: `backend/core/embedding.py`（从 `backend/embedding.py` 移入）
- Create: `backend/core/security.py`
- Delete: `backend/database.py`, `backend/cache.py`, `backend/milvus_client.py`, `backend/embedding.py`

**Interfaces:**
- Consumes: 无，这是纯迁移
- Produces:
  - `backend/core/database.py` → `Base`, `engine`, `SessionLocal`, `get_db()`
  - `backend/core/cache.py` → `cache` 实例
  - `backend/core/milvus_client.py` → `MilvusManager`
  - `backend/core/embedding.py` → `embedding_service`
  - `backend/core/security.py` → `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `create_access_token()`, `get_password_hash()`, `verify_password()`, `get_current_user()`, `require_knowledge_admin()`, `require_super_admin()`

- [ ] **Step 1: 移动 database.py 到 core/**

```bash
git mv backend/database.py backend/core/database.py
```

更新所有导入路径：将 `from database import ...` 改为 `from core.database import ...`。

- [ ] **Step 2: 移动 cache.py 到 core/**

```bash
git mv backend/cache.py backend/core/cache.py
```

更新导入。

- [ ] **Step 3: 移动 milvus_client.py 到 core/**

```bash
git mv backend/milvus_client.py backend/core/milvus_client.py
```

更新导入。

- [ ] **Step 4: 移动 embedding.py 到 core/**

```bash
git mv backend/embedding.py backend/core/embedding.py
```

更新导入。

- [ ] **Step 5: 创建 core/security.py — 从 auth.py 迁移 JWT + 密码逻辑**

```python
# backend/core/security.py

import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "")
PBKDF2_ROUNDS = int(os.getenv("PASSWORD_PBKDF2_ROUNDS", "310000"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            calculated = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(rounds))
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False
    if password_hash.startswith("$2") or password_hash.startswith("$bcrypt"):
        try:
            from passlib.context import CryptContext
            legacy_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
            return legacy_context.verify(plain_password, password_hash)
        except Exception:
            return False
    return False


def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("password is required")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt_b64}${digest_b64}"


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的认证令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    return user


def require_knowledge_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("knowledge_admin", "super_admin"):
        raise HTTPException(status_code=403, detail="需要知识管理员或更高权限")
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


def resolve_role(requested_role: str | None, admin_code: str | None) -> str:
    role = (requested_role or "user").strip().lower()
    if role == "super_admin":
        if ADMIN_INVITE_CODE and admin_code == ADMIN_INVITE_CODE:
            return "super_admin"
        raise HTTPException(status_code=403, detail="管理员邀请码错误")
    if role == "knowledge_admin":
        if ADMIN_INVITE_CODE and admin_code == ADMIN_INVITE_CODE:
            return "knowledge_admin"
        raise HTTPException(status_code=403, detail="管理员邀请码错误")
    if role == "admin":
        # 向后兼容：旧的 "admin" 映射为新 "super_admin"
        if ADMIN_INVITE_CODE and admin_code == ADMIN_INVITE_CODE:
            return "super_admin"
        raise HTTPException(status_code=403, detail="管理员邀请码错误")
    return "user"
```

- [ ] **Step 6: 删除旧的 auth.py 中的基础设施逻辑，仅保留路由**

将 `backend/auth.py` 重命名为 `backend/routers/auth.py`，删除其中已迁移到 `core/security.py` 的函数，只保留路由定义。

更新 `backend/app.py` 中的导入以反映所有路径变更。

- [ ] **Step 7: 运行测试确认无导入错误**

```bash
cd backend
uv run python -c "from app import app; print('App loaded successfully')"
```

- [ ] **Step 8: 提交**

```bash
git add backend/core/ backend/routers/auth.py backend/app.py
git rm backend/database.py backend/cache.py backend/milvus_client.py backend/embedding.py backend/auth.py
git commit -m "refactor: restructure backend into core/routers/services layers"
```

---

### Task 1.5: 拆分 api.py 路由到 routers/

**Files:**
- Create: `backend/routers/chat.py`
- Create: `backend/routers/knowledge.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/app.py`
- Delete: `backend/api.py`

**Interfaces:**
- Consumes: `core/security.py` 的依赖注入，`models.py` 的 ORM 模型
- Produces: router 对象供 `app.py` 注册

- [ ] **Step 1: 创建 routers/auth.py**

将现有 `api.py` 中的 `/auth/register`、`/auth/login`、`/auth/me` 路由提取到 `routers/auth.py`，router prefix = `"/api/v1/auth"`，tags = `["auth"]`。

```python
# backend/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import (
    authenticate_user, create_access_token, get_current_user,
    get_db, get_password_hash, resolve_role,
)
from models import User
from schemas import AuthResponse, LoginRequest, RegisterRequest, CurrentUserResponse, APIResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse[AuthResponse])
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = (request.username or "").strip()
    password = (request.password or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    role = resolve_role(request.role, request.admin_code)
    user = User(username=username, password_hash=get_password_hash(password), role=role)
    db.add(user)
    db.commit()
    token = create_access_token(username=username, role=role)
    return APIResponse(data=AuthResponse(access_token=token, username=username, role=role))


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(username=user.username, role=user.role)
    return APIResponse(data=AuthResponse(access_token=token, username=user.username, role=user.role))


@router.get("/me", response_model=APIResponse[CurrentUserResponse])
async def me(current_user: User = Depends(get_current_user)):
    return APIResponse(data=CurrentUserResponse(username=current_user.username, role=current_user.role))
```

- [ ] **Step 2: 创建 routers/chat.py**

从 `api.py` 中提取 `/chat`、`/chat/stream`、`/sessions`、`/sessions/{id}`、`/attachments/extract` 路由。prefix = `"/api/v1/chat"`，tags = `["chat"]`。

完整迁移现有路由逻辑，替换导入路径为 `core.*`，使用 `require_knowledge_admin` 替换原 `require_admin`。

- [ ] **Step 3: 创建 routers/knowledge.py**

从 `api.py` 中提取 `/documents`、`/documents/upload`、`/documents/{filename}` 路由。prefix = `"/api/v1/knowledge"`，tags = `["knowledge"]`。

- [ ] **Step 4: 更新 app.py 路由注册**

```python
# backend/app.py

from routers import auth, chat, knowledge

# 替换原来的 app.include_router(api_module.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
```

- [ ] **Step 5: 验证**

```bash
cd backend
uv run python -c "from app import app; print([r.path for r in app.routes])"
```

- [ ] **Step 6: 删除 api.py 并提交**

```bash
git rm backend/api.py
git add backend/routers/ backend/app.py
git commit -m "refactor: split api.py routes into routers/auth, chat, knowledge"
```

---

## Phase 2: 认证 & 权限

### Task 2.1: 用户角色迁移（admin → super_admin）

**Files:**
- Create: `backend/alembic/versions/002_migrate_admin_role.py`
- Modify: `backend/core/security.py`

**Interfaces:**
- 将现有数据库中 `role = 'admin'` 的用户批量更新为 `role = 'super_admin'`

- [ ] **Step 1: 创建数据迁移脚本**

```python
# backend/alembic/versions/002_migrate_admin_role.py

"""migrate admin role to super_admin

Revision ID: 002
"""

from alembic import op

def upgrade():
    op.execute("UPDATE users SET role = 'super_admin' WHERE role = 'admin'")

def downgrade():
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
```

- [ ] **Step 2: 执行迁移**

```bash
cd backend
uv run alembic upgrade head
```

- [ ] **Step 3: 验证迁移结果**

```bash
uv run python -c "
from core.database import SessionLocal
from models import User
db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f'{u.username}: {u.role}')
db.close()
"
```

- [ ] **Step 4: 提交**

```bash
git add backend/alembic/versions/002_migrate_admin_role.py
git commit -m "feat: migrate admin role to super_admin + add knowledge_admin role support"
```

---

### Task 2.2: 后端权限测试

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/test_auth.py

import pytest
from fastapi.testclient import TestClient
from app import create_app
from core.database import SessionLocal
from core.security import get_password_hash
from models import User

app = create_app()
client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    db.query(User).filter(User.username.in_(["test_user", "test_kadmin", "test_sadmin"])).delete()
    db.commit()
    db.close()
    yield

def _create_user(username: str, role: str):
    db = SessionLocal()
    user = User(username=username, password_hash=get_password_hash("test123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

def _login(client, username: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": "test123"})

def test_login_success():
    _create_user("test_user", "user")
    resp = _login(client, "test_user")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["access_token"] is not None

def test_login_wrong_password():
    _create_user("test_user", "user")
    resp = client.post("/api/v1/auth/login", json={"username": "test_user", "password": "wrong"})
    assert resp.status_code == 401

def test_me_requires_auth():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)

def test_knowledge_admin_access():
    _create_user("test_kadmin", "knowledge_admin")
    token = _login(client, "test_kadmin").json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "knowledge_admin"

def test_user_cannot_access_admin():
    _create_user("test_user", "user")
    token = _login(client, "test_user").json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403
```

- [ ] **Step 2: 运行测试确认权限逻辑**

```bash
cd backend
uv run pytest tests/test_auth.py -v
```

- [ ] **Step 3: 提交**

```bash
git add backend/tests/
git commit -m "test: add auth and permission tests"
```

---

## Phase 3: Vite + Vue 3 脚手架

### Task 3.1: 初始化 Vite + Vue 3 + TypeScript 项目

**Files:**
- Create: `frontend/` 下的 Vite 脚手架（package.json, vite.config.ts, tsconfig.json, index.html, src/）

- [ ] **Step 1: 使用 Vite 创建 Vue 3 + TS 项目**

```bash
cd frontend
# 先备份现有文件
mkdir -p ../_frontend_backup
cp -r ./* ../_frontend_backup/ 2>/dev/null || true

# 在当前目录初始化 Vite 项目
npm create vite@latest . -- --template vue-ts
# 提示覆盖时选择 yes
```

- [ ] **Step 2: 安装依赖**

```bash
cd frontend
npm install
npm install vue-router@4 element-plus echarts axios @element-plus/icons-vue
npm install -D @types/node
```

- [ ] **Step 3: 配置 vite.config.ts — API 代理**

```typescript
// frontend/vite.config.ts

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: 验证 dev server 启动**

```bash
npm run dev
# 确认 :5173 可访问
```

- [ ] **Step 5: 提交**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/
git commit -m "feat: scaffold Vite + Vue 3 + TypeScript project"
```

---

### Task 3.2: 配置 Vue Router + Element Plus

**Files:**
- Create: `frontend/src/router/index.ts`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 创建路由配置**

```typescript
// frontend/src/router/index.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatAssistant.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat/:sessionId',
    name: 'ChatSession',
    component: () => import('@/views/ChatAssistant.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'] },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/DocumentList.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'] },
  },
  {
    path: '/knowledge/categories',
    name: 'Categories',
    component: () => import('@/views/CategoryManage.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'] },
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/UserManage.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'] },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SystemSettings.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'] },
  },
  {
    path: '/audit-logs',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 2: 路由守卫**

```typescript
// 在 frontend/src/router/index.ts 中 router 定义之后追加

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('accessToken')
  const userStr = localStorage.getItem('currentUser')
  const currentUser = userStr ? JSON.parse(userStr) : null

  if (to.meta.requiresAuth !== false && !token) {
    return next('/login')
  }

  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    const allowedRoles = to.meta.roles as string[]
    if (!currentUser || !allowedRoles.includes(currentUser.role)) {
      return next('/chat')
    }
  }

  next()
})
```

- [ ] **Step 3: 更新 main.ts**

```typescript
// frontend/src/main.ts

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

- [ ] **Step 4: 更新 App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <router-view />
</template>

<script setup lang="ts">
</script>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/router/ frontend/src/main.ts frontend/src/App.vue
git commit -m "feat: add Vue Router with auth guards and Element Plus"
```

---

### Task 3.3: API 封装层 + useAuth Composable

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/composables/useAuth.ts`

- [ ] **Step 1: Axios 实例**

```typescript
// frontend/src/api/client.ts

import axios from 'axios'
import router from '@/router'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body.code !== undefined && body.code !== 0) {
      return Promise.reject(new Error(body.message || 'Request failed'))
    }
    return body
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('currentUser')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default client
```

- [ ] **Step 2: Auth API**

```typescript
// frontend/src/api/auth.ts

import client from './client'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
  role?: string
  admin_code?: string
}

export interface AuthData {
  access_token: string
  token_type: string
  username: string
  role: string
}

export interface CurrentUserData {
  username: string
  role: string
}

export function login(params: LoginParams) {
  return client.post<any, { data: AuthData }>('/auth/login', params)
}

export function register(params: RegisterParams) {
  return client.post<any, { data: AuthData }>('/auth/register', params)
}

export function getMe() {
  return client.get<any, { data: CurrentUserData }>('/auth/me')
}
```

- [ ] **Step 3: useAuth Composable**

```typescript
// frontend/src/composables/useAuth.ts

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { login as apiLogin, register as apiRegister, getMe } from '@/api/auth'
import type { LoginParams, RegisterParams, CurrentUserData } from '@/api/auth'

const token = ref<string>(localStorage.getItem('accessToken') || '')
const currentUser = ref<CurrentUserData | null>(
  JSON.parse(localStorage.getItem('currentUser') || 'null')
)

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() =>
    currentUser.value?.role === 'super_admin' || currentUser.value?.role === 'knowledge_admin'
  )
  const isSuperAdmin = computed(() => currentUser.value?.role === 'super_admin')

  async function doLogin(params: LoginParams) {
    const res = await apiLogin(params)
    token.value = res.data.access_token
    currentUser.value = { username: res.data.username, role: res.data.role }
    localStorage.setItem('accessToken', res.data.access_token)
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    router.push('/chat')
  }

  async function doRegister(params: RegisterParams) {
    const res = await apiRegister(params)
    token.value = res.data.access_token
    currentUser.value = { username: res.data.username, role: res.data.role }
    localStorage.setItem('accessToken', res.data.access_token)
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    router.push('/chat')
  }

  function logout() {
    token.value = ''
    currentUser.value = null
    localStorage.removeItem('accessToken')
    localStorage.removeItem('currentUser')
    router.push('/login')
  }

  return {
    token,
    currentUser,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    doLogin,
    doRegister,
    logout,
  }
}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/ frontend/src/composables/
git commit -m "feat: add axios API layer and useAuth composable"
```

---

### Task 3.4: 主布局组件（AppLayout + SidebarMenu + HeaderBar）

**Files:**
- Create: `frontend/src/components/AppLayout.vue`
- Create: `frontend/src/components/SidebarMenu.vue`
- Create: `frontend/src/components/HeaderBar.vue`
- Create: `frontend/src/views/Login.vue`

- [ ] **Step 1: AppLayout.vue**

```vue
<!-- frontend/src/components/AppLayout.vue -->
<template>
  <el-container style="height: 100vh">
    <el-aside :width="isCollapsed ? '64px' : '220px'" style="transition: width 0.2s">
      <SidebarMenu :collapsed="isCollapsed" />
    </el-aside>
    <el-container>
      <el-header style="height: 56px; padding: 0 16px; border-bottom: 1px solid #e4e7ed">
        <HeaderBar @toggle-collapse="isCollapsed = !isCollapsed" />
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SidebarMenu from './SidebarMenu.vue'
import HeaderBar from './HeaderBar.vue'

const isCollapsed = ref(false)
</script>
```

- [ ] **Step 2: SidebarMenu.vue**

```vue
<!-- frontend/src/components/SidebarMenu.vue -->
<template>
  <el-menu
    :default-active="route.path"
    :collapse="collapsed"
    router
    style="height: 100%; border-right: 0"
  >
    <el-menu-item index="/chat">
      <el-icon><ChatDotRound /></el-icon>
      <span>AI 助手</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/dashboard"
    >
      <el-icon><DataAnalysis /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/knowledge"
    >
      <el-icon><Document /></el-icon>
      <span>文档管理</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/knowledge/categories"
    >
      <el-icon><CollectionTag /></el-icon>
      <span>分类标签</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/users"
    >
      <el-icon><User /></el-icon>
      <span>用户管理</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/settings"
    >
      <el-icon><Setting /></el-icon>
      <span>系统设置</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/audit-logs"
    >
      <el-icon><Tickets /></el-icon>
      <span>操作日志</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

defineProps<{ collapsed: boolean }>()

const route = useRoute()
const { isAdmin, isSuperAdmin } = useAuth()
</script>
```

- [ ] **Step 3: HeaderBar.vue**

```vue
<!-- frontend/src/components/HeaderBar.vue -->
<template>
  <div style="display: flex; align-items: center; justify-content: space-between; height: 100%">
    <div>
      <el-button @click="$emit('toggleCollapse')" :icon="Fold" link />
      <el-breadcrumb separator="/" style="display: inline-block; margin-left: 12px">
        <el-breadcrumb-item :to="{ path: '/chat' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>{{ route.meta.title || route.name }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <el-dropdown @command="handleCommand">
      <span style="cursor: pointer">
        {{ currentUser?.username }}
        <el-icon><ArrowDown /></el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="logout">退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { Fold } from '@element-plus/icons-vue'

defineEmits<{ toggleCollapse: [] }>()

const route = useRoute()
const { currentUser, logout } = useAuth()

function handleCommand(cmd: string) {
  if (cmd === 'logout') logout()
}
</script>
```

- [ ] **Step 4: Login.vue（占位，Phase 4 完善）**

```vue
<!-- frontend/src/views/Login.vue -->
<template>
  <div class="login-container">
    <el-card style="width: 400px">
      <h2 style="text-align: center; margin-bottom: 24px">企业 AI 知识工坊</h2>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const username = ref('')
const password = ref('')
const loading = ref(false)
const { doLogin } = useAuth()

async function handleLogin() {
  loading.value = true
  try {
    await doLogin({ username: username.value, password: password.value })
  } catch (e: any) {
    alert(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: #f0f2f5;
}
</style>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/AppLayout.vue frontend/src/components/SidebarMenu.vue frontend/src/components/HeaderBar.vue frontend/src/views/Login.vue
git commit -m "feat: add AppLayout, SidebarMenu, HeaderBar, and Login page"
```

---

## Phase 4: AI 助手页

### Task 4.1: 迁移 AI 助手功能到 ChatAssistant.vue

**Files:**
- Create: `frontend/src/views/ChatAssistant.vue`
- Create: `frontend/src/components/SessionList.vue`
- Create: `frontend/src/components/MessageBubble.vue`
- Create: `frontend/src/components/ChatInput.vue`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/composables/useChat.ts`
- Modify: `frontend/src/router/index.ts`（让 `/chat` 使用带 AppLayout 的布局）

**Interfaces:**
- Consumes: `useAuth` composable, `/api/v1/chat/stream` SSE 端点
- Produces: 完整的 AI 对话界面

- [ ] **Step 1: chat.ts API**

```typescript
// frontend/src/api/chat.ts

import client from './client'

export interface SessionInfo {
  session_id: string
  updated_at: string
  message_count: number
}

export interface MessageInfo {
  type: string
  content: string
  timestamp: string
  rag_trace?: any
}

export function getSessions() {
  return client.get<any, { data: { sessions: SessionInfo[] } }>('/chat/sessions')
}

export function getSessionMessages(sessionId: string) {
  return client.get<any, { data: { messages: MessageInfo[] } }>(`/chat/sessions/${sessionId}`)
}

export function deleteSession(sessionId: string) {
  return client.delete<any, { data: any }>(`/chat/sessions/${sessionId}`)
}

export interface ChatStreamParams {
  message: string
  session_id: string
  attachments?: any[]
}

export function streamChat(params: ChatStreamParams): Promise<Response> {
  const token = localStorage.getItem('accessToken')
  return fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(params),
  })
}
```

- [ ] **Step 2: useChat.ts**

```typescript
// frontend/src/composables/useChat.ts

import { ref } from 'vue'
import { getSessions, getSessionMessages, deleteSession, streamChat } from '@/api/chat'
import type { SessionInfo, MessageInfo } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  ragTrace?: any
}

export function useChat() {
  const sessions = ref<SessionInfo[]>([])
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const abortController = ref<AbortController | null>(null)

  async function loadSessions() {
    const res = await getSessions()
    sessions.value = res.data.sessions
  }

  async function loadMessages(sessionId: string) {
    const res = await getSessionMessages(sessionId)
    messages.value = res.data.messages.map((m: MessageInfo) => ({
      id: `${m.timestamp}-${Math.random()}`,
      role: m.type === 'human' ? 'user' : 'assistant',
      content: m.content,
      ragTrace: m.rag_trace,
    }))
  }

  async function removeSession(sessionId: string) {
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.session_id !== sessionId)
  }

  async function sendMessage(text: string, sessionId: string, attachments?: any[]) {
    const userMsg: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: text,
    }
    messages.value.push(userMsg)

    const assistantMsg: ChatMessage = {
      id: `${Date.now()}-assistant`,
      role: 'assistant',
      content: '',
    }
    messages.value.push(assistantMsg)

    isStreaming.value = true
    const controller = new AbortController()
    abortController.value = controller

    try {
      const response = await streamChat({
        message: text,
        session_id: sessionId,
        attachments,
      })

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'error') {
                assistantMsg.content = data.content
              } else if (data.type === 'content' || data.type === 'text') {
                assistantMsg.content += data.content || data.text || ''
              } else if (typeof data === 'string') {
                assistantMsg.content += data
              } else if (data.content) {
                assistantMsg.content += data.content
              }
            } catch {
              // raw text
              assistantMsg.content += line.slice(6)
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        assistantMsg.content = `[错误] ${e.message}`
      }
    } finally {
      isStreaming.value = false
      abortController.value = null
    }
  }

  function stopStreaming() {
    abortController.value?.abort()
  }

  return {
    sessions,
    messages,
    isStreaming,
    loadSessions,
    loadMessages,
    removeSession,
    sendMessage,
    stopStreaming,
  }
}
```

- [ ] **Step 3: ChatAssistant.vue — 三栏布局**

```vue
<!-- frontend/src/views/ChatAssistant.vue -->
<template>
  <div class="chat-layout">
    <div class="chat-sidebar">
      <SessionList
        :sessions="sessions"
        :active-session-id="currentSessionId"
        @select="switchSession"
        @delete="handleDeleteSession"
        @new-chat="newChat"
      />
    </div>
    <div class="chat-main">
      <div class="chat-messages" ref="messagesContainer">
        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
        />
        <div v-if="isStreaming" style="color: #999">AI 正在思考...</div>
      </div>
      <div class="chat-input-area">
        <ChatInput
          :disabled="isStreaming"
          @send="handleSend"
          @stop="stopStreaming"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat'
import SessionList from '@/components/SessionList.vue'
import MessageBubble from '@/components/MessageBubble.vue'
import ChatInput from '@/components/ChatInput.vue'

const route = useRoute()
const router = useRouter()
const {
  sessions, messages, isStreaming,
  loadSessions, loadMessages, removeSession, sendMessage, stopStreaming,
} = useChat()

const messagesContainer = ref<HTMLElement>()
const currentSessionId = ref<string>('session_' + Date.now())

onMounted(() => {
  loadSessions()
  if (route.params.sessionId) {
    currentSessionId.value = route.params.sessionId as string
    loadMessages(currentSessionId.value)
  }
})

async function switchSession(sid: string) {
  currentSessionId.value = sid
  router.push(`/chat/${sid}`)
  await loadMessages(sid)
}

async function handleDeleteSession(sid: string) {
  await removeSession(sid)
  if (currentSessionId.value === sid) {
    newChat()
  }
}

function newChat() {
  currentSessionId.value = 'session_' + Date.now()
  messages.value = []
}

async function handleSend(text: string) {
  await sendMessage(text, currentSessionId.value)
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-layout { display: flex; height: 100%; }
.chat-sidebar { width: 260px; border-right: 1px solid #e4e7ed; }
.chat-main { flex: 1; display: flex; flex-direction: column; }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; }
.chat-input-area { padding: 12px 16px; border-top: 1px solid #e4e7ed; }
</style>
```

- [ ] **Step 4: SessionList.vue**

```vue
<!-- frontend/src/components/SessionList.vue -->
<template>
  <div class="session-list">
    <el-button type="primary" @click="$emit('newChat')" style="width: 100%; margin-bottom: 12px">
      新建会话
    </el-button>
    <div
      v-for="s in sessions"
      :key="s.session_id"
      :class="['session-item', { active: s.session_id === activeSessionId }]"
      @click="$emit('select', s.session_id)"
    >
      <span class="session-name">{{ s.session_id }}</span>
      <el-button
        link
        type="danger"
        @click.stop="$emit('delete', s.session_id)"
      >
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <div v-if="!sessions.length" style="color: #999; text-align: center; padding: 24px">
      暂无会话
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SessionInfo } from '@/api/chat'

defineProps<{
  sessions: SessionInfo[]
  activeSessionId: string
}>()

defineEmits<{
  select: [sessionId: string]
  delete: [sessionId: string]
  newChat: []
}>()
</script>

<style scoped>
.session-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; border-radius: 4px;
}
.session-item:hover { background: #f5f7fa; }
.session-item.active { background: #ecf5ff; }
</style>
```

- [ ] **Step 5: MessageBubble.vue**

```vue
<!-- frontend/src/components/MessageBubble.vue -->
<template>
  <div :class="['message-row', message.role]">
    <div :class="['bubble', message.role]">
      <div v-html="renderedContent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/composables/useChat'

const props = defineProps<{ message: ChatMessage }>()

const renderedContent = computed(() => {
  // 简单 Markdown 渲染：代码块和换行
  let text = props.message.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  text = `<p>${text}</p>`
  return text
})
</script>

<style scoped>
.message-row { display: flex; margin-bottom: 16px; }
.message-row.user { justify-content: flex-end; }
.bubble { max-width: 70%; padding: 10px 14px; border-radius: 8px; }
.bubble.user { background: #409EFF; color: white; }
.bubble.assistant { background: #f4f4f5; }
</style>
```

- [ ] **Step 6: ChatInput.vue**

```vue
<!-- frontend/src/components/ChatInput.vue -->
<template>
  <div class="input-area">
    <el-input
      v-model="text"
      type="textarea"
      :rows="3"
      placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
      @keydown.enter.exact.prevent="handleSend"
    />
    <div style="display: flex; justify-content: flex-end; margin-top: 8px; gap: 8px">
      <el-button v-if="disabled" @click="$emit('stop')" type="danger">停止</el-button>
      <el-button @click="handleSend" type="primary" :disabled="!text.trim()">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const text = ref('')

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
}
</script>
```

- [ ] **Step 7: 更新 router — 让 /chat 在 AppLayout 内渲染**

```typescript
// frontend/src/router/index.ts — 修改 chat 相关路由，添加布局包装

// 所有需要 AppLayout 的路由共用 meta: { layout: 'default' }
// /login 使用 meta: { layout: 'none' }

{
  path: '/chat',
  name: 'Chat',
  component: () => import('@/views/ChatAssistant.vue'),
  meta: { requiresAuth: true, layout: 'default' },
},
```

更新 `App.vue`：

```vue
<!-- frontend/src/App.vue -->
<template>
  <AppLayout v-if="route.meta.layout !== 'none'">
    <router-view />
  </AppLayout>
  <router-view v-else />
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

const route = useRoute()
</script>
```

- [ ] **Step 8: 提交**

```bash
git add frontend/src/views/ChatAssistant.vue frontend/src/components/SessionList.vue frontend/src/components/MessageBubble.vue frontend/src/components/ChatInput.vue frontend/src/api/chat.ts frontend/src/composables/useChat.ts frontend/src/router/index.ts frontend/src/App.vue
git commit -m "feat: migrate AI chat to Vue 3 SPA with three-column layout and SSE streaming"
```

---

## Phase 5: 文档管理

### Task 5.1: 后端 — 文档、分类、标签 API

**Files:**
- Modify: `backend/routers/knowledge.py`
- Create: `backend/services/document_service.py`
- Modify: `backend/schemas.py`
- Create: `backend/tests/test_knowledge.py`

- [ ] **Step 1: 扩展 schemas.py — 文档相关模型**

```python
# backend/schemas.py — 追加

from datetime import datetime

class DocumentSchema(PydanticBaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    category_id: str | None = None
    char_count: int = 0
    chunk_count: int = 0
    uploaded_by: str | None = None
    created_at: str
    tags: list[str] = []

class CategorySchema(PydanticBaseModel):
    id: str
    name: str
    parent_id: str | None = None
    sort_order: int = 0
    children: list["CategorySchema"] = []

class CategoryCreate(PydanticBaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0

class CategoryUpdate(PydanticBaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None

class TagSchema(PydanticBaseModel):
    id: str
    name: str
    color: str

class TagCreate(PydanticBaseModel):
    name: str
    color: str = "#409EFF"

class DocumentListQuery(PydanticBaseModel):
    page: int = 1
    page_size: int = 20
    search: str | None = None
    category_id: str | None = None
    status: str | None = None
```

- [ ] **Step 2: 创建 document_service.py**

```python
# backend/services/document_service.py

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


class DocumentService:

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
    def create_document_record(db: Session, filename: str, file_path: str, file_size: int, file_type: str, uploaded_by: int) -> Document:
        doc = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            status="processing",
            uploaded_by=uploaded_by,
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
    def process_document_async(doc_id: str, file_path: str, filename: str):
        """FastAPI BackgroundTasks 调用此函数处理文档。"""
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

    # === 分类操作 ===

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

    # === 标签操作 ===

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
```

- [ ] **Step 3: 重写 routers/knowledge.py — 接入 services 层和统一响应格式**

使用 `DocumentService` 实现所有知识库端点。每个端点用 `APIResponse` 包装返回。上传端点接入 `BackgroundTasks`。

```python
# backend/routers/knowledge.py — 完整替换

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request, BackgroundTasks
from sqlalchemy.orm import Session

from core.security import get_current_user, get_db, require_knowledge_admin
from models import User
from services.document_service import DocumentService
from schemas import (
    APIResponse, PaginatedData,
    DocumentSchema, CategorySchema, CategoryCreate, CategoryUpdate,
    TagSchema, TagCreate, DocumentListQuery,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
service = DocumentService()


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
            status=d.status, category_id=d.category_id, char_count=d.char_count,
            chunk_count=d.chunk_count, uploaded_by=str(d.uploaded_by),
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
    import os
    from pathlib import Path
    os.makedirs(UPLOAD_DIR if (UPLOAD_DIR := Path(__file__).resolve().parent.parent.parent / "data" / "documents") else None, exist_ok=True)
    upload_dir = Path(__file__).resolve().parent.parent.parent / "data" / "documents"
    file_path = upload_dir / filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = service.create_document_record(db, filename, str(file_path), len(content), file_type, current_user.id)

    background_tasks.add_task(service.process_document_async, doc.id, str(file_path), filename)

    return APIResponse(data=DocumentSchema(
        id=doc.id, filename=doc.filename, file_type=doc.file_type, file_size=doc.file_size,
        status=doc.status, char_count=0, chunk_count=0, uploaded_by=str(doc.uploaded_by),
        created_at=doc.created_at.isoformat(), tags=[],
    ))


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
    doc = db.query(DocumentSchema).filter_by(id=doc_id).first()  # type: ignore
    # 实现: 查找对应的 document 记录
    from models import Document
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
    return APIResponse(data=[CategorySchema(id=c.id, name=c.name, parent_id=c.parent_id, sort_order=c.sort_order, children=[]) for c in cats])


@router.post("/categories", response_model=APIResponse[CategorySchema])
async def create_category(
    body: CategoryCreate,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cat = service.create_category(db, body.name, body.parent_id, body.sort_order, current_user.id, request.client.host if request.client else None)
    return APIResponse(data=CategorySchema(id=cat.id, name=cat.name, parent_id=cat.parent_id, sort_order=cat.sort_order, children=[]))


@router.put("/categories/{cat_id}", response_model=APIResponse[CategorySchema])
async def update_category(
    cat_id: str,
    body: CategoryUpdate,
    request: Request,
    current_user: User = Depends(require_knowledge_admin),
    db: Session = Depends(get_db),
):
    cat = service.update_category(db, cat_id, body.name, body.parent_id, body.sort_order, current_user.id, request.client.host if request.client else None)
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    return APIResponse(data=CategorySchema(id=cat.id, name=cat.name, parent_id=cat.parent_id, sort_order=cat.sort_order, children=[]))


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
    tag = service.create_tag(db, body.name, body.color, current_user.id, request.client.host if request.client else None)
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
```

- [ ] **Step 4: 提交**

```bash
git add backend/routers/knowledge.py backend/services/document_service.py backend/schemas.py
git commit -m "feat: add document CRUD, categories, tags APIs with soft delete and audit logging"
```

---

### Task 5.2: 前端 — 文档列表页 + 上传 + 分类管理

**Files:**
- Create: `frontend/src/api/knowledge.ts`
- Create: `frontend/src/views/DocumentList.vue`
- Create: `frontend/src/views/CategoryManage.vue`
- Create: `frontend/src/components/UploadDialog.vue`
- Create: `frontend/src/components/DataState.vue`

- [ ] **Step 1: knowledge.ts API**

```typescript
// frontend/src/api/knowledge.ts

import client from './client'

export interface DocItem {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: string
  char_count: number
  chunk_count: number
  uploaded_by: string
  created_at: string
  tags: string[]
}

export interface CatItem {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
  children: CatItem[]
}

export interface TagItem {
  id: string
  name: string
  color: string
}

export function listDocuments(params: { page?: number; page_size?: number; search?: string; category_id?: string; status?: string }) {
  return client.get<any, { data: { items: DocItem[]; total: number; page: number; page_size: number } }>('/knowledge/documents', { params })
}

export function deleteDocument(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/documents/${id}`)
}

export function listCategories() {
  return client.get<any, { data: CatItem[] }>('/knowledge/categories')
}

export function createCategory(body: { name: string; parent_id?: string }) {
  return client.post<any, { data: CatItem }>('/knowledge/categories', body)
}

export function updateCategory(id: string, body: { name?: string; sort_order?: number }) {
  return client.put<any, { data: CatItem }>(`/knowledge/categories/${id}`, body)
}

export function deleteCategory(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/categories/${id}`)
}

export function listTags() {
  return client.get<any, { data: TagItem[] }>('/knowledge/tags')
}

export function createTag(body: { name: string; color: string }) {
  return client.post<any, { data: TagItem }>('/knowledge/tags', body)
}

export function deleteTag(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/tags/${id}`)
}
```

- [ ] **Step 2: DataState.vue**

```vue
<!-- frontend/src/components/DataState.vue -->
<template>
  <div>
    <div v-if="loading">
      <el-skeleton :rows="5" animated />
    </div>
    <div v-else-if="error" style="text-align: center; padding: 48px">
      <el-result icon="error" :title="error" sub-title="请稍后再试">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重试</el-button>
        </template>
      </el-result>
    </div>
    <div v-else-if="empty" style="text-align: center; padding: 48px">
      <el-result icon="info" :title="emptyText" />
    </div>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
  error: string
  empty: boolean
  emptyText: string
}>()

defineEmits<{ retry: [] }>()
</script>
```

- [ ] **Step 3: DocumentList.vue**

```vue
<!-- frontend/src/views/DocumentList.vue -->
<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h1>文档管理</h1>
      <el-button type="primary" @click="showUpload = true">上传文档</el-button>
    </div>

    <DataState :loading="loading" :error="error" :empty="!loading && !error && documents.length === 0"
      empty-text="还没有文档，上传第一份吧" @retry="fetchData">
      <el-table :data="documents" stripe>
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ready' ? 'success' : row.status === 'error' ? 'danger' : 'warning'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="切片数" width="80" />
        <el-table-column prop="created_at" label="上传时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :total="total"
        :page-size="20"
        layout="total, prev, pager, next"
        @current-change="fetchData"
      />
    </DataState>

    <UploadDialog v-model:visible="showUpload" @done="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listDocuments, deleteDocument } from '@/api/knowledge'
import type { DocItem } from '@/api/knowledge'
import DataState from '@/components/DataState.vue'
import UploadDialog from '@/components/UploadDialog.vue'

const documents = ref<DocItem[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const total = ref(0)
const showUpload = ref(false)

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDocuments({ page: page.value, page_size: 20 })
    documents.value = res.data.items
    total.value = res.data.total
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteDocument(id)
    fetchData()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

onMounted(fetchData)
</script>
```

- [ ] **Step 4: UploadDialog.vue**

```vue
<!-- frontend/src/components/UploadDialog.vue -->
<template>
  <el-dialog :model-value="visible" title="上传文档" @update:model-value="$emit('update:visible', $event)">
    <el-upload
      drag
      :action="`/api/v1/knowledge/documents/upload`"
      :headers="{ Authorization: `Bearer ${token}` }"
      :on-success="handleSuccess"
      :on-error="handleError"
      accept=".pdf,.docx,.doc,.xlsx,.xls"
    >
      <el-icon><UploadFilled /></el-icon>
      <div>拖拽文件到此处或点击上传</div>
      <template #tip>
        <div>支持 PDF、Word (.docx/.doc)、Excel (.xlsx/.xls)</div>
      </template>
    </el-upload>
  </el-dialog>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'

defineProps<{ visible: boolean }>()
defineEmits<{ 'update:visible': [boolean]; done: [] }>()

const token = localStorage.getItem('accessToken') || ''

function handleSuccess() {
  alert('上传成功，正在后台处理')
  location.reload()
}

function handleError(err: any) {
  alert('上传失败: ' + (err.message || '未知错误'))
}
</script>
```

- [ ] **Step 5: CategoryManage.vue（基础 CRUD）**

```vue
<!-- frontend/src/views/CategoryManage.vue -->
<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h1>分类标签管理</h1>
      <div>
        <el-button type="primary" @click="showAddCat = true">新增分类</el-button>
        <el-button type="success" @click="showAddTag = true">新增标签</el-button>
      </div>
    </div>

    <el-row :gutter="24">
      <el-col :span="12">
        <h3>分类列表</h3>
        <el-table :data="categories" stripe>
          <el-table-column prop="name" label="名称" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="danger" @click="handleDeleteCat(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showAddCat" title="新增分类">
          <el-input v-model="newCatName" placeholder="分类名称" />
          <template #footer>
            <el-button @click="showAddCat = false">取消</el-button>
            <el-button type="primary" @click="handleCreateCat">确认</el-button>
          </template>
        </el-dialog>
      </el-col>

      <el-col :span="12">
        <h3>标签列表</h3>
        <div>
          <el-tag
            v-for="tag in tags" :key="tag.id" :color="tag.color"
            closable @close="handleDeleteTag(tag.id)"
            style="margin: 4px"
          >
            {{ tag.name }}
          </el-tag>
        </div>

        <el-dialog v-model="showAddTag" title="新增标签">
          <el-input v-model="newTagName" placeholder="标签名称" />
          <el-color-picker v-model="newTagColor" />
          <template #footer>
            <el-button @click="showAddTag = false">取消</el-button>
            <el-button type="primary" @click="handleCreateTag">确认</el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listCategories, createCategory, deleteCategory, listTags, createTag, deleteTag } from '@/api/knowledge'
import type { CatItem, TagItem } from '@/api/knowledge'

const categories = ref<CatItem[]>([])
const tags = ref<TagItem[]>([])
const showAddCat = ref(false)
const showAddTag = ref(false)
const newCatName = ref('')
const newTagName = ref('')
const newTagColor = ref('#409EFF')

async function fetchData() {
  const [catRes, tagRes] = await Promise.all([listCategories(), listTags()])
  categories.value = catRes.data
  tags.value = tagRes.data
}

async function handleCreateCat() {
  if (!newCatName.value.trim()) return
  await createCategory({ name: newCatName.value.trim() })
  newCatName.value = ''
  showAddCat.value = false
  fetchData()
}

async function handleDeleteCat(id: string) {
  await deleteCategory(id)
  fetchData()
}

async function handleCreateTag() {
  if (!newTagName.value.trim()) return
  await createTag({ name: newTagName.value.trim(), color: newTagColor.value })
  newTagName.value = ''
  showAddTag.value = false
  fetchData()
}

async function handleDeleteTag(id: string) {
  await deleteTag(id)
  fetchData()
}

onMounted(fetchData)
</script>
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/api/knowledge.ts frontend/src/views/DocumentList.vue frontend/src/views/CategoryManage.vue frontend/src/components/UploadDialog.vue frontend/src/components/DataState.vue
git commit -m "feat: add document list, upload dialog, category/tag management pages"
```

---

## Phase 6: 仪表盘

### Task 6.1: 后端 — analytics_service + admin router

**Files:**
- Create: `backend/services/analytics_service.py`
- Create: `backend/routers/admin.py`
- Modify: `backend/schemas.py`

**Interfaces:**
- Produces: `/api/v1/admin/dashboard/stats` 聚合端点

- [ ] **Step 1: analytics_service.py**

```python
# backend/services/analytics_service.py

from datetime import datetime, timedelta
from sqlalchemy import func, text
from core.database import SessionLocal
from models import Document, UsageLog, User
from core.cache import cache


class AnalyticsService:

    CACHE_TTL = 300  # 5 分钟

    @staticmethod
    def get_dashboard_stats() -> dict:
        cached = cache.get("dashboard_stats")
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
            cache.set("dashboard_stats", result, AnalyticsService.CACHE_TTL)
            return result
        finally:
            db.close()
```

- [ ] **Step 2: admin.py router**

```python
# backend/routers/admin.py

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
```

- [ ] **Step 3: user_service.py**

```python
# backend/services/user_service.py

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
```

- [ ] **Step 4: 注册 admin router 到 app.py**

```python
# backend/app.py — 添加

from routers import admin
app.include_router(admin.router)
```

- [ ] **Step 5: 提交**

```bash
git add backend/services/analytics_service.py backend/routers/admin.py backend/services/user_service.py backend/app.py backend/schemas.py
git commit -m "feat: add dashboard stats API, user management, system settings, audit logs"
```

---

### Task 6.2: 前端 — 仪表盘、用户管理、系统设置、操作日志

**Files:**
- Create: `frontend/src/api/admin.ts`
- Create: `frontend/src/views/Dashboard.vue`
- Create: `frontend/src/views/UserManage.vue`
- Create: `frontend/src/views/SystemSettings.vue`
- Create: `frontend/src/views/AuditLogs.vue`
- Create: `frontend/src/components/StatCard.vue`
- Create: `frontend/src/components/TrendChart.vue`

- [ ] **Step 1: admin.ts API**

```typescript
// frontend/src/api/admin.ts

import client from './client'

export function getDashboardStats() {
  return client.get<any, { data: any }>('/admin/dashboard/stats')
}

export function listUsers(params: { page?: number; page_size?: number }) {
  return client.get<any, { data: { items: any[]; total: number; page: number; page_size: number } }>('/admin/users', { params })
}

export function updateUser(id: number, body: { role?: string; is_active?: boolean }) {
  return client.put<any, { data: any }>(`/admin/users/${id}`, body)
}

export function getSettings() {
  return client.get<any, { data: { key: string; value: string }[] }>('/admin/settings')
}

export function updateSettings(body: Record<string, string>) {
  return client.put<any, { data: any }>('/admin/settings', body)
}

export function listAuditLogs(params: { page?: number; page_size?: number; action?: string }) {
  return client.get<any, { data: { items: any[]; total: number; page: number; page_size: number } }>('/admin/audit-logs', { params })
}
```

- [ ] **Step 2: Dashboard.vue**

```vue
<!-- frontend/src/views/Dashboard.vue -->
<template>
  <div>
    <h1>仪表盘</h1>
    <DataState :loading="loading" :error="error" :empty="false" empty-text="" @retry="fetchData">
      <el-row :gutter="16" style="margin-bottom: 24px">
        <el-col :span="6">
          <StatCard title="文档总数" :value="stats.document_count" color="#409EFF" />
        </el-col>
        <el-col :span="6">
          <StatCard title="今日上传" :value="stats.today_upload_count" color="#67C23A" />
        </el-col>
        <el-col :span="6">
          <StatCard title="总问答数" :value="stats.total_queries" color="#E6A23C" />
        </el-col>
        <el-col :span="6">
          <StatCard title="活跃用户" :value="stats.active_users?.length || 0" color="#F56C6C" />
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="16">
          <el-card><TrendChart :data="stats.query_trend" /></el-card>
        </el-col>
        <el-col :span="8">
          <el-card header="热门搜索">
            <div v-for="q in stats.top_queries" :key="q.term" style="padding: 4px 0">
              {{ q.term }} <el-tag size="small">{{ q.count }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '@/api/admin'
import DataState from '@/components/DataState.vue'
import StatCard from '@/components/StatCard.vue'
import TrendChart from '@/components/TrendChart.vue'

const stats = ref<any>({})
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDashboardStats()
    stats.value = res.data
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
```

- [ ] **Step 3: StatCard.vue**

```vue
<!-- frontend/src/components/StatCard.vue -->
<template>
  <el-card shadow="hover">
    <div style="text-align: center">
      <div style="font-size: 28px; font-weight: bold; color: v-bind(color)">{{ value ?? '-' }}</div>
      <div style="color: #999; margin-top: 8px">{{ title }}</div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{ title: string; value: number; color: string }>()
</script>
```

- [ ] **Step 4: TrendChart.vue**

```vue
<!-- frontend/src/components/TrendChart.vue -->
<template>
  <div ref="chartRef" style="width: 100%; height: 300px" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data: { date: string; count: number }[] }>()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || !props.data?.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.data.map((d) => d.date) },
    yAxis: { type: 'value' },
    series: [{ data: props.data.map((d) => d.count), type: 'line', smooth: true, areaStyle: {} }],
  })
  chart.resize()
}

onMounted(render)
watch(() => props.data, render)
onBeforeUnmount(() => chart?.dispose())
</script>
```

- [ ] **Step 5: UserManage.vue**

```vue
<!-- frontend/src/views/UserManage.vue -->
<template>
  <div>
    <h1>用户管理</h1>
    <el-table :data="users" stripe>
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="角色" width="150">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            @change="(val: string) => handleRoleChange(row.id, val)"
          >
            <el-option label="普通用户" value="user" />
            <el-option label="知识管理员" value="knowledge_admin" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="20"
      layout="total, prev, pager, next"
      @current-change="fetchUsers"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listUsers, updateUser } from '@/api/admin'

const users = ref<any[]>([])
const page = ref(1)
const total = ref(0)

async function fetchUsers() {
  const res = await listUsers({ page: page.value })
  users.value = res.data.items
  total.value = res.data.total
}

async function handleRoleChange(userId: number, role: string) {
  await updateUser(userId, { role })
  fetchUsers()
}

onMounted(fetchUsers)
</script>
```

- [ ] **Step 6: SystemSettings.vue**

```vue
<!-- frontend/src/views/SystemSettings.vue -->
<template>
  <div>
    <h1>系统设置</h1>
    <el-form label-width="160px" style="max-width: 600px">
      <el-form-item v-for="s in settings" :key="s.key" :label="s.key">
        <el-input v-model="s.value" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">保存设置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getSettings, updateSettings } from '@/api/admin'

const settings = reactive<any[]>([])

onMounted(async () => {
  const res = await getSettings()
  settings.push(...res.data.map((s: any) => ({ key: s.key, value: s.value })))
})

async function save() {
  const body: Record<string, string> = {}
  settings.forEach((s: any) => { body[s.key] = s.value })
  await updateSettings(body)
  alert('保存成功')
}
</script>
```

- [ ] **Step 7: AuditLogs.vue**

```vue
<!-- frontend/src/views/AuditLogs.vue -->
<template>
  <div>
    <h1>操作日志</h1>
    <el-table :data="logs" stripe>
      <el-table-column prop="action" label="操作" width="150" />
      <el-table-column prop="target_type" label="对象类型" width="120" />
      <el-table-column prop="target_id" label="对象ID" width="200" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="详情">
        <template #default="{ row }">
          {{ JSON.stringify(row.detail).slice(0, 100) }}
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="20"
      layout="total, prev, pager, next"
      @current-change="fetchLogs"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listAuditLogs } from '@/api/admin'

const logs = ref<any[]>([])
const page = ref(1)
const total = ref(0)

async function fetchLogs() {
  const res = await listAuditLogs({ page: page.value })
  logs.value = res.data.items
  total.value = res.data.total
}

onMounted(fetchLogs)
</script>
```

- [ ] **Step 8: 提交**

```bash
git add frontend/src/api/admin.ts frontend/src/views/Dashboard.vue frontend/src/views/UserManage.vue frontend/src/views/SystemSettings.vue frontend/src/views/AuditLogs.vue frontend/src/components/StatCard.vue frontend/src/components/TrendChart.vue
git commit -m "feat: add dashboard, user management, system settings, and audit logs pages"
```

---

## Phase 7: AI 助手增强

### Task 7.1: usage_logs 埋点 + 语音输入迁移

**Files:**
- Modify: `backend/services/agent_service.py`
- Modify: `frontend/src/components/ChatInput.vue`（集成语音）

- [ ] **Step 1: agent_service.py 中增加 usage_logs 写入**

```python
# backend/services/agent_service.py — 在流式响应完成后追加

import uuid
from core.database import SessionLocal
from models import UsageLog

def _log_usage(user_id: int, session_id: str, query: str, has_attachment: bool, tokens_used: int):
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
```

在 `chat_with_agent_stream` 函数末尾调用 `_log_usage`。

- [ ] **Step 2: ChatInput.vue 集成语音（复用现有 voice.js）**

在 ChatInput 中增加语音按钮，调用现有 voice.js 中的 Web Speech API 逻辑。按钮点击触发语音识别，结果回填到输入框。

- [ ] **Step 3: 提交**

```bash
git add backend/services/agent_service.py frontend/src/components/ChatInput.vue
git commit -m "feat: add usage logging and voice input integration"
```

---

## Phase 8: 收尾

### Task 8.1: 回收站页面 + 恢复功能

**Files:**
- Modify: `frontend/src/views/DocumentList.vue`（增加回收站 Tab）
- Modify: `backend/routers/knowledge.py`（增加回收站列表和恢复端点）

- [ ] **Step 1: 后端增加回收站端点**

```python
# backend/routers/knowledge.py — 追加

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
```

- [ ] **Step 2: 前端 DocumentList.vue 增加"回收站"Tab**

在文档列表页顶部增加 `el-tabs`，默认 Tab 为"文档列表"，第二个 Tab 为"回收站"。回收站 Tab 内展示已删除文档，每条有"恢复"按钮。

- [ ] **Step 3: 提交**

```bash
git add backend/routers/knowledge.py frontend/src/views/DocumentList.vue
git commit -m "feat: add document recycle bin with restore functionality"
```

---

### Task 8.2: 企业级生产部署（Nginx 反向代理 + 前后端分离）

**Files:**
- Create: `nginx/nginx.conf`
- Create: `nginx/Dockerfile`
- Modify: `docker-compose.yml`（新增 nginx 服务）
- Modify: `backend/app.py`（生产模式移除 StaticFiles 挂载，保留开发模式）
- Modify: `frontend/vite.config.ts`（生产构建输出配置）
- Modify: `frontend/.env.production`（配置生产环境 API 地址）
- Modify: `README.md`

- [ ] **Step 1: 后端移除生产模式 StaticFiles 挂载**

FastAPI 不再托管前端文件。前端由 Nginx 直接 serve。

```python
# backend/app.py — 修改 create_app() 中的静态文件挂载部分

# 替换原来的 if FRONTEND_DIR.exists(): app.mount(...)
# 开发模式下前端由 Vite dev server 独立运行，不需要挂载
# 生产模式下前端由 Nginx serve，也不需要挂载

# 删除以下内容：
# if FRONTEND_DIR.exists():
#     app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
```

同时将 CORS 从 `allow_origins=["*"]` 改为从环境变量读取：

```python
# backend/app.py — CORS 配置

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Vite 生产构建配置**

```typescript
// frontend/vite.config.ts — 追加 build 配置

export default defineConfig({
  // ... 现有配置
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts'],
          'vue-vendor': ['vue', 'vue-router'],
        },
      },
    },
  },
})
```

- [ ] **Step 3: 前端生产环境变量**

```env
# frontend/.env.production
VITE_API_BASE_URL=/api/v1
```

- [ ] **Step 4: Nginx 配置**

```nginx
# nginx/nginx.conf

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;        # SPA 路由回退
    }

    # API 反向代理到 FastAPI
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持（AI 流式对话需要）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # Swagger 文档
    location /docs {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }

    # 静态资源缓存
    location /assets/ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

- [ ] **Step 5: Nginx Dockerfile**

```dockerfile
# nginx/Dockerfile

FROM nginx:1.27-alpine
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/dist /usr/share/nginx/html
```

- [ ] **Step 6: 更新 docker-compose.yml**

```yaml
# docker-compose.yml — 新增 nginx 服务，删掉原来的端口直接暴露

services:
  postgres:
    # ... 不变，不暴露端口到宿主机

  redis:
    # ... 不变

  milvus:
    # ... 不变

  backend:
    build: ./backend
    expose:
      - "8000"                          # 仅内网可达，不暴露到宿主机
    env_file: .env
    depends_on:
      - postgres
      - redis
      - milvus

  nginx:
    build:
      context: .
      dockerfile: nginx/Dockerfile
    ports:
      - "80:80"                         # 唯一入口
    depends_on:
      - backend
```

- [ ] **Step 7: 后端 Dockerfile**

```dockerfile
# backend/Dockerfile

FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY data/ ./data/

WORKDIR /app/backend
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: 启动脚本**

```bash
# 一键生产部署
cd frontend && npm run build && cd ..
docker compose up -d --build
docker compose ps  # 确认所有服务 running
```

- [ ] **Step 9: 更新 README.md**

完全重写 README：
- 企业级架构图（Nginx → Vue SPA + FastAPI → DB/Milvus）
- 开发模式启动（前端 `npm run dev`，后端 `uvicorn --reload`，Docker Compose 仅启数据层）
- 生产部署命令（`npm run build` + `docker compose up -d`）
- Alembic 迁移命令
- 三种角色说明与预设账号生成方式
- API 文档地址（`http://<host>/docs`）
- 环境变量表（完整列出所有 .env 配置项）

- [ ] **Step 10: 提交**

```bash
git add nginx/ docker-compose.yml backend/app.py backend/Dockerfile frontend/vite.config.ts frontend/.env.production README.md
git commit -m "feat: add enterprise deployment config with Nginx reverse proxy and frontend-backend separation"
```

---

### Task 8.3: 最终集成测试

**Files:**
- Create: `backend/tests/test_integration.py`

- [ ] **Step 1: 编写端到端测试**

```python
# backend/tests/test_integration.py

from fastapi.testclient import TestClient
from app import create_app

app = create_app()
client = TestClient(app)

def test_full_auth_flow():
    # 1. 注册
    resp = client.post("/api/v1/auth/register", json={"username": "e2e_user", "password": "pass123"})
    assert resp.status_code == 200

    # 2. 登录
    resp = client.post("/api/v1/auth/login", json={"username": "e2e_user", "password": "pass123"})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. 获取当前用户
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "e2e_user"

    # 4. 会话列表（空）
    resp = client.get("/api/v1/chat/sessions", headers=headers)
    assert resp.status_code == 200

    # 5. 普通用户访问 admin → 403
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403

def test_knowledge_admin_permissions():
    # 注册知识管理员（需要邀请码）
    import os
    os.environ["ADMIN_INVITE_CODE"] = "test_code"
    # ... 用邀请码注册 knowledge_admin 并测试权限
```

- [ ] **Step 2: 运行全部测试**

```bash
cd backend
uv run pytest tests/ -v
```

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_integration.py
git commit -m "test: add integration tests for auth flow and permissions"
```

---

## 实施顺序总结

| Phase | 内容 | 提交数 |
|---|---|---|
| **Phase 1** | Alembic + 新模型 + 目录重组 + 统一响应 + 路由拆分 | 5 |
| **Phase 2** | 角色迁移 + 权限测试 | 2 |
| **Phase 3** | Vite 脚手架 + Router + Element Plus + API 层 + 布局组件 | 4 |
| **Phase 4** | AI 助手 SPA 迁移（三栏布局 + SSE + 组件） | 1 |
| **Phase 5** | 文档管理（后端 API + 前端 CRUD） | 2 |
| **Phase 6** | 仪表盘 + 用户管理 + 系统设置 + 操作日志 | 2 |
| **Phase 7** | usage_logs 埋点 + 语音输入 | 1 |
| **Phase 8** | 回收站 + 部署配置 + README + 集成测试 | 3 |

总计约 **20 个 Task**，每个 Task 包含 3-8 个 Step。按 Task 逐个推进，每个 Task 结束有独立可测试的交付物。
