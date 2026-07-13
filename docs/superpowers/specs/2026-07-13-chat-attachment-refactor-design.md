# 聊天附件上传重构设计

**日期**: 2026-07-13
**状态**: 设计完成，待审核

---

## 1. 背景与目标

### 现状问题

当前聊天输入区的附件按钮将文件直接上传到 `/documents/upload`，文件进入完整 RAG 管道（分块 → 向量化 → Milvus 入库）。这带来两个问题：

1. **意图混淆**：聊天区上传的文件本意是"帮助模型理解当前问题"，不应变成永久知识库文档
2. **图片上传未实现**：点击"上传图片"只弹出"功能开发中"提示

### 目标

- **分离两条路径**：设置页 = 知识库入库（不变），聊天区 = 临时上下文（重构）
- **完善图片上传**：支持图片附件，通过多模态能力让模型理解图片内容
- **支持多文件**：一次发送最多带 5 个附件（文档或图片）

---

## 2. 整体架构

```
设置页（管理员）──→ POST /documents/upload ──→ RAG 管道 （不变）

聊天区 ──→ 图片: FileReader → base64（前端）
           文档: POST /attachments/extract → 纯文本
                 │
                 └──→ POST /chat/stream {message, attachments: [...], ...}
                           │
                           ▼
                      后端拼接附件内容到消息上下文 → Agent 处理
```

**核心原则**：聊天附件只存在于当前消息上下文中，不落盘、不入库、不进 Milvus。

---

## 3. 后端改动

### 3.1 新增 `POST /attachments/extract`

轻量文本提取接口，不做分块和向量化。

- **路径**: `POST /attachments/extract`
- **权限**: 登录用户即可（无需管理员）
- **入参**: `UploadFile`（支持 `.pdf` / `.doc` / `.docx` / `.xls` / `.xlsx`）
- **处理**: 上传的文件先写入临时文件（加载器需要文件路径），根据类型选用 `PyPDFLoader` / `Docx2txtLoader` / `UnstructuredExcelLoader` 加载，提取原始文本后拼接为全文，最后立即删除临时文件。不走 `load_document()` 的三级分块逻辑
- **返回**: `{filename: str, text: str, char_count: int}`
- **不落盘**: 文件内容仅在内存中处理，不写入 `data/documents/`

### 3.2 ChatRequest 扩展

```python
class AttachmentItem(BaseModel):
    type: str            # "text" | "image"
    content: str         # 文本内容 或 base64 data URI (data:image/...;base64,...)
    filename: str
    mime_type: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"
    attachments: Optional[List[AttachmentItem]] = None   # 新增，上限由前端控制（≤5）
```

### 3.3 chat_with_agent / chat_with_agent_stream

签名扩展为 `(user_text, user_id, session_id, attachments=None)`。

**文本附件**：在用户消息前注入格式化文本块：
```
[用户上传的文件: report.pdf]
文件内容:
<extracted text>
---
用户问题:
<original message>
```

**图片附件**：将 `HumanMessage.content` 构建为多模态列表：
```python
[
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
    {"type": "text", "text": "[用户上传的图片: screenshot.png]\n\n用户问题: <original message>"},
]
```
DeepSeek V4 原生支持 `image_url` 格式，兼容 OpenAI vision 协议。

**单消息多附件**：按顺序拼接所有附件，文本在前、图片在后，最后跟用户原始消息。

### 3.4 与现有 RAG 管道隔离

- `/attachments/extract` 仅调用 `DocumentLoader.load_document()` 做文本提取，不经过 `_split_page_to_three_levels`
- 不调用 `embedding_service`、`milvus_writer`、`parent_chunk_store`
- `/chat/stream` 中的附件内容注入发生在 agent 调用之前，不走 `search_knowledge_base` 工具

---

## 4. 前端改动

### 4.1 附件按钮重构

**删除**：
- 下拉菜单 `showAttachMenu` 及相关 HTML
- `handleAttachFileClick`、`handleAttachImageClick`、`handleAttachFileSelect`
- `attachUploading`、`attachProgress`、`attachPercent` 状态

**新增**：
- 点击 📎 按钮直接触发 `<input type="file">`
- `accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp"`
- `attachments: []` 数组，每个元素 `{type, content, filename, mime_type, status}`

### 4.2 文件 Chip 展示

输入框上方显示已选文件 chips：

```
┌──────────────────────────────────────────┐
│ [📄 report.pdf ✕] [🖼 screenshot.png ✕]  │
│                                          │
│ [输入框................................] │
└──────────────────────────────────────────┘
```

- 文档 chip：📄 图标 + 文件名 + 提取中/完成/失败状态
- 图片 chip：🖼 图标 + 文件名 + 缩略图预览（可选）
- 每个 chip 可独立删除
- 超过 5 个时 alert 提示

### 4.3 文件处理流程

**图片**（`.png` / `.jpg` / `.jpeg` / `.gif` / `.webp`）：
```javascript
const reader = new FileReader();
reader.onload = () => {
    this.attachments.push({
        type: 'image',
        content: reader.result,   // data:image/png;base64,...
        filename: file.name,
        mime_type: file.type,
        status: 'ready'
    });
};
reader.readAsDataURL(file);
```

**文档**（`.pdf` / `.doc` / `.docx` / `.xls` / `.xlsx`）：
```javascript
// chip 显示 "提取中..."
const formData = new FormData();
formData.append('file', file);
const xhr = new XMLHttpRequest();
xhr.open('POST', '/attachments/extract');
// 设置 auth header
xhr.onload = () => {
    const data = JSON.parse(xhr.responseText);
    // 存储提取结果
    this.attachments.push({
        type: 'text',
        content: data.text,
        filename: data.filename,
        status: 'ready'
    });
};
xhr.onerror = () => { /* chip 变红，显示失败 */ };
xhr.send(formData);
```

### 4.4 发送流程

`sendMessage()` 中将 `attachments` 数组放入 `ChatRequest`，发送后清空。

```javascript
const body = {
    message: this.userInput,
    session_id: this.currentSessionId,
    attachments: this.attachments.filter(a => a.status === 'ready').map(a => ({
        type: a.type,
        content: a.content,
        filename: a.filename,
        mime_type: a.mime_type || null,
    })),
};
// ... fetch('/chat/stream', {body: JSON.stringify(body)})
this.attachments = [];
```

### 4.5 设置页

**不动**。设置页的文档上传/删除功能保持原样，依然是唯一的知识库入库入口。

---

## 5. 错误处理

| 场景 | 处理 |
|---|---|
| 文档提取失败 | chip 变红显示"提取失败"，可点击移除，不阻塞发送其他附件 |
| 图片 base64 过大 | 前端校验，单文件 > 10MB 时 alert 拒绝 |
| 文本提取结果为空 | 返回 `char_count: 0`，前端显示"文件内容为空" |
| 附件超过 5 个 | 前端 alert 提示，拒绝添加 |
| 不支持的文件类型 | `/attachments/extract` 返回 400，前端 chip 变红 |
| /attachments/extract 鉴权失败 | 返回 401，前端同现有 authFetch 错误处理 |

---

## 6. 测试要点

- [ ] 文档附件提取后文本正确注入消息上下文
- [ ] 图片附件 base64 正确构建多模态消息
- [ ] 混合附件（文档 + 图片）正确拼接
- [ ] 附件内容不进入 Milvus
- [ ] 附件内容不落盘
- [ ] 设置页上传不受影响
- [ ] 非登录用户无法调用 `/attachments/extract`
- [ ] 附件 chips 增删交互正确
- [ ] 发送后 chips 自动清空
