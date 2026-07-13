# 语音输入功能 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Jarvis 助手前端新增语音输入能力（Web Speech API）+ 附件上传功能，后端零修改。

**Architecture:** 纯前端改动。新增 `voice.js` 封装浏览器 SpeechRecognition API，与 Vue 通过回调通信。`script.js` 新增双模式切换（文字/语音）VTJ状态管理。输入区布局由 textarea+attach 改为 textarea+🎤+＋（文字模式）或 voice-area+⌨+＋（语音模式）。附件上传复用现有 XMLHttpRequest 上传流程。

**Tech Stack:** Vue 3 CDN, Web Speech API (SpeechRecognition), AudioContext (提示音), XMLHttpRequest (附件上传进度)

## Global Constraints

- 后端零修改，所有改动限于 `frontend/` 目录
- 语音识别语言：`zh-CN`
- 浏览器兼容：仅 Chrome/Edge 显示语音按钮，其他浏览器隐藏
- 附件上传仅管理员可见和使用
- 语音模式下松手自动发送，不经过输入框确认
- 按住说话交互方式（pointerdown/pointerup）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/voice.js` | 新增 | Web Speech API 封装，独立于 Vue |
| `frontend/style.css` | 修改 | 麦克风/键盘/加号按钮样式，语音区域样式，动画 |
| `frontend/index.html` | 修改 | 新输入区结构，引入 voice.js |
| `frontend/script.js` | 修改 | Vue 集成：状态管理、模式切换、语音回调、附件上传 |

---

### Task 1: 创建 voice.js — Web Speech API 封装

**Files:**
- Create: `frontend/voice.js`

**Interfaces:**
- Produces: `VoiceInput` class — constructor takes `{ onStart, onInterim, onResult, onEnd }` callbacks
  - `VoiceInput.isSupported` — static boolean
  - `instance.start()` — begin speech recognition
  - `instance.stop()` — stop and finalize result
  - `instance.abort()` — cancel without result
  - `instance.isActive` — read-only boolean

- [ ] **Step 1: 创建 voice.js 完整实现**

```js
/**
 * VoiceInput — Web Speech API 封装
 *
 * 使用浏览器内置 SpeechRecognition，将语音转为文字。
 * 与 Vue 无关，通过回调通信，可独立测试。
 *
 * 回调：
 *   onStart()         — 麦克风已激活，开始收音
 *   onInterim(text)   — 实时中间结果（说话过程中持续更新）
 *   onResult(text)    — 最终识别结果（松手或自动结束后）
 *   onEnd()           — 识别结束（无论成功/失败/取消）
 *
 * 用法：
 *   const voice = new VoiceInput({ onStart, onInterim, onResult, onEnd })
 *   voice.start()   // 按住时调用
 *   voice.stop()    // 松手时调用
 *   voice.abort()   // 取消时调用
 */

class VoiceInput {
  static get isSupported() {
    return !!(
      (window.SpeechRecognition || window.webkitSpeechRecognition)
    );
  }

  constructor({ onStart, onInterim, onResult, onEnd } = {}) {
    if (!VoiceInput.isSupported) {
      throw new Error('SpeechRecognition not supported');
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this._recognition = new SpeechRecognition();
    this._recognition.lang = 'zh-CN';
    this._recognition.interimResults = true;
    this._recognition.continuous = true;
    this._maxAlternatives = 1;

    this._onStart = onStart || (() => {});
    this._onInterim = onInterim || (() => {});
    this._onResult = onResult || (() => {});
    this._onEnd = onEnd || (() => {});

    this._isActive = false;
    this._finalText = '';
    this._silenceTimer = null;
    this._SILENCE_TIMEOUT = 3000; // 3秒无声自动结束

    this._bindEvents();
  }

  get isActive() {
    return this._isActive;
  }

  _bindEvents() {
    this._recognition.onstart = () => {
      this._isActive = true;
      this._finalText = '';
      this._onStart();
      this._resetSilenceTimer();
    };

    this._recognition.onresult = (event) => {
      this._resetSilenceTimer();

      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        this._finalText += final;
      }

      const displayText = this._finalText + interim;
      this._onInterim(displayText);
    };

    this._recognition.onerror = (event) => {
      this._clearSilenceTimer();
      this._isActive = false;
      // error 也触发 onEnd，由上层区分
      this._onEnd(event.error);
    };

    this._recognition.onend = () => {
      this._clearSilenceTimer();
      this._isActive = false;
      // 正常结束且有识别内容 → 返回结果
      // （由 stop() 处理，onend 本身不触发 onResult）
    };
  }

