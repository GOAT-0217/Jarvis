<template>
  <div>
    <h1>用户管理</h1>
    <el-table :data="users" stripe>
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="角色" width="150">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            @change="(val: string) => handleRoleChange(row.id, val)"
          >
            <el-option label="普通用户" value="user" />
            <el-option label="知识管理员" value="knowledge_admin" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="20"
      layout="total, prev, pager, next"
      @current-change="fetchUsers"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listUsers, updateUser } from '@/api/admin'

const users = ref<any[]>([])
const page = ref(1)
const total = ref(0)

async function fetchUsers() {
  const res = await listUsers({ page: page.value })
  users.value = res.data.items
  total.value = res.data.total
}

async function handleRoleChange(userId: number, role: string) {
  await updateUser(userId, { role })
  fetchUsers()
}

onMounted(fetchUsers)
</script>
