import client from './client'

export interface DocItem {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: string
  char_count: number
  chunk_count: number
  uploaded_by: string
  created_at: string
  tags: string[]
}

export interface CatItem {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
  children: CatItem[]
}

export interface TagItem {
  id: string
  name: string
  color: string
}

export function listDocuments(params: { page?: number; page_size?: number; search?: string; category_id?: string; status?: string }) {
  return client.get<any, { data: { items: DocItem[]; total: number; page: number; page_size: number } }>('/knowledge/documents', { params })
}

export function deleteDocument(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/documents/${id}`)
}

export function listCategories() {
  return client.get<any, { data: CatItem[] }>('/knowledge/categories')
}

export function createCategory(body: { name: string; parent_id?: string }) {
  return client.post<any, { data: CatItem }>('/knowledge/categories', body)
}

export function updateCategory(id: string, body: { name?: string; sort_order?: number }) {
  return client.put<any, { data: CatItem }>(`/knowledge/categories/${id}`, body)
}

export function deleteCategory(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/categories/${id}`)
}

export function listTags() {
  return client.get<any, { data: TagItem[] }>('/knowledge/tags')
}

export function createTag(body: { name: string; color: string }) {
  return client.post<any, { data: TagItem }>('/knowledge/tags', body)
}

export function deleteTag(id: string) {
  return client.delete<any, { data: any }>(`/knowledge/tags/${id}`)
}
