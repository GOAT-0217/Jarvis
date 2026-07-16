<template>
  <div class="session-list">
    <el-button type="primary" @click="$emit('newChat')" style="width: 100%; margin-bottom: 12px">
      新建会话
    </el-button>

    <div v-for="group in groupedSessions" :key="group.label">
      <div class="group-label">{{ group.label }}</div>
      <div
        v-for="s in group.items"
        :key="s.session_id"
        :class="['session-item', { active: s.session_id === activeSessionId }]"
        @click="$emit('select', s.session_id)"
      >
        <div class="session-info">
          <span class="session-name">{{ s.title || '新建对话' }}</span>
          <span class="session-time">{{ formatTime(s.updated_at) }}</span>
        </div>
        <!-- 三点菜单 -->
        <el-dropdown trigger="click" @command="(cmd: string) => handleMenu(cmd, s.session_id)" class="menu-trigger" popper-class="session-popover">
          <el-button link class="menu-btn" @click.stop>
            <el-icon><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">
                <el-icon><Edit /></el-icon> 重命名
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided>
                <el-icon><Delete /></el-icon> 删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div v-if="!sessions.length" class="empty-state">
      <div class="empty-icon">💬</div>
      <div>暂无会话</div>
    </div>

    <!-- 重命名弹窗 -->
    <el-dialog v-model="showRename" title="重命名会话" width="360px" :close-on-click-modal="true">
      <el-input v-model="renameTitle" placeholder="输入新名称" maxlength="50" @keydown.enter="confirmRename" />
      <template #footer>
        <el-button @click="showRename = false">取消</el-button>
        <el-button type="primary" @click="confirmRename" :disabled="!renameTitle.trim()">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { MoreFilled, Edit, Delete } from '@element-plus/icons-vue'
import { renameSession } from '@/api/chat'
import type { SessionInfo } from '@/api/chat'

const props = defineProps<{
  sessions: SessionInfo[]
  activeSessionId: string
}>()

const emit = defineEmits<{
  select: [sessionId: string]
  delete: [sessionId: string]
  newChat: []
  'rename-done': [sessionId: string]
}>()

const showRename = ref(false)
const renameTarget = ref('')
const renameTitle = ref('')

function handleMenu(cmd: string, sessionId: string) {
  if (cmd === 'delete') {
    emit('delete', sessionId)
  } else if (cmd === 'rename') {
    const s = props.sessions.find(x => x.session_id === sessionId)
    renameTitle.value = s?.title || s?.session_id || ''
    renameTarget.value = sessionId
    showRename.value = true
  }
}

async function confirmRename() {
  if (!renameTitle.value.trim()) return
  try {
    await renameSession(renameTarget.value, renameTitle.value.trim())
    // 先更新当前已加载的 sessions
    const s = props.sessions.find(x => x.session_id === renameTarget.value)
    if (s) s.title = renameTitle.value.trim()
    // 同时通知父组件重新加载（如果提供了回调）
    emit('rename-done', renameTarget.value)
  } catch (e: any) {
    alert(e.message || '重命名失败')
  }
  showRename.value = false
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
  return order.filter(label => groups[label]?.length).map(label => ({ label, items: groups[label] }))
})
</script>

<style scoped>
.group-label {
  font-size: 11px; font-weight: 600; color: #5eead4;
  letter-spacing: 1px; padding: 12px 12px 4px; opacity: 0.7;
}

.session-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 8px 10px 12px; cursor: pointer; border-radius: 8px;
  margin: 1px 0; transition: background 0.15s;
}
.session-item:hover { background: rgba(94, 234, 212, 0.06); }
.session-item.active { background: linear-gradient(135deg, #5eead4, #a78bfa); }
.session-item.active .session-name,
.session-item.active .session-time { color: #0f141f; }

.session-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.session-name {
  font-size: 14px; color: #c9d1d9;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.session-time { font-size: 11px; color: #6d6f78; }

.session-item.active .session-name { color: #0f141f; }
.session-item.active .session-time { color: rgba(15, 20, 31, 0.6); }

/* 三点菜单按钮 */
.menu-btn {
  color: #6d6f78 !important;
  padding: 2px 4px !important;
  height: auto !important;
  flex-shrink: 0;
  opacity: 0;
}
.session-item:hover .menu-btn { opacity: 1; }
.session-item.active .menu-btn { opacity: 1; color: rgba(15, 20, 31, 0.5) !important; }

.empty-state { text-align: center; padding: 32px 16px; color: #6d6f78; font-size: 14px; }
.empty-icon { font-size: 28px; margin-bottom: 8px; }
</style>

<style>
/* 全局覆盖弹窗样式 */
.session-popover {
  background: #1e2433 !important;
  border: 1px solid rgba(94, 234, 212, 0.2) !important;
  border-radius: 8px !important;
  padding: 4px !important;
}
.session-popover .el-dropdown-menu__item {
  color: #c9d1d9 !important;
  border-radius: 6px;
}
.session-popover .el-dropdown-menu__item:hover {
  background: rgba(94, 234, 212, 0.08) !important;
}
</style>
