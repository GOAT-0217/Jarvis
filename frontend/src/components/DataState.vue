<template>
  <div>
    <div v-if="loading">
      <el-skeleton :rows="5" animated />
    </div>
    <div v-else-if="error" style="text-align: center; padding: 48px">
      <el-result icon="error" :title="error" sub-title="请稍后再试">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重试</el-button>
        </template>
      </el-result>
    </div>
    <div v-else-if="empty" style="text-align: center; padding: 48px">
      <el-result icon="info" :title="emptyText" />
    </div>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
  error: string
  empty: boolean
  emptyText: string
}>()

defineEmits<{ retry: [] }>()
</script>
