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
      <el-button @click="toggleVoice" :type="listening ? 'warning' : 'default'">
        {{ listening ? '停止录音' : '语音' }}
      </el-button>
      <el-button @click="handleSend" type="primary" :disabled="!text.trim()">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const text = ref('')
const listening = ref(false)
let recognition: SpeechRecognition | null = null

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
}

function toggleVoice() {
  if (listening.value) {
    stopVoice()
    return
  }
  const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognitionAPI) {
    alert('您的浏览器不支持语音识别功能，请使用 Chrome 或 Edge 浏览器。')
    return
  }
  recognition = new SpeechRecognitionAPI()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.continuous = false

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    const transcript = event.results[0][0].transcript
    text.value = (text.value + transcript).trim()
    listening.value = false
  }

  recognition.onerror = () => {
    listening.value = false
  }

  recognition.onend = () => {
    listening.value = false
  }

  recognition.start()
  listening.value = true
}

function stopVoice() {
  if (recognition) {
    recognition.stop()
    recognition = null
  }
  listening.value = false
}
</script>
