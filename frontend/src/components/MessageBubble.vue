<template>
  <div :class="['message', message.role]">
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
  let text = props.message.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  return `<p>${text}</p>`
})
</script>

<style scoped>
.message {
  max-width: 78%;
  display: flex;
  flex-direction: column;
  animation: msgSlide 0.25s ease-out;
}
.message.user {
  align-self: flex-end;
}
.message.assistant {
  align-self: flex-start;
}

@keyframes msgSlide {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.bubble {
  padding: 14px 18px;
  border-radius: 18px;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}

.bubble.assistant {
  background: #1e2433;
  color: #e2e8f0;
  border-bottom-left-radius: 6px;
  border: 1px solid rgba(94, 234, 212, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.bubble.user {
  background: linear-gradient(135deg, #5eead4, #a78bfa);
  color: #0f141f;
  border-bottom-right-radius: 6px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(94, 234, 212, 0.15);
}
</style>
