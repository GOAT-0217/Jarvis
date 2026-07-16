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

      <!-- 每日上传类别趋势 -->
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card header="📂 每日上传类别趋势（近 30 天）">
            <LineChart v-if="stats.category_trend?.dates?.length" :dates="stats.category_trend.dates" :series="stats.category_trend.series" />
            <div v-else style="text-align: center; color: #6d6f78; padding: 24px">暂无数据</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 标签趋势 + 类别饼图 -->
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="14">
          <el-card header="🏷️ 标签使用趋势（近 30 天）">
            <LineChart v-if="stats.tag_trend?.dates?.length" :dates="stats.tag_trend.dates" :series="stats.tag_trend.series" />
            <div v-else style="text-align: center; color: #6d6f78; padding: 24px">暂无数据</div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="🥧 文件类别分布">
            <PieChart v-if="stats.category_distribution?.length" :data="stats.category_distribution" />
            <div v-else style="text-align: center; color: #6d6f78; padding: 24px">暂无数据</div>
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
import LineChart from '@/components/LineChart.vue'
import PieChart from '@/components/PieChart.vue'

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
