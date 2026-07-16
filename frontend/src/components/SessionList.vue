<template>
  <div class="session-list">
    <el-button type="primary" @click="$emit('newChat')" style="width: 100%; margin-bottom: 12px">
      新建会话
    </el-button>

    <!-- 按时间分组 -->
    <div v-for="group in groupedSessions" :key="group.label">
      <div class="group-label">{{ group.label }}</div>
      <div
        v-for="s in group.items"
        :key="s.session_id"
        :class="['session-item', { active: s.session_id === activeSessionId }]"
        @click="$emit('select', s.session_id)"
      >
        <div class="session-info">
          <span class="session-name">{{ s.title || s.session_id }}</span>
          <span class="session-time">{{ formatTime(s.updated_at) }}</span>
        </div>
        <el-button
          link
          class="delete-btn"
          @click.stop="handleDelete(s.session_id)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>

    <div v-if="!sessions.length" class="empty-state">
      <div class="empty-icon">💬</div>
      <div>暂无会话</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SessionInfo } from '@/api/chat'

const props = defineProps<{
  sessions: SessionInfo[]
  activeSessionId: string
}>()

const emit = defineEmits<{
  select: [sessionId: string]
  delete: [sessionId: string]
  newChat: []
}>()

function handleDelete(sessionId: string) {
  emit('delete', sessionId)
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`

  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`

  const diffDay = Math.floor(diffHour / 24)
  if (diffDay === 1) return '昨天'
  if (diffDay < 7) return `${diffDay} 天前`
  if (diffDay < 30) return `${Math.floor(diffDay / 7)} 周前`
  if (diffDay < 365) return `${Math.floor(diffDay / 30)} 个月前`
  return `${Math.floor(diffDay / 365)} 年前`
}

function getGroupLabel(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekStart = new Date(today.getTime() - today.getDay() * 86400000)
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

  if (date >= today) return '今天'
  if (date >= yesterday) return '昨天'
  if (date >= weekStart) return '本周'
  if (date >= monthStart) return '本月'
  return '更早'
}

const groupedSessions = computed(() => {
  const groups: Record<string, SessionInfo[]> = {}
  const order = ['今天', '昨天', '本周', '本月', '更早']

  for (const s of props.sessions) {
    const label = getGroupLabel(s.updated_at)
    if (!groups[label]) groups[label] = []
    groups[label].push(s)
  }

  return order
    .filter(label => groups[label]?.length)
    .map(label => ({ label, items: groups[label] }))
})
</script>

<style scoped>
/* 分组标签 */
.group-label {
  font-size: 11px;
  font-weight: 600;
  color: #5eead4;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 12px 12px 4px;
  opacity: 0.7;
}

/* 会话项 */
.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 8px;
  margin: 1px 0;
  transition: background 0.15s;
}

.session-item:hover {
  background: rgba(94, 234, 212, 0.06);
}

.session-item.active {
  background: linear-gradient(135deg, #5eead4, #a78bfa);
}

.session-item.active .session-name,
.session-item.active .session-time {
  color: #0f141f;
}

/* 信息区 */
.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-name {
  font-size: 14px;
  color: #c9d1d9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 11px;
  color: #6d6f78;
}

.session-item.active .session-name { color: #0f141f; }
.session-item.active .session-time { color: rgba(15, 20, 31, 0.6); }

/* 删除按钮 */
.delete-btn {
  color: #6d6f78 !important;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}
.session-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: #ef4444 !important; }
.session-item.active .delete-btn { opacity: 1; color: rgba(15, 20, 31, 0.5) !important; }
.session-item.active .delete-btn:hover { color: #dc2626 !important; }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 32px 16px;
  color: #6d6f78;
  font-size: 14px;
}
.empty-icon {
  font-size: 28px;
  margin-bottom: 8px;
}
</style>
