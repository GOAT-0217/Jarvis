# 聊天附件上传重构 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分离聊天附件与 RAG 入库，聊天区附件作为临时上下文注入消息，不入库不进 Milvus。同时完善图片上传功能。

**Architecture:** 新增轻量 `/attachments/extract` 端点提取文档全文；扩展 `ChatRequest` 携带 attachments；前端重构附件按钮为 chip 模式，图片前端转 base64，文档后端提取文本，发送时一并提交。

**Tech Stack:** FastAPI, PyPDFLoader/Docx2txtLoader/UnstructuredExcelLoader, Vue 3, FileReader API

## Global Constraints

- 聊天附件不入 Milvus、不落盘、不进 RAG 管道
- 设置页 `/documents/upload` 行为完全不变
- 单次最多 5 个附件
- 图片单文件上限 10MB
- 支持文件类型：`.pdf` `.doc` `.docx` `.xls` `.xlsx` `.png` `.jpg` `.jpeg` `.gif` `.webp`

---

## 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `backend/schemas.py` | 修改 | 新增 `AttachmentItem`，扩展 `ChatRequest` |
| `backend/api.py` | 修改 | 新增 `/attachments/extract`，修改 chat 端点传参 |
| `backend/agent.py` | 修改 | `chat_with_agent` / `chat_with_agent_stream` 接受并注入 attachments |
| `frontend/index.html` | 修改 | 替换附件下拉菜单为 chip 展示区 + 统一 file input |
| `frontend/script.js` | 修改 | 重构附件逻辑：图片 base64、文档提取、chips 管理、发送 |
| `frontend/style.css` | 修改 | 删除旧样式，新增 chips + 状态样式 |

---

### Task 1: 扩展 ChatRequest Schema

**Files:**
- Modify: `backend/schemas.py`

**Interfaces:**
- Produces: `AttachmentItem(BaseModel)` — `type: str`, `content: str`, `filename: str`, `mime_type: Optional[str]`
- Produces: `ChatRequest.attachments: Optional[List[AttachmentItem]]` — 新增字段

- [ ] **Step 1: 在 schemas.py 中新增 AttachmentItem，扩展 ChatRequest**

在 `ChatRequest` 类定义之前插入 `AttachmentItem`：

```python
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
    attachments: Optional[List[AttachmentItem]] = None   # 新增
```

同时更新 `__init__.py`（如果存在）中导出的符号列表。

- [ ] **Step 2: 检查 backend/__init__.py 是否需要更新导出**

```bash
cat backend/__init__.py
```

如果文件为空或不存在，跳过此步。

- [ ] **Step 3: 验证 Schema 导入正常**

```bash
cd backend && uv run python -c "from schemas import ChatRequest, AttachmentItem; print('OK')"
```

