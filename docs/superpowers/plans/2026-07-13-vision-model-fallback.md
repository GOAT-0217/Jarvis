# 图片视觉理解降级 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 图片附件先经豆包视觉模型转为文字描述，再注入 DeepSeek 消息上下文，解决 ARK DeepSeek 不支持多模态的问题。

**Architecture:** `_build_user_message` 中图片附件不再构建 `image_url` 块，改为调用 `_describe_image()` 获取文字描述，以文本格式注入。纯文本聊天不受影响。

**Tech Stack:** FastAPI, langchain (`init_chat_model`, `HumanMessage`), 豆包视觉模型 (doubao-seed-1-6-vision-250815)

## Global Constraints

- 纯文本聊天不受影响（懒加载视觉模型）
- 视觉模型调用失败时返回 `(图片识别失败: <error>)` 不阻塞聊天
- 复用现有 `ARK_API_KEY` 和 `BASE_URL`
- VISION_MODEL 未配置时使用默认值 `doubao-seed-1-6-vision-250815`

---

### Task 1: 新增 `_describe_image` + 修改 `_build_user_message`

**Files:**
- Modify: `backend/agent.py` — 新增 `_describe_image()`，修改 `_build_user_message` 图片处理分支
- Modify: `.env` — 新增 `VISION_MODEL`（可选，已有默认值）
- Modify: `.env.example` — 新增 `VISION_MODEL` 说明

**Interfaces:**
- Consumes: `API_KEY`, `BASE_URL` (from os.getenv), `init_chat_model`, `HumanMessage`
- Produces: `_describe_image(base64_uri: str) -> str`
- Modifies: `_build_user_message` — image 分支从 `image_url` 块改为文本描述格式

- [ ] **Step 1: 在 agent.py 中新增 `_describe_image` 函数**

在 `_build_user_message` 之前（约第 310 行）插入：

```python
# 视觉模型懒加载缓存
_vision_model = None
_vision_model_name = None


def _describe_image(base64_uri: str) -> str:
    """调用豆包视觉模型，将图片转为文字描述。

    模型按需初始化，只初始化一次。调用失败时返回错误提示，不抛异常。
    """
    global _vision_model, _vision_model_name
    try:
        vision_name = os.getenv("VISION_MODEL", "doubao-seed-1-6-vision-250815")
        if _vision_model is None or _vision_model_name != vision_name:
            _vision_model = init_chat_model(
                model=vision_name,
                model_provider="openai",
                api_key=API_KEY,
                base_url=BASE_URL,
                temperature=0.3,
            )
            _vision_model_name = vision_name

        msg = HumanMessage(content=[
            {
                "type": "text",
                "text": "请详细描述这张图片的内容，包括文字、布局、数据等所有可见信息。",
            },
            {
                "type": "image_url",
                "image_url": {"url": base64_uri},
            },
        ])
        resp = _vision_model.invoke([msg])
        return resp.content if isinstance(resp.content, str) else str(resp.content)
    except Exception as e:
        return f"(图片识别失败: {str(e)})"
```

- [ ] **Step 2: 修改 `_build_user_message` 的图片处理分支**

将当前的图片附件处理（第 336-340 行）：

```python
        elif att.type == "image":
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": att.content},
            })
```

替换为：

```python
        elif att.type == "image":
            description = _describe_image(att.content)
            text_parts.append(
                f"[用户上传的图片: {att.filename}]\n图片内容描述:\n{description}\n---"
            )
```

- [ ] **Step 3: 删除不再需要的 `image_parts` 和 multimodal 构建逻辑**

由于图片已转为文本描述注入 `text_parts`，`image_parts` 列表和后续的 multimodal content_blocks 构建（第 342-357 行）改为：

```python
    # 统一走纯文本路径（图片已通过 _describe_image 转为文字描述）
    combined = "\n\n".join(text_parts) + f"\n\n用户问题:\n{user_text}"
    return HumanMessage(content=combined)
```

即删除 `image_parts` 变量和整个 `if image_parts:` 分支，统一走纯文本路径。

- [ ] **Step 4: 更新 .env 文件**

在 `.env` 末尾添加：

```env
# ===== 视觉模型（用于图片附件描述，DeepSeek 不支持多模态）=====
VISION_MODEL=doubao-seed-1-6-vision-250815
```

- [ ] **Step 5: 更新 .env.example**

在 `.env.example` 中 `FAST_MODEL` 之后添加：

```env
VISION_MODEL= #doubao-seed-1-6-vision-250815
```

- [ ] **Step 6: 验证后端语法和导入**

```bash
cd backend && uv run python -c "
from agent import _build_user_message, _describe_image
from schemas import AttachmentItem
print('Import OK')
"
```

预期: `Import OK`

- [ ] **Step 7: 验证纯文本附件不受影响**

```bash
cd backend && uv run python -c "
from agent import _build_user_message
from schemas import AttachmentItem

# 纯文本附件
att = [AttachmentItem(type='text', content='文件内容', filename='test.pdf')]
msg = _build_user_message('总结一下', att)
assert '文件内容' in msg.content
assert '总结一下' in msg.content
print('纯文本附件测试通过')

# 无附件
msg2 = _build_user_message('你好', None)
assert msg2.content == '你好'
print('无附件测试通过')
"
```

预期: 全部通过

- [ ] **Step 8: Commit**

```bash
git add backend/agent.py .env .env.example
git commit -m "feat: add vision model fallback for image attachments (DeepSeek doesn't support multimodal)"
```
