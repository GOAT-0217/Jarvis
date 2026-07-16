<template>
  <div>
    <h1>操作日志</h1>
    <el-table :data="logs" stripe>
      <el-table-column prop="action" label="操作" width="150" />
      <el-table-column prop="target_type" label="对象类型" width="120" />
      <el-table-column prop="target_id" label="对象ID" width="200" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="详情">
        <template #default="{ row }">
          {{ JSON.stringify(row.detail).slice(0, 100) }}
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="20"
      layout="total, prev, pager, next"
      @current-change="fetchLogs"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listAuditLogs } from '@/api/admin'

const logs = ref<any[]>([])
const page = ref(1)
const total = ref(0)

async function fetchLogs() {
  const res = await listAuditLogs({ page: page.value })
  logs.value = res.data.items
  total.value = res.data.total
}

onMounted(fetchLogs)
</script>
