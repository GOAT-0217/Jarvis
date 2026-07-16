<template>
  <el-container class="app-shell">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="app-aside">
      <!-- 侧边栏头部品牌区 -->
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
      <!-- 底部信息 -->
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
  background: var(--bg-deep);
}

.app-aside {
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

/* 品牌区 */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
}
.sidebar-brand--mini {
  justify-content: center;
  padding: 20px 0 16px;
}

.brand-icon-sm {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-teal) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 16px var(--glow);
  flex-shrink: 0;
}
.brand-icon-sm span {
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}

.brand-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 4px;
  white-space: nowrap;
}

/* 底部 */
.sidebar-footer {
  margin-top: auto;
  padding: 12px 20px;
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 1px;
  border-top: 1px solid var(--border-subtle);
}

/* 顶栏 */
.app-header {
  height: 56px;
  padding: 0 20px;
  background: rgba(15, 23, 41, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
}

/* 内容区 */
.app-main {
  background: transparent;
  padding: 24px;
  min-height: 0;
}
</style>