  _resetSilenceTimer() {
    this._clearSilenceTimer();
    this._silenceTimer = setTimeout(() => {
      // 静默超时，自动停止
      this.stop();
    }, this._SILENCE_TIMEOUT);
  }

  _clearSilenceTimer() {
    if (this._silenceTimer) {
      clearTimeout(this._silenceTimer);
      this._silenceTimer = null;
    }
  }

  /** 开始语音识别。需在用户手势（pointerdown）中调用以满足浏览器自动播放策略。 */
  start() {
    if (this._isActive) return;
    try {
      this._recognition.start();
    } catch (e) {
      // 如果已经在运行，忽略
      if (e.name === 'InvalidStateError') {
        // 已经在识别中，无操作
      } else {
        throw e;
      }
    }
  }

  /** 停止识别并获取最终结果。如果识别到文字则回调 onResult，否则回调 onEnd(null)。 */
  stop() {
    this._clearSilenceTimer();
    if (!this._isActive) return;

    try {
      this._recognition.stop();
    } catch (e) {
      // 忽略 InvalidStateError
    }

    this._isActive = false;

    // 处理结果
    const text = this._finalText.trim();
    if (text) {
      this._onResult(text);
      this._onEnd(null); // null = success
    } else {
      this._onEnd('no-speech');
    }
  }

  /** 取消识别，不产生结果。 */
  abort() {
    this._clearSilenceTimer();
    this._finalText = '';
    if (!this._isActive) return;

    try {
      this._recognition.abort();
    } catch (e) {
      // 忽略
    }

    this._isActive = false;
    this._onEnd('aborted');
  }
}
```

- [ ] **Step 2: 验证文件语法正确**

Run: `node --check frontend/voice.js`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add frontend/voice.js
git commit -m "feat: add VoiceInput module wrapping Web Speech API"
```

---

### Task 2: 添加语音和附件相关 CSS 样式

**Files:**
- Modify: `frontend/style.css` — 在文件末尾追加

**Interfaces:**
- Consumes: 无（纯样式，等待 HTML/JS 使用这些类名）

- [ ] **Step 1: 追加样式到 style.css**

在 `frontend/style.css` 末尾追加以下内容：

