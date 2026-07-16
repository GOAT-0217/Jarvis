import client from './client'

export interface SessionInfo {
  session_id: string
  updated_at: string
  message_count: number
  title?: string
}

export interface MessageInfo {
  type: string
  content: string
  timestamp: string
  rag_trace?: any
}

export function getSessions() {
  return client.get<any, { data: { sessions: SessionInfo[] } }>('/chat/sessions')
}

export function getSessionMessages(sessionId: string) {
  return client.get<any, { data: { messages: MessageInfo[] } }>(`/chat/sessions/${sessionId}`)
}

export function deleteSession(sessionId: string) {
  return client.delete<any, { data: any }>(`/chat/sessions/${sessionId}`)
}

export function renameSession(sessionId: string, title: string) {
  return client.put<any, { data: { title: string } }>(`/chat/sessions/${sessionId}/rename`, { title })
}

export interface ChatStreamParams {
  message: string
  session_id: string
  attachments?: any[]
}

export function streamChat(params: ChatStreamParams): Promise<Response> {
  const token = localStorage.getItem('accessToken')
  return fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(params),
  }).then(resp => {
    if (!resp.ok) throw new Error(`请求失败 (${resp.status})`)
    return resp
  })
}
