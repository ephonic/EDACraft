import * as vscode from 'vscode';
import { EDAAgentServer } from './server';
import { ChatViewProvider } from './chatView';

let server: EDAAgentServer | undefined;
let chatProvider: ChatViewProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('EDA Agent extension activated');

    const config = vscode.workspace.getConfiguration('eda-agent');

    // Create server manager
    server = new EDAAgentServer(context);

    // Create chat view provider
    chatProvider = new ChatViewProvider(context.extensionUri, server);

    // Register webview view
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('eda-agent.chatView', chatProvider, {
            webviewOptions: { retainContextWhenHidden: true }
        })
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.openChat', () => {
            vscode.commands.executeCommand('eda-agent.chatView.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'eda-agent');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.stopAgent', async () => {
            if (server) {
                await server.stop();
                chatProvider?.postMessage({ type: 'status', status: 'stopped' });
                vscode.window.showInformationMessage('EDA Agent stopped');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.stopThinking', async () => {
            if (server) {
                server.sendMessage({ type: 'stop' });
                chatProvider?.postMessage({ type: 'status', status: 'ready' });
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.restartAgent', async () => {
            if (server) {
                await server.restart();
                chatProvider?.postMessage({ type: 'status', status: 'ready' });
                vscode.window.showInformationMessage('EDA Agent restarted');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.clearChat', () => {
            chatProvider?.clearChat();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('eda-agent.runHarness', async () => {
            const editor = vscode.window.activeTextEditor;
            const document = editor?.document;
            if (!document) {
                vscode.window.showWarningMessage('No active file');
                return;
            }
            const lib = await vscode.window.showInputBox({ prompt: 'Library name' });
            const cell = await vscode.window.showInputBox({ prompt: 'Cell name' });
            if (!lib || !cell) { return; }

            chatProvider?.postMessage({
                type: 'addMessage',
                role: 'user',
                text: `Run circuit harness for ${lib}/${cell}`
            });

            try {
                await server?.sendRequest({
                    type: 'tool_call',
                    tool: 'circuit_harness',
                    args: { lib, cell, checks: ['netlist', 'drc', 'lvs', 'simulation'] }
                }, 300000); // 5min timeout for harness
            } catch (err: any) {
                vscode.window.showErrorMessage(`Harness failed: ${err.message}`);
            }
        })
    );

    // Auto-start if configured
    if (config.get<boolean>('autoStart', true)) {
        server.start().then(() => {
            chatProvider?.postMessage({ type: 'status', status: 'ready' });
        }).catch(err => {
            const errType = err.edaErrorType;
            if (errType === 'missing_deps') {
                // Show a rich message with action buttons for missing dependencies
                const installCmd: string = err.fullCommand;
                const missing: string[] = err.missing || [];
                vscode.window.showErrorMessage(
                    `EDA Agent requires Python packages: ${missing.join(', ')}. ` +
                    `Install them and restart the agent.`,
                    { title: 'Copy Install Command', isCloseAffordance: false },
                    { title: 'Open Settings', isCloseAffordance: false }
                ).then(selection => {
                    if (selection?.title === 'Copy Install Command') {
                        vscode.env.clipboard.writeText(installCmd);
                        vscode.window.showInformationMessage('Install command copied to clipboard!');
                    } else if (selection?.title === 'Open Settings') {
                        vscode.commands.executeCommand('workbench.action.openSettings', 'eda-agent');
                    }
                });
            } else if (errType === 'python_not_found' || (err.message && err.message.includes('ENOENT'))) {
                const tried = err.triedPaths ? err.triedPaths.join(', ') : 'python3, python, py';
                vscode.window.showErrorMessage(
                    `EDA Agent: Python not found (tried: ${tried}). ` +
                    `Please install Python and set the correct path in settings.`,
                    { title: 'Open Settings', isCloseAffordance: false }
                ).then(selection => {
                    if (selection?.title === 'Open Settings') {
                        vscode.commands.executeCommand('workbench.action.openSettings', 'eda-agent');
                    }
                });
            } else {
                vscode.window.showErrorMessage(`Failed to start EDA Agent: ${err.message}`);
            }
            chatProvider?.postMessage({ type: 'status', status: 'error', error: err.message });
        });
    }

    // Listen for configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('eda-agent')) {
                vscode.window.showInformationMessage('EDA Agent: Configuration changed. Please restart the agent.');
            }
        })
    );
}

export function deactivate() {
    server?.stop();
}
