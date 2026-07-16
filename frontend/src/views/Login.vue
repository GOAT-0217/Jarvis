<template>
  <div class="login-wrapper">
    <!-- 背景图 -->
    <div class="bg-layer" :style="{ backgroundImage: `url(${bgImage})` }">
      <div class="bg-overlay" />
      <div class="bg-grid" />
      <div class="bg-glow bg-glow-1" />
      <div class="bg-glow bg-glow-2" />
      <div class="bg-particles">
        <span v-for="n in 16" :key="n" :style="particleStyle(n)" />
      </div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <div class="card-inner">
        <!-- 标题 -->
        <div class="brand">
          <div class="brand-icon">
            <span class="brand-icon-text">J</span>
          </div>
          <h1 class="brand-name">JARVIS</h1>
          <p class="brand-sub">Enterprise AI Knowledge Workshop</p>
        </div>

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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
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

function particleStyle(n: number) {
  const size = 2 + (n % 3)
  const x = ((n * 137 + 53) % 100)
  const y = ((n * 251 + 89) % 100)
  const dur = 3 + (n % 4) * 2
  const delay = (n % 5) * 1.2
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${x}%`,
    top: `${y}%`,
    animationDuration: `${dur}s`,
    animationDelay: `${delay}s`,
  }
}
</script>

<style scoped>
/* ===== 背景层 ===== */
.login-wrapper {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.bg-layer {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  z-index: 0;
}

/* 暗色叠加层 — 让卡片文字可读 */
.bg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(10, 14, 23, 0.7) 0%, rgba(15, 23, 41, 0.55) 50%, rgba(10, 14, 23, 0.72) 100%);
}

/* 网格线 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(64, 158, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64, 158, 255, 0.04) 1px, transparent 1px);
  background-size: 60px 60px;
}

/* 光晕 */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.12;
}
.bg-glow-1 {
  width: 600px;
  height: 600px;
  background: #409EFF;
  top: -200px;
  right: -100px;
}
.bg-glow-2 {
  width: 400px;
  height: 400px;
  background: #36cfc9;
  bottom: -150px;
  left: -80px;
}

/* 粒子 */
.bg-particles span {
  position: absolute;
  background: rgba(64, 158, 255, 0.5);
  border-radius: 50%;
  animation: float-up linear infinite;
}
@keyframes float-up {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  20% { opacity: 0.8; }
  80% { opacity: 0.4; }
  100% { transform: translateY(-60px) scale(0.4); opacity: 0; }
}

/* ===== 登录卡片 ===== */
.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
}

.card-inner {
  background: rgba(26, 32, 50, 0.82);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(64, 158, 255, 0.15);
  border-radius: 16px;
  padding: 48px 40px 36px;
  box-shadow:
    0 4px 32px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

/* ===== 品牌区 ===== */
.brand {
  text-align: center;
  margin-bottom: 36px;
}

.brand-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #409EFF 0%, #36cfc9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 24px rgba(64, 158, 255, 0.3);
}

.brand-icon-text {
  color: #fff;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 1px;
}

.brand-name {
  font-size: 28px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 6px;
  margin: 0 0 8px;
}

.brand-sub {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.7);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin: 0;
}

/* ===== 输入框 ===== */
:deep(.el-input__wrapper) {
  background: rgba(30, 41, 59, 0.6) !important;
  border: 1px solid rgba(64, 158, 255, 0.12) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  transition: border-color 0.25s;
}
:deep(.el-input__wrapper:hover) {
  border-color: rgba(64, 158, 255, 0.3) !important;
}
:deep(.el-input__wrapper.is-focus) {
  border-color: #409EFF !important;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15) !important;
}
:deep(.el-input__inner) {
  color: #e2e8f0 !important;
}
:deep(.el-input__inner::placeholder) {
  color: rgba(148, 163, 184, 0.5) !important;
}

/* ===== 登录按钮 ===== */
.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 10px !important;
  border: none !important;
  background: linear-gradient(135deg, #409EFF 0%, #36cfc9 100%) !important;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  color: #fff;
  transition: opacity 0.25s, box-shadow 0.25s;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.25);
}
.login-btn:hover {
  box-shadow: 0 4px 24px rgba(64, 158, 255, 0.45);
}
.login-btn:active {
  opacity: 0.85;
}

/* ===== 底部 ===== */
.footer-hint {
  text-align: center;
  margin: 16px 0 0;
  font-size: 13px;
  color: rgba(148, 163, 184, 0.5);
}

.footer-link {
  color: rgba(64, 158, 255, 0.7);
  text-decoration: none;
  cursor: pointer;
}
.footer-link:hover {
  color: #409EFF;
}
</style>
