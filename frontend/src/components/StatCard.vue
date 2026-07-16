<template>
  <el-card shadow="hover">
    <div style="text-align: center">
      <div style="font-size: 28px; font-weight: bold; color: v-bind(color)">{{ value ?? '-' }}</div>
      <div style="color: #999; margin-top: 8px">{{ title }}</div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{ title: string; value: number; color: string }>()
</script>
