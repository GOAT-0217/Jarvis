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
        <div v-if="isStreaming" style="color: #999">AI 正在思考...</div>
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
}

.chat-sidebar {
  width: 260px;
  border-right: 1px solid var(--border-card);
  background: #fff;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  background: #f6f8fa;
}

.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--border-card);
  background: #fff;
}
</style>