```css
/* ============================================ */
/* Voice Input & Attachment Styles              */
/* ============================================ */

/* ---- 输入区按钮组 ---- */
.input-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}

.mic-btn,
.keyboard-btn,
.plus-btn {
    background: none;
    border: 1px solid rgba(94, 234, 212, 0.2);
    color: var(--text-light);
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: var(--transition);
    font-size: 1rem;
    flex-shrink: 0;
}

.mic-btn:hover,
.keyboard-btn:hover,
.plus-btn:hover {
    border-color: var(--primary-color);
    color: var(--primary-color);
    background-color: rgba(94, 234, 212, 0.08);
}

.mic-btn:disabled,
.keyboard-btn:disabled,
.plus-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    pointer-events: none;
}

/* ---- 语音输入区域（文字模式隐藏） ---- */
.voice-input-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    border-radius: 18px;
    cursor: pointer;
    user-select: none;
    transition: background-color 0.25s ease, border-color 0.25s ease;
    border: 2px dashed transparent;
    position: relative;
    overflow: hidden;
}

/* 空闲态 */
.voice-input-area.idle {
    background: rgba(94, 234, 212, 0.04);
    border-color: rgba(94, 234, 212, 0.15);
    color: var(--text-light);
}

.voice-input-area.idle:hover {
    background: rgba(94, 234, 212, 0.08);
    border-color: rgba(94, 234, 212, 0.3);
}

.voice-input-area .voice-placeholder {
    font-size: 0.95rem;
    color: var(--text-light);
    opacity: 0.8;
    pointer-events: none;
}

/* 聆听中 */
.voice-input-area.listening {
    background: rgba(248, 113, 113, 0.12);
    border-color: rgba(248, 113, 113, 0.5);
}

.voice-input-area.listening .voice-placeholder {
    color: #fca5a5;
}

/* 波纹动画容器 */
.voice-ripple-container {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
}

.voice-ripple-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin-left: -10px;
    margin-top: -10px;
    border-radius: 50%;
    border: 2px solid rgba(248, 113, 113, 0.6);
    animation: voiceRipple 1.5s ease-out infinite;
    opacity: 0;
}

.voice-ripple-ring:nth-child(2) {
    animation-delay: 0.5s;
}

.voice-ripple-ring:nth-child(3) {
    animation-delay: 1.0s;
}

@keyframes voiceRipple {
    0% {
        width: 20px;
        height: 20px;
        margin-left: -10px;
        margin-top: -10px;
        opacity: 0.7;
    }
    100% {
        width: 80px;
        height: 80px;
        margin-left: -40px;
        margin-top: -40px;
        opacity: 0;
    }
}

/* 识别中 */
.voice-input-area.processing {
    background: rgba(167, 139, 250, 0.08);
    border-color: rgba(167, 139, 250, 0.4);
}

.voice-input-area.processing .voice-placeholder {
    color: #a78bfa;
}

/* 旋转加载（识别中） */
.voice-spinner {
    display: none;
    width: 18px;
    height: 18px;
    border: 2px solid rgba(167, 139, 250, 0.3);
    border-top-color: #a78bfa;
    border-radius: 50%;
    animation: voiceSpin 0.8s linear infinite;
    margin-right: 10px;
}

.voice-input-area.processing .voice-spinner {
    display: inline-block;
}

.voice-input-area.processing .voice-placeholder {
    display: inline;
}

@keyframes voiceSpin {
    to { transform: rotate(360deg); }
}

/* 错误态 */
.voice-input-area.error {
    background: rgba(251, 191, 36, 0.08);
    border-color: rgba(251, 191, 36, 0.5);
    animation: errorFlash 0.4s ease 3;
}

.voice-input-area.error .voice-placeholder {
    color: #fbbf24;
}

@keyframes errorFlash {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ---- 实时识别文字浮层 ---- */
.voice-interim-text {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(30, 36, 51, 0.95);
    border: 1px solid rgba(94, 234, 212, 0.2);
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 0.9rem;
    color: var(--text-color);
    white-space: nowrap;
    max-width: 90vw;
    overflow: hidden;
    text-overflow: ellipsis;
    pointer-events: none;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    animation: interimFadeIn 0.2s ease;
}

@keyframes interimFadeIn {
    from { opacity: 0; transform: translateX(-50%) translateY(4px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* ---- 语音模式时隐藏 textarea ---- */
.input-area.voice-active textarea {
    display: none;
}

.input-area.voice-active .voice-input-area {
    display: flex;
}

/* ---- 默认隐藏语音区域 ---- */
.voice-input-area {
    display: none;
}

.input-area.voice-active .voice-input-area {
    display: flex;
}

/* ---- 附件上传弹窗 ---- */
.attach-dropdown {
    position: absolute;
    bottom: calc(100% + 10px);
    right: 0;
    background: rgba(26, 31, 46, 0.98);
    border: 1px solid rgba(94, 234, 212, 0.2);
    border-radius: 14px;
    padding: 8px;
    min-width: 180px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    z-index: 30;
    animation: attachSlideUp 0.2s ease;
}

@keyframes attachSlideUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

.attach-dropdown button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 14px;
    border: none;
    background: transparent;
    color: var(--text-color);
    font-size: 0.9rem;
    border-radius: 10px;
    cursor: pointer;
    transition: var(--transition);
}

.attach-dropdown button:hover {
    background: rgba(94, 234, 212, 0.08);
    color: var(--primary-color);
}

.attach-dropdown button i {
    width: 18px;
    text-align: center;
    color: var(--primary-color);
}

/* ---- 隐藏的文件输入 ---- */
.attach-file-input {
    display: none;
}
```

- [ ] **Step 2: 验证 CSS 无语法错误**

Run: `npx stylelint frontend/style.css --max-warnings 0 2>&1 || echo "stylelint not available, skipping"`
Expected: 无报错（或跳过）

- [ ] **Step 3: 提交**

```bash
git add frontend/style.css
git commit -m "style: add voice input and attachment button styles"
```

