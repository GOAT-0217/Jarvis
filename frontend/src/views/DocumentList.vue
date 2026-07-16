<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h1>文档管理</h1>
      <el-button type="primary" @click="showUpload = true">上传文档</el-button>
    </div>

    <DataState :loading="loading" :error="error" :empty="!loading && !error && documents.length === 0"
      empty-text="还没有文档，上传第一份吧" @retry="fetchData">
      <el-table :data="documents" stripe>
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ready' ? 'success' : row.status === 'error' ? 'danger' : 'warning'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="切片数" width="80" />
        <el-table-column prop="created_at" label="上传时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :total="total"
        :page-size="20"
        layout="total, prev, pager, next"
        @current-change="fetchData"
      />
    </DataState>

    <UploadDialog v-model:visible="showUpload" @done="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listDocuments, deleteDocument } from '@/api/knowledge'
import type { DocItem } from '@/api/knowledge'
import DataState from '@/components/DataState.vue'
import UploadDialog from '@/components/UploadDialog.vue'

const documents = ref<DocItem[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const total = ref(0)
const showUpload = ref(false)

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDocuments({ page: page.value, page_size: 20 })
    documents.value = res.data.items
    total.value = res.data.total
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteDocument(id)
    fetchData()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

onMounted(fetchData)
</script>
