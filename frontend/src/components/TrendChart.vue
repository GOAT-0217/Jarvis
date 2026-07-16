<template>
  <div ref="chartRef" style="width: 100%; height: 300px" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ data: { date: string; count: number }[] }>()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || !props.data?.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.data.map((d) => d.date) },
    yAxis: { type: 'value' },
    series: [{ data: props.data.map((d) => d.count), type: 'line', smooth: true, areaStyle: {} }],
  })
  chart.resize()
}

onMounted(render)
watch(() => props.data, render)
onBeforeUnmount(() => chart?.dispose())
</script>