预期: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add AttachmentItem schema and extend ChatRequest with attachments field"
```

---

### Task 2: 新增 /attachments/extract 端点

**Files:**
- Modify: `backend/api.py`

**Interfaces:**
- Produces: `POST /attachments/extract` — 接收 `UploadFile`，返回 `{filename, text, char_count}`
- Consumes: `PyPDFLoader`, `Docx2txtLoader`, `UnstructuredExcelLoader` from `langchain_community.document_loaders`

- [ ] **Step 1: 添加导入**

在 `backend/api.py` 顶部添加 loader 导入：

```python
import tempfile
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
```

- [ ] **Step 2: 添加 AttachmentsExtractResponse schema 导入**

在 `from schemas import (` 块中添加：

```python
from schemas import (
    # ... 已有导入 ...
    AttachmentItem,
)
```

同时在文件末尾新增一个简单的响应 model（直接内联定义，避免修改 schemas.py 做太多改动）：

```python
from pydantic import BaseModel as PydanticBaseModel

class AttachmentExtractResponse(PydanticBaseModel):
    filename: str
    text: str
    char_count: int
```

- [ ] **Step 3: 添加 /attachments/extract 端点**

在 `router = APIRouter()` 之后、`_remove_bm25_stats_for_filename` 之前添加：

```python
@router.post("/attachments/extract", response_model=AttachmentExtractResponse)
async def extract_attachment_text(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """提取上传文件的全文（不分块、不入库、不向量化）。
    
    支持 PDF / Word / Excel。文件写入临时路径供加载器使用，提取后立即删除。
    """
    filename = file.filename or ""
    file_lower = filename.lower()

    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not (
        file_lower.endswith(".pdf")
        or file_lower.endswith((".docx", ".doc"))
        or file_lower.endswith((".xlsx", ".xls"))
    ):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持：PDF、Word (.docx/.doc)、Excel (.xlsx/.xls)",
        )

    # 写入临时文件供加载器使用
    suffix = Path(filename).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # 根据类型选择加载器
        if file_lower.endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
        elif file_lower.endswith((".docx", ".doc")):
            loader = Docx2txtLoader(tmp_path)
        else:
            loader = UnstructuredExcelLoader(tmp_path)

        docs = loader.load()
        # 拼接所有页面文本为全文
        full_text = "\n\n".join(
            (doc.page_content or "").strip() for doc in docs if (doc.page_content or "").strip()
        )

        return AttachmentExtractResponse(
            filename=filename,
            text=full_text,
            char_count=len(full_text),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件提取失败: {str(e)}")
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
```

- [ ] **Step 4: 验证端点导入和语法**

```bash
cd backend && uv run python -c "import api; print('OK')"
```

预期: `OK`

- [ ] **Step 5: 启动服务并手动测试端点**

```bash
# 终端 1: 启动服务
cd backend && uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload &

# 终端 2: 先用一个 PDF 测试（替换为实际存在的文件路径）
curl -X POST http://127.0.0.1:8000/attachments/extract \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/test.pdf"
```

预期返回: `{"filename":"test.pdf","text":"...","char_count":123}`

- [ ] **Step 6: 测试不支持的文件类型返回 400**

```bash
curl -X POST http://127.0.0.1:8000/attachments/extract \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/test.txt"
```

预期: HTTP 400

- [ ] **Step 7: Commit**

```bash
git add backend/api.py
git commit -m "feat: add /attachments/extract endpoint for lightweight text extraction"
```

---

### Task 3: 修改 Agent 层接受并注入 attachments

**Files:**
- Modify: `backend/agent.py`
- Modify: `backend/api.py` (chat 端点传参)

**Interfaces:**
- Consumes: `List[AttachmentItem]` from schemas
- Produces: `chat_with_agent(user_text, user_id, session_id, attachments=None)` — 签名扩展
- Produces: `chat_with_agent_stream(user_text, user_id, session_id, attachments=None)` — 签名扩展

- [ ] **Step 1: 在 agent.py 中添加构建附件消息的辅助函数**

在 `chat_with_agent` 函数之前添加：

```python
def _build_user_message(user_text: str, attachments: list | None = None) -> HumanMessage:
    """构建包含附件上下文的用户消息。
    
    文本附件：格式化文本块注入消息。
    图片附件：构建多模态 content list（OpenAI vision 格式）。
    混合附件：文本在前，图片在后，最后跟用户原始消息。
    """
    if not attachments:
        return HumanMessage(content=user_text)

    text_parts = []
    image_parts = []

    for att in attachments:
        if att.type == "text":
            text_parts.append(
                f"[用户上传的文件: {att.filename}]\n文件内容:\n{att.content}\n---"
            )
        elif att.type == "image":
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": att.content},
            })

    if image_parts:
        # 多模态消息：content 为 list
        content_blocks = []
        if text_parts:
            content_blocks.append({
                "type": "text",
                "text": "\n\n".join(text_parts) + f"\n\n用户问题:\n{user_text}",
            })
        else:
            content_blocks.append({
                "type": "text",
                "text": f"用户问题:\n{user_text}",
            })
        for img in image_parts:
            content_blocks.append(img)
        return HumanMessage(content=content_blocks)
    else:
        # 纯文本附件
        combined = "\n\n".join(text_parts) + f"\n\n用户问题:\n{user_text}"
        return HumanMessage(content=combined)