---

### Task 3: 更新 index.html — 新输入区和按钮结构

**Files:**
- Modify: `frontend/index.html` — 替换输入区域，添加 voice.js 引用

**Interfaces:**
- Consumes: `voice.js` (Task 1 产出), CSS 类名 (Task 2 产出)
- Produces: DOM 结构供 Task 4 绑定 Vue 指令

- [ ] **Step 1: 替换输入区 HTML**

定位到 `frontend/index.html` 第 368-389 行（`<div class="input-area-wrapper">` 区块），将整个区块替换为：

```html
            <div class="input-area-wrapper">
                <div class="input-area" :class="{ 'voice-active': voiceMode }">
                    <!-- 文字输入模式 -->
                    <textarea
                        v-show="!voiceMode"
                        v-model="userInput"
                        @keydown="handleKeyDown"
                        @compositionstart="handleCompositionStart"
                        @compositionend="handleCompositionEnd"
                        @input="autoResize"
                        placeholder="和Javis说点什么吧... (Shift+Enter 换行)"
                        rows="1"
                        ref="textarea"
                    ></textarea>

                    <!-- 语音输入区域（语音模式显示） -->
                    <div
                        v-show="voiceMode"
                        class="voice-input-area"
                        :class="voiceState"
                        @pointerdown.prevent="handleVoicePointerDown"
                        @pointerup.prevent="handleVoicePointerUp"
                        @pointerleave.prevent="handleVoicePointerLeave"
                        ref="voiceArea"
                    >
                        <template v-if="voiceState === 'idle'">
                            <span class="voice-placeholder">按住说话...</span>
                        </template>
                        <template v-else-if="voiceState === 'listening'">
                            <div class="voice-ripple-container">
                                <div class="voice-ripple-ring"></div>
                                <div class="voice-ripple-ring"></div>
                                <div class="voice-ripple-ring"></div>
                            </div>
                            <span class="voice-placeholder">正在聆听...</span>
                        </template>
                        <template v-else-if="voiceState === 'processing'">
                            <span class="voice-spinner"></span>
                            <span class="voice-placeholder">识别中...</span>
                        </template>
                        <template v-else-if="voiceState === 'error'">
                            <span class="voice-placeholder">{{ voiceErrorMsg }}</span>
                        </template>
                    </div>

                    <!-- 实时识别文字浮层 -->
                    <div v-if="voiceMode && interimText" class="voice-interim-text">
                        {{ interimText }}
                    </div>

                    <!-- 按钮组 -->
                    <div class="input-buttons">
                        <!-- 语音模式：显示键盘按钮 -->
                        <button
                            v-if="voiceMode"
                            class="keyboard-btn"
                            @click="toggleVoiceMode"
                            title="切换文字输入"
                        >
                            <i class="fas fa-keyboard"></i>
                        </button>
                        <!-- 文字模式：显示麦克风按钮 -->
                        <button
                            v-else-if="voiceSupported"
                            class="mic-btn"
                            @click="toggleVoiceMode"
                            :disabled="isLoading || !isAuthenticated"
                            title="切换语音输入"
                        >
                            <i class="fas fa-microphone"></i>
                        </button>
                        <!-- 加号按钮（仅管理员） -->
                        <button
                            v-if="isAdmin"
                            class="plus-btn"
                            @click="handleAttachClick"
                            title="上传附件"
                        >
                            <i class="fas fa-plus"></i>
                        </button>
                        <!-- 附件上传隐藏 input -->
                        <input
                            v-if="isAdmin"
                            type="file"
                            ref="attachFileInput"
                            class="attach-file-input"
                            accept=".pdf,.doc,.docx,.xls,.xlsx"
                            @change="handleAttachFileSelect"
                        />
                        <!-- 附件上传弹窗 -->
                        <div v-if="isAdmin && showAttachMenu" class="attach-dropdown" @click.stop>
                            <button @click="handleAttachFileClick">
                                <i class="fas fa-file-alt"></i> 上传文档
                            </button>
                            <button @click="handleAttachImageClick">
                                <i class="fas fa-image"></i> 上传图片
                            </button>
                        </div>
                    </div>

                    <!-- 发送/终止按钮 -->
                    <button v-if="isLoading" @click="handleStop" class="send-btn stop-btn" title="终止回答">
                        <i class="fas fa-stop"></i>
                    </button>
                    <button v-else @click="handleSend" class="send-btn" title="发送">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div class="footer-text">AI 生成的内容可能包含错误，请仔细甄别。</div>
            </div>
```

