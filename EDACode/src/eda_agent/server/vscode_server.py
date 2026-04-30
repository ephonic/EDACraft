"""VSCode Extension Backend Server for EDA Agent.

Provides JSON-RPC over stdio communication between the VSCode extension
and the Python EDA Agent backend.
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional


def log(level: str, message: str) -> None:
    """Structured log output to stderr (for extension debugging)."""
    entry = json.dumps({"level": level, "message": message, "timestamp": int(time.time() * 1000)})
    print(entry, file=sys.stderr, flush=True)


class VSCodeServer:
    """JSON-RPC server for VSCode integration."""

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        project_root: Optional[str] = None,
        max_tokens: int = 128000,
        max_iterations: int = 50,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.project_root = project_root or os.getcwd()
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations
        self.agent: Optional[Any] = None
        self._running = False
        self._buffer = ""
        self._start_time = time.time()
        self._send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._send_task: Optional[asyncio.Task] = None
        # Single-thread executor guarantees stdout writes are serialized,
        # preventing interleaved JSON-RPC lines when multiple messages are
        # queued rapidly (e.g. multiple tool_start in one round).
        self._send_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="stdout-writer")

    async def initialize(self) -> None:
        """Initialize the EDA Agent core."""
        log("info", "Initializing EDA Agent...")
        try:
            from eda_agent.core.agent import EDAAgent
            from eda_agent.core.context import AgentContext
            from eda_agent.providers.openai_provider import OpenAIProvider
            from eda_agent.providers.anthropic_provider import AnthropicProvider
            from eda_agent.tools.registry import get_default_registry
            from eda_agent.cli import register_all_tools
        except ImportError as e:
            self.send({
                "type": "error",
                "error": f"Failed to import EDA Agent: {e}. Ensure all dependencies are installed."
            })
            log("error", f"Import failed: {e}")
            raise

        registry = get_default_registry()
        register_all_tools(registry)
        log("info", f"Registered {len(registry)} tools")

        if self.provider == "anthropic":
            provider = AnthropicProvider(
                api_key=self.api_key,
                base_url=self.base_url,
                default_model=self.model or "claude-3-5-sonnet-20241022",
            )
        else:
            provider = OpenAIProvider(
                api_key=self.api_key,
                base_url=self.base_url,
                default_model=self.model or "gpt-4o",
            )

        context = AgentContext(project_root=self.project_root)

        self.agent = EDAAgent(
            provider=provider,
            registry=registry,
            context=context,
            max_tokens=self.max_tokens,
            max_iterations=self.max_iterations,
            auto_compact=True,
        )
        log("info", "EDA Agent initialized successfully")

    async def run(self) -> None:
        """Main server loop reading from stdin and writing to stdout."""
        self._running = True
        await self.initialize()
        # Start the background send loop so that synchronous callbacks
        # (e.g. on_progress) never block the event loop on stdout writes.
        self._send_task = asyncio.create_task(self._send_loop())
        self.send({
            "type": "ready",
            "projectRoot": self.project_root,
            "version": "0.1.0",
            "timestamp": int(time.time() * 1000),
        })

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        try:
            while self._running:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=3600)
                    if not line:
                        log("info", "stdin closed, exiting")
                        break
                    await self._handle_line(line.decode("utf-8", errors="replace"))
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    log("error", f"Read loop error: {e}")
                    self.send({"type": "error", "error": f"Read loop: {str(e)}"})
        except asyncio.CancelledError:
            log("info", "Server cancelled")
        finally:
            self._running = False
            if self._send_task and not self._send_task.done():
                self._send_task.cancel()
                try:
                    await self._send_task
                except asyncio.CancelledError:
                    pass
            self._send_executor.shutdown(wait=False)
            log("info", "Server stopped")

    async def _handle_line(self, line: str) -> None:
        """Process a single JSON-RPC line from stdin."""
        line = line.strip()
        if not line:
            return

        if len(line) > 500:
            log("debug", f"Recv: {line[:200]}... ({len(line)} chars)")
        else:
            log("debug", f"Recv: {line[:200]}")

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log("warning", "Invalid JSON received")
            self.send({"type": "error", "error": f"Invalid JSON: {line[:200]}"})
            return

        msg_type = msg.get("type")
        request_id = msg.get("requestId")

        try:
            if msg_type == "shutdown":
                self._running = False
                self.send({"type": "shutdown_ack", "requestId": request_id})
                log("info", "Shutdown requested")

            elif msg_type == "chat":
                # Run chat handling in a background task so the main loop
                # can continue reading stdin (e.g., responding to ping).
                asyncio.create_task(self._handle_chat(msg, request_id))

            elif msg_type == "tool_call":
                asyncio.create_task(self._handle_tool_call(msg, request_id))

            elif msg_type == "get_context_budget":
                await self._handle_get_context_budget(request_id)

            elif msg_type == "compact_context":
                await self._handle_compact_context(request_id)

            elif msg_type == "reset_context":
                self.agent.reset()
                self.send({"type": "context_reset", "requestId": request_id})
                log("info", "Context reset")

            elif msg_type == "ping":
                self.send({"type": "pong", "requestId": request_id, "timestamp": int(time.time() * 1000)})

            elif msg_type == "stop":
                if self.agent:
                    self.agent.cancel()
                self.send({"type": "stopped", "requestId": request_id, "timestamp": int(time.time() * 1000)})
                log("info", "Stop requested by user")

            elif msg_type == "grantPermission":
                await self._handle_grant_permission(msg, request_id)

            else:
                log("warning", f"Unknown message type: {msg_type}")
                self.send({
                    "type": "error",
                    "error": f"Unknown message type: {msg_type}",
                    "requestId": request_id,
                })
        except Exception as e:
            log("error", f"Handler error: {e}")
            self.send({
                "type": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "requestId": request_id,
            })

    async def _handle_grant_permission(self, msg: Dict[str, Any], request_id: Optional[str]) -> None:
        """Handle user granting permissions for file/EDA operations."""
        permission_type = msg.get("permissionType", "")
        scope = msg.get("scope", "once")  # "once" or "session"
        ctx = self.agent.context

        if scope == "session":
            ctx.session_approved = True
            log("info", "User granted session-wide approval for all operations")
        else:
            if permission_type == "eda_access":
                ctx.eda_access_approved = True
                log("info", "User granted EDA database access approval")
            elif permission_type == "file_access":
                ctx.file_access_approved = True
                log("info", "User granted file access approval")

        self.send({
            "type": "permissionGranted",
            "permissionType": permission_type,
            "scope": scope,
            "requestId": request_id,
            "timestamp": int(time.time() * 1000),
        })

    async def _handle_chat(self, msg: Dict[str, Any], request_id: Optional[str]) -> None:
        """Handle a chat message from the user."""
        text = msg.get("text", "")
        log("info", f"Chat request: {text[:100]}")

        def on_progress(stage: str, data: Any) -> None:
            if stage == "thinking":
                self.send({
                    "type": "status",
                    "status": "thinking",
                    "iteration": data.get("iteration"),
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "budget_warning":
                self.send({
                    "type": "budget_warning",
                    "usageRatio": data.get("usage_ratio"),
                    "currentTokens": data.get("current_tokens"),
                    "availableTokens": data.get("available_tokens"),
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "compaction":
                self.send({
                    "type": "compaction",
                    "tokensSaved": data.get("tokens_saved"),
                    "originalCount": data.get("original_count"),
                    "compactedCount": data.get("compacted_count"),
                    "timestamp": int(time.time() * 1000),
                })
                log("info", f"Context compacted: saved {data.get('tokens_saved')} tokens")
            elif stage == "tool_call":
                self.send({
                    "type": "tool_start",
                    "tool": data.get("name"),
                    "args": data.get("args"),
                    "toolCallId": data.get("id") or "",
                    "iteration": data.get("iteration", 0),
                    "summary": data.get("summary", ""),
                    "reason": data.get("reason", ""),
                    "toolRound": data.get("toolRound", 0),
                    "maxToolRounds": data.get("maxToolRounds", 0),
                    "timeout": data.get("timeout", 0),
                    "timestamp": int(time.time() * 1000),
                })
                log("info", f"Tool start: {data.get('name')}")
            elif stage == "tool_progress":
                self.send({
                    "type": "tool_progress",
                    "tool": data.get("tool"),
                    "progress": data.get("data"),
                    "iteration": data.get("iteration", 0),
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "thinking_stop":
                self.send({
                    "type": "status",
                    "status": "thinking_stop",
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "phase":
                self.send({
                    "type": "phase",
                    "phase": data.get("phase"),
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "plan_update":
                self.send({
                    "type": "plan_update",
                    "plan": data.get("plan"),
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "tool_complete":
                self.send({
                    "type": "tool_complete",
                    "tool": data.get("name"),
                    "result": data.get("result"),
                    "toolCallId": data.get("tool_call_id") or "",
                    "iteration": data.get("iteration", 0),
                    "isError": data.get("is_error", False),
                    "durationMs": data.get("duration_ms"),
                    "timestamp": int(time.time() * 1000),
                })
                log("info", f"Tool complete: {data.get('name')}")
            elif stage == "design_state":
                self.send({
                    "type": "design_state",
                    "state": data,
                    "timestamp": int(time.time() * 1000),
                })
            elif stage == "token":
                self.send({
                    "type": "token",
                    "text": data.get("text"),
                    "requestId": request_id,
                    "timestamp": int(time.time() * 1000),
                })

        try:
            start = time.time()
            # No overall timeout — design tasks can take arbitrarily long.
            # Individual tool timeouts still apply (bash 120s, EDA 600s, etc.).
            response = await self.agent.run(text, on_progress=on_progress)
            duration = int((time.time() - start) * 1000)

            self.send({
                "type": "assistant",
                "text": response,
                "requestId": request_id,
                "durationMs": duration,
                "timestamp": int(time.time() * 1000),
            })
            log("info", f"Chat completed in {duration}ms")
        except asyncio.TimeoutError:
            log("error", "Chat request timed out after 10 minutes")
            self.send({
                "type": "error",
                "error": "⏱️ Request timed out after 10 minutes. The agent took too long to respond. Try a simpler request or reduce tool usage.",
                "requestId": request_id,
                "timestamp": int(time.time() * 1000),
            })
        except Exception as e:
            log("error", f"Chat failed: {e}")
            self.send({
                "type": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "requestId": request_id,
            })

    async def _handle_tool_call(self, msg: Dict[str, Any], request_id: Optional[str]) -> None:
        """Handle a direct tool call request."""
        from eda_agent.tools.registry import find_tool

        tool_name = msg.get("tool", "")
        args = msg.get("args", {})
        log("info", f"Direct tool call: {tool_name}")

        try:
            tool = find_tool(tool_name)
            self.send({
                "type": "tool_start",
                "tool": tool_name,
                "args": args,
                "timestamp": int(time.time() * 1000),
            })

            start = time.time()
            result = await tool.call(args, self.agent.context)
            duration = int((time.time() - start) * 1000)

            is_success = True
            if isinstance(result.data, dict) and "error" in result.data:
                is_success = False

            self.send({
                "type": "tool_result",
                "tool": tool_name,
                "result": result.data,
                "success": is_success,
                "durationMs": duration,
                "requestId": request_id,
                "timestamp": int(time.time() * 1000),
            })
            log("info", f"Tool {tool_name} completed in {duration}ms (success={is_success})")
        except Exception as e:
            log("error", f"Tool {tool_name} failed: {e}")
            self.send({
                "type": "tool_result",
                "tool": tool_name,
                "result": {"error": str(e)},
                "success": False,
                "requestId": request_id,
                "timestamp": int(time.time() * 1000),
            })

    async def _handle_get_context_budget(self, request_id: Optional[str]) -> None:
        """Return current context budget status."""
        budget = self.agent.get_context_budget()
        self.send({
            "type": "context_budget",
            "budget": budget,
            "requestId": request_id,
        })

    async def _handle_compact_context(self, request_id: Optional[str]) -> None:
        """Manually trigger context compaction."""
        result = await self.agent.compact_context()
        self.send({
            "type": "compaction_result",
            "result": {
                "success": result.success,
                "originalCount": result.original_count,
                "compactedCount": result.compacted_count,
                "tokensSaved": result.tokens_saved,
                "summary": result.summary,
                "error": result.error,
            },
            "requestId": request_id,
        })

    def send(self, msg: Dict[str, Any]) -> None:
        """Enqueue a JSON message for async delivery to stdout.

        This method is called from synchronous callbacks (e.g. on_progress).
        It must NOT block the asyncio event loop, so we only enqueue the
        message here. A background _send_loop coroutine does the actual
        os.write(1, ...) so that slow frontend reads cannot freeze the loop.

        If the event loop is not running (e.g. during early startup or after
        crash), falls back to direct stdout write.
        """
        try:
            msg["timestamp"] = msg.get("timestamp", int(time.time() * 1000))
            # If no event loop is running, write directly (startup / fatal path)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is None or not self._running:
                json_str = json.dumps(msg, default=str, ensure_ascii=False)
                os.write(1, (json_str + "\n").encode("utf-8"))
                return
            self._send_queue.put_nowait(msg)
        except asyncio.QueueFull:
            log("error", "Send queue full, dropping message")
        except Exception as e:
            log("error", f"Failed to enqueue message: {e}")

    async def _send_loop(self) -> None:
        """Background coroutine that drains the send queue to stdout."""
        while self._running:
            try:
                msg = await asyncio.wait_for(self._send_queue.get(), timeout=1.0)
                await self._send_one(msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log("error", f"Send loop error: {e}")

    async def _send_one(self, msg: Dict[str, Any]) -> None:
        """Serialize and write a single message to stdout (async-safe)."""
        try:
            json_str = json.dumps(msg, default=str, ensure_ascii=False)
            # Truncate extremely large messages to avoid blocking stdout pipe
            MAX_MSG_SIZE = 100_000  # 100KB cap for JSON-RPC line
            if len(json_str) > MAX_MSG_SIZE:
                _type = msg.get("type", "unknown")
                _truncated = {
                    "type": _type,
                    "truncated": True,
                    "originalSize": len(json_str),
                    "reason": "Message exceeded 100KB stdout limit",
                    "timestamp": msg.get("timestamp", int(time.time() * 1000)),
                }
                # Preserve requestId / toolCallId if present so the frontend can correlate
                if "requestId" in msg:
                    _truncated["requestId"] = msg["requestId"]
                if "toolCallId" in msg:
                    _truncated["toolCallId"] = msg["toolCallId"]
                json_str = json.dumps(_truncated, ensure_ascii=False)
            data = (json_str + "\n").encode("utf-8")
            # Use the single-thread executor so that a full stdout pipe cannot block
            # the event loop, while still guaranteeing messages are written in order.
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._send_executor, lambda: os.write(1, data))
            log("debug", f"Sent: {msg.get('type')} (len={len(json_str)})")
        except Exception as e:
            log("error", f"Failed to send message: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA Agent VSCode Backend Server")
    parser.add_argument("--transport", choices=["stdio", "tcp"], default="stdio")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--project-root", default=os.getcwd())
    parser.add_argument("--max-tokens", type=int, default=128000)
    parser.add_argument("--max-iterations", type=int, default=50)
    args = parser.parse_args()

    server = VSCodeServer(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        project_root=args.project_root,
        max_tokens=args.max_tokens,
        max_iterations=args.max_iterations,
    )

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        log("info", "Interrupted by user")
    except Exception as e:
        log("fatal", f"Server crashed: {e}")
        server.send({"type": "fatal", "error": str(e), "traceback": traceback.format_exc()})
        sys.exit(1)


if __name__ == "__main__":
    main()
