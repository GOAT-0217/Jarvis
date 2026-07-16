<template>
  <div class="chat-layout">
    <div class="chat-sidebar">
      <SessionList
        :sessions="sessions"
        :active-session-id="currentSessionId"
        @select="switchSession"
        @delete="handleDeleteSession"
        @new-chat="newChat"
      />
    </div>
    <div class="chat-main">
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
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat'
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
const currentSessionId = ref<string>('session_' + Date.now())

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

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
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