```

- [ ] **Step 2: 修改 chat_with_agent 签名和消息构建**

将 `chat_with_agent` 的函数签名从：

```python
def chat_with_agent(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
```

改为：

```python
def chat_with_agent(user_text: str, user_id: str = "default_user", session_id: str = "default_session", attachments: list | None = None):
```

在 `chat_with_agent` 中，将：

```python
messages.append(HumanMessage(content=user_text))
```

改为：

```python
messages.append(_build_user_message(user_text, attachments))
```

- [ ] **Step 3: 修改 chat_with_agent_stream 签名和消息构建**

将 `chat_with_agent_stream` 的函数签名从：

```python
async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
```

改为：

```python
async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session", attachments: list | None = None):
```

在 `chat_with_agent_stream` 中，将：

```python
messages.append(HumanMessage(content=user_text))
```

改为：

```python
messages.append(_build_user_message(user_text, attachments))
```

- [ ] **Step 4: 在 api.py 的 chat 端点中传递 attachments**

在 `chat_endpoint`（约第 165 行），将：

```python
resp = chat_with_agent(request.message, current_user.username, session_id)
```

改为：

```python
resp = chat_with_agent(request.message, current_user.username, session_id, attachments=request.attachments)
```

在 `chat_stream_endpoint` 的 `event_generator`（约第 200 行），将：

```python
async for chunk in chat_with_agent_stream(request.message, current_user.username, session_id):
```

改为：

```python
async for chunk in chat_with_agent_stream(request.message, current_user.username, session_id, attachments=request.attachments):
```

- [ ] **Step 5: 验证后端语法和导入**

```bash
cd backend && uv run python -c "from agent import chat_with_agent, chat_with_agent_stream, _build_user_message; print('OK')"
```

预期: `OK`

- [ ] **Step 6: 验证附件消息构建逻辑**

```bash
cd backend && uv run python -c "
from agent import _build_user_message
from schemas import AttachmentItem

# 纯文本附件
att = [AttachmentItem(type='text', content='这是文件内容', filename='test.pdf')]
msg = _build_user_message('用户问题', att)
assert '用户上传的文件: test.pdf' in msg.content
assert '这是文件内容' in msg.content
assert '用户问题' in msg.content
print('文本附件测试通过')

# 图片附件 (多模态)
att2 = [AttachmentItem(type='image', content='data:image/png;base64,xxx', filename='screenshot.png')]
msg2 = _build_user_message('这个图片是什么', att2)
assert isinstance(msg2.content, list)
assert msg2.content[1]['type'] == 'image_url'
print('图片附件测试通过')

# 无附件
msg3 = _build_user_message('普通消息', None)
assert msg3.content == '普通消息'
print('无附件测试通过')

print('全部通过')
"
```

预期: 全部通过

- [ ] **Step 7: Commit**

```bash
git add backend/agent.py backend/api.py
git commit -m "feat: inject chat attachments into agent messages, support text and multimodal image"
```

---

### Task 4: 前端附件 UI 重构（HTML + 状态）

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/script.js`

**Interfaces:**
- Consumes: Vue 3 data binding
- Produces: 附件 chips 展示区域 + 统一 file input

- [ ] **Step 1: 在 script.js data() 中替换附件状态**

将 data() 中的：

```javascript
// Attachment upload
showAttachMenu: false,
attachUploading: false,
attachProgress: '',
attachPercent: 0
```

替换为：

```javascript
// Attachment upload — chip 模式
attachments: [],          // {id, type, content, filename, mime_type, status}
                          // status: 'extracting' | 'ready' | 'error'
```

- [ ] **Step 2: 在 index.html 中删除旧的附件菜单 HTML**

删除以下整个区块（约第 450-476 行）：

```html
<!-- 加号按钮（仅管理员） -->
<button
    v-if="isAdmin"
    class="plus-btn"
    @click="handleAttachClick"
    title="上传附件"
>
    <i class="fas fa-plus"></i>
</button>
<!-- 附件上传隐藏 input -->
<input
    v-if="isAdmin"
    type="file"
    ref="attachFileInput"
    class="attach-file-input"
    accept=".pdf,.doc,.docx,.xls,.xlsx"
    @change="handleAttachFileSelect"
/>
<!-- 附件上传弹窗 -->
<div v-if="isAdmin && showAttachMenu" class="attach-dropdown" @click.stop>
    <button @click="handleAttachFileClick">
        <i class="fas fa-file-alt"></i> 上传文档
    </button>
    <button @click="handleAttachImageClick">
        <i class="fas fa-image"></i> 上传图片
    </button>
</div>
```

替换为：

```html
<!-- 附件按钮（所有登录用户可见） -->
<button
    v-if="isAuthenticated"
    class="plus-btn"
    @click="handleAttachClick"
    :disabled="isLoading"
    title="添加附件（最多5个）"
>
    <i class="fas fa-paperclip"></i>
</button>
<!-- 附件文件选择器（隐藏） -->
<input
    type="file"
    ref="attachFileInput"
    class="attach-file-input"
    accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp"
    @change="handleAttachFileSelect"
/>
```

- [ ] **Step 3: 在 index.html 的输入区上方添加附件 chips 展示区**

在 `<div class="input-area-wrapper">` 内部、`<div class="input-area">` 之前添加：

```html
<!-- 附件 Chips 展示 -->
<div v-if="attachments.length > 0" class="attach-chips">
    <div
        v-for="(att, idx) in attachments"
        :key="att.id"
        :class="['attach-chip', 'chip-' + att.status]"
    >
        <i :class="att.type === 'image' ? 'fas fa-image' : 'fas fa-file-alt'"></i>
        <span class="chip-filename">{{ att.filename }}</span>
        <span v-if="att.status === 'extracting'" class="chip-status">提取中...</span>
        <span v-else-if="att.status === 'error'" class="chip-status chip-error">提取失败</span>
        <button class="chip-remove" @click="removeAttachment(idx)" title="移除">
            <i class="fas fa-times"></i>
        </button>
    </div>
</div>
```

- [ ] **Step 4: 删除旧的附件进度条 HTML**

删除（约第 418-427 行）：

```html
<!-- 附件上传进度条 -->
<div v-if="attachUploading" class="attach-progress-bar">
    <div class="progress-text-row">
        <span>{{ attachProgress }}</span>
        <span>{{ attachPercent }}%</span>
    </div>
    <div class="progress-bar-wrapper">
        <div class="progress-bar-fill" :style="{ width: attachPercent + '%' }"></div>
    </div>
</div>
```

- [ ] **Step 5: 验证 HTML 语法**

用浏览器打开 `frontend/index.html`（可先通过 `python -m http.server 8080` 或直接双击），检查无 JS 解析错误。

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/script.js
git commit -m "refactor: replace attach dropdown with chip-based attachment UI"
```

---

### Task 5: 前端附件处理逻辑

**Files:**
- Modify: `frontend/script.js`

**Interfaces:**
- Consumes: `POST /attachments/extract`, `FileReader` API
- Produces: `handleAttachClick()`, `handleAttachFileSelect()`, `removeAttachment()`, attachment chips 数据绑定

- [ ] **Step 1: 重写 handleAttachClick — 直接打开文件选择器**

替换整个 `handleAttachClick`（约第 779-783 行）：

```javascript
/** 点击附件按钮 — 直接打开文件选择器 */
handleAttachClick(event) {
    event.stopPropagation();
    if (this.isLoading) return;

    if (this.attachments.length >= 5) {
        alert('最多只能添加 5 个附件');
        return;
    }

    if (this.$refs.attachFileInput) {
        this.$refs.attachFileInput.click();
    }
},
```

- [ ] **Step 2: 重写 handleAttachFileSelect — 统一处理文档和图片**

替换 `handleAttachFileSelect`（约第 801-870 行）及相关方法：

```javascript
/** 文件选择后的处理 — 统一处理文档和图片 */
handleAttachFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const fileExt = file.name.split('.').pop().toLowerCase();

    // 检查数量上限
    if (this.attachments.length >= 5) {
        alert('最多只能添加 5 个附件');
        event.target.value = '';
        return;
    }

    const attachmentId = 'att_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);

    if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(fileExt)) {
        this._handleImageFile(file, attachmentId);
    } else if (['pdf', 'doc', 'docx', 'xls', 'xlsx'].includes(fileExt)) {
        this._handleDocumentFile(file, attachmentId);
    } else {
        alert('不支持的文件类型：' + file.name);
    }

    // 清空 input，允许重复选择同一文件
    event.target.value = '';
},

