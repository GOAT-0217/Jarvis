# 粘贴图片上传设计

**日期**: 2026-07-13
**状态**: 设计完成，待审核

---

## 1. 背景

当前聊天附件重构后，用户可通过 📎 按钮选择图片文件上传。但常见使用场景是：用户截图后 Ctrl+V 直接粘贴到聊天框。目前粘贴图片不会触发上传，图片数据以乱码形式出现在文本框里。

## 2. 目标

- 在输入框 textarea 上监听 paste 事件，识别剪贴板中的图片
- 图片粘贴后自动走现有 `_handleImageFile` 流程（base64 → chip）
- 文字粘贴行为不变

## 3. 设计

### 3.1 前端改动

**文件: `frontend/script.js`** — 新增 `handlePaste` 方法：

```javascript
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
}
```

**文件: `frontend/index.html`** — textarea 添加 paste 事件绑定：

```html
@paste="handlePaste"
```

### 3.2 复用现有逻辑

- 图片大小校验（10MB）— `_handleImageFile` 已有
- 附件数量上限（5）— handlePaste 和 `_handleImageFile` 双重检查
- base64 转换 — `_handleImageFile` 已实现
- chip 展示 / 发送 — 完全复用

### 3.3 不需要改动

- 后端：无改动
- CSS：无改动
- 文档上传（📎 按钮）：无改动

---

## 4. 边界情况

| 场景 | 处理 |
|---|---|
| 粘贴纯文本 | 不干预，正常粘贴 |
| 同时粘贴文本+图片 | 阻止整个事件，只处理图片（文本不粘贴） |
| 粘贴多张图片 | `getAsFile()` 获取第一张，其余忽略 |
| 粘贴非图片文件 | 不干预，正常行为 |
| 已满 5 个附件 | alert 提示，阻止粘贴 |
| 图片 > 10MB | `_handleImageFile` 拦截，alert 提示 |

---

## 5. 测试要点

- [ ] Ctrl+V 粘贴截图正常生成 chip
- [ ] 右键粘贴图片正常生成 chip
- [ ] 粘贴文字不受影响
- [ ] 满 5 个时粘贴图片被拒绝
- [ ] 超 10MB 图片被拒绝
