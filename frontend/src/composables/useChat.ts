import { ref } from 'vue'
import { getSessions, getSessionMessages, deleteSession, streamChat } from '@/api/chat'
import type { SessionInfo, MessageInfo } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  ragTrace?: any
}

export function useChat() {
  const sessions = ref<SessionInfo[]>([])
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const abortController = ref<AbortController | null>(null)

  async function loadSessions() {
    const res = await getSessions()
    sessions.value = res.data.sessions
  }

  async function loadMessages(sessionId: string) {
    const res = await getSessionMessages(sessionId)
    messages.value = res.data.messages.map((m: MessageInfo) => ({
      id: `${m.timestamp}-${Math.random()}`,
      role: m.type === 'human' ? 'user' : 'assistant',
      content: m.content,
      ragTrace: m.rag_trace,
    }))
  }

  async function removeSession(sessionId: string) {
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.session_id !== sessionId)
  }

  async function sendMessage(text: string, sessionId: string, attachments?: any[]) {
    const userMsg: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: text,
    }
    messages.value.push(userMsg)

    const assistantMsg: ChatMessage = {
      id: `${Date.now()}-assistant`,
      role: 'assistant',
      content: '',
    }
    messages.value.push(assistantMsg)

    isStreaming.value = true
    const controller = new AbortController()
    abortController.value = controller

    try {
      const response = await streamChat({
        message: text,
        session_id: sessionId,
        attachments,
      })

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'error') {
                assistantMsg.content = data.content
              } else if (data.type === 'content' || data.type === 'text') {
                assistantMsg.content += data.content || data.text || ''
              } else if (typeof data === 'string') {
                assistantMsg.content += data
              } else if (data.content) {
                assistantMsg.content += data.content
              }
            } catch {
              // raw text
              assistantMsg.content += line.slice(6)
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        assistantMsg.content = `[错误] ${e.message}`
      }
    } finally {
      isStreaming.value = false
      abortController.value = null
    }
  }

  function stopStreaming() {
    abortController.value?.abort()
  }

  return {
    sessions,
    messages,
    isStreaming,
    loadSessions,
    loadMessages,
    removeSession,
    sendMessage,
    stopStreaming,
  }
}
