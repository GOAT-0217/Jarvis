# 粘贴图片上传 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户在聊天输入框 Ctrl+V 粘贴图片时，自动走附件 chip 流程，复用现有 `_handleImageFile` 逻辑。

**Architecture:** 在 textarea 上监听 `paste` 事件，检测 `clipboardData.items` 中的图片，阻止默认行为后调用已有的 `_handleImageFile` 方法。纯文字粘贴不受影响。

**Tech Stack:** Vue 3 (CDN), Clipboard API, FileReader

## Global Constraints

- 图片大小上限 10MB（`_handleImageFile` 已有校验）
- 附件数量上限 5 个
- 只处理图片粘贴，文字粘贴行为完全不变
- 复用现有 `_handleImageFile`，不改动后端

---

### Task 1: 新增 paste 事件处理 + textarea 绑定

**Files:**
- Modify: `frontend/script.js` — 新增 `handlePaste` 方法
- Modify: `frontend/index.html` — textarea 添加 `@paste="handlePaste"`

**Interfaces:**
- Consumes: `this.attachments` (Vue data), `this._handleImageFile(file, attachmentId)` (existing method)
- Produces: `handlePaste(event)` — ClipboardEvent 处理器

- [ ] **Step 1: 在 script.js 中添加 handlePaste 方法**

在 `handleAttachClick` 方法之前插入（约第 791 行）：

```javascript
/** 粘贴事件处理 — 识别剪贴板中的图片并走附件 chip 流程 */
handlePaste(event) {
    const items = event.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
        if (item.type.startsWith('image/')) {
            event.preventDefault();

            if (this.attachments.length >= 5) {
                alert('最多只能添加 5 个附件');
                return;
            }

            const file = item.getAsFile();
            if (!file) continue;

            const attachmentId = 'att_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);
            this._handleImageFile(file, attachmentId);
        }
    }
},
```

- [ ] **Step 2: 在 index.html 的 textarea 上添加 @paste 绑定**

在 `<textarea` 标签的属性列表中添加一行（约第 388 行）：

```html
<textarea
    v-show="!voiceMode"
    v-model="userInput"
    @keydown="handleKeyDown"
    @paste="handlePaste"
    @compositionstart="handleCompositionStart"
    @compositionend="handleCompositionEnd"
    @input="autoResize"
    placeholder="和Javis说点什么吧... (Shift+Enter 换行)"
    rows="1"
    ref="textarea"
></textarea>
```

- [ ] **Step 3: 验证 JS 语法**

```bash
node --check frontend/script.js
```

预期：无输出（无错误）

- [ ] **Step 4: 浏览器验证**

打开 `http://127.0.0.1:8000/`，登录后：
1. 截图或复制一张图片
2. 在输入框 Ctrl+V
3. 确认出现 chip，状态从"提取中"变为就绪
4. 输入文字 → 发送 → 确认模型能看到图片内容
5. 粘贴纯文字 → 确认正常粘贴不受影响
6. 已经 5 个 chip 时粘贴图片 → 确认 alert 提示

- [ ] **Step 5: Commit**

```bash
git add frontend/script.js frontend/index.html
git commit -m "feat: add paste-to-upload image support in chat input"
```
