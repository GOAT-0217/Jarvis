<template>
  <el-menu
    :default-active="route.path"
    :collapse="collapsed"
    router
    class="sidebar-menu"
  >
    <el-menu-item index="/chat">
      <el-icon><ChatDotRound /></el-icon>
      <span>AI 助手</span>
    </el-menu-item>

    <div class="menu-divider" v-if="isAdmin" />

    <el-menu-item v-if="isAdmin" index="/dashboard">
      <el-icon><DataAnalysis /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>
    <el-menu-item v-if="isAdmin" index="/knowledge">
      <el-icon><Document /></el-icon>
      <span>文档管理</span>
    </el-menu-item>
    <el-menu-item v-if="isAdmin" index="/knowledge/categories">
      <el-icon><CollectionTag /></el-icon>
      <span>分类标签</span>
    </el-menu-item>

    <div class="menu-divider" v-if="isSuperAdmin" />

    <el-menu-item v-if="isSuperAdmin" index="/users">
      <el-icon><User /></el-icon>
      <span>用户管理</span>
    </el-menu-item>
    <el-menu-item v-if="isSuperAdmin" index="/settings">
      <el-icon><Setting /></el-icon>
      <span>系统设置</span>
    </el-menu-item>
    <el-menu-item v-if="isSuperAdmin" index="/audit-logs">
      <el-icon><Tickets /></el-icon>
      <span>操作日志</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import {
  ChatDotRound,
  DataAnalysis,
  Document,
  CollectionTag,
  User,
  Setting,
  Tickets,
} from '@element-plus/icons-vue'

defineProps<{ collapsed: boolean }>()

const route = useRoute()
const { isAdmin, isSuperAdmin } = useAuth()
</script>

<style scoped>
.sidebar-menu {
  height: 100%;
  border-right: 0 !important;
  background: transparent !important;
  padding: 4px 8px;
}

.sidebar-menu :deep(.el-menu-item) {
  margin: 2px 0;
  border-radius: 10px;
  color: var(--text-secondary) !important;
  background: transparent !important;
  transition: all 0.2s;
  height: 44px;
  line-height: 44px;
  font-size: 15px;
  position: relative;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 20px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--bg-hover) !important;
  color: var(--text-body) !important;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(79, 140, 247, 0.1) 0%, rgba(124, 92, 252, 0.06) 100%) !important;
  color: var(--accent) !important;
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--accent-gradient);
}

.sidebar-menu :deep(.el-menu-item.is-active .el-icon) {
  color: var(--accent) !important;
}

.menu-divider {
  height: 1px;
  margin: 4px 12px;
  background: linear-gradient(90deg, transparent, var(--border-light), transparent);
}
</style>
