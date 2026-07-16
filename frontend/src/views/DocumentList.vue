<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h1>文档管理</h1>
      <el-button type="primary" @click="showUpload = true">上传文档</el-button>
    </div>

    <!-- 搜索框 -->
    <el-input
      v-model="searchText"
      placeholder="搜索文档名称…"
      clearable
      :prefix-icon="Search"
      style="margin-bottom: 12px"
      @input="onSearch"
      @clear="onSearch"
    />

    <!-- 分类筛选标签 -->
    <div class="category-filters">
      <span
        :class="['cat-tag', { active: !selectedCategory }]"
        @click="selectCategory('')"
      >全部</span>
      <span
        v-for="cat in categories"
        :key="cat.id"
        :class="['cat-tag', { active: selectedCategory === cat.id }]"
        @click="selectCategory(cat.id)"
      >
        <span class="cat-dot" :style="{ background: catColor(cat.id) }"></span>
        {{ cat.name }}
      </span>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="文档列表" name="documents">
        <DataState :loading="loading" :error="error" :empty="!loading && !error && documents.length === 0"
          empty-text="还没有文档，上传第一份吧" @retry="fetchData">
          <el-table :data="documents" stripe>
            <el-table-column prop="filename" label="文件名" />
            <el-table-column label="分类" width="120">
              <template #default="{ row }">
                <el-select
                  :model-value="row.category_name ? `${row.category_name}__${row.category_id}` : ''"
                  placeholder="未分类"
                  size="small"
                  clearable
                  @change="(val: string) => handleCatChange(row, val)"
                  style="width: 100%"
                >
                  <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="`${cat.name}__${cat.id}`" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="标签" width="200">
              <template #default="{ row }">
                <div class="tag-cell">
                  <template v-for="(t, i) in (row.tags || [])" :key="t">
                    <el-tag
                      v-if="i < 3 || tagExpanded[row.id]"
                      size="small"
                      closable
                      @close="removeTag(row, t)"
                      style="margin: 1px 2px"
                    >
                      {{ t }}
                    </el-tag>
                  </template>
                  <span
                    v-if="(row.tags || []).length > 3 && !tagExpanded[row.id]"
                    class="tag-toggle"
                    @click="tagExpanded[row.id] = true"
                  >
                    +{{ (row.tags || []).length - 3 }}
                  </span>
                  <span
                    v-if="tagExpanded[row.id]"
                    class="tag-toggle"
                    @click="tagExpanded[row.id] = false"
                  >
                    收起
                  </span>
                  <el-select
                    v-if="(row.tags || []).length < 5"
                    model-value=""
                    placeholder="+"
                    size="small"
                    style="width: 36px"
                    @change="(val: string) => addTag(row, val)"
                  >
                    <el-option v-for="t in availableTags(row)" :key="t.id" :label="t.name" :value="t.id" />
                  </el-select>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="file_type" label="格式" width="70" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'ready' ? 'success' : row.status === 'error' ? 'danger' : 'warning'" size="small">
                  {{ row.status === 'ready' ? '就绪' : row.status === 'error' ? '失败' : '处理中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="切片" width="60" />
            <el-table-column prop="created_at" label="上传时间" width="170" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="page"
            :total="total"
            :page-size="20"
            layout="total, prev, pager, next"
            @current-change="fetchData"
          />
        </DataState>
      </el-tab-pane>
      <el-tab-pane label="回收站" name="trash">
        <DataState :loading="trashLoading" :error="trashError" :empty="!trashLoading && !trashError && trashDocuments.length === 0"
          empty-text="回收站为空" @retry="fetchTrash">
          <el-table :data="trashDocuments" stripe>
            <el-table-column prop="filename" label="文件名" />
            <el-table-column prop="file_type" label="类型" width="80" />
            <el-table-column prop="created_at" label="删除时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleRestore(row.id)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="trashPage"
            :total="trashTotal"
            :page-size="20"
            layout="total, prev, pager, next"
            @current-change="fetchTrash"
          />
        </DataState>
      </el-tab-pane>
    </el-tabs>

    <UploadDialog v-model:visible="showUpload" @done="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listDocuments, deleteDocument, listTrashDocuments, restoreDocument, listCategories, updateDocCategory, updateDocTags, listTags } from '@/api/knowledge'
import type { DocItem, CatItem, TagItem } from '@/api/knowledge'
import { Search } from '@element-plus/icons-vue'
import DataState from '@/components/DataState.vue'
import UploadDialog from '@/components/UploadDialog.vue'

const CAT_COLORS = ['#5eead4', '#a78bfa', '#f59e0b', '#3b82f6', '#ef4444', '#22c55e', '#ec4899', '#6366f1']

const searchText = ref('')
const tagExpanded = ref<Record<string, boolean>>({})
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchData()
  }, 300)
}

