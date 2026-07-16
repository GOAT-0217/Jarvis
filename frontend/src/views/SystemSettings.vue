<template>
  <div>
    <h1>系统设置</h1>
    <el-form label-width="160px" style="max-width: 600px">
      <el-form-item v-for="s in settings" :key="s.key" :label="s.key">
        <el-input v-model="s.value" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">保存设置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { getSettings, updateSettings } from '@/api/admin'

const settings = reactive<any[]>([])

onMounted(async () => {
  const res = await getSettings()
  settings.push(...res.data.map((s: any) => ({ key: s.key, value: s.value })))
})

async function save() {
  const body: Record<string, string> = {}
  settings.forEach((s: any) => { body[s.key] = s.value })
  await updateSettings(body)
  alert('保存成功')
}
</script>