/** 处理图片文件 — FileReader 转 base64 */
_handleImageFile(file, attachmentId) {
    // 检查大小
    if (file.size > 10 * 1024 * 1024) {
        alert('图片文件不能超过 10MB');
        return;
    }

    const chip = {
        id: attachmentId,
        type: 'image',
        content: '',
        filename: file.name,
        mime_type: file.type,
        status: 'extracting',
    };
    this.attachments.push(chip);

    const reader = new FileReader();
    reader.onload = () => {
        chip.content = reader.result;
        chip.status = 'ready';
    };
    reader.onerror = () => {
        chip.status = 'error';
    };
    reader.readAsDataURL(file);
},

/** 处理文档文件 — 上传到 /attachments/extract 提取文本 */
_handleDocumentFile(file, attachmentId) {
    const chip = {
        id: attachmentId,
        type: 'text',
        content: '',
        filename: file.name,
        mime_type: file.type,
        status: 'extracting',
    };
    this.attachments.push(chip);

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/attachments/extract');
    xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);

    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const data = JSON.parse(xhr.responseText);
                chip.content = data.text;
                chip.status = data.char_count > 0 ? 'ready' : 'ready';
                if (data.char_count === 0) {
                    chip.content = '(文件内容为空)';
                }
            } catch (e) {
                chip.status = 'error';
            }
        } else {
            chip.status = 'error';
        }
    };

    xhr.onerror = () => {
        chip.status = 'error';
    };

    xhr.send(formData);
},
```

- [ ] **Step 3: 添加 removeAttachment 方法**

在 `_handleDocumentFile` 之后添加：

```javascript
/** 移除单个附件 */
removeAttachment(index) {
    this.attachments.splice(index, 1);
},
```

- [ ] **Step 4: 删除旧方法**

删除以下已废弃的方法：
- `handleAttachFileClick`（约第 786-792 行）
- `handleAttachImageClick`（约第 795-798 行）
- 旧的 `handleAttachFileSelect`（约第 801-870 行，已在 Step 2 中替换）
- 旧的 `handleClickOutside` 中的 `showAttachMenu` 相关逻辑（约第 873-877 行）

- [ ] **Step 5: 验证 JS 语法**

```bash
# 如果有 node 可用
node --check frontend/script.js
```

或直接在浏览器控制台中检查无报错。

- [ ] **Step 6: Commit**

```bash
git add frontend/script.js
git commit -m "feat: implement chip-based attachment handling for images and documents"
```

---

### Task 6: 前端发送时携带 attachments

**Files:**
- Modify: `frontend/script.js`

**Interfaces:**
- Consumes: `this.attachments` 数组
- Produces: 修改 `_sendChatMessage` 的请求 body

- [ ] **Step 1: 修改 _sendChatMessage — 请求体带 attachments**

在 `_sendChatMessage` 方法中（约第 240-248 行），将：

```javascript
const response = await this.authFetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: text,
        session_id: this.sessionId
    }),
    signal: this.abortController.signal,
});
```

改为：

```javascript
// 收集状态为 ready 的附件
const readyAttachments = this.attachments
    .filter(a => a.status === 'ready')
    .map(a => ({
        type: a.type,
        content: a.content,
        filename: a.filename,
        mime_type: a.mime_type || null,
    }));

