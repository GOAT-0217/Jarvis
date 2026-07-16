# 企业 AI 知识工坊 — 全栈重构设计文档

**版本:** v0.1.0  
**日期:** 2026-07-16  
**状态:** 待审阅  

---

## 1. 产品概览

### 1.1 定位

企业 AI 知识工坊 —— 面向企业内部的知识管理平台，提供文档智能入库、AI 检索问答、后台运营管理三大核心能力。

### 1.2 用户角色

| 角色 | 权限范围 |
|---|---|
| **普通用户** (user) | AI 对话问答、浏览知识库 |
| **知识管理员** (knowledge_admin) | 以上权限 + 上传/管理文档、分类标签管理、查看仪表盘 |
| **超级管理员** (super_admin) | 全部权限 + 用户管理、系统设置 |

### 1.3 页面清单

| 页面 | 路由 | 可见角色 |
|---|---|---|
| 登录/注册 | `/login` | 所有人（未登录） |
| AI 助手 | `/chat` | 全部 |
| 仪表盘 | `/dashboard` | 知识管理员、超管 |
| 文档列表 | `/knowledge` | 知识管理员、超管 |
| 分类标签管理 | `/knowledge/categories` | 知识管理员、超管 |
| 用户管理 | `/users` | 超管 |
| 系统设置 | `/settings` | 超管 |
| 操作日志 | `/audit-logs` | 超管 |

---

## 2. 技术架构

### 2.1 总览

```
浏览器
  │
  ├── Vue 3 SPA（Vite + TypeScript + Vue Router + Element Plus + ECharts）
  │
  ▼ HTTP + SSE
FastAPI (:8000)
  ├── routers/     ← 路由层：参数校验、权限注入、HTTP 响应
  ├── services/    ← 服务层：全部业务逻辑
  └── core/        ← 基础设施：DB、Cache、Milvus、Embedding、JWT
  │
  ▼
Docker Compose → PostgreSQL / Redis / Milvus
```

### 2.2 前端技术栈

| 层 | 选型 |
|---|---|
| 框架 | Vue 3（Composition API + `<script setup lang="ts">`） |
| 语言 | TypeScript |
| 构建工具 | Vite |
| 路由 | Vue Router 4 |
| UI 组件库 | Element Plus |
| 图表 | ECharts |
| HTTP 客户端 | Axios（统一拦截器） |
| 样式 | Element Plus SCSS 变量定制 + scoped CSS |

### 2.3 后端技术栈

| 层 | 选型 |
|---|---|
| 框架 | FastAPI (Python 3.12+) |
| ORM | SQLAlchemy |
| 数据库迁移 | Alembic |
| 向量库 | Milvus (pymilvus) |
| 缓存 | Redis |
| LLM 框架 | LangChain (Agent + RAG) |
| 认证 | JWT (python-jose) |

### 2.4 部署方式

- **开发时:** Vite dev server (:5173) 通过 proxy 转发 `/api/*` 到 FastAPI (:8000)
- **生产时:** `vite build` 产出静态文件，FastAPI 通过 `StaticFiles` 挂载，单进程单端口部署
- **基础设施:** Docker Compose 管理 PostgreSQL、Redis、Milvus

---

## 3. 项目结构