- [ ] **Step 2: 添加 voice.js 脚本引用**

在 `frontend/index.html` 第 395 行（`<script src="script.js"></script>` 之前）插入：

```html
    <script src="voice.js"></script>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/index.html
git commit -m "feat: add voice input area and attachment button to chat UI"
```

---

### Task 4: 修改 script.js — 语音模式状态管理

**Files:**
- Modify: `frontend/script.js` — 在 Vue data 中添加语音相关属性，在 methods 中添加切换和处理方法

**Interfaces:**
- Consumes: `VoiceInput` 类 (Task 1), DOM 结构 (Task 3)
- Produces: `voiceMode`, `voiceState`, `voiceSupported`, `interimText`, `voiceErrorMsg` 等响应式属性；`toggleVoiceMode()`, `handleVoicePointerDown()`, `handleVoicePointerUp()`, `handleVoicePointerLeave()` 方法

- [ ] **Step 1: 在 data() 中添加语音相关属性**

在 `frontend/script.js` 第 30 行（`uploadPercent: 0` 之后）添加：

```js
                // Voice input
                voiceMode: false,
                voiceState: 'idle',       // idle | listening | processing | error
                voiceSupported: false,
                interimText: '',
                voiceErrorMsg: '',
                voiceInput: null,
                voiceErrorTimer: null,
```

- [ ] **Step 2: 在 computed 中无改动，但确认 isAdmin 已存在**

`isAdmin` 已在第 37-39 行定义，无需修改。

- [ ] **Step 3: 在 mounted() 中添加语音支持检测**

在 `frontend/script.js` 第 43 行（`this.configureMarked();` 之后）添加：

```js
            this.voiceSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
```

- [ ] **Step 4: 在 methods 中添加模式切换和语音处理方法**

在 `frontend/script.js` 的 methods 对象中，`getFileIcon` 方法之后（第 545 行之前），添加以下方法：

