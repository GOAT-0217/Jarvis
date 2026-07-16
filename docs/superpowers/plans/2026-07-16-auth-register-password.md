# 用户注册、昵称与密码修改 — 实施计划

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 为 JARVIS 补充开放注册、昵称展示、自助修改密码三项能力。

**Architecture:** 数据库通过 Alembic 迁移增加 `nickname` + `email` 列；后端在 `routers/auth.py` 更新注册和 `/me` 接口、新增 `PUT /api/v1/auth/password`；前端在 Login.vue 增加注册表单切换、HeaderBar 增加修改密码入口。

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy / Alembic / Vue 3 + TypeScript + Element Plus

## Global Constraints

- 所有 API 路径以 `/api/v1/` 开头
- 统一响应格式 `{code: int, message: str, data: T | null}`
- `nickname` 和 `email` 为可选字段，存量用户值为 NULL
- 注册逻辑不变：用户名唯一校验、角色由 `resolve_role()` 解析（默认 `user`）
- 修改密码后不清除 Token
- 不做邮箱验证、忘记密码、密码强度条

---

### Task 1: 数据库 — Alembic 迁移 + User 模型

**Files:**
- Modify: `backend/models.py:17`（User 模型追加两个字段）
- Create: `backend/alembic/versions/003_add_nickname_email.py`

**Interfaces:**
- Produces: `User.nickname: Mapped[str | None]`, `User.email: Mapped[str | None]`

- [ ] **Step 1: 修改 User 模型**

在 `backend/models.py` 的 `User` 类中，`created_at` 行之前追加：

```python
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

- [ ] **Step 2: 生成并运行迁移**

```bash
cd backend
uv run alembic revision --autogenerate -m "003_add_nickname_email"
uv run alembic upgrade head
```

- [ ] **Step 3: 验证**

```bash
cd backend
uv run python -c "
from core.database import SessionLocal
from models import User
db = SessionLocal()
# 测试查询存量用户，nickname/email 应为 None
u = db.query(User).first()
print(f'user={u.username}, nickname={u.nickname}, email={u.email}')
db.close()
"
```

- [ ] **Step 4: 提交**

```bash
git add backend/models.py backend/alembic/versions/003_add_nickname_email.py
git commit -m "feat: add nickname and email columns to users table"
```

---

### Task 2: 后端 — Schema + 注册 + /me + 修改密码

**Files:**
- Modify: `backend/schemas.py:8-13`（RegisterRequest 加 nickname + email）
- Modify: `backend/schemas.py:30-33`（CurrentUserResponse 加 nickname + email）
- Modify: `backend/schemas.py`（末尾追加 ChangePasswordRequest）
- Modify: `backend/routers/auth.py`（register 写入新字段，/me 返回新字段，新增 password 端点）

**Interfaces:**
- Consumes: `User.nickname`, `User.email` (Task 1)
- Produces:
  - `RegisterRequest` 新增 `nickname: Optional[str] = None`, `email: Optional[str] = None`
  - `CurrentUserResponse` 新增 `nickname: Optional[str] = None`, `email: Optional[str] = None`
  - `ChangePasswordRequest(old_password: str, new_password: str)`
  - `PUT /api/v1/auth/password` — response `APIResponse[dict]`

- [ ] **Step 1: 更新 schemas.py**

修改 `RegisterRequest`：

```python
class RegisterRequest(BaseModel):
    """注册请求。"""
    username: str
    password: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "user"
    admin_code: Optional[str] = None
```

修改 `CurrentUserResponse`：

```python
class CurrentUserResponse(BaseModel):
    """标准化当前用户信息的响应结构"""
    username: str
    role: str
    nickname: Optional[str] = None
    email: Optional[str] = None
```

在 schemas.py 末尾追加：

```python
class ChangePasswordRequest(BaseModel):
    """修改密码请求。"""
    old_password: str
    new_password: str
