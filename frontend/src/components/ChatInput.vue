<template>
  <div class="input-area">
    <div class="input-row">
      <textarea
        v-model="text"
        placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
        :rows="1"
        @input="autoResize"
        @keydown.enter.exact.prevent="handleSend"
        ref="textareaRef"
      />
      <div class="input-actions">
        <button
          v-if="disabled"
          class="stop-btn"
          @click="$emit('stop')"
          title="停止"
        >
          ■
        </button>
        <button
          class="voice-btn"
          :class="{ active: listening }"
          @click="toggleVoice"
          :title="listening ? '停止录音' : '语音输入'"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
        <button
          class="send-btn"
          @click="handleSend"
          :disabled="!text.trim()"
          title="发送"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const listening = ref(false)
let recognition: any = null

function autoResize() {
  const el = textareaRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }
}

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
  const el = textareaRef.value
  if (el) el.style.height = 'auto'
}

function toggleVoice() {
  if (listening.value) { stopVoice(); return }
  const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognitionAPI) {
    alert('您的浏览器不支持语音识别，请使用 Chrome 或 Edge。')
    return
  }
  recognition = new SpeechRecognitionAPI()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.continuous = false
  recognition.onresult = (event: any) => {
    text.value = (text.value + ' ' + event.results[0][0].transcript).trim()
    listening.value = false
  }
  recognition.onerror = () => { listening.value = false }
  recognition.onend = () => { listening.value = false }
  recognition.start()
  listening.value = true
}

function stopVoice() {
  if (recognition) { recognition.stop(); recognition = null }
  listening.value = false
}
</script>

<style scoped>
.input-area {
  background: transparent;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: rgba(30, 36, 51, 0.8);
  padding: 8px 8px 8px 18px;
  border-radius: 24px;
  border: 1px solid rgba(94, 234, 212, 0.12);
  transition: border-color 0.25s, box-shadow 0.25s;
  backdrop-filter: blur(10px);
}
.input-row:focus-within {
  border-color: #5eead4;
  box-shadow: 0 0 0 3px rgba(94, 234, 212, 0.1);
}

textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  padding: 10px 0;
  font-family: inherit;
  font-size: 15px;
  outline: none;
  max-height: 120px;
  color: #e2e8f0;
  line-height: 1.5;
}
textarea::placeholder {
  color: #94a3b8;
  opacity: 0.7;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 20px;
  border: none;
  background: linear-gradient(135deg, #5eead4, #a78bfa);
  color: #0f141f;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 12px rgba(94, 234, 212, 0.2);
}
.send-btn:hover:not(:disabled) {
  transform: scale(1.04);
  box-shadow: 0 6px 16px rgba(94, 234, 212, 0.35);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.voice-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(94, 234, 212, 0.08);
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.voice-btn:hover { background: rgba(94, 234, 212, 0.15); color: #5eead4; }
.voice-btn.active { background: rgba(220, 38, 38, 0.2); color: #ef4444; }

.stop-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
}
</style>
