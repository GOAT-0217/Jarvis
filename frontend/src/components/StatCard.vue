<template>
  <el-card shadow="hover" class="stat-card">
    <div class="stat-inner">
      <div class="stat-value" :style="{ color }">{{ value ?? '-' }}</div>
      <div class="stat-title">{{ title }}</div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{ title: string; value: number; color: string }>()
</script>

<style scoped>
.stat-card {
  border-radius: var(--radius-lg) !important;
  transition: transform 0.2s, box-shadow 0.25s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg) !important;
}

.stat-inner {
  text-align: center;
  padding: 8px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 4px;
}

.stat-title {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}
</style>
