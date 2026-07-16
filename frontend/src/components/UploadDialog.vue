<template>
  <el-dialog :model-value="visible" title="上传文档" width="480px" @update:model-value="$emit('update:visible', $event)" @open="loadCategories">
    <div class="upload-section">
      <!-- 分类选择 -->
      <div class="category-row">
        <el-select v-model="categoryId" placeholder="选择分类（可选）" clearable style="flex: 1">
          <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
        <!-- 内联新建 -->
        <template v-if="!showNewCat">
          <el-button @click="showNewCat = true" size="default" style="flex-shrink: 0">+ 新建分类</el-button>
        </template>
        <template v-else>
          <el-input
            v-model="newCatName"
            ref="newCatInput"
            placeholder="分类名"
            size="default"
            style="width: 120px; flex-shrink: 0"
            maxlength="20"
            @keydown.enter="createCategory"
          />
          <el-button type="primary" size="default" @click="createCategory" :disabled="!newCatName.trim()" style="flex-shrink: 0">确认</el-button>
          <el-button size="default" @click="showNewCat = false; newCatName = ''" style="flex-shrink: 0">取消</el-button>
        </template>
      </div>

      <!-- 上传区域 -->
      <el-upload
        drag
        :http-request="customUpload"
        :show-file-list="false"
        accept=".pdf,.docx,.doc,.xlsx,.xls"
      >
        <el-icon :size="40"><UploadFilled /></el-icon>
        <div style="margin-top: 8px">拖拽文件到此处或点击上传</div>
        <template #tip>
          <div style="margin-top: 8px; color: #6d6f78; font-size: 12px">
            支持 PDF、Word (.docx/.doc)、Excel (.xlsx/.xls)
          </div>
        </template>
      </el-upload>

      <div v-if="uploading" style="text-align: center; margin-top: 12px; color: #5eead4">
        正在上传…
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { listCategories, createCategory } from '@/api/knowledge'
import type { CatItem } from '@/api/knowledge'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [boolean]; done: [] }>()

const token = localStorage.getItem('accessToken') || ''
const categoryId = ref('')
const categories = ref<CatItem[]>([])
const uploading = ref(false)

// 内联新建分类
const showNewCat = ref(false)
const newCatName = ref('')
const newCatInput = ref()

async function loadCategories() {
  try {
    const res = await listCategories()
    categories.value = res.data || []
  } catch { /* ignore */ }
}

async function createCategory() {
  const name = newCatName.value.trim()
  if (!name) return
  try {
    const res = await createCategory({ name })
    categories.value.push(res.data)
    categoryId.value = res.data.id
    newCatName.value = ''
    showNewCat.value = false
  } catch (e: any) {
    alert(e.message || '创建分类失败')
  }
}

async function customUpload(options: any) {
  uploading.value = true
  const formData = new FormData()
  formData.append('file', options.file)
  if (categoryId.value) {
    formData.append('category_id', categoryId.value)
  }

  try {
    const resp = await fetch('/api/v1/knowledge/documents/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
    if (!resp.ok) throw new Error(`上传失败 (${resp.status})`)
    alert('上传成功，正在后台处理')
    emit('done')
  } catch (e: any) {
    alert('上传失败: ' + (e.message || '未知错误'))
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.category-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
