/**
 * EDA Agent Chat Webview Frontend — Kimi Code inspired
 */

(function () {
    const vscode = acquireVsCodeApi();

    const messagesEl = document.getElementById('messages');
    const inputEl = document.getElementById('message-input');
    const sendBtn = document.getElementById('btn-send');
    const stopBtn = document.getElementById('btn-stop');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const btnHistory = document.getElementById('btn-history');
    const btnClear = document.getElementById('btn-clear');
    const historyPanel = document.getElementById('history-panel');
    const historyClose = document.getElementById('history-close');
    const historyList = document.getElementById('history-list');
    const historyNew = document.getElementById('history-new');
    const queueBar = document.getElementById('queue-bar');
    const queueCountEl = document.getElementById('queue-count');
    const btnQueueClear = document.getElementById('btn-queue-clear');
    const btnQueueToggle = document.getElementById('btn-queue-toggle');
    const queueListEl = document.getElementById('queue-list');
    const designStatePanel = document.getElementById('design-state-panel');
    const designStateHeader = document.getElementById('design-state-header');
    const designStateTitle = document.getElementById('design-state-title');
    const designStateBody = document.getElementById('design-state-body');

    let isThinking = false;
    let messageHistory = [];
    let activeToolCalls = new Map();
    let currentBudget = null;
    let isComposing = false;
    let currentSessionId = Date.now().toString();
    let currentStreamElement = null;   // The .message-content being streamed into
    let currentStreamMsgDiv = null;    // The parent .message div
    let currentStreamText = "";        // Accumulated raw text
    let currentTurnMsgDiv = null;      // Current turn's message container (may span multiple iterations)
    let messageQueue = [];             // Queued messages while thinking
    let designState = null;            // Current design state from backend
    let currentPhase = '';               // Current agent phase: analyzing / executing / responding
    let activePlan = null;               // Current task plan from backend

    const STORAGE_KEY = 'eda_chat_history';

    function init() {
        sendBtn.addEventListener('click', sendMessage);
        if (stopBtn) {
            stopBtn.addEventListener('click', stopThinking);
        }
        inputEl.addEventListener('keydown', handleKeyDown);
        inputEl.addEventListener('compositionstart', () => { isComposing = true; });
        inputEl.addEventListener('compositionend', () => { isComposing = false; });
        inputEl.addEventListener('input', autoResize);

        btnHistory.addEventListener('click', toggleHistory);
        historyClose.addEventListener('click', toggleHistory);
        historyNew.addEventListener('click', startNewChat);
        btnClear.addEventListener('click', clearChat);
        btnQueueClear.addEventListener('click', clearQueue);
        if (btnQueueToggle) {
            btnQueueToggle.addEventListener('click', toggleQueueList);
        }
        designStateHeader.addEventListener('click', toggleDesignState);

        createPermissionDialog();
        loadSession();
        renderHistory();
        scrollToBottom();
    }

    /* ---------- Permission Dialog ---------- */

    let permissionDialog = null;

    function createPermissionDialog() {
        if (permissionDialog) return;
        permissionDialog = document.createElement('div');
        permissionDialog.className = 'permission-dialog';
        permissionDialog.style.display = 'none';
        document.body.appendChild(permissionDialog);
    }

    function showPermissionDialog(permissionType, tool, message) {
        if (!permissionDialog) createPermissionDialog();
        const typeLabel = permissionType === 'eda_access' ? 'EDA 数据库操作' : '文件访问';
        const toolLabel = tool || 'unknown';
        permissionDialog.innerHTML = `
            <div class="permission-dialog-overlay">
                <div class="permission-dialog-box">
                    <div class="permission-dialog-title">⚠️ 需要用户授权</div>
                    <div class="permission-dialog-body">
                        <p>工具 <strong>${escapeHtml(toolLabel)}</strong> 请求 <strong>${escapeHtml(typeLabel)}</strong> 权限：</p>
                        <p class="permission-dialog-detail">${escapeHtml(message || '')}</p>
                    </div>
                    <div class="permission-dialog-actions">
                        <button class="permission-btn permission-btn-deny" onclick="window._edaDenyPermission()">拒绝</button>
                        <button class="permission-btn permission-btn-once" onclick="window._edaGrantOnce('${escapeHtml(permissionType)}')">同意本次</button>
                        <button class="permission-btn permission-btn-session" onclick="window._edaGrantSession()">同意整个 Session</button>
                    </div>
                </div>
            </div>
        `;
        permissionDialog.style.display = 'block';
    }

    function hidePermissionDialog() {
        if (permissionDialog) {
            permissionDialog.style.display = 'none';
            permissionDialog.innerHTML = '';
        }
    }

    window._edaDenyPermission = function() {
        hidePermissionDialog();
        addMessage('system', '❌ 用户拒绝了权限请求。请调整操作范围后重试。', [], null);
    };

    window._edaGrantOnce = function(permissionType) {
        vscode.postMessage({ type: 'grantPermission', permissionType: permissionType, scope: 'once' });
        hidePermissionDialog();
        addMessage('system', '✅ 已同意本次 ' + (permissionType === 'eda_access' ? 'EDA 数据库' : '文件访问') + ' 权限。', [], null);
    };

    window._edaGrantSession = function() {
        vscode.postMessage({ type: 'grantPermission', permissionType: 'all', scope: 'session' });
        hidePermissionDialog();
        addMessage('system', '✅ 已同意整个 Session 的所有操作权限。后续不再提示。', [], null);
    };

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey && !isComposing && !e.repeat) {
            e.preventDefault();
            if (e.ctrlKey || e.metaKey) {
                // Ctrl+Enter: queue the message
                queueMessage();
            } else {
                sendMessage();
            }
        }
    }

    function sendMessage() {
        const text = inputEl.value.trim();
        if (!text) return;
        if (isThinking) {
            // Auto-queue if currently thinking
            queueMessage(text);
            inputEl.value = '';
            inputEl.style.height = 'auto';
            return;
        }
        vscode.postMessage({ type: 'sendMessage', text });
        inputEl.value = '';
        inputEl.style.height = 'auto';
        setInputEnabled(false);
    }

    function queueMessage(text) {
        const t = (text !== undefined ? text : inputEl.value).trim();
        if (!t) return;
        messageQueue.push(t);
        if (text === undefined) {
            inputEl.value = '';
            inputEl.style.height = 'auto';
        }
        renderQueue();
    }

    function clearQueue() {
        messageQueue = [];
        renderQueue();
    }

    function toggleQueueList() {
        if (!queueListEl) return;
        const isHidden = queueListEl.style.display === 'none';
        queueListEl.style.display = isHidden ? 'block' : 'none';
        if (btnQueueToggle) {
            btnQueueToggle.textContent = isHidden ? '▴' : '▾';
        }
    }

    function executeQueuedMessage(index) {
        if (index < 0 || index >= messageQueue.length) return;
        const text = messageQueue[index];
        messageQueue.splice(index, 1);
        renderQueue();
        addMessage('user', text, [], null);
        vscode.postMessage({ type: 'sendMessage', text });
        setInputEnabled(false);
    }

    function removeQueuedMessage(index) {
        if (index < 0 || index >= messageQueue.length) return;
        messageQueue.splice(index, 1);
        renderQueue();
    }

    function renderQueue() {
        if (messageQueue.length === 0) {
            queueBar.style.display = 'none';
            if (queueListEl) queueListEl.style.display = 'none';
            return;
        }
        queueBar.style.display = 'block';
        queueCountEl.textContent = `${messageQueue.length} queued`;

        // Render queue list
        if (queueListEl) {
            queueListEl.innerHTML = '';
            messageQueue.forEach((text, idx) => {
                const item = document.createElement('div');
                item.className = 'queue-item';

                const content = document.createElement('span');
                content.className = 'queue-item-text';
                content.textContent = text;
                content.title = text;

                const actions = document.createElement('div');
                actions.className = 'queue-item-actions';

                const runBtn = document.createElement('button');
                runBtn.className = 'queue-item-btn run';
                runBtn.textContent = '▶';
                runBtn.title = '执行';
                runBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    executeQueuedMessage(idx);
                });

                const delBtn = document.createElement('button');
                delBtn.className = 'queue-item-btn delete';
                delBtn.textContent = '✕';
                delBtn.title = '删除';
                delBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    removeQueuedMessage(idx);
                });

                actions.appendChild(runBtn);
                actions.appendChild(delBtn);
                item.appendChild(content);
                item.appendChild(actions);
                queueListEl.appendChild(item);
            });
        }
    }

    function processQueue() {
        if (messageQueue.length === 0) return;
        const text = messageQueue.shift();
        renderQueue();
        addMessage('user', text, [], null);
        vscode.postMessage({ type: 'sendMessage', text });
        setInputEnabled(false);
    }

    function autoResize() {
        inputEl.style.height = 'auto';
        // Allow textarea to grow up to ~50% of viewport or 400px,
        // whichever is smaller, so users can see more of their input.
        const maxHeight = Math.min(window.innerHeight * 0.5, 400);
        inputEl.style.height = Math.min(inputEl.scrollHeight, maxHeight) + 'px';
    }

    function setInputEnabled(enabled) {
        inputEl.disabled = !enabled;
        sendBtn.disabled = !enabled;
    }

    function showStopButton(show) {
        if (!stopBtn) return;
        stopBtn.style.display = show ? 'flex' : 'none';
        sendBtn.style.display = show ? 'none' : 'flex';
    }

    function stopThinking() {
        vscode.postMessage({ type: 'stop' });
        showStopButton(false);
        // Show a temporary system message
        addMessage('system', '⏹️ 停止请求已发送...', [], null);
    }

    function updateStatus(status, error) {
        statusDot.className = 'status-dot';
        statusDot.classList.add(status);
        const map = {
            ready: 'Ready',
            starting: 'Starting...',
            stopped: 'Stopped',
            error: error ? error.substring(0, 40) : 'Error',
            thinking: 'Thinking...',
            executing: 'Executing...'
        };
        statusText.textContent = map[status] || status;
        statusText.title = error || '';
        if (status === 'ready') {
            processQueue();
        }
    }

    function updatePhaseIndicator(phase) {
        currentPhase = phase;
        const phaseMap = {
            analyzing: '🔍 分析中',
            executing: '⚙️ 执行中',
            responding: '💬 回答中',
        };
        const label = phaseMap[phase] || phase;
        // Update status text to show phase
        if (phase && phase !== 'responding') {
            statusText.textContent = label;
        }
        // Show stop button when agent is working
        if (phase === 'analyzing' || phase === 'executing') {
            showStopButton(true);
        } else if (phase === 'responding') {
            isThinking = false;
            showStopButton(false);
            setInputEnabled(true);
        }
        // Add phase badge to current turn message if exists
        if (currentTurnMsgDiv) {
            let badge = currentTurnMsgDiv.querySelector('.phase-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'phase-badge';
                const header = currentTurnMsgDiv.querySelector('.message-header');
                if (header) {
                    header.appendChild(badge);
                }
            }
            badge.textContent = label;
            badge.dataset.phase = phase;
        }
    }

    function renderPlanPanel(plan) {
        activePlan = plan;
        let panel = document.getElementById('plan-panel');
        if (!plan || !plan.phases || plan.phases.length === 0) {
            if (panel) {
                panel.style.display = 'none';
            }
            return;
        }
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'plan-panel';
            panel.className = 'plan-panel';
            // Insert before messages element
            messagesEl.parentNode.insertBefore(panel, messagesEl);
        }
        panel.style.display = 'block';

        const statusIcon = {
            pending: '⏳',
            active: '🔄',
            done: '✅',
        };

        const title = plan.goal || '任务计划';
        let html = `<div class="plan-panel-header">
            <span class="plan-panel-title">📋 ${escapeHtml(title)}</span>
            <span class="plan-panel-toggle">▾</span>
        </div>
        <div class="plan-panel-body">`;

        for (const phase of plan.phases) {
            const icon = statusIcon[phase.status] || '⏳';
            const cls = `plan-phase ${phase.status}`;
            html += `<div class="${cls}">
                <span class="plan-phase-icon">${icon}</span>
                <span class="plan-phase-name">${escapeHtml(phase.phase)}</span>
                <span class="plan-phase-desc">${escapeHtml(phase.description)}</span>
            </div>`;
        }

        html += '</div>';
        panel.innerHTML = html;

        // Toggle behavior
        const header = panel.querySelector('.plan-panel-header');
        header.addEventListener('click', () => {
            panel.classList.toggle('collapsed');
        });
    }

    /* ---------- Messages ---------- */

    function addMessage(role, text, toolCalls, durationMs) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;

        const header = document.createElement('div');
        header.className = 'message-header';

        const avatar = document.createElement('span');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';

        const name = document.createElement('span');
        name.textContent = role === 'user' ? 'You' : 'EDA Agent';

        const meta = document.createElement('span');
        meta.className = 'message-time';
        let metaText = new Date().toLocaleTimeString();
        if (durationMs) metaText += ` · ${durationMs}ms`;
        meta.textContent = metaText;

        header.appendChild(avatar);
        header.appendChild(name);
        header.appendChild(meta);
        msgDiv.appendChild(header);

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = formatMarkdown(text);
        msgDiv.appendChild(content);

        if (toolCalls && toolCalls.length > 0) {
            toolCalls.forEach(tc => {
                const tcId = String(tc.id || tc.toolCallId || '');
                if (activeToolCalls.has(tcId)) {
                    return; // Already live-added, skip duplicate
                }
                const toolDiv = createToolCallElement(tc);
                msgDiv.appendChild(toolDiv);
                activeToolCalls.set(tcId, toolDiv);
            });
        }

        messagesEl.appendChild(msgDiv);
        scrollToBottom();
        messageHistory.push({ role, text, timestamp: Date.now() });
        saveSession();
        return msgDiv;
    }

    // Batch token rendering to reduce DOM reflows
    let _pendingTokens = '';
    let _tokenRafId = null;

    function appendToken(text) {
        if (!text) return;
        showThinking(false);
        // Ensure we have a message container
        if (!currentStreamMsgDiv) {
            currentStreamMsgDiv = createAssistantMessageDiv();
            currentTurnMsgDiv = currentStreamMsgDiv;
        }
        // Ensure we have a content element for streaming
        if (!currentStreamElement) {
            const content = document.createElement('div');
            content.className = 'message-content streaming';
            currentStreamMsgDiv.appendChild(content);
            currentStreamElement = content;
            currentStreamText = '';
        }
        currentStreamText += text;
        _pendingTokens += text;

        // Use requestAnimationFrame to batch DOM updates
        if (!_tokenRafId) {
            _tokenRafId = requestAnimationFrame(() => {
                _tokenRafId = null;
                if (_pendingTokens && currentStreamElement) {
                    // Append as a single text node instead of per-token spans
                    // This avoids N reflows for N tokens
                    currentStreamElement.appendChild(document.createTextNode(_pendingTokens));
                    _pendingTokens = '';
                    scrollToBottom();
                }
            });
        }
    }

    function createAssistantMessageDiv() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';

        const header = document.createElement('div');
        header.className = 'message-header';

        const avatar = document.createElement('span');
        avatar.className = 'message-avatar';
        avatar.textContent = 'AI';

        const name = document.createElement('span');
        name.textContent = 'EDA Agent';

        const meta = document.createElement('span');
        meta.className = 'message-time';
        meta.textContent = new Date().toLocaleTimeString();

        header.appendChild(avatar);
        header.appendChild(name);
        header.appendChild(meta);
        msgDiv.appendChild(header);

        messagesEl.appendChild(msgDiv);
        scrollToBottom();
        return msgDiv;
    }

    function finalizeStream(text, toolCalls, durationMs) {
        // Flush any pending batched tokens first
        if (_tokenRafId) {
            cancelAnimationFrame(_tokenRafId);
            _tokenRafId = null;
        }
        if (_pendingTokens && currentStreamElement) {
            currentStreamElement.appendChild(document.createTextNode(_pendingTokens));
            _pendingTokens = '';
        }
        if (currentStreamElement) {
            currentStreamElement.innerHTML = formatMarkdown(text || currentStreamText);
            currentStreamElement.classList.remove('streaming');
        }
        // Update meta with duration on the current turn message
        if (durationMs && currentTurnMsgDiv) {
            const meta = currentTurnMsgDiv.querySelector('.message-time');
            if (meta) {
                meta.textContent = new Date().toLocaleTimeString() + ` · ${durationMs}ms`;
            }
        }
        // Fallback: attach tool calls if passed (should already be live-added)
        if (toolCalls && toolCalls.length > 0 && currentTurnMsgDiv) {
            toolCalls.forEach(tc => {
                const tcId = String(tc.id || tc.toolCallId || '');
                if (activeToolCalls.has(tcId)) {
                    return; // Already live-added, skip duplicate
                }
                const toolDiv = createToolCallElement(tc);
                currentTurnMsgDiv.appendChild(toolDiv);
                activeToolCalls.set(tcId, toolDiv);
            });
        }
        const finalText = text || currentStreamText;
        if (finalText) {
            messageHistory.push({
                role: 'assistant',
                text: finalText,
                timestamp: Date.now(),
            });
            saveSession();
        }
        currentStreamElement = null;
        currentStreamText = '';
        currentStreamMsgDiv = null;
        currentTurnMsgDiv = null;
    }

    // Track running tool timers for elapsed-time display
    const toolTimers = new Map();
    // Cache for toolComplete events that arrive before toolStart (fast-fail cases)
    const pendingToolResults = new Map();

    function createToolCallElement(tc) {
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call running';  // collapsed by default
        const tid = tc.id || tc.toolCallId || '';
        toolDiv.dataset.toolId = tid;
        toolDiv.dataset.toolName = tc.function?.name || tc.tool || 'tool';

        const toolHeader = document.createElement('div');
        toolHeader.className = 'tool-call-header';
        const toolName = tc.function?.name || tc.tool || 'tool';

        // Backend summary first; fallback: derive from args for common tools
        let summary = tc.summary || '';
        if (!summary && tc.args && typeof tc.args === 'object') {
            const a = tc.args;
            if (toolName === 'bash') {
                summary = a.command || '';
            } else if (['file_read', 'file_write', 'file_edit'].includes(toolName)) {
                summary = a.path || a.file_path || '';
                if (summary) summary = 'file: ' + summary;
            } else if (toolName === 'glob') {
                summary = a.pattern || a.path || '';
                if (summary) summary = 'pattern: ' + summary;
            } else if (toolName === 'grep') {
                summary = (a.pattern || '') + (a.path ? ' in ' + a.path : '');
                if (summary) summary = 'pattern: ' + summary;
            } else {
                // Generic fallback: first non-empty key
                for (const [k, v] of Object.entries(a)) {
                    if (v && k !== 'description' && k !== 'detail' && k !== 'verbose') {
                        summary = `${k}: ${String(v).substring(0, 60)}`;
                        break;
                    }
                }
            }
            if (summary.length > 60) {
                summary = summary.substring(0, 60) + '...';
            }
        }
        const summaryHtml = summary ? ` <span class="tool-summary">— ${escapeHtml(summary)}</span>` : '';

        const round = tc.toolRound || 0;
        const maxRounds = tc.maxToolRounds || 0;
        let roundHtml = '';
        if (round > 0 && maxRounds > 0) {
            roundHtml = ` <span class="tool-round-badge">Round ${round}/${maxRounds}</span>`;
        }

        const timeout = tc.timeout || 0;
        const timeoutHtml = timeout > 0 ? ` <span class="tool-timeout">⏱ ${timeout}s</span>` : '';

        toolHeader.innerHTML = `<span class="tool-spinner"></span> ${escapeHtml(toolName)}${summaryHtml}${roundHtml}${timeoutHtml}`;
        toolDiv.appendChild(toolHeader);

        const body = document.createElement('div');
        body.className = 'tool-call-body';

        const toolArgs = document.createElement('div');
        toolArgs.className = 'tool-call-args';
        try {
            const args = typeof tc.function?.arguments === 'string'
                ? JSON.parse(tc.function.arguments)
                : (tc.args || tc.function?.arguments || {});
            toolArgs.textContent = JSON.stringify(args, null, 2);
        } catch {
            toolArgs.textContent = String(tc.args || tc.function?.arguments || '');
        }
        body.appendChild(toolArgs);

        const toolResult = document.createElement('div');
        toolResult.className = 'tool-call-result';
        toolResult.style.display = 'none';
        body.appendChild(toolResult);

        const processing = document.createElement('div');
        processing.className = 'tool-call-processing';
        processing.innerHTML = '<span class="tool-spinner-small"></span> Processing...';
        body.appendChild(processing);

        toolDiv.appendChild(body);

        // Click header to expand/collapse
        toolHeader.addEventListener('click', () => {
            toolDiv.classList.toggle('expanded');
        });

        // Start elapsed-time ticker
        if (tid) {
            const startTs = Date.now();
            const timer = setInterval(() => {
                const elapsed = Math.round((Date.now() - startTs) / 1000);
                const procEl = toolDiv.querySelector('.tool-call-processing');
                if (procEl) {
                    const limitText = timeout > 0 ? ` / ${timeout}s` : '';
                    procEl.innerHTML = `<span class="tool-spinner-small"></span> Running… ${elapsed}s${limitText}`;
                }
            }, 1000);
            toolTimers.set(tid, timer);

            // Safety net: auto-mark as failed if toolComplete never arrives
            const timeoutMs = (timeout || 60) * 1000 + 10000; // tool timeout + 10s buffer
            setTimeout(() => {
                if (toolTimers.has(tid)) {
                    updateToolResult(tid, false, {error: 'Tool completion event not received — possible backend/frontend sync issue'}, timeoutMs);
                }
            }, timeoutMs);

            // Apply any pending result that arrived before this toolStart
            if (pendingToolResults.has(tid)) {
                const pending = pendingToolResults.get(tid);
                pendingToolResults.delete(tid);
                updateToolResult(tid, pending.success, pending.result, pending.durationMs);
            }
        }

        return toolDiv;
    }

    function updateToolResult(toolCallId, success, result, durationMs, hintToolName) {
        const normalizedId = String(toolCallId || '');
        let toolEl = activeToolCalls.get(normalizedId);
        if (!toolEl && normalizedId) {
            // Fallback: match by tool name among running elements.
            // Extract tool name from the normalizedId if it's a synthetic ID
            // like "tc-bash-r1-i0-n0", or use the explicitly passed hintToolName.
            const matchName = hintToolName || (normalizedId.startsWith('tc-') ? normalizedId.split('-')[1] : null);
            if (matchName) {
                const runningEls = Array.from(document.querySelectorAll('.tool-call.running'));
                for (const el of runningEls) {
                    if (el.dataset.toolName === matchName) {
                        toolEl = el;
                        activeToolCalls.set(normalizedId, toolEl);
                        break;
                    }
                }
            }
        }
        if (!toolEl) {
            // toolComplete arrived before toolStart (fast-fail case).
            // Cache the result so it can be applied when toolStart arrives.
            pendingToolResults.set(normalizedId, { success, result, durationMs });
            return;
        }

        // Stop elapsed-time ticker
        if (toolTimers.has(normalizedId)) {
            clearInterval(toolTimers.get(normalizedId));
            toolTimers.delete(normalizedId);
        }

        toolEl.classList.remove('running', 'success', 'error');
        toolEl.classList.add(success ? 'success' : 'error');

        const header = toolEl.querySelector('.tool-call-header');
        const toolName = toolEl.dataset.toolName || 'tool';
        const icon = success ? '✓' : '✕';
        const dur = durationMs ? ` (${durationMs}ms)` : '';
        // Preserve the summary (e.g. bash command) that was shown while running
        const existingSummary = header.querySelector('.tool-summary');
        const summaryHtml = existingSummary ? existingSummary.outerHTML : '';
        header.innerHTML = `${icon} ${escapeHtml(toolName)}${summaryHtml}${dur}`;

        const resultEl = toolEl.querySelector('.tool-call-result');
        if (result !== undefined && resultEl) {
            resultEl.style.display = 'block';
            let text;
            // Pretty-print todo list and task plan results
            if (toolName === 'set_todo_list' && result && Array.isArray(result.todos)) {
                text = formatTodoList(result.todos);
            } else if (toolName === 'task_plan' && result && result.phases) {
                text = formatTaskPlan(result);
            } else {
                text = typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result);
                const MAX_RESULT_CHARS = 3000;
                if (text.length > MAX_RESULT_CHARS) {
                    text = text.substring(0, MAX_RESULT_CHARS) + `\n...[truncated, total ${text.length} chars]`;
                }
            }
            resultEl.innerHTML = text;
        }

        // Hide processing indicator
        const procEl = toolEl.querySelector('.tool-call-processing');
        if (procEl) {
            procEl.style.display = 'none';
        }

        // Keep collapsed by default; user can click to expand
        toolEl.classList.remove('expanded');
    }

    function updateToolProgress(toolCallId, data) {
        const normalizedId = String(toolCallId || '');
        const toolEl = activeToolCalls.get(normalizedId);
        if (!toolEl) return;

        // Update the processing indicator text if present
        const procEl = toolEl.querySelector('.tool-call-processing');
        if (procEl) {
            const msg = data?.message || data?.stage || 'Processing...';
            const pct = data?.progress !== undefined ? ` ${data.progress}%` : '';
            procEl.innerHTML = `<span class="tool-spinner-small"></span> ${escapeHtml(msg)}${pct}`;
        }

        let progressEl = toolEl.querySelector('.tool-call-progress');
        if (!progressEl) {
            progressEl = document.createElement('div');
            progressEl.className = 'tool-call-progress';
            toolEl.querySelector('.tool-call-body').appendChild(progressEl);
        }
        const msg = data?.message || data?.stage || 'Running...';
        const pct = data?.progress !== undefined ? `${data.progress}%` : '';
        progressEl.textContent = `${msg} ${pct}`;
    }

    /* ---------- Thinking ---------- */

    function showThinking(show) {
        isThinking = show;
        let indicator = document.querySelector('.thinking-indicator');
        if (show) {
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.className = 'thinking-indicator';
                indicator.innerHTML = '<span class="spinner"></span> EDA Agent is thinking...';
                messagesEl.appendChild(indicator);
                scrollToBottom();
            }
            // When thinking starts, finalize any active partial stream
            // so the previous turn's text is rendered before new thinking
            if (currentStreamElement) {
                finalizePartialStream();
            }
        } else {
            indicator?.remove();
            // Note: we do NOT enable input here — that only happens when the
            // entire assistant turn is complete (assistant message or error).
        }
    }

    /* ---------- Design State Panel ---------- */

    function toggleDesignState() {
        designStatePanel.classList.toggle('collapsed');
    }

    function updateDesignState(state) {
        designState = state;
        const hasDesign = state && (state.activeLib || state.activeCell || state.activeDesign);
        designStatePanel.style.display = hasDesign ? 'block' : 'none';

        let title = '📁 No active design';
        if (state?.activeDesign) {
            title = `🔧 ${escapeHtml(state.activeDesign)}`;
        } else if (state?.activeCell) {
            title = `📐 ${escapeHtml(state.activeCell)}`;
        } else if (state?.activeLib) {
            title = `📂 ${escapeHtml(state.activeLib)}`;
        }
        designStateTitle.textContent = title;

        const dsDesign = document.getElementById('ds-design');
        const dsProgress = document.getElementById('ds-progress');
        const dsActions = document.getElementById('ds-actions');

        if (dsDesign) {
            const parts = [];
            if (state?.activeLib) parts.push(`Lib: ${escapeHtml(state.activeLib)}`);
            if (state?.activeCell) parts.push(`Cell: ${escapeHtml(state.activeCell)}`);
            if (state?.activeView) parts.push(`View: ${escapeHtml(state.activeView)}`);
            dsDesign.innerHTML = parts.length ? parts.join(' · ') : '—';
        }

        if (dsProgress) {
            const todo = state?.todoList || [];
            const done = todo.filter(t => t.status === 'done').length;
            const total = todo.length;
            if (total > 0) {
                const pct = Math.round((done / total) * 100);
                dsProgress.innerHTML = `<div class="ds-progress-bar"><div class="ds-progress-fill" style="width:${pct}%"></div></div><span>${done}/${total} done</span>`;
            } else {
                dsProgress.textContent = '—';
            }
        }

        if (dsActions) {
            const actions = state?.recentActions || [];
            if (actions.length > 0) {
                dsActions.innerHTML = actions.slice(-5).reverse().map(a =>
                    `<div class="ds-action">${escapeHtml(a)}</div>`
                ).join('');
            } else {
                dsActions.textContent = '—';
            }
        }
    }

    function finalizePartialStream() {
        if (!currentStreamElement) return;
        // Flush pending batched tokens before re-rendering markdown
        if (_tokenRafId) {
            cancelAnimationFrame(_tokenRafId);
            _tokenRafId = null;
        }
        if (_pendingTokens) {
            currentStreamElement.appendChild(document.createTextNode(_pendingTokens));
            _pendingTokens = '';
        }
        currentStreamElement.innerHTML = formatMarkdown(currentStreamText);
        currentStreamElement.classList.remove('streaming');
        currentStreamElement = null;
        currentStreamText = '';
    }

    /* ---------- History ---------- */

    function toggleHistory() {
        historyPanel.classList.toggle('open');
        renderHistory();
    }

    function startNewChat() {
        messagesEl.innerHTML = '';
        messageHistory = [];
        activeToolCalls.clear();
        currentSessionId = Date.now().toString();
        saveSession();
        vscode.postMessage({ type: 'clearChat' });
        historyPanel.classList.remove('open');
    }

    function clearChat() {
        messagesEl.innerHTML = '';
        messageHistory = [];
        activeToolCalls.clear();
        saveSession();
        vscode.postMessage({ type: 'clearChat' });
    }

    function getHistory() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch { return []; }
    }

    function saveHistory(history) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 50)));
    }

    function saveSession() {
        if (messageHistory.length === 0) return;
        const history = getHistory();
        const title = messageHistory[0].text.substring(0, 40) || 'New Chat';
        const idx = history.findIndex(h => h.id === currentSessionId);
        const session = {
            id: currentSessionId,
            title,
            timestamp: Date.now(),
            messages: messageHistory.slice()
        };
        if (idx >= 0) history[idx] = session;
        else history.unshift(session);
        saveHistory(history);
    }

    function loadSession() {
        // Try to restore from state (if webview was hidden)
        const state = vscode.getState();
        if (state && state.messages) {
            messageHistory = state.messages;
            currentSessionId = state.sessionId || currentSessionId;
            renderMessages();
            return;
        }
        // Otherwise start fresh
    }

    function renderMessages() {
        messagesEl.innerHTML = '';
        messageHistory.forEach(m => {
            addMessage(m.role, m.text, m.toolCalls, m.durationMs);
        });
    }

    function renderHistory() {
        const history = getHistory();
        historyList.innerHTML = '';
        if (history.length === 0) {
            historyList.innerHTML = '<div class="history-empty">No history yet</div>';
            return;
        }
        history.forEach(h => {
            const item = document.createElement('div');
            item.className = 'history-item' + (h.id === currentSessionId ? ' active' : '');
            item.textContent = h.title || 'Untitled';
            item.title = new Date(h.timestamp).toLocaleString();
            item.addEventListener('click', () => loadHistorySession(h.id));
            historyList.appendChild(item);
        });
    }

    function loadHistorySession(sessionId) {
        const history = getHistory();
        const session = history.find(h => h.id === sessionId);
        if (!session) return;
        currentSessionId = sessionId;
        messageHistory = session.messages || [];
        renderMessages();
        historyPanel.classList.remove('open');
        vscode.setState({ messages: messageHistory, sessionId: currentSessionId });
    }

    /* ---------- Utilities ---------- */

    function scrollToBottom() {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function formatMarkdown(text) {
        if (!text) return '';
        if (typeof marked !== 'undefined') {
            try {
                const raw = marked.parse(text, { gfm: true, breaks: false });
                // Basic sanitization: strip <script> and event handlers
                return raw
                    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                    .replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '');
            } catch {
                return escapeHtml(text).replace(/\n/g, '<br>');
            }
        }
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatTodoList(todos) {
        if (!todos || todos.length === 0) {
            return '<em>No items</em>';
        }
        const statusIcons = {
            pending: '⏳',
            in_progress: '🔄',
            done: '✅',
            blocked: '🚫',
        };
        const statusClasses = {
            pending: 'todo-pending',
            in_progress: 'todo-in-progress',
            done: 'todo-done',
            blocked: 'todo-blocked',
        };

        // Progress summary
        const counts = { done: 0, in_progress: 0, pending: 0, blocked: 0 };
        for (const t of todos) {
            const s = t.status || 'pending';
            if (counts.hasOwnProperty(s)) counts[s]++;
        }
        const total = todos.length;
        const parts = [];
        if (counts.done) parts.push(`${counts.done}/${total} done`);
        if (counts.in_progress) parts.push(`${counts.in_progress} in progress`);
        if (counts.pending) parts.push(`${counts.pending} pending`);
        if (counts.blocked) parts.push(`${counts.blocked} blocked`);
        const summaryText = parts.length ? parts.join(' · ') : `${total} pending`;

        let html = `<div class="todo-summary">${summaryText}</div>`;
        html += '<ul class="todo-list">';
        for (let i = 0; i < todos.length; i++) {
            const t = todos[i];
            const status = t.status || 'pending';
            const icon = statusIcons[status] || '⏳';
            const cls = statusClasses[status] || 'todo-pending';
            html += `<li class="todo-item ${cls}"><span class="todo-icon">${icon}</span> <span class="todo-text">${escapeHtml(t.item || '')}</span></li>`;
        }
        html += '</ul>';
        return html;
    }

    function formatTaskPlan(plan) {
        if (!plan || typeof plan !== 'object') {
            return '<em>No plan data</em>';
        }
        const statusIcons = {
            pending: '⏳',
            active: '🔄',
            done: '✅',
        };
        const statusClasses = {
            pending: 'plan-phase-pending',
            active: 'plan-phase-active',
            done: 'plan-phase-done',
        };
        let html = '<div class="task-plan">';

        // Header
        const designType = plan.design_type || 'custom';
        const goal = plan.goal || '';
        html += `<div class="plan-header">📋 <strong>${escapeHtml(designType.toUpperCase())}</strong>`;
        if (goal) {
            html += ` — ${escapeHtml(goal)}`;
        }
        html += '</div>';

        // Phases
        const phases = plan.phases || [];
        if (phases.length > 0) {
            html += '<div class="plan-phases">';
            for (let i = 0; i < phases.length; i++) {
                const p = phases[i];
                const status = p.status || 'pending';
                const icon = statusIcons[status] || '⏳';
                const cls = statusClasses[status] || 'plan-phase-pending';
                const tools = (p.suggested_tools || []).join(', ');
                html += `
                    <div class="plan-phase ${cls}">
                        <div class="plan-phase-header">
                            <span class="plan-phase-icon">${icon}</span>
                            <span class="plan-phase-name">${p.index || i + 1}. ${escapeHtml(p.phase || '')}</span>
                        </div>
                        <div class="plan-phase-desc">${escapeHtml(p.description || '')}</div>
                        ${tools ? `<div class="plan-phase-tools">🛠 ${escapeHtml(tools)}</div>` : ''}
                    </div>`;
            }
            html += '</div>';
        }

        // Recommended first steps
        const steps = plan.recommended_first_steps || [];
        if (steps.length > 0) {
            html += '<div class="plan-steps"><strong>Recommended first steps:</strong><ul>';
            for (const step of steps) {
                html += `<li>${escapeHtml(step)}</li>`;
            }
            html += '</ul></div>';
        }

        // Key metrics
        const metrics = plan.key_metrics || [];
        if (metrics.length > 0) {
            html += '<div class="plan-metrics"><strong>Key metrics:</strong> ' + metrics.map(m => escapeHtml(m)).join(' · ') + '</div>';
        }

        html += '</div>';
        return html;
    }

    /* ---------- Message Router ---------- */

    window.addEventListener('message', (event) => {
        const msg = event.data;
        switch (msg.type) {
            case 'addMessage':
                addMessage(msg.role, msg.text, msg.toolCalls, msg.durationMs);
                break;
            case 'token':
                appendToken(msg.text);
                break;
            case 'assistant':
                finalizeStream(msg.text, msg.toolCalls, msg.durationMs);
                showThinking(false);
                showStopButton(false);
                setInputEnabled(true);
                processQueue();
                break;
            case 'thinking':
                showThinking(msg.thinking);
                break;
            case 'status':
                updateStatus(msg.status, msg.error);
                if (msg.status === 'ready') {
                    setInputEnabled(true);
                    showStopButton(false);
                }
                if (msg.status === 'thinking') {
                    showThinking(true);
                } else if (msg.status === 'thinking_stop') {
                    showThinking(false);
                }
                break;
            case 'toolStart':
                {
                    // Model switched from thinking to executing tools
                    showThinking(false);
                    let tcId = String(msg.toolCallId || '');

                    // If the backend didn't provide a toolCallId, generate a
                    // deterministic synthetic one based on tool name + round + iteration
                    // so that toolStart and toolComplete use the SAME id.
                    if (!tcId) {
                        tcId = `tc-${msg.tool || 'tool'}-r${msg.toolRound || 0}-i${msg.iteration || 0}-n${activeToolCalls.size}`;
                    }

                    // Backend may send tool_call twice (once during streaming,
                    // once during execution). If we already have a card for this
                    // id, just update its metadata instead of creating a duplicate.
                    if (activeToolCalls.has(tcId)) {
                        const existing = activeToolCalls.get(tcId);
                        // Update summary if now available
                        if (msg.summary) {
                            const header = existing.querySelector('.tool-call-header');
                            const oldSummary = header.querySelector('.tool-summary');
                            if (oldSummary) {
                                oldSummary.textContent = `— ${escapeHtml(msg.summary)}`;
                            } else {
                                const span = document.createElement('span');
                                span.className = 'tool-summary';
                                span.innerHTML = ` — ${escapeHtml(msg.summary)}`;
                                header.appendChild(span);
                            }
                        }
                        if (msg.toolRound > 0 && msg.maxToolRounds > 0) {
                            const header = existing.querySelector('.tool-call-header');
                            const oldBadge = header.querySelector('.tool-round-badge');
                            if (!oldBadge) {
                                const span = document.createElement('span');
                                span.className = 'tool-round-badge';
                                span.textContent = `Round ${msg.toolRound}/${msg.maxToolRounds}`;
                                header.appendChild(span);
                            }
                        }
                        // Update timeout display
                        if (msg.timeout > 0) {
                            const header = existing.querySelector('.tool-call-header');
                            const oldTimeout = header.querySelector('.tool-timeout');
                            if (!oldTimeout) {
                                const span = document.createElement('span');
                                span.className = 'tool-timeout';
                                span.textContent = `⏱ ${msg.timeout}s`;
                                header.appendChild(span);
                            }
                        }
                        break;
                    }

                    const tc = {
                        id: msg.toolCallId,
                        tool: msg.tool,
                        args: msg.args,
                        summary: msg.summary,
                        reason: msg.reason,
                        toolRound: msg.toolRound,
                        maxToolRounds: msg.maxToolRounds,
                        timeout: msg.timeout,
                    };
                    const toolDiv = createToolCallElement(tc);
                    let container = currentStreamMsgDiv || currentTurnMsgDiv;
                    if (!container) {
                        container = addMessage('assistant', '', [], null);
                        currentTurnMsgDiv = container;
                    }
                    container.appendChild(toolDiv);
                    activeToolCalls.set(tcId, toolDiv);
                }
                break;
            case 'toolProgress':
                updateToolProgress(msg.toolCallId, msg.data);
                break;
            case 'toolResult':
                if (msg.result?.needsPermission) {
                    showPermissionDialog(msg.result.permissionType, msg.result.tool, msg.result.error || msg.result.path);
                }
                updateToolResult(msg.toolCallId, msg.success, msg.result, msg.durationMs, msg.tool);
                break;
            case 'toolComplete':
                {
                    // Agent-streamed tool completion (chat flow)
                    const isSuccess = !msg.isError;
                    updateToolResult(msg.toolCallId, isSuccess, msg.result, msg.durationMs, msg.tool);
                }
                break;
            case 'stopped':
                showStopButton(false);
                setInputEnabled(true);
                showThinking(false);
                isThinking = false;
                // Add a system message to indicate cancellation
                if (currentStreamMsgDiv) {
                    finalizeStream('⏹️ 已取消', [], null);
                }
                addMessage('system', '⏹️ 操作已取消。', [], null);
                break;
            case 'phase':
                updatePhaseIndicator(msg.phase);
                break;
            case 'planUpdate':
                renderPlanPanel(msg.plan);
                break;
            case 'permissionGranted':
                hidePermissionDialog();
                break;
            case 'budgetWarning':
                showBudgetWarning(msg.usageRatio, msg.currentTokens, msg.availableTokens);
                break;
            case 'compaction':
                showCompaction(msg.tokensSaved, msg.originalCount, msg.compactedCount);
                break;
            case 'contextBudget':
                showContextBudget(msg.budget);
                break;
            case 'compactionResult':
                if (msg.result?.success) {
                    showCompaction(msg.result.tokensSaved, msg.result.originalCount, msg.result.compactedCount);
                } else {
                    const div = document.createElement('div');
                    div.className = 'message system';
                    div.innerHTML = `<div class="message-content" style="font-size:11px;color:var(--vscode-testing-iconFailed)">Compaction failed: ${escapeHtml(msg.result?.error || '')}</div>`;
                    messagesEl.appendChild(div);
                    scrollToBottom();
                }
                break;
            case 'editResult':
                const editDiv = document.createElement('div');
                editDiv.className = 'message system';
                const color = msg.success ? 'var(--vscode-testing-iconPassed)' : 'var(--vscode-testing-iconFailed)';
                editDiv.innerHTML = `<div class="message-content" style="font-size:11px;color:${color}">${escapeHtml(msg.message)}</div>`;
                messagesEl.appendChild(editDiv);
                scrollToBottom();
                break;
            case 'clearChat':
                messagesEl.innerHTML = '';
                messageHistory = [];
                activeToolCalls.clear();
                break;
            case 'designState':
                updateDesignState(msg.state);
                break;
        }
    });

    function showBudgetWarning(usageRatio, currentTokens, availableTokens) {
        const div = document.createElement('div');
        div.className = 'message system';
        const pct = Math.round(usageRatio * 100);
        div.innerHTML = `<div class="message-content" style="font-size:11px;color:var(--vscode-editorWarning-foreground)">
            ⚠️ Context budget: ${pct}% used (${currentTokens}/${availableTokens} tokens). Compaction recommended.
        </div>`;
        messagesEl.appendChild(div);
        scrollToBottom();
    }

    function showCompaction(tokensSaved, originalCount, compactedCount) {
        const div = document.createElement('div');
        div.className = 'message system';
        div.innerHTML = `<div class="message-content" style="font-size:11px;color:var(--vscode-testing-iconPassed)">
            ♻️ Context compacted: ${originalCount} → ${compactedCount} messages, saved ${tokensSaved} tokens
        </div>`;
        messagesEl.appendChild(div);
        scrollToBottom();
    }

    function showContextBudget(budget) {
        currentBudget = budget;
        const div = document.createElement('div');
        div.className = 'message system';
        const pct = Math.round((budget.usage_ratio || 0) * 100);
        const color = pct > 80 ? 'var(--vscode-testing-iconFailed)' : (pct > 60 ? 'var(--vscode-editorWarning-foreground)' : 'var(--vscode-testing-iconPassed)');
        div.innerHTML = `<div class="message-content" style="font-size:11px;color:${color}">
            📊 Context Budget: ${pct}% used<br>
            Current: ${budget.current_tokens} / Available: ${budget.available_tokens} tokens<br>
            Messages: ${budget.message_count} | Compactions: ${budget.compaction_count}
        </div>`;
        messagesEl.appendChild(div);
        scrollToBottom();
    }

    init();
})();
