<template>
  <div class="header-bar">
    <div class="header-left">
      <el-button @click="$emit('toggleCollapse')" :icon="Fold" link class="collapse-btn" />
      <el-breadcrumb separator="/" class="header-breadcrumb">
        <el-breadcrumb-item :to="{ path: '/chat' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>{{ route.meta.title || route.name }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <el-dropdown @command="handleCommand" class="user-dropdown">
      <span class="user-trigger">
        <div class="user-avatar">
          <span>{{ (displayName || 'U')[0].toUpperCase() }}</span>
        </div>
        <span class="user-name">{{ displayName }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { changePassword } from '@/api/auth'
import { Fold, ArrowDown } from '@element-plus/icons-vue'

defineEmits<{ toggleCollapse: [] }>()

const route = useRoute()
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
</script>

<style scoped>
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
}

.collapse-btn {
  color: var(--text-secondary) !important;
}
.collapse-btn:hover {
  color: var(--accent) !important;
}

.header-breadcrumb {
  margin-left: 8px;
}
.header-breadcrumb :deep(.el-breadcrumb__inner) {
  color: var(--text-secondary) !important;
}
.header-breadcrumb :deep(.el-breadcrumb__inner.is-link:hover) {
  color: var(--accent) !important;
}
.header-breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--text-primary) !important;
}
.header-breadcrumb :deep(.el-breadcrumb__separator) {
  color: var(--text-muted) !important;
}

/* 用户下拉 */
.user-trigger {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  transition: color 0.2s;
}
.user-trigger:hover {
  color: var(--text-primary);
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-teal) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}

.user-name {
  font-size: 14px;
}
</style>
