import client from './client'

export function getDashboardStats() {
  return client.get<any, { data: any }>('/admin/dashboard/stats')
}

export function listUsers(params: { page?: number; page_size?: number }) {
  return client.get<any, { data: { items: any[]; total: number; page: number; page_size: number } }>('/admin/users', { params })
}

export function updateUser(id: number, body: { role?: string; is_active?: boolean }) {
  return client.put<any, { data: any }>(`/admin/users/${id}`, body)
}

export function getSettings() {
  return client.get<any, { data: { key: string; value: string }[] }>('/admin/settings')
}

export function updateSettings(body: Record<string, string>) {
  return client.put<any, { data: any }>('/admin/settings', body)
}

export function listAuditLogs(params: { page?: number; page_size?: number; action?: string }) {
  return client.get<any, { data: { items: any[]; total: number; page: number; page_size: number } }>('/admin/audit-logs', { params })
}
