<template>
  <div style="display: flex; align-items: center; justify-content: space-between; height: 100%">
    <div>
      <el-button @click="$emit('toggleCollapse')" :icon="Fold" link />
      <el-breadcrumb separator="/" style="display: inline-block; margin-left: 12px">
        <el-breadcrumb-item :to="{ path: '/chat' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>{{ route.meta.title || route.name }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>
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
