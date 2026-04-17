/* Chat — message display + SSE streaming + TTS voice (SbayAI pixel-perfect) */
const Chat = {
    isStreaming: false,
    ttsEnabled: false,
    voiceMode: false, // full voice mode: mic + TTS together
    activePresetName: null,
    activeSystemPrompt: null,
    currentModel: 'deepseek-chat',
    temporaryMode: false, // true = không lưu, không dùng history

    loadConversation(conv) {
        const area = document.getElementById('chatArea');
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.style.display = 'none';

        area.innerHTML = '';
        conv.messages.forEach(msg => {
            this.appendMessage(msg.role, msg.content);
        });
        this.scrollToBottom();
    },

    clear() {
        const area = document.getElementById('chatArea');
        area.innerHTML = `
            <div class="welcome" id="welcome">
                <h1>Khi bạn sẵn sàng là chúng ta có thể bắt đầu.</h1>
            </div>`;
    },

    _createMessageEl(role) {
        const isUser = role === 'user';
        const msgEl = document.createElement('div');
        msgEl.className = `message ${role}`;

        const inner = document.createElement('div');
        inner.className = 'message-inner';

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (isUser) {
            avatar.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
        } else {
            avatar.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>';
        }

        // Body
        const body = document.createElement('div');
        body.className = 'message-body';

        const roleLabel = document.createElement('div');
        roleLabel.className = 'message-role';
        roleLabel.textContent = isUser ? 'You' : 'SbayAI';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';

        // Action buttons (copy, regenerate) for assistant messages
        const actions = document.createElement('div');
        actions.className = 'message-actions';
        if (isUser) {
            actions.innerHTML = `
                <button class="msg-action-btn" title="Chỉnh sửa" onclick="Chat.editMessage(this)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                </button>
            `;
        } else {
            actions.innerHTML = `
                <button class="msg-action-btn" title="Sao chép" onclick="Chat.copyMessage(this)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                </button>
                <button class="msg-action-btn" title="Tạo lại" onclick="Chat.regenerate(this)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                </button>
            `;
        }

        body.appendChild(roleLabel);
        body.appendChild(contentEl);
        body.appendChild(actions);
        inner.appendChild(avatar);
        inner.appendChild(body);
        msgEl.appendChild(inner);

        return { msgEl, contentEl };
    },

    appendMessage(role, content) {
        const area = document.getElementById('chatArea');
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.style.display = 'none';

        const { msgEl, contentEl } = this._createMessageEl(role);

        if (role === 'assistant') {
            contentEl.innerHTML = MD.render(content);
            this._addQuickReplies(contentEl, content);
        } else {
            contentEl.textContent = content;
        }

        area.appendChild(msgEl);
        return contentEl;
    },

    _addQuickReplies(contentEl, rawText) {
        if (!rawText) return;
        // Tìm gợi ý dạng: 1️⃣ ..., 1. ..., 1) ...
        const lines = rawText.split('\n');
        const suggestions = [];
        for (const line of lines) {
            const m = line.match(/^(?:[1-6][️⃣.)]\s*|[1-6]\.\s+)(.+)/);
            if (m) {
                const s = m[1].replace(/\*\*/g, '').replace(/\[|\]/g, '').trim();
                if (s.length > 2 && s.length < 200) suggestions.push(s);
            }
        }
        if (suggestions.length < 2) return;

        const btnRow = document.createElement('div');
        btnRow.className = 'quick-reply-row';
        suggestions.slice(0, 6).forEach((s, i) => {
            const btn = document.createElement('button');
            btn.className = 'quick-reply-btn';
            btn.innerHTML = `<span class="qr-num">${i + 1}</span> ${s}`;
            btn.addEventListener('click', () => {
                document.querySelectorAll('.quick-reply-row').forEach(r => r.remove());
                Chat.send(s);
            });
            btnRow.appendChild(btn);
        });
        contentEl.appendChild(btnRow);
    },

    createStreamMessage() {
        const area = document.getElementById('chatArea');
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.style.display = 'none';

        const { msgEl, contentEl } = this._createMessageEl('assistant');
        contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

        area.appendChild(msgEl);
        return contentEl;
    },

    async send(message) {
        if (this.isStreaming || !message.trim()) return;

        this.isStreaming = true;
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;

        // Show user message
        this.appendMessage('user', message);
        this.scrollToBottom();

        // Create streaming target
        const targetEl = this.createStreamMessage();
        this.scrollToBottom();

        let fullText = '';
        let convId = Sidebar.currentConvId;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: convId,
                    model: this.currentModel,
                    system_prompt: this.activeSystemPrompt || null,
                    temporary: this.temporaryMode,
                }),
            });

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP ${res.status}: ${errorText || res.statusText}`);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();

                    if (data === '[DONE]') {
                        // Remove cursor class
                        targetEl.classList.remove('streaming-cursor');
                        break;
                    }

                    try {
                        const parsed = JSON.parse(data);

                        if (parsed.conversation_id) {
                            // Validate conversation_id format
                            if (typeof parsed.conversation_id === 'string' && parsed.conversation_id.match(/^[a-f0-9-]+$/)) {
                                Sidebar.currentConvId = parsed.conversation_id;
                                convId = parsed.conversation_id;
                            }
                        }

                        if (parsed.token) {
                            // Remove typing indicator on first token
                            const typing = targetEl.querySelector('.typing-indicator');
                            if (typing) {
                                typing.remove();
                                targetEl.classList.add('streaming-cursor');
                            }

                            fullText += parsed.token;
                            targetEl.innerHTML = MD.render(fullText);
                            targetEl.classList.add('streaming-cursor');
                            requestAnimationFrame(() => this.scrollToBottom());
                        }

                        if (parsed.error) {
                            const typing = targetEl.querySelector('.typing-indicator');
                            if (typing) typing.remove();
                            targetEl.classList.remove('streaming-cursor');
                            targetEl.innerHTML = `<p style="color:#ef4444">Error: ${parsed.error}</p>`;
                            throw new Error(parsed.error);
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                        // Continue streaming despite parse errors
                    }
                }
            }
        } catch (err) {
            console.error('Chat error:', err);
            const typing = targetEl.querySelector('.typing-indicator');
            if (typing) typing.remove();
            targetEl.classList.remove('streaming-cursor');
            
            // Show appropriate error message
            let errorMessage = err.message;
            if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                errorMessage = 'Network error. Please check your connection.';
            } else if (err.message.includes('HTTP 4')) {
                errorMessage = 'Request error. Please try again.';
            } else if (err.message.includes('HTTP 5')) {
                errorMessage = 'Server error. Please try again later.';
            }
            
            targetEl.innerHTML = `<p style="color:#ef4444">${errorMessage}</p>`;
        } finally {
            targetEl.classList.remove('streaming-cursor');
            this.isStreaming = false;
            sendBtn.disabled = false;

            // Re-enable send btn based on input
            const input = document.getElementById('messageInput');
            sendBtn.disabled = !input.value.trim();

            // TTS: read AI response aloud
            if (fullText && this.ttsEnabled) {
                this.speak(fullText);
            }

            // Thông báo âm thanh "Sbay" sau khi trả lời xong
            if (fullText) {
                this.playNotification();
            }

            // Quick reply buttons (Ask mode)
            if (fullText && targetEl) {
                this._addQuickReplies(targetEl, fullText);
            }

            Sidebar.load();
        }
    },

    editMessage(btn) {
        const msgBody = btn.closest('.message-body');
        const contentEl = msgBody.querySelector('.message-content');
        const oldText = contentEl.textContent;

        // Replace content with editable textarea
        const textarea = document.createElement('textarea');
        textarea.value = oldText;
        textarea.style.cssText = 'width:100%;min-height:60px;padding:8px;border:1px solid var(--border);border-radius:8px;font-size:15px;font-family:inherit;background:var(--bg);color:var(--text);resize:vertical;outline:none';
        contentEl.innerHTML = '';
        contentEl.appendChild(textarea);
        textarea.focus();

        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;margin-top:8px';
        btnRow.innerHTML = '<button style="padding:6px 16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px">Gửi lại</button><button style="padding:6px 16px;background:none;color:var(--text-muted);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:13px">Hủy</button>';
        contentEl.appendChild(btnRow);

        // Save & resend
        btnRow.children[0].onclick = () => {
            const newText = textarea.value.trim();
            if (!newText) return;
            contentEl.textContent = newText;
            // Remove all messages after this one and resend
            const msgEl = btn.closest('.message');
            let sibling = msgEl.nextElementSibling;
            while (sibling) {
                const next = sibling.nextElementSibling;
                sibling.remove();
                sibling = next;
            }
            // Resend edited message
            const target = this.createStreamMessage();
            this.scrollToBottom();
            this.isStreaming = true;
            document.getElementById('sendBtn').disabled = true;
            let fullText = '';
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: newText, conversation_id: Sidebar.currentConvId }),
            }).then(r => r.body.getReader()).then(async reader => {
                const decoder = new TextDecoder();
                let buffer = '';
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') break;
                        try {
                            const p = JSON.parse(data);
                            if (p.token) {
                                const typing = target.querySelector('.typing-indicator');
                                if (typing) { typing.remove(); target.classList.add('streaming-cursor'); }
                                fullText += p.token;
                                target.innerHTML = MD.render(fullText);
                                target.classList.add('streaming-cursor');
                                requestAnimationFrame(() => this.scrollToBottom());
                            }
                        } catch(e) {}
                    }
                }
            }).finally(() => {
                target.classList.remove('streaming-cursor');
                this.isStreaming = false;
                document.getElementById('sendBtn').disabled = false;
            });
        };

        // Cancel
        btnRow.children[1].onclick = () => { contentEl.textContent = oldText; };
    },

    copyMessage(btn) {
        const content = btn.closest('.message-body').querySelector('.message-content');
        if (!content) return;
        navigator.clipboard.writeText(content.textContent).then(() => {
            btn.title = 'Đã sao chép!';
            btn.style.color = 'var(--green, #10a37f)';
            setTimeout(() => { btn.title = 'Sao chép'; btn.style.color = ''; }, 2000);
        });
    },

    regenerate(btn) {
        if (this.isStreaming) return;
        // Find the last user message
        const messages = document.querySelectorAll('.message');
        let lastUserMsg = '';
        messages.forEach(m => {
            if (m.classList.contains('user')) {
                lastUserMsg = m.querySelector('.message-content')?.textContent || '';
            }
        });
        if (!lastUserMsg) return;

        // Remove last assistant message
        const lastAssist = document.querySelector('.message.assistant:last-of-type');
        if (lastAssist) lastAssist.remove();

        // Re-send
        this.isStreaming = true;
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;

        const targetEl = this.createStreamMessage();
        this.scrollToBottom();

        let fullText = '';
        const convId = Sidebar.currentConvId;

        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: lastUserMsg, conversation_id: convId }),
        }).then(res => res.body.getReader()).then(async reader => {
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') { targetEl.classList.remove('streaming-cursor'); break; }
                    try {
                        const p = JSON.parse(data);
                        if (p.token) {
                            const typing = targetEl.querySelector('.typing-indicator');
                            if (typing) { typing.remove(); targetEl.classList.add('streaming-cursor'); }
                            fullText += p.token;
                            targetEl.innerHTML = MD.render(fullText);
                            targetEl.classList.add('streaming-cursor');
                            requestAnimationFrame(() => this.scrollToBottom());
                        }
                    } catch(e) {}
                }
            }
        }).finally(() => {
            targetEl.classList.remove('streaming-cursor');
            this.isStreaming = false;
            sendBtn.disabled = false;
        });
    },

    // ===== Text-to-Speech (1 lời thoại duy nhất, cấm chồng chéo) =====
    _ttsAudio: null,
    _ttsSpeaking: false,
    _ttsAborted: false,

    speak(text) {
        if (!this.ttsEnabled) return;

        // RULE: Cancel mọi audio cũ trước khi phát mới
        this.stopSpeaking();
        this._ttsAborted = false;
        this._ttsSpeaking = true;

        // Tắt mic khi AI đang nói (tránh chồng chéo)
        if (this.voiceMode) {
            try {
                const micBtn = document.getElementById('micBtn');
                if (micBtn && micBtn.classList.contains('active')) {
                    micBtn.click(); // stop mic
                }
            } catch(_) {}
        }

        // Clean text
        let clean = text
            .replace(/```[\s\S]*?```/g, '')
            .replace(/`[^`]+`/g, '')
            .replace(/#{1,6}\s/g, '')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/<[^>]+>/g, '')
            .replace(/\n{2,}/g, '. ')
            .replace(/\n/g, ' ')
            .trim();

        if (!clean) { this._ttsSpeaking = false; return; }

        // Split chunks (max 190 chars)
        const chunks = [];
        const sentences = clean.split(/(?<=[.!?。,])\s+/);
        let current = '';
        for (const s of sentences) {
            if ((current + ' ' + s).length > 190) {
                if (current) chunks.push(current.trim());
                current = s;
            } else {
                current = current ? current + ' ' + s : s;
            }
        }
        if (current) chunks.push(current.trim());

        // Phát tuần tự — 1 chunk tại 1 thời điểm
        const speakChunk = (i) => {
            // Đã bị cancel → dừng
            if (this._ttsAborted) { this._ttsSpeaking = false; return; }

            // Hết chunks → xong
            if (i >= chunks.length) {
                this._ttsSpeaking = false;
                this._ttsAudio = null;
                // Voice mode: bật lại mic SAU KHI AI nói xong
                if (this.voiceMode && !this.isStreaming) {
                    setTimeout(() => {
                        const micBtn = document.getElementById('micBtn');
                        if (micBtn && !this._ttsSpeaking) micBtn.click();
                    }, 500);
                }
                return;
            }

            const encoded = encodeURIComponent(chunks[i]);
            const audio = new Audio(`/api/tts?text=${encoded}`);
            this._ttsAudio = audio;
            audio.playbackRate = 1.1;

            audio.onended = () => {
                this._ttsAudio = null;
                speakChunk(i + 1); // chunk tiếp theo
            };
            audio.onerror = () => {
                this._ttsAudio = null;
                speakChunk(i + 1); // skip lỗi
            };
            audio.play().catch(() => {
                this._ttsAudio = null;
                speakChunk(i + 1);
            });
        };

        speakChunk(0);
    },

    stopSpeaking() {
        this._ttsAborted = true;
        this._ttsSpeaking = false;
        if (this._ttsAudio) {
            try { this._ttsAudio.pause(); this._ttsAudio.currentTime = 0; } catch(_) {}
            this._ttsAudio = null;
        }
    },

    toggleTTS() {
        this.ttsEnabled = !this.ttsEnabled;
        return this.ttsEnabled;
    },

    startVoiceMode() {
        this.voiceMode = true;
        this.ttsEnabled = true;
        // Start mic — chi khi chua dang nghe
        setTimeout(() => {
            const micBtn = document.getElementById('micBtn');
            if (micBtn && !micBtn.style.background) {
                micBtn.click();
            }
        }, 100);
    },

    stopVoiceMode() {
        this.voiceMode = false;
        this.ttsEnabled = false;
        this.stopSpeaking();
        // Tat mic neu dang nghe
        const micBtn = document.getElementById('micBtn');
        if (micBtn && micBtn.style.background) {
            micBtn.click();
        }
    },

    // ===== Notification sound "Sbay" =====
    _notifAudio: null,
    _notifLoaded: false,

    loadNotificationSound() {
        if (this._notifLoaded) return;
        this._notifLoaded = true;
        // Preload "Sbay" audio từ TTS
        fetch('/api/tts?text=Sbay')
            .then(r => r.blob())
            .then(blob => {
                this._notifAudio = new Audio(URL.createObjectURL(blob));
                this._notifAudio.volume = 0.6;
            })
            .catch(() => {});
    },

    playNotification() {
        // Không phát nếu TTS đang nói (tránh chồng)
        if (this._ttsSpeaking) return;

        if (this._notifAudio) {
            const sound = this._notifAudio.cloneNode();
            sound.volume = 0.6;
            sound.play().catch(() => {});
        } else {
            // Fallback: tạo beep đơn giản
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 800;
                gain.gain.value = 0.15;
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
            } catch(_) {}
        }
    },

    scrollToBottom() {
        const area = document.getElementById('chatArea');
        area.scrollTop = area.scrollHeight;
    }
};