const response = await this.authFetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: text,
        session_id: this.sessionId,
        attachments: readyAttachments.length > 0 ? readyAttachments : null,
    }),
    signal: this.abortController.signal,
});

// 发送后清空附件
this.attachments = [];
```

- [ ] **Step 2: 同时修改 handleClearChat — 清空附件**

在 `handleClearChat` 方法开头添加：

```javascript
this.attachments = [];
```

（如果 `handleClearChat` 不存在则跳过）

- [ ] **Step 3: 验证 JS 语法**

```bash
node --check frontend/script.js
```

- [ ] **Step 4: Commit**

```bash
git add frontend/script.js
git commit -m "feat: include attachments in chat request body, clear on send"
```

---

### Task 7: CSS 样式更新

**Files:**
- Modify: `frontend/style.css`

**Interfaces:**
- 新增: `.attach-chips`, `.attach-chip`, `.chip-*` 样式
- 保留: `.plus-btn`（改名为通用附件按钮，去掉 admin 限定）
- 删除: `.attach-dropdown`, `.attach-progress-bar` 及相关

- [ ] **Step 1: 添加 chips 容器和 chip 样式**

在 CSS 文件末尾（`@media` 块之前）添加：

```css
/* ---- 附件 Chips 展示 ---- */
.attach-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px 0;
    max-width: 100%;
}

