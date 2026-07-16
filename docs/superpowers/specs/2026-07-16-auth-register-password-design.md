# 用户注册、昵称与密码修改 — 设计文档

**版本:** v1.1.0  
**日期:** 2026-07-16  
**状态:** 待审阅  

---

## 1. 概述

为 JARVIS 补充完整的用户自助能力：开放注册、昵称展示、自助修改密码。

---

## 2. 数据库变更

### 2.1 users 表新增字段

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `nickname` | VARCHAR(100) | NULL | 显示名称，可重复，可修改 |
| `email` | VARCHAR(255) | NULL | 邮箱，预留密码找回 |

通过 Alembic 迁移脚本新增，`NULL` 兼容存量数据。

---

## 3. 后端设计

### 3.1 接口清单

| 方法 | 路径 | 变更类型 | 说明 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | **修改** | 入参增加 `nickname`、`email` |
| GET | `/api/v1/auth/me` | **修改** | 返回值增加 `nickname`、`email` |
| PUT | `/api/v1/auth/password` | **新增** | 修改当前用户密码，需验证旧密码 |

### 3.2 Schema 变更

**RegisterRequest（修改）：**
```python
class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "user"
    admin_code: Optional[str] = None
```

**CurrentUserResponse（修改）：**
```python
class CurrentUserResponse(BaseModel):
    username: str
    role: str
    nickname: Optional[str] = None
    email: Optional[str] = None
```

**ChangePasswordRequest（新增）：**
```python
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
```

### 3.3 修改密码接口

```
PUT /api/v1/auth/password

Request:  { "old_password": "xxx", "new_password": "yyy" }
Response: { "code": 0, "message": "success", "data": { "message": "密码已修改" } }
Errors:   400 — 新密码不能为空
          403 — 旧密码错误
```

- 校验 `old_password` 与当前用户密码哈希是否匹配
- 新密码哈希写入数据库
- 不强制重新登录（Token 仍有效）

### 3.4 注册接口变更

- 接受 `nickname` 和 `email` 可选参数
- 创建 User 时写入这两个字段
- 现有逻辑不变：用户名唯一校验、角色由 `resolve_role()` 解析

---

## 4. 前端设计

### 4.1 登录页改造

同一张卡片内切换登录/注册模式，不跳页，保持科技感背景不变。

**登录模式：**
- 用户名 + 密码 + 登录按钮
- 底部："没有账号？**立即注册**"（文字链接，点击切换到注册模式）

**注册模式：**
- 用户名 + 昵称 + 邮箱 + 密码 + 确认密码 + 注册按钮
- 底部："已有账号？**返回登录**"（文字链接，点击切回登录模式）

卡片高度随内容平滑过渡。

### 4.2 修改密码

**入口：** HeaderBar 右上角头像下拉菜单，"退出登录"上方新增"修改密码"项。

**弹窗：** `el-dialog`，标题"修改密码"，三个输入框：

| 字段 | 说明 |
|---|---|
| 旧密码 | 必须填写 |
| 新密码 | 最少 6 位 |
| 确认新密码 | 必须与新密码一致 |

前端校验两次输入一致后再提交，旧密码错误时提示。

### 4.3 昵称展示

- 右上角 HeaderBar 显示昵称（有昵称时）→ 回退显示 username（无昵称时）
- 管理后台用户列表显示昵称列

---

## 5. 实施要点

- Alembic 迁移：`ALTER TABLE users ADD COLUMN nickname VARCHAR(100), ADD COLUMN email VARCHAR(255);`
- 注册表单前端校验：用户名 ≥ 2 位，密码 ≥ 6 位，确认密码一致
- 修改密码后不清除 Token，保留会话
- 昵称和邮箱均为可选字段，存量用户这两个字段为 NULL

---

## 6. 排除项

- 不做邮箱验证（发送验证邮件）
- 不做忘记密码 / 邮件重置
- 不做密码强度指示器
- 不做注册激活流程
- 昵称不做唯一性约束
