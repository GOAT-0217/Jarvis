<template>
  <div ref="chartRef" style="width: 100%; height: 320px" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  dates: string[]
  series: { name: string; data: number[] }[]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || !props.dates?.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#94a3b8' } },
    grid: { left: 40, right: 20, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: props.dates, axisLabel: { color: '#6d6f78' } },
    yAxis: { type: 'value', axisLabel: { color: '#6d6f78' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: props.series.map(s => ({ ...s, type: 'line', smooth: true, symbol: 'circle', symbolSize: 4 })),
  })
  chart.resize()
}

onMounted(render)
watch(() => [props.dates, props.series], render)
onBeforeUnmount(() => chart?.dispose())
</script>