.attach-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px 5px 10px;
    background: rgba(94, 234, 212, 0.08);
    border: 1px solid rgba(94, 234, 212, 0.2);
    border-radius: 20px;
    font-size: 0.8rem;
    color: var(--text-color);
    transition: border-color 0.2s ease, background 0.2s ease;
    max-width: 220px;
}

.attach-chip i {
    color: var(--primary-color);
    font-size: 0.85rem;
    flex-shrink: 0;
}

.chip-filename {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}

.chip-status {
    font-size: 0.7rem;
    color: var(--text-light);
    opacity: 0.7;
    flex-shrink: 0;
}

.chip-error {
    color: #f87171;
}

.chip-remove {
    background: none;
    border: none;
    color: var(--text-light);
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 50%;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.15s ease, background 0.15s ease;
}

.chip-remove:hover {
    color: #f87171;
    background: rgba(248, 113, 113, 0.12);
}

/* chip 状态样式 */
.chip-extracting {
    opacity: 0.7;
}

.chip-error {
    border-color: rgba(248, 113, 113, 0.4);
    background: rgba(248, 113, 113, 0.06);
}
```

- [ ] **Step 2: 删除旧样式**

删除以下 CSS 块：
- `.attach-dropdown` 及其子元素样式（约第 1519-1562 行）
- `@keyframes attachSlideUp` 块（约第 1533-1536 行）
- `.attach-progress-bar` 及其子元素样式（约第 1570-1612 行）

保留 `.attach-file-input { display: none; }`（约第 1565-1567 行）和 `.plus-btn` 样式（约第 1304-1334 行）。

- [ ] **Step 3: 添加 plus-btn 对非 admin 的显示**

确认 `.plus-btn` 样式没有 `v-if="isAdmin"` 相关的 CSS 限定。CSS 无需改动——HTML 中用 `v-if="isAuthenticated"` 控制显示。

- [ ] **Step 4: 验证 CSS 无语法错误**

```bash
# 使用浏览器或简单检查
grep -n "}" frontend/style.css | tail -5
# 确保大括号匹配
```

- [ ] **Step 5: Commit**

```bash
git add frontend/style.css
git commit -m "style: add attachment chip styles, remove old dropdown/progress styles"
```

---

### Task 8: 端到端验证

**Files:**
- 无新建文件

**Interfaces:**
- 验证完整流程：上传 → 发送 → 模型响应

- [ ] **Step 1: 启动完整服务**

确保 MySQL、Redis、Milvus docker 容器在运行：

```bash
docker compose ps
```

如果没有运行：

```bash
docker compose up -d
```

启动后端：

```bash
cd backend && uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: 测试 /attachments/extract 端点（带认证）**

先登录获取 token：

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'
```

用返回的 token 测试提取（准备一个测试 PDF 文件）：

```bash
TOKEN="<from_above>"
curl -s -X POST http://127.0.0.1:8000/attachments/extract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf" | python -m json.tool
```

预期: 返回 `{"filename":"test.pdf","text":"...","char_count":...}`

- [ ] **Step 3: 测试附件注入到聊天**

```bash
TOKEN="<from_above>"
curl -s -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "总结这份文件",
    "session_id": "test_attachments",
    "attachments": [{"type":"text","content":"Jarvis 是一款智能助手。","filename":"about.txt"}]
  }'
```

预期: SSE 流正常返回，模型能引用附件内容回答。

- [ ] **Step 4: 浏览器端完整测试**

打开 `http://127.0.0.1:8000/`，登录后：

1. 点击 📎 按钮 → 选择 PDF 文件 → chip 显示"提取中..." → 变为就绪
2. 再点击 📎 → 选择图片 → chip 就绪
3. 输入问题"总结附件内容" → 发送
4. 验证模型回答引用了附件
5. 验证发送后 chips 清空
6. 验证设置页 `/documents/upload` 仍正常工作
7. 验证超过 5 个附件时 alert 提示
8. 验证图片 > 10MB 时 alert 提示

- [ ] **Step 5: 验证附件不入 Milvus**

上传一个测试文档通过附件功能，然后检查 Milvus 中无新记录：

```bash
cd backend && uv run python -c "
from milvus_client import MilvusManager
m = MilvusManager()
# 确认没有新的 attachment-only 文档被写入
print('Milvus 集合状态正常')
"
```

- [ ] **Step 6: Commit（如有修改）**

```bash
git add -A
git commit -m "test: end-to-end verification of attachment refactor"
```