```

- [ ] **Step 2: 更新 routers/auth.py — 注册接口**

将现有 `register` 函数中的 `User(...)` 构造改为写入 `nickname` 和 `email`：

```python
@router.post("/register", response_model=APIResponse[AuthResponse])
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = (request.username or "").strip()
    password = (request.password or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")

    role = resolve_role(request.role, request.admin_code)
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
        nickname=(request.nickname or "").strip() or None,
        email=(request.email or "").strip() or None,
    )
    db.add(user)
    db.commit()

    token = create_access_token(username=username, role=role)
    return APIResponse(data=AuthResponse(access_token=token, username=username, role=role))
```

- [ ] **Step 3: 更新 routers/auth.py — /me 接口**

```python
@router.get("/me", response_model=APIResponse[CurrentUserResponse])
async def me(current_user: User = Depends(get_current_user)):
    return APIResponse(data=CurrentUserResponse(
        username=current_user.username,
        role=current_user.role,
        nickname=current_user.nickname,
        email=current_user.email,
    ))
```

- [ ] **Step 4: routers/auth.py — 新增修改密码端点**

在文件末尾追加，import 列表追加 `verify_password, get_password_hash, ChangePasswordRequest`：

```python
from core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
    verify_password,
    resolve_role,
)
from schemas import APIResponse, AuthResponse, ChangePasswordRequest, CurrentUserResponse, LoginRequest, RegisterRequest


@router.put("/password", response_model=APIResponse[dict])
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.new_password or not request.new_password.strip():
        raise HTTPException(status_code=400, detail="新密码不能为空")

    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="旧密码错误")

    current_user.password_hash = get_password_hash(request.new_password.strip())
    db.commit()

    return APIResponse(data={"message": "密码已修改"})
```

- [ ] **Step 5: 验证后端**

```bash
cd backend
uv run python -c "from app import app; print('App loaded OK')"
uv run pytest tests/test_auth.py -v
```

- [ ] **Step 6: 提交**

```bash
git add backend/schemas.py backend/routers/auth.py
git commit -m "feat: add nickname/email to register, update /me, add change-password endpoint"
```

---

### Task 3: 前端 — 登录/注册切换 + 修改密码 + 昵称展示

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/composables/useAuth.ts`
- Modify: `frontend/src/views/Login.vue`
- Modify: `frontend/src/components/HeaderBar.vue`

**Interfaces:**
- Consumes: `CurrentUserData.nickname`, `CurrentUserData.email`, `RegisterParams.nickname`, `RegisterParams.email` (Task 2)
- Consumes: `PUT /api/v1/auth/password` (Task 2)

- [ ] **Step 1: 更新 api/auth.ts**

```typescript
export interface RegisterParams {
  username: string
  password: string
  nickname?: string
  email?: string
  role?: string
  admin_code?: string
}

export interface CurrentUserData {
  username: string
  role: string
  nickname?: string
  email?: string
}

export function changePassword(params: { old_password: string; new_password: string }) {
  return client.put<any, { data: { message: string } }>('/auth/password', params)
}
```

- [ ] **Step 2: 更新 composables/useAuth.ts**

`doRegister` 和 `doLogin` 中保存 `currentUser` 时携带 `nickname` 和 `email`：

```typescript
async function doLogin(params: LoginParams) {
  const res = await apiLogin(params)
  token.value = res.data.access_token
  currentUser.value = {
    username: res.data.username,
    role: res.data.role,
    nickname: (res.data as any).nickname ?? undefined,
    email: (res.data as any).email ?? undefined,
  }
  localStorage.setItem('accessToken', res.data.access_token)
  localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
  router.push('/chat')
}

async function doRegister(params: RegisterParams) {
  const res = await apiRegister(params)
  token.value = res.data.access_token
  currentUser.value = {
    username: res.data.username,
    role: res.data.role,
    nickname: params.nickname ?? undefined,
    email: params.email ?? undefined,
  }
  localStorage.setItem('accessToken', res.data.access_token)
  localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
  router.push('/chat')
}
```

