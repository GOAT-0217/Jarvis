import { ref } from 'vue'
import { getSessions, getSessionMessages, deleteSession, streamChat } from '@/api/chat'
import type { SessionInfo, MessageInfo } from '@/api/chat'

export interface RagStep {
  icon: string
  label: string
  detail: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  ragTrace?: any
  ragSteps?: RagStep[]
  isThinking?: boolean
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
        ragSteps: [],
        isThinking: false,
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
      ragSteps: [],
      isThinking: true,
    }
    messages.value.push(assistantMsg)

    isStreaming.value = true
    const lastIdx = messages.value.length - 1
    const controller = new AbortController()
    abortController.value = controller

    try {
      const response = await streamChat({
        message: text,
        session_id: sessionId,
        attachments,
      })

      if (!response.body) {
        messages.value[lastIdx] = { ...messages.value[lastIdx], content: '[错误] 响应流不可用' }
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
            const cur = messages.value[lastIdx]
            if (data.type === 'error') {
              cur.content = `[错误] ${data.content}`
            } else if (data.type === 'content' || data.type === 'text') {
              cur.isThinking = false
              cur.content += data.content || data.text || ''
            } else if (data.type === 'rag_step') {
              if (!cur.ragSteps) cur.ragSteps = []
              cur.ragSteps.push(data.step)
            } else if (data.type === 'trace') {
              cur.ragTrace = data.rag_trace
            } else if (typeof data.content === 'string') {
              cur.content += data.content
            } else if (typeof data === 'string') {
              cur.content += data
            }
            messages.value[lastIdx] = { ...cur }
          } catch {
            const cur = messages.value[lastIdx]
            cur.content += payload
            messages.value[lastIdx] = { ...cur }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        messages.value[lastIdx] = { ...messages.value[lastIdx], content: `[错误] ${e.message || '请求失败'}` }
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
