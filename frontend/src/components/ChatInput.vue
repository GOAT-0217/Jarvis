<template>
  <div class="input-area" :class="{ 'voice-active': voiceMode }">
    <!-- 附件芯片区 -->
    <div v-if="attachments.length" class="attach-chips">
      <span v-for="a in attachments" :key="a.id" class="chip" :class="a.status">
        <span class="chip-icon">{{ a.type === 'image' ? '🖼' : '📎' }}</span>
        <span class="chip-name">{{ a.filename }}</span>
        <span v-if="a.status === 'extracting'" class="chip-status">提取中…</span>
        <span v-else-if="a.status === 'ready'" class="chip-status ready">✓</span>
        <span v-else-if="a.status === 'error'" class="chip-status error">✗</span>
      </span>
    </div>

    <!-- 语音模式：显示语音交互区 -->
    <div v-if="voiceMode" class="voice-input-area" :class="voiceState">
      <div class="voice-ripple-container">
        <div class="voice-ripple r1"></div>
        <div class="voice-ripple r2"></div>
        <div class="voice-ripple r3"></div>
      </div>
      <div class="voice-placeholder">
        <template v-if="voiceState === 'idle'">点击下方麦克风开始录音</template>
        <template v-else-if="voiceState === 'listening'">
          <span class="voice-dot"></span> 正在聆听…
        </template>
        <template v-else-if="voiceState === 'processing'">
          <span class="voice-spinner"></span> 识别中…
        </template>
        <template v-else-if="voiceState === 'error'">
          {{ voiceErrorMsg || '语音识别不可用，请使用文字输入' }}
        </template>
      </div>
      <div v-if="voiceState === 'listening'" class="interim-text">{{ interimText }}</div>
    </div>

    <!-- 文字模式：输入框 -->
    <div v-else class="input-row">
      <!-- 附件按钮（管理员可见） -->
      <label v-if="isAdmin" class="attach-btn" title="上传附件">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
        </svg>
        <input type="file" hidden @change="onFileChange" accept=".pdf,.docx,.doc,.xlsx,.xls" />
      </label>

      <textarea
        ref="textareaRef"
        v-model="text"
        placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
        :rows="1"
        @input="autoResize"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="input-actions">
        <button v-if="disabled" class="stop-btn" @click="$emit('stop')" title="停止">■</button>
        <button class="voice-btn" :class="{ active: voiceMode }" @click="toggleVoice" title="语音输入">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
        <button class="send-btn" @click="handleSend" :disabled="!text.trim()" title="发送">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 语音模式下的底部按钮 -->
    <div v-if="voiceMode" class="voice-actions">
      <button class="voice-toggle-btn" @click="toggleVoice" title="切回文字">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/>
        </svg>
      </button>
      <span v-if="voiceState === 'listening'" class="voice-hint">说完点击按钮停止</span>
      <span v-else class="voice-hint">点击按钮开始录音</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const { isAdmin } = useAuth()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const attachments = ref<any[]>([])

const voiceMode = ref(false)
const voiceState = ref<'idle' | 'listening' | 'processing' | 'error'>('idle')
const interimText = ref('')
const voiceErrorMsg = ref('')

let recognition: any = null

function autoResize() {
  const el = textareaRef.value
  if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px' }
}

function handleSend() {
  if (!text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
  const el = textareaRef.value
  if (el) el.style.height = 'auto'
}

function toggleVoice() {
  if (voiceMode.value) {
    stopVoice()
    voiceMode.value = false
    return
  }
  const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognitionAPI) {
    voiceState.value = 'error'
    voiceErrorMsg.value = '浏览器不支持语音识别，请使用 Chrome 或 Edge'
    return
  }
  voiceMode.value = true
  voiceState.value = 'idle'
  startListening()
}

function startListening() {
  const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognitionAPI) return
  try {
    recognition = new SpeechRecognitionAPI()
    recognition.lang = 'zh-CN'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.onstart = () => { voiceState.value = 'listening'; interimText.value = '' }
    recognition.onresult = (event: any) => {
      let interim = ''
      let final = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i]
        if (r.isFinal) final += r[0].transcript
        else interim += r[0].transcript
      }
      interimText.value = interim
      if (final) {
        voiceState.value = 'processing'
        setTimeout(() => {
          emit('send', final.trim())
          voiceMode.value = false
          voiceState.value = 'idle'
          interimText.value = ''
        }, 400)
      }
    }
    recognition.onerror = (event: any) => {
      if (event.error === 'not-allowed') {
        voiceState.value = 'error'
        voiceErrorMsg.value = '麦克风权限被拒绝，请在浏览器设置中允许'
      } else if (event.error !== 'no-speech') {
        voiceState.value = 'error'
        voiceErrorMsg.value = '语音识别出错，请重试'
      }
    }
    recognition.onend = () => { if (voiceMode.value) voiceState.value = 'idle' }
    recognition.start()
  } catch {
    voiceState.value = 'error'
    voiceErrorMsg.value = '语音识别启动失败'
  }
}

