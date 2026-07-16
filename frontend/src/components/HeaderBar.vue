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
        {{ currentUser?.username }}
        <el-icon><ArrowDown /></el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="logout">退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { Fold, ArrowDown } from '@element-plus/icons-vue'

defineEmits<{ toggleCollapse: [] }>()

const route = useRoute()
const { currentUser, logout } = useAuth()

function handleCommand(cmd: string) {
  if (cmd === 'logout') logout()
}
</script>
