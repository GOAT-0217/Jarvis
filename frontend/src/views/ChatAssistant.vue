<template>
  <div class="chat-layout">
    <div class="chat-sidebar">
      <SessionList
        :sessions="sessions"
        :active-session-id="currentSessionId"
        @select="switchSession"
        @delete="handleDeleteSession"
        @new-chat="newChat"
        @rename-done="loadSessions"
      />
    </div>
    <div class="chat-main">
      <!-- 当前会话标题栏 -->
      <div class="chat-title-bar">
        <div v-if="editingTitle" class="title-edit">
          <input
            v-model="titleDraft"
            ref="titleInput"
            class="title-input"
            maxlength="50"
            @keydown.enter="saveTitle"
            @keydown.escape="cancelEditTitle"
            @blur="saveTitle"
          />
        </div>
        <div v-else class="title-display" @click="startEditTitle">
          <span class="title-text">{{ currentTitle }}</span>
          <el-icon class="title-edit-icon"><Edit /></el-icon>
        </div>
      </div>
      <div class="chat-messages" ref="messagesContainer">
        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
        />
        <div v-if="isStreaming && !messages[messages.length-1]?.content" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
      <div class="chat-input-area">
        <ChatInput
          :disabled="isStreaming"
          @send="handleSend"
          @stop="stopStreaming"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat'
import { renameSession } from '@/api/chat'
import { Edit } from '@element-plus/icons-vue'
import SessionList from '@/components/SessionList.vue'
import MessageBubble from '@/components/MessageBubble.vue'
import ChatInput from '@/components/ChatInput.vue'

const route = useRoute()
const router = useRouter()
const {
  sessions, messages, isStreaming,
  loadSessions, loadMessages, removeSession, sendMessage, stopStreaming,
} = useChat()

const messagesContainer = ref<HTMLElement>()
const titleInput = ref<HTMLInputElement>()
const currentSessionId = ref<string>('session_' + Date.now())

// 标题编辑
const editingTitle = ref(false)
const titleDraft = ref('')

const currentTitle = computed(() => {
  const s = sessions.value.find(x => x.session_id === currentSessionId.value)
  return s?.title || '新建对话'
})

function startEditTitle() {
  titleDraft.value = currentTitle.value
  editingTitle.value = true
  nextTick(() => titleInput.value?.focus())
}

async function saveTitle() {
  editingTitle.value = false
  const newTitle = titleDraft.value.trim()
  if (!newTitle || newTitle === currentTitle.value) return
  try {
    await renameSession(currentSessionId.value, newTitle)
    const s = sessions.value.find(x => x.session_id === currentSessionId.value)
    if (s) s.title = newTitle
    await loadSessions()
  } catch (e: any) {
    console.error('重命名失败:', e)
    alert(e?.response?.data?.message || e.message || '重命名失败')
  }
}

function cancelEditTitle() {
  editingTitle.value = false
}

onMounted(() => {
  loadSessions()
  if (route.params.sessionId) {
    currentSessionId.value = route.params.sessionId as string
    loadMessages(currentSessionId.value)
  }
})

async function switchSession(sid: string) {
  currentSessionId.value = sid
  router.push(`/chat/${sid}`)
  await loadMessages(sid)
}

async function handleDeleteSession(sid: string) {
  await removeSession(sid)
  if (currentSessionId.value === sid) {
    newChat()
  }
}

function newChat() {
  currentSessionId.value = 'session_' + Date.now()
  messages.value = []
}

async function handleSend(text: string) {
  await sendMessage(text, currentSessionId.value)
  // 刷新会话列表以获取新标题
  await loadSessions()
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  margin: -24px;
  background: #0f141f;
}

/* 会话列表 */
.chat-sidebar {
  width: 260px;
  border-right: 1px solid rgba(94, 234, 212, 0.06);
  background: #141a28;
}

/* 消息区 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 标题栏 */
.chat-title-bar {
  padding: 12px 28px;
  border-bottom: 1px solid rgba(94, 234, 212, 0.08);
  background: rgba(20, 26, 40, 0.6);
  backdrop-filter: blur(10px);
}
.title-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 6px;
  transition: background 0.15s;
}
.title-display:hover {
  background: rgba(94, 234, 212, 0.06);
}
.title-text {
  font-size: 17px;
  font-weight: 600;
  color: #e2e8f0;
}
.title-edit-icon {
  font-size: 13px;
  color: #6d6f78;
  opacity: 0;
  transition: opacity 0.15s;
}
.title-display:hover .title-edit-icon { opacity: 1; }

.title-edit {
  display: flex;
  align-items: center;
}
.title-input {
  width: 100%;
  background: rgba(30, 36, 51, 0.8);
  border: 1px solid #5eead4;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
  outline: none;
  font-family: inherit;
}
.title-input::placeholder { color: #6d6f78; }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}

/* 输入区 */
.chat-input-area {
  padding: 18px 28px 20px;
  background: transparent;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 14px 18px;
  align-self: flex-start;
}
.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #5eead4;
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
