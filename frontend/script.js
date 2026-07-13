const { createApp } = Vue;

createApp({
    data() {
        return {
            messages: [],
            userInput: '',
            isLoading: false,
            activeNav: 'newChat',
            abortController: null,
            sessionId: 'session_' + Date.now(),
            sessions: [],
            showHistorySidebar: false,
            isComposing: false,
            documents: [],
            documentsLoading: false,
            selectedFile: null,
            isUploading: false,
            uploadProgress: '',
            token: localStorage.getItem('accessToken') || '',
            currentUser: null,
            authMode: 'login',
            authForm: {
                username: '',
                password: '',
                role: 'user',
                admin_code: ''
            },
            authLoading: false,
            uploadPercent: 0,

            // Voice input
            voiceMode: false,
            voiceState: 'idle',       // idle | listening | processing | error
            voiceSupported: false,
            interimText: '',
            voiceErrorMsg: '',
            voiceInput: null,
            voiceErrorTimer: null,

            // Attachment upload — chip mode
            attachments: [],          // {id, type, content, filename, mime_type, status}
                                      // status: 'extracting' | 'ready' | 'error'
        };
    },
    computed: {
        isAuthenticated() {
            return !!this.token && !!this.currentUser;
        },
        isAdmin() {
            return this.currentUser?.role === 'admin';
        }
    },
    async mounted() {
        this.configureMarked();
        this.voiceSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
        if (this.token) {
            try {
                await this.fetchMe();
            } catch (_) {
                this.handleLogout();
            }
        }

    },
    methods: {
        configureMarked() {
            marked.setOptions({
                highlight: function(code, lang) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                },
                langPrefix: 'hljs language-',
                breaks: true,
                gfm: true
            });
        },

        parseMarkdown(text) {
            return marked.parse(text);
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        authHeaders(extra = {}) {
            const headers = { ...extra };
            if (this.token) {
                headers.Authorization = `Bearer ${this.token}`;
            }
            return headers;
        },

        async authFetch(url, options = {}) {
            const opts = { ...options };
            opts.headers = this.authHeaders(opts.headers || {});
            const response = await fetch(url, opts);
            if (response.status === 401) {
                this.handleLogout();
                throw new Error('登录已过期，请重新登录');
            }
            return response;
        },

        async fetchMe() {
            const response = await this.authFetch('/auth/me');
            if (!response.ok) {
                throw new Error('认证失败');
            }
            this.currentUser = await response.json();
        },

        async handleAuthSubmit() {
            if (this.authLoading) return;
            const username = this.authForm.username.trim();
            const password = this.authForm.password.trim();
            if (!username || !password) {
                alert('用户名和密码不能为空');
                return;
            }

            this.authLoading = true;
            try {
                const endpoint = this.authMode === 'login' ? '/auth/login' : '/auth/register';
                const payload = {
                    username,
                    password
                };
                if (this.authMode === 'register') {
                    payload.role = this.authForm.role;
                    payload.admin_code = this.authForm.admin_code || null;
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.detail || '认证失败');
                }

                this.token = data.access_token;
                this.currentUser = { username: data.username, role: data.role };
                localStorage.setItem('accessToken', this.token);
                this.authForm.password = '';
                this.authForm.admin_code = '';
                this.messages = [];
                this.sessionId = 'session_' + Date.now();
                this.activeNav = 'newChat';
            } catch (error) {
                alert(error.message);
            } finally {
                this.authLoading = false;
            }
        },

        handleLogout() {
            this.token = '';
            this.currentUser = null;
            this.messages = [];
            this.sessions = [];
            this.documents = [];
            this.attachments = [];
            this.activeNav = 'newChat';
            this.showHistorySidebar = false;
            localStorage.removeItem('accessToken');
        },

        handleCompositionStart() {
            this.isComposing = true;
        },

        handleCompositionEnd() {
            this.isComposing = false;
        },

        handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey && !this.isComposing) {
                event.preventDefault();
                this.handleSend();
            }
        },

        handleStop() {
            if (this.abortController) {
                this.abortController.abort();
            }
        },

        async handleSend() {
            if (!this.isAuthenticated) {
                alert('请先登录');
                return;
            }

            const text = this.userInput.trim();
            if (!text || this.isLoading || this.isComposing) return;

            this.userInput = '';
            this.$nextTick(() => {
                this.resetTextareaHeight();
            });

            this._sendChatMessage(text);
        },

        /** 发送聊天消息（SSE 流式请求），供 handleSend 和 sendVoiceMessage 复用 */
        async _sendChatMessage(text) {
            this.messages.push({
                text: text,
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

            try {
                // 收集状态为 ready 的附件
                const readyAttachments = this.attachments
                    .filter(a => a.status === 'ready')
                    .map(a => ({
                        type: a.type,
                        content: a.content,
                        filename: a.filename,
                        mime_type: a.mime_type || null,
                    }));

                const response = await this.authFetch('/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        session_id: this.sessionId,
                        attachments: readyAttachments.length > 0 ? readyAttachments : null,
                    }),
                    signal: this.abortController.signal,
                });

                // 发送后清空附件
                this.attachments = [];

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

            } catch (error) {
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
            } finally {
                this.isLoading = false;
                this.abortController = null;
                this.$nextTick(() => this.scrollToBottom());
            }
        },

        autoResize(event) {
            const textarea = event.target;
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        },

        resetTextareaHeight() {
            if (this.$refs.textarea) {
                this.$refs.textarea.style.height = 'auto';
            }
        },

        scrollToBottom() {
            if (this.$refs.chatContainer) {
                this.$refs.chatContainer.scrollTop = this.$refs.chatContainer.scrollHeight;
            }
        },

        handleNewChat() {
            if (!this.isAuthenticated) return;
            this.messages = [];
            this.attachments = [];
            this.sessionId = 'session_' + Date.now();
            this.activeNav = 'newChat';
            this.showHistorySidebar = false;
        },

        handleClearChat() {
            if (confirm('确定要清空当前对话吗？主人？')) {
                this.attachments = [];
                this.messages = [];
            }
        },

        async handleHistory() {
            if (!this.isAuthenticated) return;
            this.activeNav = 'history';
            this.showHistorySidebar = true;
            try {
                const response = await this.authFetch('/sessions');
                if (!response.ok) {
                    throw new Error('Failed to load sessions');
                }
                const data = await response.json();
                this.sessions = data.sessions;
            } catch (error) {
                alert('加载历史记录失败：' + error.message);
            }
        },

        async loadSession(sessionId) {
            this.sessionId = sessionId;
            this.showHistorySidebar = false;
            this.activeNav = 'newChat';

            try {
                const response = await this.authFetch(`/sessions/${encodeURIComponent(sessionId)}`);
                if (!response.ok) {
                    throw new Error('Failed to load session messages');
                }
                const data = await response.json();
                this.messages = data.messages.map(msg => ({
                    text: msg.content,
                    isUser: msg.type === 'human',
                    ragTrace: msg.rag_trace || null
                }));

                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            } catch (error) {
                alert('加载会话失败：' + error.message);
                this.messages = [];
            }
        },

        async deleteSession(sessionId) {
            if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) {
                return;
            }

            try {
                const response = await this.authFetch(`/sessions/${encodeURIComponent(sessionId)}`, {
                    method: 'DELETE'
                });

                const payload = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(payload.detail || 'Delete failed');
                }

                this.sessions = this.sessions.filter(s => s.session_id !== sessionId);

                if (this.sessionId === sessionId) {
                    this.messages = [];
                    this.sessionId = 'session_' + Date.now();
                    this.activeNav = 'newChat';
                }

                if (payload.message) {
                    alert(payload.message);
                }
            } catch (error) {
                alert('删除会话失败：' + error.message);
            }
        },

        handleSettings() {
            if (!this.isAdmin) {
                alert('仅管理员可访问文档管理');
                return;
            }
            this.activeNav = 'settings';
            this.showHistorySidebar = false;
            this.loadDocuments();
        },

        async loadDocuments() {
            this.documentsLoading = true;
            try {
                const response = await this.authFetch('/documents');
                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    throw new Error(data.detail || 'Failed to load documents');
                }
                const data = await response.json();
                this.documents = data.documents;
            } catch (error) {
                alert('加载文档列表失败：' + error.message);
            } finally {
                this.documentsLoading = false;
            }
        },

        handleFileSelect(event) {
            const files = event.target.files;
            if (files && files.length > 0) {
                this.selectedFile = files[0];
                this.uploadProgress = '';
            }
        },

        async uploadDocument() {
            if (!this.selectedFile) {
                alert('请先选择文件');
                return;
            }

            this.isUploading = true;
            this.uploadProgress = '准备上传...';
            this.uploadPercent = 0;

            const formData = new FormData();
            formData.append('file', this.selectedFile);

            // 使用 XMLHttpRequest 来监听上传进度
            const xhr = new XMLHttpRequest();

            // 监听上传进度
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    this.uploadPercent = percentComplete;
                    this.uploadProgress = `上传中 ${this.formatFileSize(e.loaded)} / ${this.formatFileSize(e.total)}`;
                }
            });

            // 完成后的处理
            xhr.addEventListener('load', async () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        this.uploadProgress = data.message;
                        this.uploadPercent = 100;

                        this.selectedFile = null;
                        if (this.$refs.fileInputRef) {
                            this.$refs.fileInputRef.value = '';
                        }

                        await this.loadDocuments();

                        setTimeout(() => {
                            this.uploadProgress = '';
                            this.uploadPercent = 0;
                        }, 3000);
                    } catch (error) {
                        this.uploadProgress = '解析响应失败';
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        this.uploadProgress = `上传失败：${error.detail || xhr.statusText}`;
                    } catch {
                        this.uploadProgress = `上传失败：HTTP ${xhr.status}`;
                    }
                }
                this.isUploading = false;
            });

            // 错误处理
            xhr.addEventListener('error', () => {
                this.uploadProgress = '上传失败：网络错误';
                this.isUploading = false;
            });

            xhr.addEventListener('abort', () => {
                this.uploadProgress = '上传已取消';
                this.isUploading = false;
            });

            // 发送请求
            xhr.open('POST', '/documents/upload');
            xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
            xhr.send(formData);
        },

        // 添加文件大小格式化辅助方法
        formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        async deleteDocument(filename) {
            if (!confirm(`确定要删除文档 "${filename}" 吗？这将同时删除 Milvus 中的所有相关向量。`)) {
                return;
            }

            try {
                const response = await this.authFetch(`/documents/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.detail || 'Delete failed');
                }

                const data = await response.json();
                alert(data.message);
                await this.loadDocuments();

            } catch (error) {
                alert('删除文档失败：' + error.message);
            }
        },

        // ========== Voice Input Methods ==========

        /** 切换文字/语音输入模式 */
        toggleVoiceMode() {
            if (this.isLoading) return;
            if (!this.isAuthenticated) return;

            if (this.voiceMode) {
                // 从语音切回文字
                if (this.voiceInput) {
                    this.voiceInput.abort();
                    this.voiceInput = null;
                }
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
                            this.scheduleVoiceErrorReset('no-speech');
                        } else if (error === 'not-allowed') {
                            // 权限被拒 → 切回文字模式
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '无麦克风权限';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset('not-allowed');
                        } else if (error === 'network') {
                            // 网络不可用 → 切回文字模式
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '网络不可用';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset('network');
                        } else if (error === 'aborted') {
                            // 用户取消
                            this.voiceState = 'idle';
                            this.interimText = '';
                        } else if (error === 'unexpected') {
                            // 浏览器意外结束识别（切标签页、静默超时等）
                            this.voiceState = 'idle';
                            this.interimText = '';
                        } else if (error) {
                            // 其他错误
                            this.voiceState = 'error';
                            this.voiceErrorMsg = '识别失败，请重试';
                            this.playBeep('error');
                            this.scheduleVoiceErrorReset('generic');
                        } else {
                            // null/undefined — 成功（onResult 已处理）或浏览器意外触发
                            if (this.voiceState !== 'processing') {
                                this.voiceState = 'idle';
                                this.interimText = '';
                            }
                        }
                    }
                });

                this.voiceInput.start();
            } catch (e) {
                this.voiceState = 'error';
                this.voiceErrorMsg = '语音功能不可用';
                this.scheduleVoiceErrorReset('exception');
            }
        },

        /** 松手停止录音 */
        handleVoicePointerUp() {
            if (this.voiceInput && this.voiceInput.isActive) {
                this.voiceState = 'processing';
                this.voiceInput.stop();
            } else if (this.voiceInput && !this.voiceInput.isActive) {
                // 快速点击：指针抬起时识别尚未开始，取消等待中的识别
                this.voiceInput.abort();
                this.voiceState = 'idle';
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

            this._sendChatMessage(text.trim()).finally(() => {
                this.voiceState = 'idle';
                this.interimText = '';
            });
        },

        /** 错误状态定时恢复。not-allowed / network 会切回文字模式。 */
        scheduleVoiceErrorReset(errorType) {
            this.clearVoiceErrorTimer();
            this.voiceErrorTimer = setTimeout(() => {
                this.voiceState = 'idle';
                this.voiceErrorMsg = '';
                this.interimText = '';
                if (errorType === 'not-allowed' || errorType === 'network') {
                    this.voiceMode = false;
                }
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

        // ========== Attachment Upload Methods ==========

        /** 点击附件按钮 — 直接打开文件选择器 */
        handleAttachClick(event) {
            event.stopPropagation();
            if (this.isLoading) return;

            if (this.attachments.length >= 5) {
                alert('最多只能添加 5 个附件');
                return;
            }

            if (this.$refs.attachFileInput) {
                this.$refs.attachFileInput.click();
            }
        },

        /** 文件选择后的处理 — 统一处理文档和图片 */
        handleAttachFileSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            const file = files[0];
            const fileExt = file.name.split('.').pop().toLowerCase();

            // 检查数量上限
            if (this.attachments.length >= 5) {
                alert('最多只能添加 5 个附件');
                event.target.value = '';
                return;
            }

            const attachmentId = 'att_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);

            if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(fileExt)) {
                this._handleImageFile(file, attachmentId);
            } else if (['pdf', 'doc', 'docx', 'xls', 'xlsx'].includes(fileExt)) {
                this._handleDocumentFile(file, attachmentId);
            } else {
                alert('不支持的文件类型：' + file.name);
            }

            // 清空 input，允许重复选择同一文件
            event.target.value = '';
        },

        /** 处理图片文件 — FileReader 转 base64 */
        _handleImageFile(file, attachmentId) {
            // 检查大小
            if (file.size > 10 * 1024 * 1024) {
                alert('图片文件不能超过 10MB');
                return;
            }

            const chip = {
                id: attachmentId,
                type: 'image',
                content: '',
                filename: file.name,
                mime_type: file.type,
                status: 'extracting',
            };
            this.attachments.push(chip);

            const reader = new FileReader();
            reader.onload = () => {
                chip.content = reader.result;
                chip.status = 'ready';
            };
            reader.onerror = () => {
                chip.status = 'error';
            };
            reader.readAsDataURL(file);
        },

        /** 处理文档文件 — 上传到 /attachments/extract 提取文本 */
        _handleDocumentFile(file, attachmentId) {
            // 检查大小（50MB 上限）
            if (file.size > 50 * 1024 * 1024) {
                alert('文档文件不能超过 50MB');
                return;
            }

            const chip = {
                id: attachmentId,
                type: 'text',
                content: '',
                filename: file.name,
                mime_type: file.type,
                status: 'extracting',
            };
            this.attachments.push(chip);

            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/attachments/extract');
            xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);

            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        chip.content = data.text;
                        chip.status = 'ready';
                        if (data.char_count === 0) {
                            chip.content = '(文件内容为空)';
                        }
                    } catch (e) {
                        chip.status = 'error';
                    }
                } else {
                    chip.status = 'error';
                }
            };

            xhr.onerror = () => {
                chip.status = 'error';
            };

            xhr.send(formData);
        },

        /** 移除单个附件 */
        removeAttachment(index) {
            this.attachments.splice(index, 1);
        },

        getFileIcon(fileType) {
            if (fileType === 'PDF') {
                return 'fas fa-file-pdf';
            } else if (fileType === 'Word') {
                return 'fas fa-file-word';
            } else if (fileType === 'Excel') {
                return 'fas fa-file-excel';
            }
            return 'fas fa-file';
        }
    },
    watch: {
        messages: {
            handler() {
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            },
            deep: true
        }
    }
}).mount('#app');
