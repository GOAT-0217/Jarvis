<template>
  <el-menu
    :default-active="route.path"
    :collapse="collapsed"
    router
    style="height: 100%; border-right: 0"
  >
    <el-menu-item index="/chat">
      <el-icon><ChatDotRound /></el-icon>
      <span>AI 助手</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/dashboard"
    >
      <el-icon><DataAnalysis /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/knowledge"
    >
      <el-icon><Document /></el-icon>
      <span>文档管理</span>
    </el-menu-item>
    <el-menu-item
      v-if="isAdmin"
      index="/knowledge/categories"
    >
      <el-icon><CollectionTag /></el-icon>
      <span>分类标签</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/users"
    >
      <el-icon><User /></el-icon>
      <span>用户管理</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/settings"
    >
      <el-icon><Setting /></el-icon>
      <span>系统设置</span>
    </el-menu-item>
    <el-menu-item
      v-if="isSuperAdmin"
      index="/audit-logs"
    >
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
