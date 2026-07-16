<template>
  <div class="session-list">
    <el-button type="primary" @click="$emit('newChat')" style="width: 100%; margin-bottom: 12px">
      新建会话
    </el-button>
    <div
      v-for="s in sessions"
      :key="s.session_id"
      :class="['session-item', { active: s.session_id === activeSessionId }]"
      @click="$emit('select', s.session_id)"
    >
      <span class="session-name">{{ s.session_id }}</span>
      <el-button
        link
        type="danger"
        @click.stop="$emit('delete', s.session_id)"
      >
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <div v-if="!sessions.length" style="color: #999; text-align: center; padding: 24px">
      暂无会话
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SessionInfo } from '@/api/chat'

defineProps<{
  sessions: SessionInfo[]
  activeSessionId: string
}>()

defineEmits<{
  select: [sessionId: string]
  delete: [sessionId: string]
  newChat: []
}>()
</script>

<style scoped>
.session-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; border-radius: 4px;
}
.session-item:hover { background: #f5f7fa; }
.session-item.active { background: #ecf5ff; }
</style>