```js
        // ========== Voice Input Methods ==========

        /** 切换文字/语音输入模式 */
        toggleVoiceMode() {
            if (this.isLoading) return;
            if (!this.isAuthenticated) return;

            if (this.voiceMode) {
                // 从语音切回文字
                this.voiceMode = false;
                this.voiceState = 'idle';
                this.interimText = '';
                this.clearVoiceErrorTimer();
            } else {
                // 从文字切到语音
                this.voiceMode = true;
                this.voiceState = 'idle';
                this.interimText = '';
                this.$nextTick(() => {
                    // 聚焦语音区域（可选，辅助无障碍）
                });
            }
        },

        /** 按住开始录音 */
        handleVoicePointerDown(e) {
            if (this.isLoading || !this.voiceMode || this.voiceState === 'processing') return;

            // 创建 VoiceInput 实例（每次按下新建，用完即弃）
            if (this.voiceInput) {
                this.voiceInput.abort();
                this.voiceInput = null;
            }

            this.voiceState = 'listening';
            this.interimText = '';
            this.voiceErrorMsg = '';
            this.clearVoiceErrorTimer();

            try {
                this.voiceInput = new VoiceInput({
                    onStart: () => {
                        this.voiceState = 'listening';
                        this.playBeep('start');
                    },
                    onInterim: (text) => {
                        this.interimText = text;
                    },
                    onResult: (text) => {
                        // 识别成功 → 自动发送
                        this.voiceState = 'processing';
                        this.playBeep('success');
                        this.voiceInput = null;

                        // 直接发送（复用现有 handleSend 逻辑的核心部分）
                        this.sendVoiceMessage(text);
                    },
                    onEnd: (error) => {
                        this.voiceInput = null;

                        if (error === 'no-speech') {
                            // 没有识别到语音
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '未识别到语音，请重试';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset();
                        } else if (error === 'not-allowed') {
                            // 权限被拒
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '无麦克风权限';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset();
                        } else if (error === 'network') {
                            // 网络不可用
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '网络不可用';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset();
                        } else if (error === 'aborted') {
                            // 用户取消
                            this.voiceState = 'idle';
                            this.interimText = '';
                        } else if (error) {
                            // 其他错误
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '识别失败，请重试';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset();
                        } else {
                            // null = 成功（由 onResult 已处理，这里是 stop 后的正常 onEnd）
                            if (this.voiceState !== 'processing') {
                                this.voiceState = 'idle';
                            }
                        }
                    }
                });

                this.voiceInput.start();
            } catch (e) {
                this.voiceState = 'error';
                this.voiceErrorMsg = '语音功能不可用';
                this.scheduleVoiceErrorReset();
            }
        },

        /** 松手停止录音 */
        handleVoicePointerUp() {
            if (this.voiceInput && this.voiceInput.isActive) {
                this.voiceState = 'processing';
                this.voiceInput.stop();
            }
        },

        /** 手指滑出区域 */
        handleVoicePointerLeave() {
            // 滑出不中断，用户可以滑回来继续。真正取消由 pointerup 处理。
        },

        /** 发送语音消息（绕过输入框，直接发送） */
        sendVoiceMessage(text) {
            if (!text || !text.trim()) {
                this.voiceState = 'idle';
                return;
            }

            const trimmedText = text.trim();

            // 添加用户消息
            this.messages.push({
                text: trimmedText,
                isUser: true
            });

            this.$nextTick(() => {
                this.scrollToBottom();
            });

            this.isLoading = true;
            this.messages.push({
                text: '',
                isUser: false,
                isThinking: true,
                ragTrace: null,
                ragSteps: []
            });
            const botMsgIdx = this.messages.length - 1;

            this.abortController = new AbortController();

            // 发起流式请求（与 handleSend 核心逻辑一致）
            this.authFetch('/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: trimmedText,
                    session_id: this.sessionId
                }),
                signal: this.abortController.signal,
            }).then(async (response) => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    let eventEndIndex;

                    while ((eventEndIndex = buffer.indexOf('\n\n')) !== -1) {
                        const eventStr = buffer.slice(0, eventEndIndex);
                        buffer = buffer.slice(eventEndIndex + 2);

                        if (eventStr.startsWith('data: ')) {
                            const dataStr = eventStr.slice(6);
                            if (dataStr === '[DONE]') continue;
                            try {
                                const data = JSON.parse(dataStr);
                                if (data.type === 'content') {
                                    if (this.messages[botMsgIdx].isThinking) {
                                        this.messages[botMsgIdx].isThinking = false;
                                    }
                                    this.messages[botMsgIdx].text += data.content;
                                } else if (data.type === 'trace') {
                                    this.messages[botMsgIdx].ragTrace = data.rag_trace;
                                } else if (data.type === 'rag_step') {
                                    if (!this.messages[botMsgIdx].ragSteps) {
                                        this.messages[botMsgIdx].ragSteps = [];
                                    }
                                    this.messages[botMsgIdx].ragSteps.push(data.step);
                                } else if (data.type === 'error') {
                                    this.messages[botMsgIdx].isThinking = false;
                                    this.messages[botMsgIdx].text += `\n[Error: ${data.content}]`;
                                }
                            } catch (e) {
                                console.warn('SSE parse error:', e);
                            }
                        }
                    }
                    this.$nextTick(() => this.scrollToBottom());
                }
            }).catch((error) => {
                if (error.name === 'AbortError') {
                    this.messages[botMsgIdx].isThinking = false;
                    if (!this.messages[botMsgIdx].text) {
                        this.messages[botMsgIdx].text = '(已终止回答)';
                    } else {
                        this.messages[botMsgIdx].text += '\n\n_(回答已被终止)_';
                    }
                } else {
                    this.messages[botMsgIdx].isThinking = false;
                    this.messages[botMsgIdx].text = `抱歉主人... 出了点问题：${error.message}`;
                }
            }).finally(() => {
                this.isLoading = false;
                this.abortController = null;
                this.voiceState = 'idle';
                this.interimText = '';
                this.$nextTick(() => this.scrollToBottom());
            });
        },

        /** 错误状态定时恢复 */
        scheduleVoiceErrorReset() {
            this.clearVoiceErrorTimer();
            this.voiceErrorTimer = setTimeout(() => {
                this.voiceState = 'idle';
                this.voiceErrorMsg = '';
                this.interimText = '';
            }, 2500);
        },

        /** 清除错误计时器 */
        clearVoiceErrorTimer() {
            if (this.voiceErrorTimer) {
                clearTimeout(this.voiceErrorTimer);
                this.voiceErrorTimer = null;
            }
        },

        /** 提示音（AudioContext 动态生成） */
        playBeep(type) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);

                gain.gain.value = 0.08; // 低音量

                if (type === 'start') {
                    // 1kHz 短升调
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(800, ctx.currentTime);
                    osc.frequency.linearRampToValueAtTime(1200, ctx.currentTime + 0.15);
                    gain.gain.setValueAtTime(0.08, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.2);
                } else if (type === 'success') {
                    // 800→1200Hz 双音节
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(800, ctx.currentTime);
                    osc.frequency.setValueAtTime(1200, ctx.currentTime + 0.1);
                    gain.gain.setValueAtTime(0.08, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.25);
                } else if (type === 'error') {
                    // 300Hz 低音短鸣
                    osc.type = 'triangle';
                    osc.frequency.value = 300;
                    gain.gain.setValueAtTime(0.1, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.3);
                }

                // 清理
                setTimeout(() => {
                    if (ctx.state !== 'closed') ctx.close();
                }, 500);
            } catch (e) {
                // 提示音失败不影响核心功能
            }
        },
```

