import * as vscode from 'vscode';
import * as path from 'path';
import { EDAAgentServer, ServerMessage } from './server';

/**
 * Webview view provider for the EDA Agent chat panel.
 */
export class ChatViewProvider implements vscode.WebviewViewProvider {
    private view?: vscode.WebviewView;
    private disposables: vscode.Disposable[] = [];
    private outputChannel: vscode.OutputChannel;

    constructor(
        private readonly extensionUri: vscode.Uri,
        private readonly server: EDAAgentServer
    ) {
        this.outputChannel = vscode.window.createOutputChannel('EDA Agent');
    }

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ): void {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };
        webviewView.webview.html = this.getHtml(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(
            async (message) => {
                this.log('debug', `Webview msg: ${message.type}`);
                switch (message.type) {
                    case 'sendMessage':
                        await this.handleUserMessage(message.text);
                        break;
                    case 'stop':
                        await vscode.commands.executeCommand('eda-agent.stopThinking');
                        break;
                    case 'restart':
                        await vscode.commands.executeCommand('eda-agent.restartAgent');
                        break;
                    case 'clearChat':
                        this.clearChat();
                        break;
                    case 'getContextBudget':
                        this.server.sendMessage({ type: 'get_context_budget' });
                        break;
                    case 'compactContext':
                        this.server.sendMessage({ type: 'compact_context' });
                        break;
                    case 'openFile':
                        if (message.filePath) {
                            try {
                                const doc = await vscode.workspace.openTextDocument(message.filePath);
                                await vscode.window.showTextDocument(doc);
                            } catch (err: any) {
                                vscode.window.showErrorMessage(`Cannot open file: ${err.message}`);
                            }
                        }
                        break;
                    case 'applyEdit':
                        await this.handleApplyEdit(message);
                        break;
                    case 'runCommand':
                        if (message.command) {
                            const terminal = vscode.window.activeTerminal || vscode.window.createTerminal('EDA Agent');
                            terminal.show();
                            terminal.sendText(message.command);
                        }
                        break;
                }
            },
            undefined,
            this.disposables
        );

        const serverDisposable = this.server.onMessage((msg) => {
            this.handleServerMessage(msg);
        });
        this.disposables.push(serverDisposable);

        webviewView.onDidDispose(() => {
            this.disposables.forEach(d => d.dispose());
            this.disposables = [];
        });
    }

    postMessage(message: any): void {
        this.view?.webview.postMessage(message);
    }

    clearChat(): void {
        this.postMessage({ type: 'clearChat' });
    }

    private async handleUserMessage(text: string): Promise<void> {
        this.postMessage({ type: 'addMessage', role: 'user', text });
        this.postMessage({ type: 'thinking', thinking: true });
        try {
            this.server.sendMessage({ type: 'chat', text });
        } catch (err: any) {
            this.postMessage({
                type: 'addMessage',
                role: 'assistant',
                text: `Failed to send message: ${err.message}`
            });
            this.postMessage({ type: 'thinking', thinking: false });
        }
    }

    private handleServerMessage(msg: ServerMessage): void {
        switch (msg.type) {
            case 'assistant':
                this.postMessage({
                    type: 'assistant',
                    text: msg.text || '',
                    toolCalls: msg.toolCalls,
                    durationMs: msg.durationMs,
                });
                this.postMessage({ type: 'thinking', thinking: false });
                this.log('info', `Assistant reply (${msg.durationMs || '?'}ms): ${msg.text?.substring(0, 100)}...`);
                break;

            case 'tool_start':
                this.postMessage({ type: 'toolStart', tool: msg.tool, args: msg.args, toolCallId: msg.toolCallId, iteration: msg.iteration, summary: msg.summary, reason: msg.reason, toolRound: msg.toolRound, maxToolRounds: msg.maxToolRounds, timeout: msg.timeout });
                this.log('info', `Tool start: ${msg.tool}`);
                break;

            case 'tool_progress':
                this.postMessage({ type: 'toolProgress', tool: msg.tool, data: msg.data, toolCallId: msg.toolCallId, iteration: msg.iteration });
                break;

            case 'tool_result':
                this.postMessage({
                    type: 'toolResult',
                    tool: msg.tool,
                    result: msg.result,
                    success: msg.success !== false,
                    durationMs: msg.durationMs,
                    toolCallId: msg.toolCallId,
                });
                this.log('info', `Tool result: ${msg.tool} (success=${msg.success !== false}, ${msg.durationMs || '?'}ms)`);
                break;

            case 'tool_complete':
                this.postMessage({
                    type: 'toolComplete',
                    tool: msg.tool,
                    result: msg.result,
                    toolCallId: msg.toolCallId,
                    iteration: msg.iteration,
                    isError: msg.isError,
                    durationMs: msg.durationMs,
                });
                this.log('info', `Tool complete: ${msg.tool} (error=${msg.isError})`);
                break;

            case 'phase':
                this.postMessage({
                    type: 'phase',
                    phase: msg.phase,
                });
                this.log('info', `Phase: ${msg.phase}`);
                break;

            case 'stopped':
                this.postMessage({
                    type: 'stopped',
                });
                this.log('info', 'Agent stopped by user');
                break;

            case 'plan_update':
                this.postMessage({
                    type: 'planUpdate',
                    plan: msg.plan,
                });
                this.log('info', `Plan updated: ${msg.plan?.phases?.length || 0} phases`);
                break;

            case 'permissionGranted':
                this.postMessage({
                    type: 'permissionGranted',
                    permissionType: msg.permissionType,
                    scope: msg.scope,
                });
                break;

            case 'token':
                this.postMessage({ type: 'token', text: msg.text });
                break;

            case 'design_state':
                this.postMessage({ type: 'designState', state: msg.state });
                break;

            case 'status':
                this.postMessage({ type: 'status', status: msg.status, error: msg.error });
                if (msg.status === 'thinking') {
                    this.postMessage({ type: 'thinking', thinking: true, iteration: msg.iteration });
                } else if (msg.status === 'thinking_stop') {
                    this.postMessage({ type: 'thinking', thinking: false });
                }
                this.log('info', `Status: ${msg.status}`);
                break;

            case 'budget_warning':
                this.postMessage({
                    type: 'budgetWarning',
                    usageRatio: msg.usageRatio,
                    currentTokens: msg.currentTokens,
                    availableTokens: msg.availableTokens,
                });
                break;

            case 'compaction':
                this.postMessage({
                    type: 'compaction',
                    tokensSaved: msg.tokensSaved,
                    originalCount: msg.originalCount,
                    compactedCount: msg.compactedCount,
                });
                break;

            case 'context_budget':
                this.postMessage({ type: 'contextBudget', budget: msg.budget });
                break;

            case 'compaction_result':
                this.postMessage({ type: 'compactionResult', result: msg.result });
                break;

            case 'file_updated':
                this.handleFileUpdated(msg);
                break;

            case 'stdout':
                this.log('debug', `[PY stdout] ${msg.text?.substring(0, 200)}`);
                break;

            case 'stderr':
                this.log('debug', `[PY stderr] ${msg.text?.substring(0, 200)}`);
                break;

            case 'error':
                this.postMessage({ type: 'addMessage', role: 'assistant', text: `⚠️ Error: ${msg.error}` });
                this.postMessage({ type: 'thinking', thinking: false });
                this.postMessage({ type: 'status', status: 'ready' });
                this.log('error', `Server error: ${msg.error}`);
                if (msg.traceback) this.outputChannel.appendLine(msg.traceback);
                break;
        }
    }

    private handleFileUpdated(msg: ServerMessage): void {
        const filePath = msg.filePath as string;
        if (!filePath) return;
        const doc = vscode.workspace.textDocuments.find(d => d.uri.fsPath === filePath);
        if (doc) {
            vscode.window.showInformationMessage(
                `EDA Agent modified: ${path.basename(filePath)}`,
                'Show Diff'
            ).then(selection => {
                if (selection === 'Show Diff') {
                    vscode.commands.executeCommand('vscode.open', vscode.Uri.file(filePath));
                }
            });
        }
        this.log('info', `File updated: ${filePath}`);
    }

    private async handleApplyEdit(message: any): Promise<void> {
        const { filePath, oldString, newString } = message;
        if (!filePath || oldString === undefined || newString === undefined) return;
        const uri = vscode.Uri.file(filePath);
        try {
            const document = await vscode.workspace.openTextDocument(uri);
            const content = document.getText();
            if (!content.includes(oldString)) {
                this.postMessage({ type: 'editResult', success: false, message: 'Old string not found in file' });
                return;
            }
            const edit = new vscode.WorkspaceEdit();
            const fullRange = new vscode.Range(document.positionAt(0), document.positionAt(content.length));
            const newContent = content.replace(oldString, newString);
            edit.replace(uri, fullRange, newContent);
            const success = await vscode.workspace.applyEdit(edit);
            if (success) await document.save();
            this.postMessage({ type: 'editResult', success, message: success ? 'Edit applied successfully' : 'Failed to apply edit' });
            this.log('info', `Edit applied: ${filePath}`);
        } catch (err: any) {
            this.postMessage({ type: 'editResult', success: false, message: err.message });
            this.log('error', `Edit failed: ${err.message}`);
        }
    }

    private getHtml(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'chat.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'chat.css'));
        const markedUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'marked.min.js'));
        const nonce = this.getNonce();

        // SVG icons
        const iconSend = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M1.5 2a.5.5 0 0 0-.5.5v2a.5.5 0 0 0 .5.5h10.793l-8.147 8.146a.5.5 0 0 0 .708.708L13 5.207V15.5a.5.5 0 0 0 .5.5h2a.5.5 0 0 0 .5-.5v-13a.5.5 0 0 0-.5-.5h-13z"/></svg>`;
        const iconStop = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect width="10" height="10" x="3" y="3" rx="1.5"/></svg>`;
        const iconHistory = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 1a6 6 0 1 1 0 12A6 6 0 0 1 8 2zm-.5 3v4.5l3.5 2 .5-.866-3-1.732V5H7.5z"/></svg>`;
        const iconClear = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M2 3h12v1H2V3zm2 2h8v9H4V5zm2 2v5h4V7H6z"/></svg>`;
        const iconClose = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/></svg>`;
        const iconNewChat = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 2a.5.5 0 0 1 .5.5v5h5a.5.5 0 0 1 0 1h-5v5a.5.5 0 0 1-1 0v-5h-5a.5.5 0 0 1 0-1h5v-5A.5.5 0 0 1 8 2z"/></svg>`;

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} https:; font-src ${webview.cspSource};">
    <link href="${styleUri}" rel="stylesheet">
    <title>EDA Agent</title>
