<template>
  <div :class="['message', message.role]">
    <!-- 思考过程（仅 AI 消息） -->
    <div v-if="message.role === 'assistant' && hasThinking" class="thinking-box">
      <div class="thinking-header" @click="showThinking = !showThinking">
        <svg class="thinking-icon-spin" :class="{ spinning: message.isThinking }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
        <span>{{ message.isThinking ? '思考中…' : `思考过程（${message.ragSteps?.length || message.ragTrace ? '已完成' : ''}）` }}</span>
        <svg class="chevron" :class="{ open: showThinking }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>
      <div v-show="showThinking" class="thinking-body">
        <!-- RAG 步骤列表 -->
        <div v-if="message.ragSteps?.length" class="thinking-steps">
          <div v-for="(step, i) in message.ragSteps" :key="i" class="thinking-step">
            <span class="step-icon">{{ step.icon }}</span>
            <span class="step-label">{{ step.label }}</span>
            <span v-if="step.detail" class="step-detail">{{ step.detail }}</span>
          </div>
        </div>
        <!-- 无步骤但仍在思考 -->
        <div v-else-if="message.isThinking" class="thinking-empty">
          正在分析问题…
        </div>
      </div>
    </div>

    <!-- 消息正文 -->
    <div v-if="message.content" :class="['bubble', message.role]">
      <div v-html="renderedContent" />
    </div>
    <!-- 思考中无内容时显示加载 -->
    <div v-else-if="message.role === 'assistant' && message.isThinking && !hasThinking" class="thinking-empty-bubble">
      思考中…
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ChatMessage } from '@/composables/useChat'

const props = defineProps<{ message: ChatMessage }>()

const showThinking = ref(true)

const hasThinking = computed(() =>
  (props.message.ragSteps && props.message.ragSteps.length > 0) ||
  props.message.isThinking
)

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
  max-width: 60%;
  display: flex;
  flex-direction: column;
  animation: msgSlide 0.25s ease-out;
  gap: 6px;
}
.message.user { align-self: flex-end; }
.message.assistant { align-self: flex-start; }

@keyframes msgSlide {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 思考过程框 */
.thinking-box {
  background: rgba(30, 36, 51, 0.7);
  border: 1px solid rgba(94, 234, 212, 0.15);
  border-radius: 10px;
  overflow: hidden;
  font-size: 13px;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  color: #94a3b8;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.thinking-header:hover { background: rgba(94, 234, 212, 0.04); }

.thinking-icon-spin {
  flex-shrink: 0;
  color: #5eead4;
}
.thinking-icon-spin.spinning { animation: spin 2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.chevron { flex-shrink: 0; margin-left: auto; transition: transform 0.2s; color: #6d6f78; }
.chevron.open { transform: rotate(180deg); }

.thinking-body { padding: 0 14px 12px; }

.thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}
.step-icon { flex-shrink: 0; font-size: 13px; }
.step-label { font-weight: 500; white-space: nowrap; }
.step-detail { opacity: 0.7; word-break: break-all; }

.thinking-empty {
  color: #6d6f78;
  font-size: 12px;
  font-style: italic;
}
.thinking-empty-bubble {
  color: #6d6f78;
  font-size: 13px;
  padding: 8px 0;
}

/* 消息气泡 */
.bubble {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.5;
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
