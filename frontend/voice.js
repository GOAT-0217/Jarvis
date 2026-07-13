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