</head>
<body>
    <div id="app">
        <!-- Top Bar -->
        <div class="top-bar">
            <div class="top-bar-title">
                <span class="status-dot" id="status-dot"></span>
                <span>EDA Agent</span>
                <span id="status-text" style="font-size:11px;font-weight:400;color:var(--vscode-descriptionForeground);margin-left:4px;">Initializing...</span>
            </div>
            <div class="top-bar-actions">
                <button id="btn-history" class="icon-btn" title="History">${iconHistory}</button>
                <button id="btn-clear" class="icon-btn" title="Clear Chat">${iconClear}</button>
            </div>
        </div>

        <!-- Messages -->
        <div id="messages" class="messages"></div>

        <!-- Design State Panel (expandable) -->
        <div id="design-state-panel" class="design-state-panel collapsed">
            <div class="design-state-header" id="design-state-header">
                <span class="design-state-arrow">▸</span>
                <span class="design-state-title" id="design-state-title">📁 No active design</span>
            </div>
            <div class="design-state-body" id="design-state-body">
                <div class="design-state-section">
                    <div class="design-state-label">Design</div>
                    <div class="design-state-value" id="ds-design">—</div>
                </div>
                <div class="design-state-section">
                    <div class="design-state-label">Task Progress</div>
                    <div class="design-state-value" id="ds-progress">—</div>
                </div>
                <div class="design-state-section">
                    <div class="design-state-label">Recent Actions</div>
                    <div class="design-state-value" id="ds-actions">—</div>
                </div>
            </div>
        </div>

        <!-- Queue Panel -->
        <div id="queue-bar" class="queue-bar" style="display:none;">
            <div class="queue-header">
                <span id="queue-count">0 queued</span>
                <div style="display:flex;gap:4px;">
                    <button id="btn-queue-toggle" class="queue-btn" title="Expand/Collapse">▾</button>
                    <button id="btn-queue-clear" class="queue-btn">Clear All</button>
                </div>
            </div>
            <div id="queue-list" class="queue-list" style="display:none;"></div>
        </div>

        <!-- Input -->
        <div id="input-area" class="input-area">
            <textarea id="message-input" placeholder="Ask EDA Agent anything..." rows="1"></textarea>
            <button id="btn-send" class="send-btn" title="Send">${iconSend}</button>
            <button id="btn-stop" class="stop-btn" style="display:none;" title="Stop">${iconStop}</button>
        </div>
        <div class="input-hint">Enter to send · Shift+Enter for new line · Ctrl+Enter to queue</div>

        <!-- History Panel -->
        <div id="history-panel" class="history-panel">
            <div class="history-header">
                <span>History</span>
                <div style="display:flex;gap:4px;">
                    <button id="history-new" class="icon-btn" title="New Chat">${iconNewChat}</button>
                    <button id="history-close" class="icon-btn" title="Close">${iconClose}</button>
                </div>
            </div>
            <div id="history-list" class="history-list"></div>
        </div>
    </div>
    <script nonce="${nonce}" src="${markedUri}"></script>
    <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }

    private getNonce(): string {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }

    private log(level: string, message: string): void {
        const time = new Date().toISOString();
        this.outputChannel.appendLine(`[${time}] [${level.toUpperCase()}] ${message}`);
    }
}