```
jarvis/
├── backend/
│   ├── app.py                 # FastAPI 工厂函数、中间件、StaticFiles 挂载
│   ├── routers/               # HTTP 路由层
│   │   ├── __init__.py
│   │   ├── auth.py            # 登录、注册、Token 刷新
│   │   ├── chat.py            # AI 对话 (SSE)、会话管理
│   │   ├── knowledge.py       # 文档 CRUD、分类、标签
│   │   ├── users.py           # 用户管理 (超管)
│   │   └── admin.py           # 仪表盘统计、系统设置、操作日志
│   ├── services/              # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── agent_service.py   # LangChain Agent 对话封装
│   │   ├── rag_service.py     # 知识库检索（向量 + 关键词混合）
│   │   ├── document_service.py # 文档上传、解析、向量化、分类标签
│   │   ├── user_service.py    # 用户 CRUD、角色管理
│   │   └── analytics_service.py # 仪表盘统计聚合
│   ├── core/                  # 基础设施层
│   │   ├── __init__.py
│   │   ├── database.py        # PostgreSQL 连接 + session 管理
│   │   ├── cache.py           # Redis 缓存
│   │   ├── milvus_client.py   # Milvus 向量库管理
│   │   ├── embedding.py       # 文本向量化服务
│   │   └── security.py        # JWT 生成/校验、角色依赖注入
│   ├── models.py              # SQLAlchemy ORM 模型
│   ├── schemas.py             # Pydantic 请求/响应模型
│   └── alembic/               # 数据库迁移脚本
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts            # Vue 应用入口
│   │   ├── App.vue            # 根组件
│   │   ├── router/
│   │   │   └── index.ts       # 路由配置 + 守卫
│   │   ├── api/               # API 请求封装层
│   │   │   ├── client.ts      # Axios 实例、拦截器
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   ├── knowledge.ts
│   │   │   └── admin.ts
│   │   ├── views/             # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── ChatAssistant.vue
│   │   │   ├── DocumentList.vue
│   │   │   ├── CategoryManage.vue
│   │   │   ├── UserManage.vue
│   │   │   ├── SystemSettings.vue
│   │   │   └── AuditLogs.vue
│   │   ├── components/        # 可复用组件
│   │   │   ├── AppLayout.vue      # 主布局（侧边栏 + Header + 内容区）
│   │   │   ├── SidebarMenu.vue    # 角色感知侧边栏
│   │   │   ├── HeaderBar.vue      # 面包屑 + 用户下拉
│   │   │   ├── SessionList.vue    # AI 助手左侧会话列表
│   │   │   ├── MessageBubble.vue  # 消息气泡（Markdown 渲染）
│   │   │   ├── ChatInput.vue      # 输入区（文字 + 语音 + 附件）
│   │   │   ├── AttachmentPreview.vue
│   │   │   ├── StatCard.vue       # 统计数字卡片
│   │   │   ├── TrendChart.vue     # ECharts 折线图封装
│   │   │   ├── DataState.vue      # 三态容器（加载/空/错/正常）
│   │   │   └── UploadDialog.vue   # 文档上传弹窗
│   │   ├── composables/       # 组合式函数
│   │   │   ├── useAuth.ts     # 登录态管理
│   │   │   ├── useChat.ts     # SSE 流式对话
│   │   │   └── useDocuments.ts
│   │   └── styles/
│   │       └── main.css
│   └── public/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 4. 数据库设计

### 4.1 现有表（保留，做增量变更）

**users** — 新增 `role` 枚举值 `knowledge_admin`

**sessions / messages** — 不变

### 4.2 新增表

#### documents

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK, 默认 uuid4 | |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| file_path | VARCHAR(500) | NOT NULL | 服务器存储路径 |
| file_size | INTEGER | NOT NULL | 字节数 |
| file_type | VARCHAR(20) | NOT NULL | pdf / docx / txt / xlsx / image |
| category_id | UUID | FK → categories, NULL | 所属分类 |
| status | VARCHAR(20) | NOT NULL, 默认 processing | processing / ready / error |
| error_message | TEXT | NULL | 处理失败原因 |
| char_count | INTEGER | 默认 0 | 解析出字符数 |
| chunk_count | INTEGER | 默认 0 | 向量切片数 |
| uploaded_by | UUID | FK → users, NOT NULL | 上传者 |
| deleted_at | TIMESTAMP | NULL | 软删除标记 |
| created_at | TIMESTAMP | NOT NULL, 默认 now() | |
| updated_at | TIMESTAMP | NOT NULL, 默认 now() | |

**索引:** `(status, deleted_at)`、`(category_id)`、`(uploaded_by)`

#### categories

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(100) | NOT NULL | |
| parent_id | UUID | FK → categories, NULL | NULL 为一级分类 |
| sort_order | INTEGER | 默认 0 | |
| deleted_at | TIMESTAMP | NULL | 软删除 |
| created_at | TIMESTAMP | NOT NULL | |

#### tags

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(50) | NOT NULL, UNIQUE | |
| color | VARCHAR(7) | 默认 #409EFF | 十六进制色值 |
| deleted_at | TIMESTAMP | NULL | 软删除 |
| created_at | TIMESTAMP | NOT NULL | |

#### document_tags（多对多关联）

| 列 | 类型 | 约束 |
|---|---|---|
| document_id | UUID | FK → documents |
| tag_id | UUID | FK → tags |
| PRIMARY KEY | | (document_id, tag_id) |

#### system_settings

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| key | VARCHAR(100) | PK | 配置键 |
| value | TEXT | NOT NULL | 配置值 |
| updated_at | TIMESTAMP | NOT NULL | |

预设配置项: `model_name`、`temperature`、`retrieval_threshold`、`voice_enabled`、`log_retention_days`

#### usage_logs

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK → users, NOT NULL | |
| session_id | UUID | FK → sessions, NOT NULL | |
| query | TEXT | NOT NULL | 截断 200 字符 |
| has_attachment | BOOLEAN | 默认 false | |
| tokens_used | INTEGER | 默认 0 | |
| created_at | TIMESTAMP | NOT NULL, 默认 now() | |

**索引:** `(created_at)`、`(user_id, created_at)`

#### audit_logs

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK → users, NOT NULL | 操作人 |
| action | VARCHAR(50) | NOT NULL | 操作标识 |
| target_type | VARCHAR(50) | NOT NULL | 操作对象类型 |
| target_id | VARCHAR(100) | NOT NULL | 操作对象 ID |
| detail | JSONB | 默认 {} | 变更内容 |
| ip_address | VARCHAR(45) | NULL | 操作 IP |
| created_at | TIMESTAMP | NOT NULL, 默认 now() | |

**索引:** `(created_at)`、`(user_id)`

审计日志仅在 services 层写入，前端"操作日志"页面只读展示，不可编辑或删除。

---

## 5. API 设计

### 5.1 统一响应格式

**成功:**
```json
{"code": 0, "message": "success", "data": {...}}
```

**错误:**
```json
{"code": 40101, "message": "Token 已过期，请重新登录", "data": null}
```

**分页:**
```json
{"code": 0, "message": "success", "data": {"items": [...], "total": 128, "page": 1, "page_size": 20}}
```

### 5.2 接口清单

#### 认证 `/api/v1/auth/`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | /login | 用户名密码登录，返回 JWT | 公开 |
| POST | /register | 注册（需超管邀请码） | 公开 |
| GET | /me | 获取当前用户信息 | 登录 |
| POST | /refresh | 刷新 Token | 登录 |

#### AI 对话 `/api/v1/chat/`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | /stream | AI 对话（SSE 流式），支持文字+附件 | 登录 |
| GET | /sessions | 当前用户会话列表 | 登录 |
| GET | /sessions/{id} | 会话消息历史 | 登录 |
| DELETE | /sessions/{id} | 删除会话 | 登录 |

#### 知识库 `/api/v1/knowledge/`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | /documents/upload | 上传文档，异步处理 | 知识管理员+ |
| GET | /documents | 文档列表（分页、搜索、分类筛选） | 知识管理员+ |
| GET | /documents/{id} | 文档详情 | 知识管理员+ |
| DELETE | /documents/{id} | 删除文档（软删除） | 知识管理员+ |
| POST | /documents/{id}/reindex | 重新向量化 | 知识管理员+ |
| GET | /categories | 分类列表（树形） | 知识管理员+ |
| POST | /categories | 创建分类 | 知识管理员+ |
| PUT | /categories/{id} | 编辑分类 | 知识管理员+ |
| DELETE | /categories/{id} | 删除分类（软删除） | 知识管理员+ |
| GET | /tags | 标签列表 | 知识管理员+ |
| POST | /tags | 创建标签 | 知识管理员+ |
| DELETE | /tags/{id} | 删除标签（软删除） | 知识管理员+ |

#### 管理后台 `/api/v1/admin/`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | /dashboard/stats | 仪表盘聚合数据 | 知识管理员+ |
| GET | /users | 用户列表（分页） | 超管 |
| POST | /users | 创建用户 | 超管 |
| PUT | /users/{id} | 编辑用户（角色、状态） | 超管 |
| DELETE | /users/{id} | 停用用户（is_active=false） | 超管 |
| GET | /settings | 系统设置列表 | 超管 |
| PUT | /settings | 批量更新设置 | 超管 |
| GET | /audit-logs | 操作日志（分页、筛选） | 超管 |

### 5.3 权限实现

通过 FastAPI `Depends` 注入三级权限检查：

- `get_current_user` — 校验 JWT，返回用户，所有需要登录的接口使用
- `require_knowledge_admin` — 包装 `get_current_user`，校验角色为 knowledge_admin 或 super_admin，否则返回 403
- `require_super_admin` — 包装 `get_current_user`，校验角色为 super_admin，否则返回 403

### 5.4 错误码规范

| 范围 | 含义 |
|---|---|
| 0 | 成功 |
| 400xx | 请求参数错误 |
| 401xx | 认证/授权错误 |
| 403xx | 权限不足 |
| 404xx | 资源不存在 |
| 500xx | 服务器内部错误 |

### 5.5 仪表盘数据查询

`GET /api/v1/admin/dashboard/stats` 返回：

```json
{
  "document_count": 128,
  "today_upload_count": 5,
  "total_queries": 3420,
  "query_trend": [
    {"date": "2026-07-10", "count": 45},
    {"date": "2026-07-11", "count": 52}
  ],
  "top_queries": [
    {"term": "请假流程", "count": 28}
  ],
  "active_users": [
    {"username": "张三", "query_count": 67, "last_active": "2026-07-16"}
  ]
}
```

所有统计走 PostgreSQL `GROUP BY` + `date_trunc` 聚合，结果在 Redis 缓存 5 分钟。

---

## 6. 前端设计

### 6.1 路由结构

| 路由 | 页面 | 角色要求 |
|---|---|---|
| `/login` | 登录/注册 | 未登录 |
| `/` | 重定向到 `/chat` | — |
| `/chat` | AI 助手 | 登录 |
| `/chat/:sessionId` | AI 助手（指定会话） | 登录 |
| `/dashboard` | 仪表盘 | 知识管理员+ |
| `/knowledge` | 文档列表 | 知识管理员+ |
| `/knowledge/categories` | 分类标签管理 | 知识管理员+ |
| `/users` | 用户管理 | 超管 |
| `/settings` | 系统设置 | 超管 |
| `/audit-logs` | 操作日志（只读） | 超管 |

路由守卫 `router.beforeEach`：
- 目标路由需登录但无 token → `/login`
- 目标路由角色不足 → `/chat`

### 6.2 布局方案

**登录页:** 无外层布局，居中卡片。

**管理页面:** `AppLayout.vue` — 左侧 `SidebarMenu.vue`（角色感知渲染） + 右侧 Header + `<router-view>` 内容区。

**AI 助手页:** 主侧边栏折叠，页面内部独立三栏 — 会话列表 | 聊天消息区 | 附件预览区（可收起）。

### 6.3 核心组件清单

| 组件 | 说明 |
|---|---|
| AppLayout | 主布局容器 |
| SidebarMenu | 根据 currentUser.role 动态渲染菜单项 |
| HeaderBar | 面包屑 + 用户头像下拉（退出登录） |
| SessionList | AI 助手左侧会话列表，支持搜索和删除 |
| MessageBubble | 消息气泡，支持 Markdown 渲染 |
| ChatInput | 输入区，整合文字、语音、文件/图片上传 |
| StatCard | Element Plus Card 封装，展示统计数字 |
| TrendChart | ECharts 折线图封装，自适应 resize |
| DataState | 统一三态容器：加载骨架屏 / 空数据插图 / 错误重试 / 正常内容 |
| UploadDialog | Element Plus Upload 封装，拖拽上传 + 进度条 + 分类选择 |

### 6.4 API 封装层

`src/api/client.ts` — Axios 实例，统一 `baseURL: '/api/v1'`，请求拦截器加 `Authorization` header，响应拦截器解包 `data` 并处理 401 跳登录。

`src/api/` 下每个业务域一个文件，导出具名函数，返回 `Promise<T>`。Composables 只做状态管理，不直接操作 HTTP。

### 6.5 三态处理

所有列表页和仪表盘必须覆盖四种状态：

| 状态 | UI 表现 |
|---|---|
| 加载中 | Element Plus `el-skeleton` 骨架屏 |
| 空数据 | 居中插图 + 引导文案（如"还没有文档，上传第一份吧"）+ 操作按钮 |
| 出错 | `el-result` 错误状态 + 错误信息 + 重试按钮 |
| 正常 | 展示数据 |

`DataState.vue` 接收 `loading / error / empty / emptyText` props，内部根据状态渲染对应 UI，各页面统一使用。

---

## 7. 工程实践

### 7.1 软删除

documents、categories、tags 三表使用 `deleted_at` 时间戳实现软删除。所有查询默认过滤 `WHERE deleted_at IS NULL`。管理后台提供"回收站"入口查看已删除项并支持恢复。

users 表使用 `is_active` 字段停用，不做软删除。

### 7.2 审计日志

所有后台管理操作（文档上传/删除、用户角色变更、系统设置修改等）在 `services/` 层同步写入 `audit_logs` 表。日志只增不删不改，超管通过"操作日志"页面只读查看。

### 7.3 数据库索引

在 SQLAlchemy 模型声明时直接加 `index=True`，Alembic 生成迁移时自动创建。关键索引见第 4 节各表说明。

### 7.4 异步文档处理

文档上传流程：
1. 接收文件 → 存盘 → 写 `documents` 表（status=processing）→ 返回 201
2. FastAPI `BackgroundTasks` 异步执行：文件解析 → 文本切片 → 向量化 → 写入 Milvus → 更新 status=ready
3. 失败时更新 status=error 并写入 error_message

### 7.5 数据库迁移

使用 Alembic 管理所有 schema 变更。每次模型变更生成迁移脚本、提交到版本控制。首次部署执行 `alembic upgrade head` 建表，后续升级仅执行增量迁移。

### 7.6 现有代码迁移原则

- 现有接口逻辑不做重写，仅拆分搬运到对应 `routers/` 和 `services/` 文件
- `agent.py` → `services/agent_service.py`
- `rag_pipeline.py` → `services/rag_service.py`
- `api.py` 中的路由按业务域拆分到各 router 文件
- `app.py` 保留 FastAPI 工厂和中间件，移除路由直接定义

---

## 8. 测试策略

### 8.1 后端测试

| 层级 | 工具 | 说明 |
|---|---|---|
| 单元测试 | pytest | services/ 和 core/ 层，mock 外部依赖 |
| 接口测试 | pytest + httpx | 所有 `/api/v1/` 接口，覆盖正常 + 异常 + 权限 |
| 覆盖率目标 | — | 核心 services 80%+，routers 70%+ |

### 8.2 前端测试（第一期不做，列入后续计划）

| 层级 | 工具 | 说明 |
|---|---|---|
| 组件测试 | Vitest + vue-test-utils | 关键组件渲染和交互 |
| E2E | Playwright | 核心用户流程 |

---

## 9. 实施顺序

| 阶段 | 内容 | 预估 |
|---|---|---|
| **Phase 1: 基础设施** | Alembic 初始化、数据库迁移建表、后端目录重组（routers/services/core 拆分）、统一响应格式和错误码 | 先做 |
| **Phase 2: 认证 & 权限** | 升级 role 枚举、实现三级 Depends 权限注入、前端路由守卫 + useAuth | 先做 |
| **Phase 3: Vite + Vue 3 脚手架** | 初始化 Vite 项目、Vue Router、Element Plus、TypeScript、axios 封装、AppLayout + SidebarMenu | 先做 |
| **Phase 4: AI 助手页** | 迁移现有 chat 功能到 SPA、三栏布局、SSE 流式、语音输入、附件上传 | 核心 |
| **Phase 5: 文档管理** | 文档 CRUD + 上传 + 软删除、分类标签管理、异步处理 | 核心 |
| **Phase 6: 仪表盘** | ECharts 图表、统计数字卡片、usage_logs 记录 + 聚合查询 | 延后 |
| **Phase 7: 用户管理 & 系统设置** | 用户 CRUD、系统设置 KV 表单、操作日志查看 | 延后 |
| **Phase 8: 收尾** | 回收站、审计日志、生产部署配置、README 更新 | 收尾 |

---

## 10. 排除项（明确不做）

- 不做多租户/工作空间
- 不做实时协作编辑
- 不做消息推送/通知系统
- 不做 SSO/LDAP 集成
- 不做移动端适配（桌面端优先）
- usage_logs 自动归档第一期不实现，仅定义 `log_retention_days` 配置项
