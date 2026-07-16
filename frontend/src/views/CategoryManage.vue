<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h1>分类标签管理</h1>
      <div>
        <el-button type="primary" @click="showAddCat = true">新增分类</el-button>
        <el-button type="success" @click="showAddTag = true">新增标签</el-button>
      </div>
    </div>

    <el-row :gutter="24">
      <el-col :span="12">
        <h3>分类列表</h3>
        <el-table :data="categories" stripe>
          <el-table-column prop="name" label="名称" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="danger" @click="handleDeleteCat(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showAddCat" title="新增分类">
          <el-input v-model="newCatName" placeholder="分类名称" />
          <template #footer>
            <el-button @click="showAddCat = false">取消</el-button>
            <el-button type="primary" @click="handleCreateCat">确认</el-button>
          </template>
        </el-dialog>
      </el-col>

      <el-col :span="12">
        <h3>标签列表</h3>
        <div>
          <el-tag
            v-for="tag in tags" :key="tag.id" :color="tag.color"
            closable @close="handleDeleteTag(tag.id)"
            style="margin: 4px"
          >
            {{ tag.name }}
          </el-tag>
        </div>

        <el-dialog v-model="showAddTag" title="新增标签">
          <el-input v-model="newTagName" placeholder="标签名称" />
          <el-color-picker v-model="newTagColor" />
          <template #footer>
            <el-button @click="showAddTag = false">取消</el-button>
            <el-button type="primary" @click="handleCreateTag">确认</el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listCategories, createCategory, deleteCategory, listTags, createTag, deleteTag } from '@/api/knowledge'
import type { CatItem, TagItem } from '@/api/knowledge'

const categories = ref<CatItem[]>([])
const tags = ref<TagItem[]>([])
const showAddCat = ref(false)
const showAddTag = ref(false)
const newCatName = ref('')
const newTagName = ref('')
const newTagColor = ref('#409EFF')

async function fetchData() {
  const [catRes, tagRes] = await Promise.all([listCategories(), listTags()])
  categories.value = catRes.data
  tags.value = tagRes.data
}

async function handleCreateCat() {
  if (!newCatName.value.trim()) return
  await createCategory({ name: newCatName.value.trim() })
  newCatName.value = ''
  showAddCat.value = false
  fetchData()
}

async function handleDeleteCat(id: string) {
  await deleteCategory(id)
  fetchData()
}

async function handleCreateTag() {
  if (!newTagName.value.trim()) return
  await createTag({ name: newTagName.value.trim(), color: newTagColor.value })
  newTagName.value = ''
  showAddTag.value = false
  fetchData()
}

async function handleDeleteTag(id: string) {
  await deleteTag(id)
  fetchData()
}

onMounted(fetchData)
</script>