function stopVoice() {
  if (recognition) { try { recognition.stop() } catch {} recognition = null }
  voiceMode.value = false
  voiceState.value = 'idle'
  interimText.value = ''
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  for (const file of Array.from(input.files)) {
    const chip = { id: Date.now() + Math.random(), type: 'file', filename: file.name, status: 'extracting' }
    attachments.value.push(chip)
    // 模拟提取完成
    setTimeout(() => { chip.status = 'ready' }, 1500)
  }
  input.value = ''
}
</script>

<style scoped>
.input-area { padding: 0; }
.input-row {
  display: flex; align-items: flex-end; gap: 10px;
  background: rgba(30, 36, 51, 0.8); padding: 8px 8px 8px 18px;
  border-radius: 24px; border: 1px solid rgba(94, 234, 212, 0.12);
  transition: border-color 0.25s, box-shadow 0.25s; backdrop-filter: blur(10px);
}
.input-row:focus-within { border-color: #5eead4; box-shadow: 0 0 0 3px rgba(94, 234, 212, 0.1); }

/* 附件按钮 */
.attach-btn {
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 50%; cursor: pointer;
  color: #94a3b8; transition: background 0.2s, color 0.2s; flex-shrink: 0;
}
.attach-btn:hover { background: rgba(94, 234, 212, 0.1); color: #5eead4; }

/* 附件芯片 */
.attach-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; padding: 0 4px; }
.chip {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px;
  border-radius: 12px; font-size: 12px; background: rgba(94, 234, 212, 0.08);
  color: #94a3b8; border: 1px solid rgba(94, 234, 212, 0.12);
}
.chip.ready { border-color: rgba(94, 234, 212, 0.3); color: #5eead4; }
.chip.error { border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }

/* 语音交互区 */
.voice-input-area {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 120px; padding: 24px; border-radius: 24px; position: relative; overflow: hidden;
  background: rgba(30, 36, 51, 0.6); border: 1px solid rgba(94, 234, 212, 0.12);
  transition: border-color 0.3s;
}
.voice-input-area.listening { border-color: rgba(94, 234, 212, 0.4); }
.voice-input-area.processing { border-color: rgba(167, 139, 250, 0.4); }
.voice-input-area.error { border-color: rgba(239, 68, 68, 0.3); }

.voice-ripple-container { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
.voice-ripple { position: absolute; border-radius: 50%; border: 2px solid rgba(94, 234, 212, 0.3); opacity: 0; }
.voice-input-area.listening .r1 { animation: ripple 2s infinite; width: 60px; height: 60px; }
.voice-input-area.listening .r2 { animation: ripple 2s infinite 0.5s; width: 80px; height: 80px; }
.voice-input-area.listening .r3 { animation: ripple 2s infinite 1s; width: 100px; height: 100px; }
@keyframes ripple {
  0% { transform: scale(0.5); opacity: 0.6; }
  100% { transform: scale(2); opacity: 0; }
}

.voice-placeholder { position: relative; z-index: 1; color: #94a3b8; font-size: 15px; display: flex; align-items: center; gap: 8px; }
.voice-dot { width: 8px; height: 8px; border-radius: 50%; background: #5eead4; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }
.voice-spinner { width: 16px; height: 16px; border: 2px solid rgba(167,139,250,0.3); border-top-color: #a78bfa; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }
.interim-text { position: relative; z-index: 1; color: #e2e8f0; font-size: 18px; margin-top: 12px; text-align: center; }

.voice-actions { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 12px; }
.voice-toggle-btn {
  width: 48px; height: 48px; border-radius: 50%; border: none;
  background: rgba(239, 68, 68, 0.15); color: #ef4444;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.voice-hint { font-size: 13px; color: #6d6f78; }

textarea {
  flex: 1; border: none; background: transparent; resize: none; padding: 10px 0;
  font-family: inherit; font-size: 15px; outline: none; max-height: 120px;
  color: #e2e8f0; line-height: 1.5;
}
textarea::placeholder { color: #94a3b8; opacity: 0.7; }
.input-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.send-btn {
  width: 44px; height: 44px; border-radius: 20px; border: none;
  background: linear-gradient(135deg, #5eead4, #a78bfa); color: #0f141f;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(94, 234, 212, 0.2);
}
.send-btn:hover:not(:disabled) { transform: scale(1.04); box-shadow: 0 6px 16px rgba(94, 234, 212, 0.35); }
.send-btn:disabled { opacity: 0.4; cursor: default; }

.voice-btn {
  width: 36px; height: 36px; border-radius: 50%; border: none;
  background: rgba(94, 234, 212, 0.08); color: #94a3b8;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.voice-btn:hover { background: rgba(94, 234, 212, 0.15); color: #5eead4; }
.voice-btn.active { background: rgba(94, 234, 212, 0.2); color: #5eead4; }
.stop-btn {
  width: 36px; height: 36px; border-radius: 50%; border: none;
  background: rgba(239, 68, 68, 0.15); color: #ef4444;
  display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 12px;
}
</style>