- [ ] **Step 3: 改造 Login.vue — 登录/注册切换**

在 Login.vue 的 `<script setup>` 中增加：

```typescript
import { ref, computed } from 'vue'
import { useAuth } from '@/composables/useAuth'
import bgImage from '@/assets/images/Jarvis登录背景图.png'

const isRegister = ref(false)

const username = ref('')
const nickname = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const { doLogin, doRegister } = useAuth()

async function handleSubmit() {
  if (isRegister.value) {
    if (password.value !== confirmPassword.value) {
      alert('两次密码不一致')
      return
    }
    loading.value = true
    try {
      await doRegister({
        username: username.value,
        password: password.value,
        nickname: nickname.value || undefined,
        email: email.value || undefined,
      })
    } catch (e: any) {
      alert(e.message || '注册失败')
    } finally {
      loading.value = false
    }
  } else {
    loading.value = true
    try {
      await doLogin({ username: username.value, password: password.value })
    } catch (e: any) {
      alert(e.message || '登录失败')
    } finally {
      loading.value = false
    }
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
  username.value = ''
  nickname.value = ''
  email.value = ''
  password.value = ''
  confirmPassword.value = ''
}
```

替换模板中 `<el-form>` 及底部文字为：

```vue
<el-form @submit.prevent="handleSubmit">
  <el-form-item>
    <el-input v-model="username" placeholder="用户名" size="large" />
  </el-form-item>
  <el-form-item v-if="isRegister">
    <el-input v-model="nickname" placeholder="昵称（选填）" size="large" />
  </el-form-item>
  <el-form-item v-if="isRegister">
    <el-input v-model="email" placeholder="邮箱（选填）" size="large" />
  </el-form-item>
  <el-form-item>
    <el-input v-model="password" type="password" placeholder="密码" show-password size="large" />
  </el-form-item>
  <el-form-item v-if="isRegister">
    <el-input v-model="confirmPassword" type="password" placeholder="确认密码" show-password size="large" />
  </el-form-item>
  <el-form-item>
    <el-button native-type="submit" :loading="loading" size="large" class="login-btn">
      {{ loading ? (isRegister ? '注册中…' : '验证中…') : (isRegister ? '注 册' : '登 录') }}
    </el-button>
  </el-form-item>
</el-form>

<p class="footer-hint">
  <span v-if="!isRegister">
    没有账号？<a href="#" @click.prevent="toggleMode" class="footer-link">立即注册</a>
  </span>
  <span v-else>
    已有账号？<a href="#" @click.prevent="toggleMode" class="footer-link">返回登录</a>
  </span>
</p>
```

在 `<style scoped>` 末尾追加：

```css
.footer-link {
  color: rgba(64, 158, 255, 0.7);
  text-decoration: none;
  cursor: pointer;
}
.footer-link:hover {
  color: #409EFF;
}
```

同时将 `.footer-hint` 改为：

```css
.footer-hint {
  text-align: center;
  margin: 16px 0 0;
  font-size: 13px;
  color: rgba(148, 163, 184, 0.5);
}
```

- [ ] **Step 4: HeaderBar.vue — 昵称展示 + 修改密码入口**

模板中将 `{{ currentUser?.username }}` 改为 `{{ displayName }}`，下拉菜单增加修改密码项：

