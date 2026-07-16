<template>
  <el-dialog :model-value="visible" title="上传文档" @update:model-value="$emit('update:visible', $event)">
    <el-upload
      drag
      :action="`/api/v1/knowledge/documents/upload`"
      :headers="{ Authorization: `Bearer ${token}` }"
      :on-success="handleSuccess"
      :on-error="handleError"
      accept=".pdf,.docx,.doc,.xlsx,.xls"
    >
      <el-icon><UploadFilled /></el-icon>
      <div>拖拽文件到此处或点击上传</div>
      <template #tip>
        <div>支持 PDF、Word (.docx/.doc)、Excel (.xlsx/.xls)</div>
      </template>
    </el-upload>
  </el-dialog>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'

defineProps<{ visible: boolean }>()
defineEmits<{ 'update:visible': [boolean]; done: [] }>()

const token = localStorage.getItem('accessToken') || ''

function handleSuccess() {
  alert('上传成功，正在后台处理')
  location.reload()
}

function handleError(err: any) {
  alert('上传失败: ' + (err.message || '未知错误'))
}
</script>
