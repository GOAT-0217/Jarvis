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
    this._recognition.maxAlternatives = this._maxAlternatives;

    this._onStart = onStart || (() => {});
    this._onInterim = onInterim || (() => {});
    this._onResult = onResult || (() => {});
    this._onEnd = onEnd || (() => {});

    this._isActive = false;
    this._finalText = '';
    this._silenceTimer = null;
    this._SILENCE_TIMEOUT = 3000; // 3秒无声自动结束
    this._stopRequested = false;  // 标记 stop() 是否被调用，避免 stop() 中同步检查结果

    this._bindEvents();
  }

  get isActive() {
    return this._isActive;
  }

  _bindEvents() {
    this._recognition.onstart = () => {
      this._isActive = true;
      this._finalText = '';
      this._stopRequested = false;
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
      this._stopRequested = false;
      this._onEnd(event.error);
    };

    this._recognition.onend = () => {
      this._clearSilenceTimer();
      const wasActive = this._isActive;
      this._isActive = false;

      if (this._stopRequested) {
        // stop() 被调用 → 在这里检查最终结果（此时 onresult 已异步返回）
        this._stopRequested = false;
        const text = this._finalText.trim();
        if (text) {
          this._onResult(text);
          this._onEnd(null);
        } else {
          this._onEnd('no-speech');
        }
      } else if (wasActive) {
        // 浏览器意外结束（切标签页等）
        this._onEnd('unexpected');
      }
    };
  }

  _resetSilenceTimer() {
    this._clearSilenceTimer();
    this._silenceTimer = setTimeout(() => {
      this.stop();
    }, this._SILENCE_TIMEOUT);
  }

  _clearSilenceTimer() {
    if (this._silenceTimer) {
      clearTimeout(this._silenceTimer);
      this._silenceTimer = null;
    }
  }

  /** 开始语音识别。需在用户手势（pointerdown）中调用。 */
  start() {
    if (this._isActive) return;
    try {
      this._recognition.start();
    } catch (e) {
      if (e.name === 'InvalidStateError') {
        // 已经在识别中，无操作
      } else {
        throw e;
      }
    }
  }

  /** 停止识别。结果通过 onResult/onEnd 回调异步返回（在 onend 事件中处理）。 */
  stop() {
    this._clearSilenceTimer();
    if (!this._isActive) return;

    // 标记由我们主动停止，结果在 onend 中处理
    this._stopRequested = true;
    try {
      this._recognition.stop();
    } catch (e) {
      this._stopRequested = false;
      if (e.name !== 'InvalidStateError') throw e;
    }
  }

  /** 取消识别，不产生结果。 */
  abort() {
    this._clearSilenceTimer();
    this._finalText = '';
    this._stopRequested = false;

    try {
      this._recognition.abort();
    } catch (e) {
      if (e.name !== 'InvalidStateError') throw e;
    }

    this._isActive = false;
    this._onEnd('aborted');
  }
}