- [ ] **Step 5: 提交**

```bash
git add frontend/script.js
git commit -m "feat: add voice mode toggle and speech recognition integration"
```

---

### Task 5: 添加附件上传功能

**Files:**
- Modify: `frontend/script.js` — 在 methods 中添加附件上传相关方法

**Interfaces:**
- Consumes: Task 4 的 `showAttachMenu`, `attachFileInput` ref
- Produces: 附件上传功能，复用现有 `uploadDocument` 的 XMLHttpRequest 逻辑

- [ ] **Step 1: 在 data() 中添加附件相关属性**

在 `frontend/script.js` 的 data 中，`voiceErrorTimer: null` 之后添加：

```js
                // Attachment upload
                showAttachMenu: false,
                attachUploading: false,
                attachProgress: '',
                attachPercent: 0,
```

- [ ] **Step 2: 在 methods 中添加附件上传方法**

在 `frontend/script.js` 的 methods 中，`playBeep` 方法之后添加：

```js
        // ========== Attachment Upload Methods ==========

        /** 点击加号 — 切换附件菜单 */
        handleAttachClick() {
            if (this.isLoading) return;
            this.showAttachMenu = !this.showAttachMenu;
        },

        /** 点击上传文档 — 打开文件选择器 */
        handleAttachFileClick() {
            this.showAttachMenu = false;
            if (this.$refs.attachFileInput) {
                this.$refs.attachFileInput.accept = '.pdf,.doc,.docx,.xls,.xlsx';
                this.$refs.attachFileInput.click();
            }
        },

        /** 点击上传图片 — 暂不支持，提示用户 */
        handleAttachImageClick() {
            this.showAttachMenu = false;
            alert('图片上传功能正在开发中，当前仅支持 PDF、Word、Excel 文档。');
        },

        /** 文件选择后的上传处理 */
        handleAttachFileSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            const file = files[0];
            this.attachUploading = true;
            this.attachProgress = '准备上传...';
            this.attachPercent = 0;

            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    this.attachPercent = pct;
                    this.attachProgress = `上传中 ${this.formatFileSize(e.loaded)} / ${this.formatFileSize(e.total)}`;
                }
            });

            xhr.addEventListener('load', () => {
                this.attachUploading = false;
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        alert(data.message || '上传成功');

                        // 如果当前在设置页面，刷新文档列表
                        if (this.activeNav === 'settings') {
                            this.loadDocuments();
                        }

                        setTimeout(() => {
                            this.attachProgress = '';
                            this.attachPercent = 0;
                        }, 3000);
                    } catch (e) {
                        this.attachProgress = '解析响应失败';
                    }
                } else {
                    try {
                        const err = JSON.parse(xhr.responseText);
                        alert(`上传失败：${err.detail || xhr.statusText}`);
                    } catch {
                        alert(`上传失败：HTTP ${xhr.status}`);
                    }
                    this.attachProgress = '';
                }
            });

            xhr.addEventListener('error', () => {
                this.attachUploading = false;
                alert('上传失败：网络错误');
                this.attachProgress = '';
            });

            xhr.addEventListener('abort', () => {
                this.attachUploading = false;
                this.attachProgress = '';
            });

            xhr.open('POST', '/documents/upload');
            xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
            xhr.send(formData);

            // 清空 input，允许重复上传同一文件
            event.target.value = '';
        },

        /** 关闭附件菜单（点击其他地方时） */
        handleClickOutside() {
            if (this.showAttachMenu) {
                this.showAttachMenu = false;
            }
        },
```

