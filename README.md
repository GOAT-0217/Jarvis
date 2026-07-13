# Jarvis

> 基于 LangChain Agent + RAG 的企业级 AI 知识助手，支持多模态输入、混合检索与流式对话。

**Version:** v0.0.2 | **License:** MIT | **Python:** 3.12+

---

## 目录

- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [架构概览](#架构概览)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [部署指南](#部署指南)
- [API 参考](#api-参考)
- [核心设计](#核心设计)
- [更新日志](#更新日志)

---

## 快速开始

### 前置条件

- **Python** ≥ 3.12
- **Docker Desktop**（运行 PostgreSQL、Redis、Milvus）
- **包管理**：[uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少配置 LLM 接入：

```env
ARK_API_KEY=your_api_key
MODEL=your_endpoint_id
BASE_URL=https://your-llm-endpoint/v1
```

### 3. 启动基础设施

```bash
docker compose up -d
docker compose ps  # 确认 postgres / redis / milvus 均为 Up
```

### 4. 启动应用

```bash
cd backend
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问：

| URL | 说明 |
|-----|------|
| `http://127.0.0.1:8000/` | 前端页面 |
| `http://127.0.0.1:8000/docs` | Swagger API 文档 |

---

## 功能特性

### 对话与 Agent

- **流式对话**：基于 SSE + ReadableStream 的打字机效果，支持随时终止回答
- **工具调用**：内置知识库检索（`search_knowledge_base`）与天气查询（`get_current_weather`），可扩展
- **会话管理**：多会话切换，自动摘要压缩长上下文，PostgreSQL 持久化 + Redis 缓存
- **认证鉴权**：JWT 登录/注册，RBAC 权限（admin / user），PBKDF2-SHA256 密码哈希

### 语音输入 (v0.0.2)

- 🎤 **语音转文字**：基于浏览器 Web Speech API，Chrome / Edge 原生支持
- 🔄 **双模式切换**：文字 ⇄ 语音一键切换，按住说话松手自动发送
- 📊 **四态视觉反馈**：空闲 / 聆听中（波纹）/ 识别中（旋转）/ 错误（闪烁），配合 AudioContext 提示音
- 🛡 **优雅降级**：权限拒绝或网络不可用时自动切回文字模式；不支持的浏览器隐藏语音按钮

### 附件上传 (v0.0.2)

- ＋ 按钮（管理员可见），点击选择 PDF / Word / Excel 直接上传至知识库
- 实时进度条，复用文档入库全链路（切分 → 向量化 → Milvus 写入）

### RAG 检索增强生成

- **混合检索**：Dense（BGE-M3）+ Sparse（BM25）双路召回，Milvus Hybrid Search + RRF 融合
- **Jina Rerank 精排**：召回后 API 级重排序，支持 `rerank_score` 可视化
- **三级分块 + Auto-merging**：L1 / L2 / L3 滑动窗口切分，仅叶子块向量化，检索后自动合并父块
- **查询重写**：Step-Back / HyDE 双策略 + 路由选择，相关性评分门控按需触发
- **实时思考链路**：检索过程在回答前实时推送（Searching → Grading → Rewriting），彻底消除"静默思考"

### 文档管理

- 上传 PDF / Word / Excel → 自动分块 → 稠密 + 稀疏向量生成 → Milvus 入库
- 重复上传自动清理旧 chunk，BM25 统计增量更新
- 管理员独享上传 / 删除权限，普通用户仅可对话

---

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                        Frontend                          │
│  Vue 3 CDN + marked + highlight.js                       │
│  ├─ Chat UI (SSE streaming, thinking animation)          │
│  ├─ Voice Input (Web Speech API)          ← v0.0.2      │
│  ├─ Attachment Upload (XHR + progress)    ← v0.0.2      │
│  └─ Session / Doc Management                             │
└──────────────┬───────────────────────────────────────────┘
               │  POST /chat/stream (SSE)
               │  REST API (auth / sessions / documents)
               ▼
┌──────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ agent.py    │  │ rag_pipeline │  │ document_loader  │  │
│  │ LangChain   │  │ Hybrid Search│  │ Chunking (L1-L3) │  │
│  │ Agent+tools │  │ Rerank+Grade │  │ milvus_writer    │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                │                    │           │
│  ┌──────┴────────────────┴────────────────────┴────────┐  │
│  │              Data Layer                              │  │
│  │  PostgreSQL ←→ Redis ←→ Milvus (HNSW + SPARSE)      │  │
│  │  SQLAlchemy    cache      Dense + Sparse vectors     │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**请求全链路**：用户输入 → POST `/chat/stream` → Agent 决策 →（命中知识库）→ Hybrid 检索 → Rerank → 评分门控 →（必要时）查询重写 → 二次检索 → Agent 流式生成 → SSE 推送前端

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **AI 引擎** | LangChain + LangGraph Agent |
| **LLM** | OpenAI 兼容协议（火山方舟 / 任意兼容服务） |
| **向量数据库** | Milvus 2.5+（HNSW 稠密 + SPARSE_INVERTED_INDEX 稀疏） |
| **稠密嵌入** | `langchain_huggingface` / BAAI/bge-m3（本地 CPU） |
| **稀疏嵌入** | 自研 BM25（中英混合分词，统计持久化至 `bm25_state.json`） |
| **精排** | Jina Reranker v2（API） |
| **关系数据库** | PostgreSQL + SQLAlchemy ORM |
| **缓存** | Redis（会话 / 父文档热点缓存） |
| **前端** | Vue 3 CDN + marked + highlight.js + Font Awesome |
| **语音** | Web Speech API（浏览器原生，Chrome/Edge） |
| **部署** | Docker Compose（PostgreSQL + Redis + Milvus + Etcd + MinIO） |

---

## 项目结构

```
Jarvis/
├── backend/                     # 后端服务
│   ├── app.py                   # FastAPI 入口、CORS、静态资源挂载
│   ├── api.py                   # 路由：聊天 / 会话 / 文档管理
│   ├── agent.py                 # LangGraph Agent、流式生成、会话摘要
│   ├── auth.py                  # JWT 鉴权、密码哈希、权限检查
│   ├── database.py              # SQLAlchemy 引擎、建表
│   ├── models.py                # ORM：User / ChatSession / ChatMessage / ParentChunk
│   ├── cache.py                 # Redis JSON 缓存封装
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── tools.py                 # Agent 工具：知识库检索 / 天气查询 / RAG 步骤发射
│   ├── rag_pipeline.py          # RAG 全链路：检索 → 评分 → 重写 → 扩展检索
│   ├── rag_utils.py             # 混合检索 / Rerank / Step-Back / HyDE 工具函数
│   ├── embedding.py             # 稠密向量（BGE-M3）+ 稀疏向量（BM25）服务
│   ├── document_loader.py       # PDF/Word 解析与三级分块
│   ├── milvus_client.py         # Milvus 集合定义、Hybrid Search、分页查询
│   ├── milvus_writer.py         # 向量写入（稠密+稀疏同步）
│   └── parent_chunk_store.py    # 父级分块仓储（PostgreSQL + Redis）
├── frontend/                    # 前端（纯静态，CDN 依赖）
│   ├── index.html               # Vue 3 SPA 主页面
│   ├── script.js                # Vue 应用：聊天 / 会话 / 文档 / 语音 / 附件
│   ├── voice.js                 # Web Speech API 封装（v0.0.2）
│   └── style.css                # 全局样式 + 语音动画 + 附件进度条
├── data/                        # 运行时数据
│   ├── bm25_state.json          # BM25 词表与统计状态
│   └── documents/               # 上传文档原文件
├── docker-compose.yml           # 基础设施编排
├── pyproject.toml               # Python 依赖
├── .env.example                 # 环境变量模板
└── README.md
```

---

## 部署指南

### 环境变量参考

| 分类 | 变量 | 说明 | 必填 |
|------|------|------|:--:|
| **LLM** | `ARK_API_KEY` | API 密钥 | ✅ |
| | `MODEL` | 模型 / 端点 ID | ✅ |
| | `BASE_URL` | API 地址（OpenAI 兼容） | ✅ |
| **向量** | `EMBEDDING_MODEL` | 本地嵌入模型（默认 `BAAI/bge-m3`） | |
| | `EMBEDDING_DEVICE` | `cpu` / `cuda` | |
| | `DENSE_EMBEDDING_DIM` | 稠密向量维度（默认 1024） | |
| **Milvus** | `MILVUS_HOST` | Milvus 地址（默认 `127.0.0.1`） | |
| | `MILVUS_PORT` | Milvus 端口（默认 `19530`） | |
| **数据库** | `DATABASE_URL` | PostgreSQL 连接串 | ✅ |
| | `REDIS_URL` | Redis 连接串 | ✅ |
| **鉴权** | `JWT_SECRET_KEY` | JWT 签名密钥 | ✅ |
| | `ADMIN_INVITE_CODE` | 管理员注册邀请码 | |
| **Rerank** | `RERANK_MODEL` | Rerank 模型名 | |
| | `RERANK_BINDING_HOST` | Rerank API 地址 | |
| **工具** | `AMAP_API_KEY` | 高德天气 API 密钥 | |

### Docker 端口映射

| 端口 | 服务 |
|------|------|
| `5432` | PostgreSQL |
| `6379` | Redis |
| `19530` | Milvus |
| `9091` | Milvus 健康检查 |
| `9000` | MinIO API |
| `9001` | MinIO Console |
| `8080` | Attu（Milvus GUI） |

---

## API 参考

### 鉴权

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录（返回 Bearer Token） |
| GET | `/auth/me` | 当前用户信息 |

### 聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 非流式对话 |
| POST | `/chat/stream` | 流式对话（SSE，`text/event-stream`） |

### 会话

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sessions` | 当前用户会话列表 |
| GET | `/sessions/{id}` | 会话消息历史 |
| DELETE | `/sessions/{id}` | 删除会话 |

### 文档（需 admin 权限）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/documents` | 已入库文档列表 |
| POST | `/documents/upload` | 上传文档 |
| DELETE | `/documents/{filename}` | 删除文档及向量 |

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

### 跨线程事件调度

RAG 工具在线程池中同步执行，通过 **Global Loop Capture + `call_soon_threadsafe`** 模式将步骤事件安全地注入主线程的 `asyncio.Queue`，实现工具执行期间的实时前端推送。

---

## 更新日志

### v0.0.2 — 2026-07-13 语音输入与附件上传

新增前端语音输入和附件上传能力，面向老人和不识字的儿童用户。

- **语音输入**：基于 Web Speech API（`voice.js`），Chrome / Edge 原生支持。点击 🎤 切换语音模式，按住说话松手自动发送，点击 ⌨ 切回文字模式。
- **视觉反馈**：四态交互（空闲 / 聆听中 / 识别中 / 错误），波纹动画 + 旋转加载 + 错误闪烁 + AudioContext 提示音。
- **附件上传**：输入区 ＋ 按钮（管理员可见），点击选择 PDF / Word / Excel 上传至知识库，带进度条。
- **错误降级**：权限 / 网络不可用时自动切回文字模式；不支持的浏览器隐藏语音按钮。

**范围**：纯前端（`voice.js` 新增，`script.js` / `index.html` / `style.css` 修改），后端未变。

### v0.0.1 — 2026-04-08 本地嵌入与 BM25 持久化

- 稠密向量切换为 `langchain_huggingface` 本地模型（默认 `BAAI/bge-m3`）
- BM25 词表 + 统计持久化至 `bm25_state.json`，入库/删除增量更新
- Milvus `query_all` 分页查询，修复单次 limit 过大导致的 RPC 报错

### 更早版本

| 日期 | 里程碑 |
|------|--------|
| 2026-03-21 | 认证 + 数据库 + 缓存：JWT / PostgreSQL / Redis / RBAC |
| 2026-03-13 | 三级分块 + Auto-merging：L1/L2/L3，Leaf-only 向量化 |
| 2026-02-19 | RAG 实时思考链路修复：跨线程事件调度 |
