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
    try {
      const res = await getSessions()
      // 后端 sessions 接口返回 {sessions: [...]}，未包装在 data 内
      sessions.value = (res.data?.sessions || res.sessions || [])
    } catch (e: any) {
      console.error('加载会话列表失败:', e)
    }
  }

  async function loadMessages(sessionId: string) {
    try {
      const res = await getSessionMessages(sessionId)
      // 后端 messages 接口返回 {messages: [...]}，未包装在 data 内
      const msgs = res.data?.messages || res.messages || []
      messages.value = msgs.map((m: MessageInfo) => ({
        id: `${m.timestamp}-${Math.random()}`,
        role: m.type === 'human' ? 'user' : 'assistant',
        content: m.content || '',
        ragTrace: m.rag_trace,
      }))
    } catch (e: any) {
      console.error('加载消息失败:', e)
      messages.value = []
    }
  }

  async function removeSession(sessionId: string) {
    try {
      await deleteSession(sessionId)
      sessions.value = sessions.value.filter((s) => s.session_id !== sessionId)
    } catch (e: any) {
      console.error('删除会话失败:', e)
    }
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

      if (!response.body) {
        assistantMsg.content = '[错误] 响应流不可用'
        console.error('response.body is null')
        return
      }

      console.log('开始读取 SSE 流...')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (!payload || payload === '[DONE]') continue

          try {
            const data = JSON.parse(payload)
            console.log('SSE event:', data.type, typeof data.content === 'string' ? data.content.slice(0, 20) : data.content)
            if (data.type === 'error') {
              assistantMsg.content = `[错误] ${data.content}`
            } else if (data.type === 'content' || data.type === 'text') {
              assistantMsg.content += data.content || data.text || ''
            } else if (typeof data.content === 'string') {
              assistantMsg.content += data.content
            } else if (typeof data === 'string') {
              assistantMsg.content += data
            }
          } catch {
            assistantMsg.content += payload
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        assistantMsg.content = `[错误] ${e.message || '请求失败'}`
        console.error('AI 请求失败:', e)
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
