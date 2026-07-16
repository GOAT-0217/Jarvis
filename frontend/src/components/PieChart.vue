<template>
  <div ref="chartRef" style="width: 100%; height: 320px" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data: { name: string; count: number }[] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const colors = ['#5eead4', '#a78bfa', '#f59e0b', '#3b82f6', '#ef4444', '#22c55e', '#ec4899', '#6366f1', '#14b8a6', '#f97316']

function render() {
  if (!chartRef.value || !props.data?.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 0, top: 'center', textStyle: { color: '#94a3b8' } },
    series: [{
      type: 'pie',
      radius: ['50%', '80%'],
      center: ['40%', '50%'],
      itemStyle: { borderRadius: 6, borderColor: '#1a1b1e', borderWidth: 2 },
      label: { color: '#94a3b8' },
      data: props.data.map((d, i) => ({ ...d, value: d.count, itemStyle: { color: colors[i % colors.length] } })),
    }],
  })
  chart.resize()
}

onMounted(render)
watch(() => props.data, render)
onBeforeUnmount(() => chart?.dispose())
</script>