const documents = ref<DocItem[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const total = ref(0)
const showUpload = ref(false)
const categories = ref<CatItem[]>([])
const selectedCategory = ref('')

const activeTab = ref('documents')
const trashDocuments = ref<DocItem[]>([])
const trashLoading = ref(false)
const trashError = ref('')
const trashPage = ref(1)
const trashTotal = ref(0)

function catColor(id: string): string {
  let hash = 0
  for (const c of id) hash = ((hash << 5) - hash) + c.charCodeAt(0)
  return CAT_COLORS[Math.abs(hash) % CAT_COLORS.length]
}

async function handleCatChange(row: any, val: string) {
  if (!val) {
    await updateDocCategory(row.id, null)
    row.category_id = null
    row.category_name = null
  } else {
    const [name, id] = val.split('__')
    await updateDocCategory(row.id, id)
    row.category_id = id
    row.category_name = name
  }
}

// 标签
const allTags = ref<TagItem[]>([])
async function loadTags() {
  try { const res = await listTags(); allTags.value = res.data || [] } catch { /* ignore */ }
}
function availableTags(row: any) {
  return allTags.value.filter(t => !(row.tags || []).includes(t.name))
}
async function addTag(row: any, tagId: string) {
  if ((row.tags || []).length >= 5) return
  const tagIds = [...(row.tags || []), (allTags.value.find(t => t.id === tagId)?.name || '')]
  const res = await updateDocTags(row.id, allTags.value.filter(t => tagIds.includes(t.name)).map(t => t.id))
  row.tags = res.data.tags
}
async function removeTag(row: any, tagName: string) {
  const tagIds = (row.tags || []).filter((t: string) => t !== tagName)
    .map((t: string) => allTags.value.find(tt => tt.name === t)?.id).filter(Boolean)
  const res = await updateDocTags(row.id, tagIds)
  row.tags = res.data.tags
}

function selectCategory(catId: string) {
  selectedCategory.value = catId
  page.value = 1
  fetchData()
}

async function loadCategories() {
  try {
    const res = await listCategories()
    categories.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDocuments({
      page: page.value,
      page_size: 20,
      category_id: selectedCategory.value || undefined,
      search: searchText.value || undefined,
    })
    documents.value = res.data.items
    total.value = res.data.total
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteDocument(id)
    fetchData()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

async function fetchTrash() {
  trashLoading.value = true
  trashError.value = ''
  try {
    const res = await listTrashDocuments({ page: trashPage.value, page_size: 20 })
    trashDocuments.value = res.data.items
    trashTotal.value = res.data.total
  } catch (e: any) {
    trashError.value = e.message || '加载失败'
  } finally {
    trashLoading.value = false
  }
}

async function handleRestore(id: string) {
  try {
    await restoreDocument(id)
    fetchTrash()
    // Refresh the active documents list if user switches back
    fetchData()
  } catch (e: any) {
    alert(e.message || '恢复失败')
  }
}

function onTabChange(tab: string) {
  if (tab === 'trash') {
    fetchTrash()
  }
}

onMounted(() => { loadCategories(); loadTags(); fetchData() })
</script>

<style scoped>
.category-filters {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px;
}
.cat-tag {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: #8b949e; background: rgba(30, 36, 51, 0.5);
  border: 1px solid rgba(94, 234, 212, 0.08); transition: all 0.15s;
}
.cat-tag:hover { color: #e2e8f0; border-color: rgba(94, 234, 212, 0.2); }
.cat-tag.active { color: #5eead4; border-color: #5eead4; background: rgba(94, 234, 212, 0.08); }
.cat-dot { width: 7px; height: 7px; border-radius: 50%; }

.cat-label {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 12px; font-weight: 500; border: 1px solid;
}
.tag-cell { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
.tag-toggle {
  font-size: 11px; color: #5eead4; cursor: pointer; white-space: nowrap;
  padding: 2px 6px; border-radius: 4px; background: rgba(94, 234, 212, 0.08);
}
.tag-toggle:hover { background: rgba(94, 234, 212, 0.18); }
</style>
