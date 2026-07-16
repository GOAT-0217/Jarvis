<template>
  <div class="input-area">
    <el-input
      v-model="text"
      type="textarea"
      :rows="3"
      placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
      @keydown.enter.exact.prevent="handleSend"
    />
    <div style="display: flex; justify-content: flex-end; margin-top: 8px; gap: 8px">
      <el-button v-if="disabled" @click="$emit('stop')" type="danger">停止</el-button>
      <el-button @click="handleSend" type="primary" :disabled="!text.trim()">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const text = ref('')

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
}
</script>
