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
      <span class="session-name">{{ s.title || s.session_id }}</span>
      <el-button
        link
        type="danger"
        @click.stop="$emit('delete', s.session_id)"
      >
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <div v-if="!sessions.length" style="color: var(--text-muted); text-align: center; padding: 24px">
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
.session-item { color: #8b949e; }
.session-item:hover { background: rgba(94, 234, 212, 0.06); color: #e2e8f0; }
.session-item.active { background: linear-gradient(135deg, #5eead4, #a78bfa); color: #0f141f; font-weight: 500; }
.session-item.active .session-name { color: #0f141f; }
</style>
