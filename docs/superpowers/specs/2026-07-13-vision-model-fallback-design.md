# 图片附件视觉理解降级设计

**日期**: 2026-07-13
**状态**: 设计完成，待审核

---

## 1. 背景

ARK（火山方舟）上的 DeepSeek 模型不支持多模态/图片理解。聊天区图片附件以 `image_url` 格式发送时模型无法识别。需要改用两步走方案：图片先经豆包视觉模型转文字描述，再喂给 DeepSeek。

## 2. 设计

### 2.1 配置

`.env` 新增：

```env
VISION_MODEL=doubao-seed-1-6-vision-250815
```

复用现有 `ARK_API_KEY` 和 `BASE_URL`。

### 2.2 agent.py 改动

**新增 `_describe_image(base64_uri: str) -> str`**：

- 调用豆包视觉模型，将 base64 图片转为文字描述
- prompt: "请详细描述这张图片的内容，包括文字、布局、数据等所有可见信息。"
- 视觉模型按需初始化（只有有图片附件时才加载）
- 调用失败时返回 `(图片识别失败: <error>)` 不阻塞聊天

**修改 `_build_user_message`**：

- 图片附件不再构建 `image_url` 块
- 改为调用 `_describe_image()` 获取文字描述
- 将描述以文本格式注入：`[用户上传的图片: xxx.png]\n图片内容描述:\n<description>\n---`

### 2.3 数据流

```
用户发送 [{type: "image", content: "data:image/png;base64,..."}]
    │
    ▼
_build_user_message() 检测到 image 附件
    │
    ├── _describe_image(base64) → 豆包视觉模型
    │     └── "这是一张截图，显示了..."
    │
    └── 构建纯文本 HumanMessage:
        [用户上传的图片: screenshot.png]
        图片内容描述:
        这是一张截图，显示了...
        ---
        用户问题: 这是什么？
    │
    ▼
DeepSeek 收到纯文本 → 正常回复
```

### 2.4 错误处理

| 场景 | 处理 |
|---|---|
| 视觉模型调用失败 | 返回 `(图片识别失败: <error>)`，不阻塞聊天 |
| VISION_MODEL 未配置 | 使用默认值 `doubao-seed-1-6-vision-250815` |
| 图片 base64 过长 | 视觉模型 32k 上下文足够，不做额外限制 |

---

## 3. 测试要点

- [ ] 纯文本聊天不受影响
- [ ] 发送图片 → 模型能描述图片内容
- [ ] 视觉模型调用失败时降级不阻塞
- [ ] 多张图片都能被描述
- [ ] 图片 + 文档混合附件正常
