"""Bash tool for shell command execution.

Adapts Claude Code's BashTool for Python/EDA workflows.
Supports timeout, working directory, environment variables, and sandbox mode.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import BaseTool, ToolProgress, ToolResult, ValidationResult


@dataclass
class BashOutput:
    """Output from a bash command execution."""

    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: int


class BashTool(BaseTool):
    """Execute bash commands in the project environment.

    This is the primary interface for running external tools, build scripts,
    file operations, and any shell-based EDA tool invocations.
    """

    name = "bash"
    aliases = ["shell", "exec", "run"]
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "REQUIRED. The bash command string to execute. MUST be non-empty. Examples: 'ls -la', 'python script.py', 'cd /tmp && make'. NEVER omit this parameter.",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in milliseconds. Default: 60000 (60s). Max: 600000 (10min).",
                "default": 60000,
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command. Defaults to the project root.",
            },
            "env": {
                "type": "object",
                "description": "Additional environment variables to set for this command.",
            },
            "description": {
                "type": "string",
                "description": "A short description of what this command does (for logging/audit).",
            },
        },
        "required": ["command"],
    }

    is_read_only = False
    is_destructive = True

    # Known safe read-only command prefixes
    SAFE_READ_COMMANDS = {
        "cat", "head", "tail", "less", "more", "grep", "find", "ls", "tree",
        "wc", "stat", "file", "strings", "jq", "awk", "cut", "sort", "uniq",
        "tr", "echo", "printf", "pwd", "which", "whereis", "ps", "top",
    }

    def __init__(self, default_cwd: Optional[str] = None) -> None:
        self.default_cwd = default_cwd or os.getcwd()

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        import json
        command = args.get("command")
        if not command or not isinstance(command, str) or not command.strip():
            return ValidationResult(
                result=False,
                message=(
                    f"CRITICAL ERROR: Missing required parameter 'command'. "
                    f"You sent: {json.dumps(args, ensure_ascii=False)}. "
                    "Correct format: {'command': 'your command here', 'timeout': 60000}. "
                    "NEVER call bash with empty {} or without 'command'."
                ),
            )
        return ValidationResult(result=True)

    def description(self) -> str:
        return (
            "Execute bash shell commands. Supports pipes, redirects, and compound commands. "
            "Use this for running EDA tools, build scripts, file operations, and system commands. "
            "MUST provide the 'command' parameter — calling bash without a command is an error. "
            "Always prefer using specialized EDA tools for design operations when available."
        )

    def is_read_only_command(self, command: str) -> bool:
        """Heuristic to detect if a command is read-only."""
        parts = shlex.split(command)
        if not parts:
            return True
        # Simple heuristic: first token is a known safe command
        first_cmd = parts[0].split("/")[-1]  # Handle absolute paths
        return first_cmd in self.SAFE_READ_COMMANDS

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        command = args.get("command")
        if not command:
            return ToolResult(data={
                "error": (
                    "Missing required parameter for bash: 'command' (the shell command to execute). "
                    "Example: {'command': 'ls -la /home/user/workspace', 'timeout': 60000}"
                ),
            })
        timeout = min(args.get("timeout", 60000), 600000) / 1000.0
        cwd = args.get("cwd", self.default_cwd)
        env_override = args.get("env", {})
        description = args.get("description", command)

        # Build environment
        env = os.environ.copy()
        env.update(env_override)

        # EDA-specific environment defaults
        if "EDA_HOME" not in env:
            env.setdefault("EDA_HOME", os.environ.get("EDA_HOME", ""))

        start_time = asyncio.get_event_loop().time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            MAX_OUTPUT_BYTES = 512 * 1024  # 512 KB cap
            total_bytes = len(stdout_bytes) + len(stderr_bytes)
            truncated = False
            if total_bytes > MAX_OUTPUT_BYTES:
                # Proportionally truncate stdout and stderr
                stdout_ratio = len(stdout_bytes) / total_bytes if total_bytes > 0 else 0.5
                stdout_limit = int(MAX_OUTPUT_BYTES * stdout_ratio)
                stderr_limit = MAX_OUTPUT_BYTES - stdout_limit
                stdout_bytes = stdout_bytes[:stdout_limit]
                stderr_bytes = stderr_bytes[:stderr_limit]
                truncated = True

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            if truncated:
                notice = f"\n...[truncated, total output was {total_bytes} bytes]"
                # Append notice to whichever stream is non-empty, preferring stderr
                if stderr:
                    stderr += notice
                else:
                    stdout += notice

            output = BashOutput(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode or 0,
                command=command,
                duration_ms=duration_ms,
            )

            return ToolResult(data=output)

        except asyncio.TimeoutError:
            # Try to kill the process and its children
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                # Force kill the entire process group if possible
                try:
                    import signal
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError, AttributeError):
                    pass
            except Exception:
                pass

            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            output = BashOutput(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                command=command,
                duration_ms=duration_ms,
            )
            return ToolResult(data=output)

        except Exception as e:
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            output = BashOutput(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                command=command,
                duration_ms=duration_ms,
            )
            return ToolResult(data=output)

    def user_facing_name(self, args: Optional[Dict[str, Any]] = None) -> str:
        if args and args.get("description"):
            return f"bash: {args['description']}"
        return "bash"

    def get_activity_description(self, args: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if args:
            desc = args.get("description", args.get("command", ""))
            return f"Running: {desc}"
        return None
