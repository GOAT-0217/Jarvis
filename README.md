# Jarvis

> 基于 LangChain Agent + RAG 的多模态企业级 AI 知识助手，支持多模态输入、混合检索与流式对话。

**Version:** v1.0.1 | **License:** MIT | **Python:** 3.12+

---

## 目录

- [架构概览](#架构概览)
- [快速开始（开发模式）](#快速开始开发模式)
- [生产部署](#生产部署)
- [角色与权限](#角色与权限)
- [数据库迁移](#数据库迁移)
- [API 参考](#api-参考)
- [环境变量](#环境变量)
- [核心设计](#核心设计)
- [更新日志](#更新日志)

---

## 架构概览

### 企业级部署架构

```
                    ┌──────────────────────────────┐
                    │         Nginx :80              │
                    │    (反向代理 + 静态文件服务)      │
                    └─────┬────────────┬─────────────┘
                          │            │
              /assets/*   │   /api/*   │   /docs
              /           │            │
          ┌───────────────┘            └───────────────┐
          ▼                                            ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│    Vue 3 SPA (静态)      │              │    FastAPI (backend:8000) │
│    Element Plus         │              │    LangChain Agent       │
│    ECharts              │              │    RAG Pipeline          │
│    /usr/share/nginx/html│              │    JWT Auth              │
└─────────────────────────┘              └───────────┬─────────────┘
                                                     │
                          ┌──────────────────────────┼──────────────────────┐
                          │              Data Layer  │                      │
                          ▼                          ▼                      ▼
                   ┌─────────────┐          ┌──────────────┐       ┌──────────────┐
                   │ PostgreSQL  │          │    Redis      │       │    Milvus     │
                   │ :5432       │          │    :6379      │       │    :19530     │
                   │ (会话+用户)  │          │   (缓存)      │       │  (向量检索)   │
                   └─────────────┘          └──────────────┘       └──────────────┘
```

**请求全链路**：用户输入 → Nginx 反向代理 → FastAPI `/api/v1/chat/stream` → Agent 决策 →（命中知识库）→ Hybrid 检索 → Rerank → 评分门控 →（必要时）查询重写 → 二次检索 → Agent 流式生成 → SSE 推送前端

### 开发模式架构

```
┌───────────────┐      ┌────────────────┐
│ Vite Dev Srv  │      │ Uvicorn :8000   │
│ :5173         │ ──── │ --reload        │
│ (HMR 热更新)  │/api  │ (自动重载)      │
└───────────────┘      └──────┬─────────┘
                              │
          ┌───────────────────┼────────────────────┐
          ▼                   ▼                    ▼
   Docker Compose: PostgreSQL | Redis | Milvus + Etcd + MinIO
```

---

## 快速开始（开发模式）

### 前置条件

- **Docker Desktop**（运行全部服务）
- **uv**（可选，仅本地调试后端时需安装）
- **Node.js >= 18**（可选，仅本地调试前端时需安装）

### 1. 配置环境变量

> 以下所有命令均在**项目根目录** `Jarvis/` 下执行。

```bash
cp .env.example .env
```

编辑 `.env`，至少配置 LLM 接入：

```env
ARK_API_KEY=your_api_key
MODEL=your_endpoint_id
BASE_URL=https://your-llm-endpoint/v1
```

### 2. 一键启动

```bash
docker compose --profile dev up -d
```

### 3. 访问

| URL | 说明 |
|-----|------|
| `http://localhost:5173` | 前端页面（Vite HMR 热更新） |
| `http://localhost:8000/docs` | Swagger API 文档 |
| `http://localhost:8080` | Attu（Milvus GUI） |

---

## 生产部署

> 以下所有命令均在**项目根目录** `Jarvis/` 下执行。

### 一键部署

```bash
# 1. 构建前端
cd frontend && npm run build && cd ..

# 2. 启动全部服务
docker compose --profile prod up -d --build
docker compose ps  # 确认全部服务均为 Up
```

访问 `http://localhost`（Nginx :80 统一入口）。

### 访问

生产环境所有流量通过 Nginx（`:80`）统一入口：

| URL | 说明 |
|-----|------|
| `http://<host>/` | 前端页面 |
| `http://<host>/docs` | Swagger API 文档 |
| `http://<host>/api/v1/health` | 健康检查 |

### 服务清单

| 服务 | 容器名 | 端口暴露 | 说明 |
|------|--------|:--------:|------|
| nginx | — | **80** | 反向代理 + 静态文件，唯一对外入口 |
| backend | — | — | FastAPI，仅内网可达 |
| postgres | supermew-postgres | 5432 | 关系数据库 |
| redis | supermew-redis | 6379 | 缓存 |
| milvus-standalone | milvus-standalone | 19530 | 向量数据库 |
| milvus-etcd | milvus-etcd | — | Milvus 元数据 |
| milvus-minio | milvus-minio | 9000/9001 | Milvus 对象存储 |
| milvus-attu | milvus-attu | 8080 | Milvus GUI |

---

## 角色与权限

系统内置三种角色：

| 角色 | 注册方式 | 权限 |
|------|---------|------|
| `user` | 直接注册，无需邀请码 | 对话、会话管理 |
| `knowledge_admin` | 注册时选择 + 填写邀请码 | user 权限 + 文档上传/删除、查看统计 |
| `super_admin` | 注册时选择 + 填写邀请码 | knowledge_admin 权限 + 用户管理、系统设置 |

### 预设管理员账号

在 `.env` 中设置 `ADMIN_INVITE_CODE`（例如 `ADMIN_INVITE_CODE=jarv1s-adm1n-2026`），然后用该邀请码注册管理员账号：

```bash
# 通过 API 注册 super_admin
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password", "role": "super_admin", "admin_code": "jarv1s-adm1n-2026"}'
```

也可以使用前端注册页面，选择"超级管理员"角色并填写邀请码。

---

## 数据库迁移

使用 Alembic 管理数据库 schema 变更：

```bash
# 应用所有迁移（生产/开发均需执行）
cd backend
uv run alembic upgrade head

# 生成新迁移（schema 变更后）
uv run alembic revision --autogenerate -m "描述此次变更"

# 回退一个版本
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current
```

---

## API 参考

### 鉴权

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录（返回 Bearer Token） |
| GET | `/api/v1/auth/me` | 当前用户信息 |

### 聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 非流式对话 |
| POST | `/api/v1/chat/stream` | 流式对话（SSE，`text/event-stream`） |

### 会话

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions` | 当前用户会话列表 |
| GET | `/api/v1/sessions/{id}` | 会话消息历史 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话 |

### 文档（需 knowledge_admin 或以上权限）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/documents` | 已入库文档列表 |
| POST | `/api/v1/documents/upload` | 上传文档 |
| DELETE | `/api/v1/documents/{filename}` | 删除文档及向量 |

### 管理（需 super_admin 权限）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/users` | 用户列表 |
| PUT | `/api/v1/admin/users/{id}` | 修改用户角色/状态 |
| DELETE | `/api/v1/admin/users/{id}` | 删除用户 |
| GET | `/api/v1/admin/stats` | 系统统计概览 |

完整 Swagger 文档：`http://<host>/docs`

---

## 环境变量

完整的环境变量列表（在 `.env` 中配置）：

| 分类 | 变量 | 说明 | 默认值 | 必填 |
|------|------|------|--------|:--:|
| **LLM** | `ARK_API_KEY` | API 密钥 | — | ✅ |
| | `MODEL` | 模型 / 端点 ID | — | ✅ |
| | `BASE_URL` | API 地址（OpenAI 兼容） | — | ✅ |
| **向量** | `EMBEDDING_MODEL` | 本地嵌入模型 | `BAAI/bge-m3` | |
| | `EMBEDDING_DEVICE` | `cpu` 或 `cuda` | `cpu` | |
| | `DENSE_EMBEDDING_DIM` | 稠密向量维度 | `1024` | |
| **Milvus** | `MILVUS_HOST` | Milvus 地址 | `127.0.0.1` | |
| | `MILVUS_PORT` | Milvus 端口 | `19530` | |
| **数据库** | `DATABASE_URL` | PostgreSQL 连接串 | — | ✅ |
| | `REDIS_URL` | Redis 连接串 | — | ✅ |
| **鉴权** | `JWT_SECRET_KEY` | JWT 签名密钥 | — | ✅ |
| | `ADMIN_INVITE_CODE` | 管理员注册邀请码 | — | |
| | `JWT_ALGORITHM` | JWT 签名算法 | `HS256` | |
| | `JWT_EXPIRE_HOURS` | Token 过期时间（小时） | `24` | |
| **CORS** | `CORS_ORIGINS` | 允许的来源（逗号分隔） | `http://localhost:5173` | |
| **Rerank** | `RERANK_MODEL` | Rerank 模型名 | — | |
| | `RERANK_BINDING_HOST` | Rerank API 地址 | — | |
| **工具** | `AMAP_API_KEY` | 高德天气 API 密钥 | — | |
| **服务** | `HOST` | FastAPI 监听地址 | `0.0.0.0` | |
| | `PORT` | FastAPI 监听端口 | `8000` | |

---

## 核心设计

### RAG 流水线

```
用户查询 → Hybrid 检索 (Dense+Sparse+RRF)
         → Jina Rerank 精排
         → Auto-merging (L3→L2→L1)
         → 相关性评分 (grade_documents)
              ├─ yes → 生成回答
              └─ no  → 查询重写 (Step-Back / HyDE)
                       → 扩展检索 → 去重 → 生成回答
```

### 三级分块策略

| 层级 | Token 范围 | 存储位置 | 用途 |
|------|-----------|---------|------|
| L1 | 2000–3000 | PostgreSQL DocStore | 最大上下文窗口 |
| L2 | 1000–1500 | PostgreSQL DocStore | 中等粒度合并 |
| L3 | 512–1024 | Milvus（向量化） | 检索召回入口 |

### 流式 SSE 协议

```
data: {"type":"rag_step","step":{"icon":"🔍","label":"正在检索..."}}\n\n
data: {"type":"content","content":"答案片段"}\n\n
data: {"type":"trace","rag_trace":{...}}\n\n
data: [DONE]\n\n
```

### 功能特性

- **流式对话**：SSE + ReadableStream 打字机效果，支持随时终止回答
- **工具调用**：内置知识库检索（`search_knowledge_base`）与天气查询（`get_current_weather`）
- **会话管理**：多会话切换，自动摘要压缩长上下文，PostgreSQL + Redis 双层存储
- **认证鉴权**：JWT 登录/注册，RBAC 三角色权限，PBKDF2-SHA256 密码哈希
- **语音输入**：Web Speech API（Chrome / Edge 原生支持），四态视觉反馈，优雅降级
- **附件上传**：PDF / Word / Excel 上传至知识库，实时进度条
- **混合检索**：Dense（BGE-M3）+ Sparse（BM25）双路召回，Milvus Hybrid Search + RRF 融合
- **查询重写**：Step-Back / HyDE 双策略 + 路由选择，相关性评分门控按需触发

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **反向代理** | Nginx 1.27 |
| **后端框架** | FastAPI + Uvicorn |
| **AI 引擎** | LangChain + LangGraph Agent |
| **LLM** | OpenAI 兼容协议（火山方舟 / 任意兼容服务） |
| **向量数据库** | Milvus 2.5+（HNSW 稠密 + SPARSE_INVERTED_INDEX 稀疏） |
| **稠密嵌入** | `langchain_huggingface` / BAAI/bge-m3（本地 CPU） |
| **稀疏嵌入** | 自研 BM25（中英混合分词，统计持久化至 `bm25_state.json`） |
| **精排** | Jina Reranker v2（API） |
| **关系数据库** | PostgreSQL + SQLAlchemy ORM |
| **缓存** | Redis（会话 / 父文档热点缓存） |
| **前端** | Vue 3 + Vite + Element Plus + ECharts |
| **语音** | Web Speech API（浏览器原生，Chrome/Edge） |
| **部署** | Docker Compose + Nginx 反向代理 |

---

## 项目结构

```
Jarvis/
├── nginx/
│   ├── Dockerfile                 # Nginx 镜像（serve 前端 + 反向代理后端）
│   └── nginx.conf                 # Nginx 配置（SPA 路由、API 代理、SSE）
├── backend/
│   ├── Dockerfile                 # 后端生产镜像
│   ├── app.py                     # FastAPI 入口、CORS、异常处理
│   ├── alembic.ini                # Alembic 配置
│   ├── alembic/                   # 数据库迁移脚本
│   │   └── versions/
│   ├── core/
│   │   ├── database.py            # SQLAlchemy 引擎、建表
│   │   └── security.py            # JWT 鉴权、密码哈希、角色解析
│   ├── routers/
│   │   ├── admin.py               # 管理接口（用户管理、统计）
│   │   ├── auth.py                # 注册/登录/当前用户
│   │   ├── chat.py                # 聊天接口（流式 + 非流式）
│   │   └── knowledge.py           # 文档上传/删除/查询
│   ├── services/
│   │   └── user_service.py        # 用户业务逻辑
│   ├── models.py                  # SQLAlchemy ORM 模型
│   ├── schemas.py                 # Pydantic 请求/响应模型
│   ├── agent.py                   # LangGraph Agent、流式生成、会话摘要
│   ├── tools.py                   # Agent 工具：知识库检索 / 天气查询
│   ├── rag_pipeline.py            # RAG 全链路：检索 → 评分 → 重写 → 扩展检索
│   ├── rag_utils.py               # 混合检索 / Rerank / Step-Back / HyDE
│   ├── embedding.py               # 稠密向量（BGE-M3）+ 稀疏向量（BM25）
│   ├── document_loader.py         # PDF/Word 解析与三级分块
│   ├── milvus_client.py           # Milvus 集合定义、Hybrid Search
│   ├── milvus_writer.py           # 向量写入（稠密+稀疏同步）
│   └── parent_chunk_store.py      # 父级分块仓储（PostgreSQL + Redis）
├── frontend/
│   ├── .env.production            # 生产环境 API 地址
│   ├── vite.config.ts             # Vite 配置（代理、构建分块）
│   └── src/
│       ├── main.ts                # Vue 入口
│       ├── App.vue                # 根组件
│       ├── router/index.ts        # 路由配置
│       ├── api/                   # HTTP 请求封装
│       ├── composables/           # 组合式函数（useAuth / useChat）
│       ├── components/            # 可复用组件
│       └── views/                 # 页面视图
├── data/
│   ├── bm25_state.json            # BM25 词表与统计状态
│   └── documents/                 # 上传文档原文件
├── docker-compose.yml             # 完整服务编排
├── pyproject.toml                 # Python 依赖
├── .env.example                   # 环境变量模板
└── README.md
```

---

## 更新日志

### v1.0.1 — 2026-07-16 全栈架构重构

> **Release Theme:** Enterprise-Grade Fullstack Architecture

本次发布是 Jarvis 从原型阶段迈向企业级产品的重要里程碑。我们将原有的单页 CDN 应用重构为真正的前后端分离架构，引入了模块化后端服务层、基于角色的访问控制（RBAC）三权分立模型、以及面向运营的管理后台。

---

#### 🏗️ 架构变更（Breaking Changes）

- **前后端分离部署**：前端由 FastAPI `StaticFiles` 托管改为 Nginx 反向代理 + 独立静态资源服务。FastAPI 专注 API，Nginx 作为唯一流量入口，承担 SSL 终结、缓存策略与路由分发。
- **API 路径迁移**：所有接口前缀统一为 `/api/v1/`。旧路径（`/auth/login`、`/chat`、`/documents` 等）已全部移除，无向后兼容重定向。详见 [API 参考](#api-参考)。
- **角色重命名**：`admin` 角色拆分为 `super_admin`（超级管理员）和 `knowledge_admin`（知识管理员）。升级前需执行 Alembic 迁移：`alembic upgrade head`，该迁移会自动将现有 `admin` 用户转为 `super_admin`。
- **数据库迁移接管**：`Base.metadata.create_all()` 自动建表已移除，Alembic 为唯一的 Schema 管理工具。首次部署必须运行 `alembic upgrade head`，否则应用启动后首次请求将报错。

#### ✨ 新增功能

- **管理后台（Dashboard）**：仪表盘首页展示文档总数、今日上传量、问答量趋势（ECharts 折线图）、热门搜索词 TOP 5、活跃用户排行。数据走 PostgreSQL 聚合 + Redis 5 分钟缓存。
- **文档管理中心**：文档 CRUD、多条件筛选（分类/状态/搜索）、异步向量化处理（FastAPI `BackgroundTasks`）、重新索引、回收站（软删除 + 恢复）。支持 PDF / Word / Excel。
- **分类与标签系统**：两级分类树 + 扁平标签，各自支持软删除。标签颜色可自定义。
- **用户管理**：超管可查看用户列表、分配角色（`user` / `knowledge_admin` / `super_admin`）、停用账号。
- **系统设置**：键值对配置表单（模型名称、Temperature、检索阈值、语音开关、日志保留天数），持久化至 `system_settings` 表。
- **操作日志（Audit Log）**：所有后台管理操作（文档上传/删除、用户角色变更、系统设置修改）写入 `audit_logs` 表，JSONB 存储变更详情。仅超级管理员可查看，不可编辑或删除。
- **使用统计（Usage Logs）**：每次流式 AI 问答结束时记录用户、会话、查询摘要、附件标记。为后续成本核算和用户行为分析提供数据基础。

#### 🛠️ 工程改进

- **后端模块化**：单体 `api.py`（459 行）拆分为 `routers/` → `services/` → `core/` 三层架构，每层职责单一。
  - `routers/`: `auth.py` · `chat.py` · `knowledge.py` · `admin.py` · `users.py`
  - `services/`: `agent_service.py` · `rag_service.py` · `document_service.py` · `user_service.py` · `analytics_service.py`
  - `core/`: `database.py` · `cache.py` · `milvus_client.py` · `embedding.py` · `security.py`
- **前端现代化**：CDN Vue 3 Options API → Vite + Vue 3 Composition API + TypeScript + Vue Router 4 + Element Plus。84 个 `.vue` / `.ts` 文件，零 `any` 类型逃逸。
- **统一响应格式**：所有接口返回 `{code: int, message: str, data: T | null}`。分页统一为 `{items: T[], total: int, page: int, page_size: int}`。异常由全局 handler 统一序列化。
- **权限模型升级**：`Depends(get_current_user)` → `Depends(require_knowledge_admin)` → `Depends(require_super_admin)` 三级权限注入，路由声明即权限声明，消除分散的 `if role != 'admin'` 防御代码。
- **数据库 7 张新表**：`documents` · `categories` · `tags` · `document_tags` · `system_settings` · `usage_logs` · `audit_logs`，全部通过 Alembic 自动生成迁移。
- **索引策略**：对高频查询列（`documents.status + deleted_at`、`usage_logs.created_at`、`audit_logs.created_at` 等）建立复合索引。
- **CORS 安全加固**：`allow_origins` 从 `["*"]` 改为环境变量 `CORS_ORIGINS` 控制，生产环境按需配置允许域名。
- **部署容器化**：新增 `nginx/Dockerfile`、`backend/Dockerfile`，`docker compose up -d --build` 一键编排全部 5 个服务（Nginx + FastAPI + PostgreSQL + Redis + Milvus）。

#### 🚀 v1.0.1 更新内容（2026-07-16）

**AI & 对话**

- **Agent 思考链可视化** — 工具调用、RAG 检索步骤实时展示，可折叠查看
- **Loop Engineer 智能追问** — 参数不全时生成候选选项（回复数字即可），最多 3 轮追问后兜底回复
- **会话自动总结** — 对话结束后取首条消息作为标题，支持重命名、删除
- **历史会话按时间分组** — 今天 / 昨天 / 本周 / 本月 / 更早，相对时间戳
- **省份级天气过滤** — 输入"河南"不直接查天气，先列出郑州、洛阳等候选城市

**文档管理**

- **文档分类体系** — 上传时选分类，列表页彩色标签 + 分类筛选 Tab，上传弹窗内联新建分类
- **文档标签系统** — 每文档最多 5 个标签，上传时选择，列表页内联增删，支持自定义新建标签
- **全局搜索框** — 文档管理、分类标签页均支持关键词搜索

**仪表盘**

- **3 张新统计图**：每日上传类别趋势（折线）、标签使用趋势（折线）、文件类别分布（环形饼图）
- 每 30 秒自动刷新数据

**用户**

- **开放注册** — 用户名 + 昵称 + 邮箱，默认 `user` 角色
- **自助修改密码** — 右上角下拉菜单入口

**UI**

- **全站暗色主题** — GitHub 风格深色侧边栏 + 毛玻璃顶栏 + 柔和内容区
- **DeepSeek 风格聊天页** — v0.0.2 青紫渐变气泡 + 毛玻璃输入框

#### ⚠️ 已知限制（Known Issues）

- 文档重新上传/重新索引时不会清理旧的 Milvus 向量和 BM25 统计，可能导致检索返回陈旧数据。将在 v1.0.2 修复。
- 软删除的文档不会清理 Milvus 中的关联向量，向量检索可能仍命中"已删除"文档。将在 v1.0.2 修复。
- `usage_logs.tokens_used` 当前固定记录为 0，上游 Agent 未返回 token 计数字段。成本核算功能需等待模型接口升级。
- 前端测试（Vitest + Playwright E2E）暂未纳入 CI，列于后续迭代计划。

#### 🔄 升级指南（Upgrade from v0.0.2）

```bash
# 1. 拉取最新代码
git pull origin master

# 2. 安装新依赖
cd frontend && npm install && cd ..

# 3. 执行数据库迁移（将 admin → super_admin）
cd backend && uv run alembic upgrade head && cd ..

# 4. 构建前端
cd frontend && npm run build && cd ..

# 5. 重启服务栈
docker compose up -d --build

# 6. 验证
curl http://localhost/api/v1/auth/me
```

---

### v0.0.2 — 2026-07-13 语音输入与附件上传

新增前端语音输入和附件上传能力，面向老人和不识字的儿童用户。

- **语音输入**：基于 Web Speech API（`voice.js`），Chrome / Edge 原生支持
- **视觉反馈**：四态交互（空闲 / 聆听中 / 识别中 / 错误），波纹动画 + AudioContext 提示音
- **附件上传**：输入区 ＋ 按钮（管理员可见），PDF / Word / Excel 上传至知识库
- **错误降级**：权限 / 网络不可用时自动切回文字模式

### v0.0.1 — 2026-04-08 本地嵌入与 BM25 持久化

- 稠密向量切换为 `langchain_huggingface` 本地模型（默认 `BAAI/bge-m3`）
- BM25 词表 + 统计持久化至 `bm25_state.json`，入库/删除增量更新
- Milvus `query_all` 分页查询

### 更早版本

| 日期 | 里程碑 |
|------|--------|
| 2026-03-21 | 认证 + 数据库 + 缓存：JWT / PostgreSQL / Redis / RBAC |
| 2026-03-13 | 三级分块 + Auto-merging：L1/L2/L3，Leaf-only 向量化 |
| 2026-02-19 | RAG 实时思考链路修复：跨线程事件调度 |