```vue
<el-dropdown @command="handleCommand">
  <span style="cursor: pointer">
    {{ displayName }}
    <el-icon><ArrowDown /></el-icon>
  </span>
  <template #dropdown>
    <el-dropdown-menu>
      <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
      <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
    </el-dropdown-menu>
  </template>
</el-dropdown>

<!-- 修改密码弹窗 -->
<el-dialog v-model="showPasswordDialog" title="修改密码" width="400px">
  <el-form @submit.prevent="handleChangePassword">
    <el-form-item>
      <el-input v-model="oldPassword" type="password" placeholder="旧密码" show-password />
    </el-form-item>
    <el-form-item>
      <el-input v-model="newPassword" type="password" placeholder="新密码（最少 6 位）" show-password />
    </el-form-item>
    <el-form-item>
      <el-input v-model="confirmNewPassword" type="password" placeholder="确认新密码" show-password />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" native-type="submit" :loading="passwordLoading" style="width: 100%">
        确认修改
      </el-button>
    </el-form-item>
  </el-form>
</el-dialog>
```

在 `<script setup>` 中增加：

```typescript
import { ref, computed } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { changePassword } from '@/api/auth'
import { Fold, ArrowDown } from '@element-plus/icons-vue'

const { currentUser, logout } = useAuth()

const displayName = computed(() =>
  currentUser.value?.nickname || currentUser.value?.username || ''
)

const showPasswordDialog = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')
const passwordLoading = ref(false)

async function handleChangePassword() {
  if (newPassword.value.length < 6) {
    alert('新密码最少 6 位')
    return
  }
  if (newPassword.value !== confirmNewPassword.value) {
    alert('两次密码不一致')
    return
  }
  passwordLoading.value = true
  try {
    await changePassword({ old_password: oldPassword.value, new_password: newPassword.value })
    alert('密码修改成功')
    showPasswordDialog.value = false
    oldPassword.value = ''
    newPassword.value = ''
    confirmNewPassword.value = ''
  } catch (e: any) {
    alert(e.response?.data?.message || e.message || '修改失败')
  } finally {
    passwordLoading.value = false
  }
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') logout()
  if (cmd === 'changePassword') showPasswordDialog.value = true
}
```

- [ ] **Step 5: 验证前端**

```bash
cd frontend
npx vue-tsc --noEmit
npm run build
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/api/auth.ts frontend/src/composables/useAuth.ts frontend/src/views/Login.vue frontend/src/components/HeaderBar.vue
git commit -m "feat: add register form toggle, change-password dialog, nickname display"
```

---

### Task 4: 测试

**Files:**
- Modify: `backend/tests/test_auth.py`

- [ ] **Step 1: 添加测试用例**

在 `test_auth.py` 末尾追加：

```python
def test_register_with_nickname_and_email():
    """注册时传入 nickname 和 email。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": "test_extra_fields",
        "password": "test123",
        "nickname": "测试昵称",
        "email": "test@example.com",
    })
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_change_password_success():
    """正确旧密码修改成功。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": "test_pwd_change",
        "password": "oldpass123",
    })
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/v1/auth/password", json={
        "old_password": "oldpass123",
        "new_password": "newpass456",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["message"] == "密码已修改"


def test_change_password_wrong_old():
    """旧密码错误返回 403。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": "test_pwd_fail",
        "password": "oldpass123",
    })
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/v1/auth/password", json={
        "old_password": "wrong_old",
        "new_password": "newpass456",
    }, headers=headers)
    assert resp.status_code == 403


def test_change_password_empty_new():
    """新密码为空返回 400。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": "test_pwd_empty",
        "password": "oldpass123",
    })
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/v1/auth/password", json={
        "old_password": "oldpass123",
        "new_password": "",
    }, headers=headers)
    assert resp.status_code == 400


def test_me_returns_nickname_and_email():
    """/me 返回 nickname 和 email。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": "test_me_fields",
        "password": "test123",
        "nickname": "小明",
        "email": "xiaoming@test.com",
    })
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nickname"] == "小明"
    assert data["email"] == "xiaoming@test.com"
```

- [ ] **Step 2: 运行全部测试**

```bash
cd backend
uv run pytest tests/ -v
```

期望：全部通过（原有 21 个 + 新增 5 个 = 26 个），无失败。

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_auth.py
git commit -m "test: add register/change-password/nickname test cases"
```