- [ ] **Step 3: 在 watch 或 mounted 中添加全局点击关闭附件菜单**

在 `frontend/script.js` 的 `mounted()` 方法末尾添加：

```js
            // 全局点击关闭附件菜单
            document.addEventListener('click', this.handleClickOutside);
```

- [ ] **Step 4: 提交**

```bash
git add frontend/script.js
git commit -m "feat: add attachment upload from chat input area"
```

---

### Task 6: 添加附件上传进度提示样式

**Files:**
- Modify: `frontend/style.css` — 追加上传进度条样式

- [ ] **Step 1: 追加附件上传进度样式**

在 `frontend/style.css` 末尾追加：

```css
/* ---- 附件上传进度提示 ---- */
.attach-progress-bar {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(30, 36, 51, 0.98);
    border: 1px solid rgba(94, 234, 212, 0.2);
    border-radius: 12px;
    padding: 10px 16px;
    min-width: 220px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    z-index: 30;
    animation: attachSlideUp 0.2s ease;
}

.attach-progress-bar .progress-text-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: var(--text-light);
    margin-bottom: 6px;
}

.attach-progress-bar .progress-text-row span:last-child {
    color: var(--primary-color);
    font-weight: 600;
}

.attach-progress-bar .progress-bar-wrapper {
    width: 100%;
    height: 6px;
    background: rgba(15, 20, 31, 0.8);
    border-radius: 6px;
    overflow: hidden;
}

.attach-progress-bar .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #5eead4, #a78bfa);
    border-radius: 6px;
    transition: width 0.3s ease;
    box-shadow: 0 0 8px rgba(94, 234, 212, 0.4);
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/style.css
git commit -m "style: add attachment upload progress bar styles"
```

---

### Task 7: 端到端集成测试

**Files:**
- 无需修改代码文件

- [ ] **Step 1: 启动开发服务器**

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 &
```
确认服务启动后，浏览器打开 `http://127.0.0.1:8000/`。

- [ ] **Step 2: 测试文字模式基础功能**

- 登录（admin 账户）
- 发送文字消息，确认流式回答正常
- 确认终止按钮正常工作
- 确认历史记录可查看

- [ ] **Step 3: 测试语音模式**

- 使用 Chrome/Edge 浏览器
- 点击 🎤 按钮 → 输入区切换为语音区域，textarea 隐藏，⌨ 按钮出现
- 按住语音区域 → 红色脉冲动画出现，提示 "正在聆听..."
- 说话 → 实时文字浮层显示识别内容
- 松手 → "识别中..." → 消息自动发送 → 流式回答正常展示
- 语音模式保持，可继续按住说话
- 点 ⌨ → 切回文字模式，textarea 恢复

- [ ] **Step 4: 测试语音错误处理**

- 拒绝麦克风权限 → "无麦克风权限" → 2.5s 后恢复
- 不说话按住 3 秒 → "未识别到语音" → beep 提示后恢复
- 回答进行中按语音按钮 → 无反应（disabled 状态）

- [ ] **Step 5: 测试附件上传**

- 作为 admin 登录
- 点 ＋ → 弹出附件菜单
- 点"上传文档" → 文件选择器打开
- 选择 PDF/Word/Excel → 上传进度显示
- 上传成功 → 弹出成功提示
- 非 admin 用户 → 不显示 ＋ 按钮

- [ ] **Step 6: 测试浏览器兼容**

- Firefox → 🎤 按钮不显示，textarea 照常工作
- Safari → 同上

- [ ] **Step 7: 最终提交**

```bash
git add -A
git commit -m "feat: complete voice input and attachment upload integration"
```
