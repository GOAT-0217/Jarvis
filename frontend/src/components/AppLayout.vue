<template>
  <el-container style="height: 100vh">
    <el-aside :width="isCollapsed ? '64px' : '220px'" style="transition: width 0.2s">
      <SidebarMenu :collapsed="isCollapsed" />
    </el-aside>
    <el-container>
      <el-header style="height: 56px; padding: 0 16px; border-bottom: 1px solid #e4e7ed">
        <HeaderBar @toggle-collapse="isCollapsed = !isCollapsed" />
      </el-header>
      <el-main>
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
