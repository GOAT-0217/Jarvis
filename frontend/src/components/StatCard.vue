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
  border-radius: 12px !important;
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4) !important;
}

.stat-inner {
  text-align: center;
  padding: 8px 0;
}

.stat-value {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 4px;
}

.stat-title {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
