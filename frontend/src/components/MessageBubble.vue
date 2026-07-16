<template>
  <div :class="['message-row', message.role]">
    <div :class="['bubble', message.role]">
      <div v-html="renderedContent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/composables/useChat'

const props = defineProps<{ message: ChatMessage }>()

const renderedContent = computed(() => {
  // 简单 Markdown 渲染：代码块和换行
  let text = props.message.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  text = `<p>${text}</p>`
  return text
})
</script>

<style scoped>
.message-row { display: flex; margin-bottom: 16px; }
.message-row.user { justify-content: flex-end; }
.bubble { max-width: 70%; padding: 10px 14px; border-radius: 8px; }
.bubble.user { background: var(--accent); color: #fff; }
.bubble.assistant { background: #383a40; color: var(--text-body); }
</style>
