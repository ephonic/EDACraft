# EDA Agent — VSCode Extension

VSCode extension for EDA Agent, an AI-powered assistant for analog/mixed-signal IC design.

**Affiliation**: State Key Lab of Integrated Chips and Systems, Fudan University.

## Features

- **Interactive Chat Panel**: Sidebar chat interface for natural language circuit design
- **Agent Lifecycle Management**: Start, stop, and restart the Python backend from VSCode
- **Tool Execution Visualization**: See which tools are being called in real-time
- **File Integration**: Auto-refresh files edited by the agent, apply edits directly in VSCode
- **Terminal Integration**: Run bash commands in integrated terminal
- **Circuit Harness**: One-click validation workflows (netlist + DRC + LVS + simulation)

## Architecture

```
VSCode Extension (TypeScript)
├── Sidebar Webview (Chat UI)
├── Server Manager (spawns Python backend)
└── Message Router (JSON-RPC over stdio)

Python Backend
├── VSCodeServer (stdio JSON-RPC)
├── EDAAgent (conversation loop)
└── Tool Registry (code + EDA tools)
```

## Configuration Guide

### How to Open Settings

**Method 1 — Settings UI:**
1. Press `Cmd/Ctrl + ,` to open VSCode Settings
2. Search for `eda-agent`

**Method 2 — settings.json:**
1. Press `Cmd/Ctrl + Shift + P`
2. Type `Preferences: Open User Settings (JSON)`
3. Add configuration under the `"eda-agent"` namespace

### LLM Provider Configuration

EDA Agent supports two provider types:

| Provider | Official API | Suitable For |
|----------|-------------|--------------|
| `openai` | OpenAI, Azure OpenAI, One API, Cloudflare AI Gateway, any OpenAI-compatible proxy | GPT-4o, GPT-4, custom models via proxy |
| `anthropic` | Anthropic Claude API | Claude 3.5 Sonnet, Claude 3 Opus |

> **Important:** If you are using a proxy service (One API, Cloudflare AI Gateway, custom OpenAI-compatible proxy), **always select `openai` as the provider**, even when calling Claude models. Set `baseUrl` to your proxy endpoint.

### Setting Reference

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `eda-agent.provider` | `string` | LLM provider: `"openai"` or `"anthropic"` | `"openai"` |
| `eda-agent.model` | `string` | Model identifier | `"gpt-4o"` |
| `eda-agent.apiKey` | `string` | API key for the provider | `""` |
| `eda-agent.baseUrl` | `string` | Custom base URL for OpenAI-compatible APIs | `""` |
| `eda-agent.pythonPath` | `string` | Python interpreter path | `"python3"` |
| `eda-agent.autoStart` | `boolean` | Auto-start agent on extension activation | `true` |
| `eda-agent.projectRoot` | `string` | Project root directory | workspace root |

### Configuration Examples

#### Example 1 — OpenAI Official API

```json
{
  "eda-agent.provider": "openai",
  "eda-agent.model": "gpt-4o",
  "eda-agent.apiKey": "sk-your-openai-api-key"
}
```

#### Example 2 — Anthropic Claude Official API

```json
{
  "eda-agent.provider": "anthropic",
  "eda-agent.model": "claude-3-5-sonnet-20241022",
  "eda-agent.apiKey": "sk-ant-your-anthropic-api-key"
}
```

#### Example 3 — One API / Cloudflare AI Gateway (OpenAI-compatible Proxy)

If you use a unified proxy like **One API** or **Cloudflare AI Gateway**:

```json
{
  "eda-agent.provider": "openai",
  "eda-agent.model": "claude-3-5-sonnet-20241022",
  "eda-agent.apiKey": "sk-your-proxy-api-key",
  "eda-agent.baseUrl": "https://your-proxy.example.com/v1"
}
```

**Key points for proxy users:**
- Provider must be `"openai"` (the proxy speaks OpenAI-compatible protocol)
- `baseUrl` must include the `/v1` path suffix if your proxy requires it
- `model` should match the model name configured in your proxy

#### Example 4 — Local Model (Ollama / vLLM / llama.cpp)

```json
{
  "eda-agent.provider": "openai",
  "eda-agent.model": "qwen2.5-coder:32b",
  "eda-agent.apiKey": "ollama",
  "eda-agent.baseUrl": "http://localhost:11434/v1"
}
```

#### Example 5 — Custom Python Path (macOS/Linux with Homebrew)

```json
{
  "eda-agent.pythonPath": "/opt/homebrew/bin/python3",
  "eda-agent.provider": "openai",
  "eda-agent.model": "gpt-4o",
  "eda-agent.apiKey": "sk-your-api-key"
}
```

### Troubleshooting

**"invalid api-key" error**
- Double-check your API key is correct and has not expired
- If using a proxy, ensure `provider` is set to `"openai"`, not `"anthropic"`
- Verify `baseUrl` includes any required path suffix (e.g., `/v1`)

**"Python not found" error**
- Set `eda-agent.pythonPath` to the full path of your Python executable
- On macOS GUI apps do not inherit shell PATH, so full path is required

**Agent shows "thinking..." indefinitely**
- Check VSCode Output panel → "EDA Agent" for error logs
- Verify network connectivity to the LLM API endpoint
- Try setting `baseUrl` explicitly if behind a corporate proxy

## Development

### Prerequisites

- Node.js >= 18
- VSCode >= 1.85
- Python >= 3.9

### Build

```bash
cd vscode-extension
npm install
npm run compile
```

### Package (Custom script, avoids vsce Node 23 issues)

```bash
node scripts/pack.js
```

### Run Extension

1. Open `vscode-extension/` folder in VSCode
2. Press `F5` to launch Extension Development Host
3. The EDA Agent sidebar should appear in the activity bar

### Debug

- Use the "Run Extension" launch configuration
- Check Output panel → "EDA Agent" for logs
- Python backend stderr is forwarded to the VSCode extension host console

## Communication Protocol

The VSCode extension and Python backend communicate via **newline-delimited JSON over stdio**:

### Request (VSCode → Python)
```json
{"type": "chat", "text": "Open mylib/inv1 schematic", "requestId": "abc123"}
```

### Response (Python → VSCode)
```json
{"type": "assistant", "text": "Opened mylib/inv1 schematic...", "requestId": "abc123"}
```

### Tool Execution Progress
```json
{"type": "tool_start", "tool": "design_open", "args": {"lib": "mylib", "cell": "inv1"}}
{"type": "tool_result", "tool": "design_open", "result": {"status": "opened"}, "success": true}
```

## Commands

| Command | Title | Context |
|---------|-------|---------|
| `eda-agent.openChat` | Open EDA Agent Chat | Command Palette, Editor Context |
| `eda-agent.stopAgent` | Stop Agent | Sidebar Title |
| `eda-agent.restartAgent` | Restart Agent | Sidebar Title |
| `eda-agent.runHarness` | Run Circuit Harness | Command Palette |

## License

MIT
