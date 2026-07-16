<template>
  <el-container class="app-shell">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="app-aside">
      <div class="sidebar-brand" v-show="!isCollapsed">
        <div class="brand-icon-sm">
          <span>J</span>
        </div>
        <span class="brand-text">JARVIS</span>
      </div>
      <div class="sidebar-brand sidebar-brand--mini" v-show="isCollapsed">
        <div class="brand-icon-sm">
          <span>J</span>
        </div>
      </div>
      <SidebarMenu :collapsed="isCollapsed" />
      <div class="sidebar-footer" v-show="!isCollapsed">
        <span>v1.1 · Enterprise</span>
      </div>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <HeaderBar @toggle-collapse="isCollapsed = !isCollapsed" />
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SidebarMenu from './SidebarMenu.vue'
import HeaderBar from './HeaderBar.vue'

const isCollapsed = ref(false)
</script>

<style scoped>
.app-shell {
  height: 100vh;
}

/* ===== 侧边栏 — GitHub 暗色 ===== */
.app-aside {
  background: #24292f;
  border-right: 1px solid #373e47;
  display: flex;
  flex-direction: column;
  transition: width 0.25s;
  overflow: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 18px;
  border-bottom: 1px solid #373e47;
}
.sidebar-brand--mini {
  justify-content: center;
  padding: 20px 0 18px;
}

.brand-icon-sm {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-icon-sm span {
  color: #24292f;
  font-size: 18px;
  font-weight: 800;
}

.brand-text {
  font-size: 17px;
  font-weight: 700;
  color: #e6edf3;
  letter-spacing: 2px;
  white-space: nowrap;
}

.sidebar-footer {
  margin-top: auto;
  padding: 12px 20px;
  font-size: 11px;
  color: #8b949e;
  border-top: 1px solid #373e47;
}

/* ===== 顶栏 — 白色 ===== */
.app-header {
  height: 56px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #d0d7de;
  display: flex;
  align-items: center;
}

/* ===== 内容区 — 浅灰底 ===== */
.app-main {
  background: #f6f8fa;
  padding: 24px;
  min-height: 0;
}
</style>
