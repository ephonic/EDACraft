# Changelog

All notable changes to the EDA Agent VSCode extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-04-21

### Added
- Initial release of EDA Agent VSCode extension
- Interactive chat sidebar panel with rich markdown rendering
- Python backend process management (auto-start/stop/restart)
- Real-time tool execution visualization in chat UI
- File edit integration via VSCode WorkspaceEdit API
- Terminal command execution from agent
- 5 core commands: Open Chat, Stop/Restart Agent, Run Harness, Clear Chat
- Keyboard shortcut: `Ctrl+Shift+A` / `Cmd+Shift+A`
- Settings: provider, model, API key, base URL, python path, project root
- Support for OpenAI, Anthropic, and OpenAI-compatible APIs (vLLM, Ollama)
- Communication protocol: JSON-RPC over stdio
