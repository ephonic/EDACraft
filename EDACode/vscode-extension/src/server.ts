import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export interface ServerMessage {
    type: string;
    [key: string]: any;
}

export type ServerMessageHandler = (msg: ServerMessage) => void;

/**
 * Manages the EDAAgent Python backend server.
 *
 * Communication: JSON-RPC over stdio (newline-delimited JSON)
 * Features: heartbeat, auto-restart, structured logging, request-response matching
 */
export class EDAAgentServer {
    private process: cp.ChildProcess | undefined;
    private messageHandlers: ServerMessageHandler[] = [];
    private buffer: string = '';
    private _status: 'idle' | 'starting' | 'ready' | 'error' | 'stopped' = 'idle';
    private outputChannel: vscode.OutputChannel;
    private heartbeatTimer?: NodeJS.Timeout;
    private heartbeatMissed = 0;
    private pendingRequests = new Map<string, { resolve: (msg: ServerMessage) => void; reject: (err: Error) => void }>();

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('EDA Agent');
    }

    get status(): string { return this._status; }

    /** Register a message handler. Returns disposable for cleanup. */
    onMessage(handler: ServerMessageHandler): vscode.Disposable {
        this.messageHandlers.push(handler);
        return {
            dispose: () => {
                const idx = this.messageHandlers.indexOf(handler);
                if (idx >= 0) { this.messageHandlers.splice(idx, 1); }
            }
        };
    }

    /** Write a log line to the Output Channel. */
    private log(level: string, message: string): void {
        const time = new Date().toISOString();
        this.outputChannel.appendLine(`[${time}] [${level.toUpperCase()}] ${message}`);
    }

    async start(): Promise<void> {
        if (this._status === 'starting' || this._status === 'ready') {
            this.log('warn', 'Server already starting or running');
            return;
        }
        this._status = 'starting';
        this.log('info', 'Starting EDAAgent server...');

        const config = vscode.workspace.getConfiguration('eda-agent');
        let pythonPath = config.get<string>('pythonPath', 'python3');
        const provider = config.get<string>('provider', 'openai');
        const model = config.get<string>('model', 'gpt-4o');
        const apiKey = config.get<string>('apiKey', '');
        const baseUrl = config.get<string>('baseUrl', '');
        const projectRoot = config.get<string>('projectRoot', '') || this.getWorkspaceRoot();

        this.log('info', `Config: provider=${provider}, model=${model}, root=${projectRoot}`);

        this.log('info', `Configured pythonPath: ${pythonPath}`);

        // Find bundled Python backend source inside the VSIX extension.
        // In the VSIX, source is at extension/python/eda_agent/ (package root).
        const extPath = this.context.extensionUri.fsPath;
        const bundledPythonPaths = [
            path.join(extPath, 'python', 'eda_agent'),          // VSIX packaged
            path.join(extPath, 'out', 'python', 'eda_agent'),   // Alternative location
            path.join(extPath, '..', 'src', 'eda_agent'),       // Dev mode (workspace)
            path.join(extPath, '..', '..', 'src', 'eda_agent'), // Dev mode (nested)
        ];

        let pythonModulePath: string | undefined;
        for (const p of bundledPythonPaths) {
            if (await this.fileExists(path.join(p, '__init__.py'))) {
                pythonModulePath = p;
                break;
            }
        }

        // Determine site-packages dir inside the extension (for auto-installing deps)
        const bundledSitePackages = pythonModulePath
            ? path.join(path.dirname(pythonModulePath), 'site-packages')
            : undefined;

        // Find Python backend script (entry point)
        const scriptCandidates = [
            path.join(extPath, 'python', 'eda_agent', 'server', 'vscode_server.py'),
            path.join(extPath, 'out', 'python', 'eda_agent', 'server', 'vscode_server.py'),
            path.join(extPath, '..', 'src', 'eda_agent', 'server', 'vscode_server.py'),
            path.join(extPath, '..', '..', 'src', 'eda_agent', 'server', 'vscode_server.py'),
        ];

        let scriptPath: string | undefined;
        for (const c of scriptCandidates) {
            if (await this.fileExists(c)) {
                scriptPath = c;
                break;
            }
        }

        // Auto-install third-party Python deps if missing.
        // We install into extension/python/site-packages so each user gets
        // deps matched to their local Python version & platform.
        if (bundledSitePackages) {
            const depsOk = await this.ensurePythonDependencies(pythonPath, bundledSitePackages);
            if (!depsOk) {
                this._status = 'error';
                const err = new Error(
                    `Failed to install Python dependencies. ` +
                    `Please run: ${pythonPath} -m pip install pydantic openai anthropic rich prompt-toolkit jsonschema`
                );
                (err as any).edaErrorType = 'missing_deps';
                throw err;
            }
        }

        // Sanitize env: filter out undefined values to avoid Node.js spawn issues
        const env: NodeJS.ProcessEnv = {};
        for (const [k, v] of Object.entries(process.env)) {
            if (v !== undefined) { env[k] = v; }
        }

        // Ensure cwd exists — spawn ENOENT can also mean cwd is missing
        let cwd = projectRoot;
        try {
            await vscode.workspace.fs.stat(vscode.Uri.file(cwd));
        } catch {
            cwd = process.cwd();
            this.log('warn', `projectRoot ${projectRoot} not accessible, falling back to cwd: ${cwd}`);
        }

        // Set PYTHONPATH so bundled eda_agent + third-party deps can be imported.
        // Structure inside VSIX:
        //   extension/python/eda_agent/     <- our source
        //   extension/python/site-packages/    <- auto-installed pydantic, openai, etc.
        if (pythonModulePath) {
            const pythonDir = path.dirname(pythonModulePath); // e.g. .../extension/python
            const sitePackagesDir = path.join(pythonDir, 'site-packages');
            const paths: string[] = [pythonDir];

            // Include bundled site-packages if they exist
            if (await this.fileExists(sitePackagesDir)) {
                paths.push(sitePackagesDir);
                this.log('info', `Bundled site-packages found: ${sitePackagesDir}`);
            }

            const existingPythonPath = env.PYTHONPATH || '';
            env.PYTHONPATH = existingPythonPath
                ? `${paths.join(path.delimiter)}${path.delimiter}${existingPythonPath}`
                : paths.join(path.delimiter);
            this.log('info', `PYTHONPATH set to: ${env.PYTHONPATH}`);
        } else {
            this.log('warn', 'Bundled Python backend not found. Will rely on pip-installed eda-agent.');
        }

        if (apiKey) {
            if (provider === 'anthropic') { env.ANTHROPIC_API_KEY = apiKey; }
            else { env.OPENAI_API_KEY = apiKey; }
        }

        const args: string[] = [];
        if (scriptPath) {
            args.push(scriptPath);
            this.log('info', `Using server script: ${scriptPath}`);
        } else if (pythonModulePath) {
            // Use module mode with PYTHONPATH pointing to bundled source
            args.push('-m', 'eda_agent.server.vscode_server');
            this.log('info', 'Using bundled module mode: eda_agent.server.vscode_server');
        } else {
            // Last resort: assume pip-installed
            args.push('-m', 'eda_agent.server.vscode_server');
            this.log('info', 'Using pip-installed module mode: eda_agent.server.vscode_server');
        }

        args.push('--transport', 'stdio');
        args.push('--provider', provider);
        args.push('--model', model);
        args.push('--project-root', projectRoot);
        args.push('--max-iterations', String(config.get<number>('maxIterations', 50)));
        if (apiKey) { args.push('--api-key', apiKey); }
        if (baseUrl) { args.push('--base-url', baseUrl); }

        return new Promise((resolve, reject) => {
            // Build fallback candidate list (de-duplicate)
            const configured = config.get<string>('pythonPath', 'python3');
            const allCandidates = [configured, 'python3', 'python', 'py'];
            const candidates = allCandidates.filter((v, i, a) => a.indexOf(v) === i);

            const attemptSpawn = (index: number) => {
                if (index >= candidates.length) {
                    const tried = candidates.join(', ');
                    const err = new Error(
                        `Python not found. Tried: ${tried}. ` +
                        `Please install Python and set the correct path in EDA Agent settings.`
                    );
                    (err as any).edaErrorType = 'python_not_found';
                    (err as any).triedPaths = candidates;
                    this._status = 'error';
                    this.log('error', err.message);
                    reject(err);
                    return;
                }

                const py = candidates[index];
                this.log('info', `Spawning: ${py} ${args.join(' ')}`);

                let proc: cp.ChildProcess;
                try {
                    proc = cp.spawn(py, args, {
                        env,
                        cwd,
                        stdio: ['pipe', 'pipe', 'pipe']
                    });
                } catch (spawnErr: any) {
                    this.log('warn', `Sync spawn throw for ${py}: ${spawnErr?.message || spawnErr}`);
                    if (index < candidates.length - 1) {
                        setTimeout(() => attemptSpawn(index + 1), 50);
                    } else {
                        this._status = 'error';
                        reject(spawnErr);
                    }
                    return;
                }
                this.process = proc;

                this.process.stdout?.on('data', (data: Buffer) => {
                    this.handleStdout(data.toString());
                });

                this.process.stderr?.on('data', (data: Buffer) => {
                    const text = data.toString().trim();
                    if (text) {
                        try {
                            const logEntry = JSON.parse(text);
                            this.log(logEntry.level || 'info', `[PY] ${logEntry.message}`);
                        } catch {
                            this.log('stderr', text);
                        }
                        this.notifyHandlers({ type: 'stderr', text });
                    }
                });

                this.process.on('error', (err: any) => {
                    const isENOENT = err && (
                        err.code === 'ENOENT' ||
                        (typeof err.message === 'string' && err.message.includes('ENOENT')) ||
                        (typeof err === 'string' && err.includes('ENOENT'))
                    );
                    this.log('warn', `Spawn error for ${py}: code=${err?.code}, msg=${err?.message}, isENOENT=${isENOENT}`);
                    if (isENOENT && index < candidates.length - 1) {
                        this.log('warn', `${py} not found, trying fallback ${candidates[index + 1]}...`);
                        setTimeout(() => attemptSpawn(index + 1), 50);
                    } else {
                        this._status = 'error';
                        this.log('error', `Process error: ${err?.message || err}`);
                        reject(err);
                    }
                });

                this.process.on('exit', (code, signal) => {
                    this.stopHeartbeat();
                    if (code !== 0 && code !== null) {
                        this._status = 'error';
                        this.log('error', `Process exited with code ${code}, signal ${signal}`);
                        this.notifyHandlers({ type: 'status', status: 'error', exitCode: code });
                    } else {
                        this._status = 'stopped';
                        this.log('info', 'Process stopped');
                    }
                });
            };

            attemptSpawn(0);

            // Wait for ready signal
            const checkReady = setInterval(() => {
                if (this._status === 'ready') {
                    clearInterval(checkReady);
                    this.startHeartbeat();
                    resolve();
                } else if (this._status === 'error') {
                    clearInterval(checkReady);
                    reject(new Error('Server failed to start'));
                }
            }, 100);

            setTimeout(() => {
                clearInterval(checkReady);
                if (this._status !== 'ready') {
                    this.stop();
                    reject(new Error('Server startup timeout (30s)'));
                }
            }, 30000);
        });
    }

    async stop(): Promise<void> {
        this.stopHeartbeat();
        if (this.process && !this.process.killed) {
            this.log('info', 'Sending shutdown request...');
            this.sendMessage({ type: 'shutdown' });
            await this.sleep(500);
            this.process.kill('SIGTERM');
            await this.sleep(1000);
            if (!this.process.killed) {
                this.log('warn', 'Force killing process');
                this.process.kill('SIGKILL');
            }
        }
        this.process = undefined;
        this._status = 'stopped';
        this.pendingRequests.clear();
        this.log('info', 'Server stopped');
    }

    async restart(): Promise<void> {
        this.log('info', 'Restarting server...');
        await this.stop();
        await this.start();
    }

    /** Send a one-way message to the backend. */
    sendMessage(msg: ServerMessage): void {
        if (this.process?.stdin?.writable) {
            const line = JSON.stringify(msg) + '\n';
            this.process.stdin.write(line);
            this.log('debug', `Send: ${msg.type}`);
        } else {
            this.log('warn', `Cannot send ${msg.type}: stdin not writable`);
        }
    }

    /** Send a request and wait for matching response (by requestId). */
    async sendRequest(msg: ServerMessage, timeoutMs: number = 60000): Promise<ServerMessage> {
        return new Promise((resolve, reject) => {
            const requestId = this.generateId();
            const req = { ...msg, requestId };

            const handler = (response: ServerMessage) => {
                if (response.requestId === requestId) {
                    dispose.dispose();
                    this.pendingRequests.delete(requestId);
                    if (response.type === 'error') {
                        reject(new Error(response.error || 'Request failed'));
                    } else {
                        resolve(response);
                    }
                }
            };
            const dispose = this.onMessage(handler);
            this.pendingRequests.set(requestId, { resolve, reject });
            this.sendMessage(req);

            setTimeout(() => {
                if (this.pendingRequests.has(requestId)) {
                    dispose.dispose();
                    this.pendingRequests.delete(requestId);
                    reject(new Error(`Request timeout (${timeoutMs}ms)`));
                }
            }, timeoutMs);
        });
    }

    private handleStdout(chunk: string): void {
        this.buffer += chunk;
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() || '';

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) { continue; }
            try {
                const msg = JSON.parse(trimmed);
                this.handleMessage(msg);
            } catch {
                this.log('debug', `Non-JSON stdout: ${trimmed.substring(0, 200)}`);
                this.notifyHandlers({ type: 'stdout', text: trimmed });
            }
        }
    }

    private handleMessage(msg: ServerMessage): void {
        // Handle internal messages
        if (msg.type === 'ready') {
            this._status = 'ready';
            this.log('info', `Server ready (projectRoot: ${msg.projectRoot})`);
        } else if (msg.type === 'pong') {
            this.heartbeatMissed = 0;
            return; // Don't broadcast pong
        }

        // Resolve pending requests
        if (msg.requestId && this.pendingRequests.has(msg.requestId)) {
            const { resolve } = this.pendingRequests.get(msg.requestId)!;
            resolve(msg);
            this.pendingRequests.delete(msg.requestId);
        }

        this.notifyHandlers(msg);
    }

    private notifyHandlers(msg: ServerMessage): void {
        for (const h of this.messageHandlers) {
            try { h(msg); } catch (e: any) { this.log('error', `Handler error: ${e.message}`); }
        }
    }

    /** Start heartbeat to detect dead connections. */
    private startHeartbeat(): void {
        this.stopHeartbeat();
        this.heartbeatMissed = 0;
        this.heartbeatTimer = setInterval(async () => {
            if (this._status !== 'ready') { return; }
            try {
                await this.sendRequest({ type: 'ping' }, 10000);
            } catch {
                this.heartbeatMissed++;
                this.log('warn', `Heartbeat missed #${this.heartbeatMissed}`);
                if (this.heartbeatMissed >= 3) {
                    this.log('error', 'Connection lost, attempting auto-restart');
                    this._status = 'error';
                    this.notifyHandlers({ type: 'status', status: 'error', error: 'Connection lost (heartbeat timeout). Attempting auto-restart...' });
                    this.stopHeartbeat();
                    try {
                        await this.restart();
                        this.notifyHandlers({ type: 'status', status: 'ready', message: 'Auto-restart successful' });
                    } catch (restartErr: any) {
                        this.log('error', `Auto-restart failed: ${restartErr?.message || restartErr}`);
                        this.notifyHandlers({ type: 'status', status: 'error', error: `Auto-restart failed: ${restartErr?.message || restartErr}` });
                    }
                }
            }
        }, 30000);
    }

    private stopHeartbeat(): void {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = undefined;
        }
    }

    private async fileExists(p: string): Promise<boolean> {
        try {
            await vscode.workspace.fs.stat(vscode.Uri.file(p));
            return true;
        } catch {
            return false;
        }
    }

    private getWorkspaceRoot(): string {
        const folders = vscode.workspace.workspaceFolders;
        return folders && folders.length > 0 ? folders[0].uri.fsPath : process.cwd();
    }

    private sleep(ms: number): Promise<void> {
        return new Promise(r => setTimeout(r, ms));
    }

    private generateId(): string {
        return Math.random().toString(36).substring(2, 10);
    }

    /**
     * Ensure third-party Python dependencies are installed in the extension's
     * site-packages directory. If missing, auto-install via pip --target.
     * This guarantees the deps match the user's Python version & platform.
     */
    private async ensurePythonDependencies(
        pythonPath: string,
        sitePackagesDir: string
    ): Promise<boolean> {
        // Quick check: does pydantic already exist in our site-packages?
        const marker = path.join(sitePackagesDir, 'pydantic', '__init__.py');
        if (await this.fileExists(marker)) {
            this.log('info', 'Python dependencies already installed in extension site-packages');
            return true;
        }

        const pkgs = [
            'pydantic>=2.0',
            'openai>=1.0',
            'anthropic>=0.20',
            'rich>=13.0',
            'prompt-toolkit>=3.0',
            'jsonschema>=4.0',
            'typing-extensions>=4.0',
        ];

        this.log('info', `Installing Python dependencies into ${sitePackagesDir}...`);
        this.notifyHandlers({ type: 'status', status: 'installing_deps' });

        return new Promise((resolve) => {
            const args = [
                '-m', 'pip', 'install',
                '--target', sitePackagesDir,
                '--no-user',
                '--only-binary', ':all:',
                '--no-cache-dir',
                ...pkgs,
            ];
            this.log('info', `Running: ${pythonPath} ${args.join(' ')}`);

            const proc = cp.spawn(pythonPath, args, {
                stdio: ['pipe', 'pipe', 'pipe'],
            });

            let stdout = '';
            let stderr = '';
            proc.stdout?.on('data', (d) => { stdout += d.toString(); });
            proc.stderr?.on('data', (d) => { stderr += d.toString(); });

            proc.on('error', (err: any) => {
                this.log('error', `pip install failed to start: ${err.message}`);
                resolve(false);
            });

            proc.on('close', (code) => {
                if (code !== 0) {
                    this.log('error', `pip install exited with code ${code}`);
                    this.log('error', `stdout: ${stdout.substring(0, 500)}`);
                    this.log('error', `stderr: ${stderr.substring(0, 500)}`);
                    resolve(false);
                    return;
                }
                this.log('info', 'Python dependencies installed successfully');
                resolve(true);
            });
        });
    }
}
