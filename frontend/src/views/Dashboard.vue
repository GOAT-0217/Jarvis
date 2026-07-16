<template>
  <div>
    <h1>仪表盘</h1>
    <DataState :loading="loading" :error="error" :empty="false" empty-text="" @retry="fetchData">
      <el-row :gutter="16" style="margin-bottom: 24px">
        <el-col :span="6">
          <StatCard title="文档总数" :value="stats.document_count" color="#409EFF" />
        </el-col>
        <el-col :span="6">
          <StatCard title="今日上传" :value="stats.today_upload_count" color="#67C23A" />
        </el-col>
        <el-col :span="6">
          <StatCard title="总问答数" :value="stats.total_queries" color="#E6A23C" />
        </el-col>
        <el-col :span="6">
          <StatCard title="活跃用户" :value="stats.active_users?.length || 0" color="#F56C6C" />
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="16">
          <el-card><TrendChart :data="stats.query_trend" /></el-card>
        </el-col>
        <el-col :span="8">
          <el-card header="热门搜索">
            <div v-for="q in stats.top_queries" :key="q.term" style="padding: 4px 0">
              {{ q.term }} <el-tag size="small">{{ q.count }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '@/api/admin'
import DataState from '@/components/DataState.vue'
import StatCard from '@/components/StatCard.vue'
import TrendChart from '@/components/TrendChart.vue'

const stats = ref<any>({})
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDashboardStats()
    stats.value = res.data
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
