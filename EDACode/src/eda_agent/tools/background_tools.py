"""Background task execution tools for long-running EDA operations.

Allows the agent to start tools (especially simulations, DRC, LVS) in the
background and check their status later without blocking the conversation loop.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import BaseTool, ToolProgress, ToolResult, ValidationResult
from eda_agent.tools.registry import ToolRegistry


class BackgroundTaskManager:
    """Manages asynchronous background tool executions."""

    # Auto-clear completed tasks after this many seconds
    _AUTO_CLEAR_SECONDS: float = 300.0  # 5 minutes

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, ToolResult] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def _auto_clear(self) -> int:
        """Remove completed/failed tasks older than _AUTO_CLEAR_SECONDS."""
        now = time.time()
        cleared = 0
        for tid in list(self._metadata.keys()):
            meta = self._metadata[tid]
            start_time = meta.get("start_time", now)
            status_info = self.get_status(tid)
            status = status_info.get("status")
            if status in ("completed", "failed", "not_found"):
                elapsed = now - start_time
                if elapsed > self._AUTO_CLEAR_SECONDS:
                    if tid in self._tasks and not self._tasks[tid].done():
                        self._tasks[tid].cancel()
                    self._tasks.pop(tid, None)
                    self._results.pop(tid, None)
                    self._metadata.pop(tid, None)
                    cleared += 1
        return cleared

    async def submit(
        self,
        tool_name: str,
        args: Dict[str, Any],
        registry: ToolRegistry,
        context: Any,
    ) -> str:
        """Submit a tool to run in the background."""
        task_id = f"bg_{uuid.uuid4().hex[:8]}"

        async def _run() -> None:
            tool = registry.get(tool_name)
            if tool is None:
                self._results[task_id] = ToolResult(
                    data={"error": f"Tool '{tool_name}' not found"}
                )
                return
            try:
                result = await tool.call(args, context)
                self._results[task_id] = result
            except Exception as e:
                self._results[task_id] = ToolResult(data={"error": str(e)})

        self._tasks[task_id] = asyncio.create_task(_run())
        self._metadata[task_id] = {
            "tool": tool_name,
            "args": args,
            "status": "running",
            "start_time": time.time(),
        }
        return task_id

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a background task."""
        self._auto_clear()
        if task_id in self._results:
            meta = self._metadata.get(task_id, {})
            return {
                "status": "completed",
                "tool": meta.get("tool"),
                "result": self._results[task_id].data,
                "elapsed": time.time() - meta.get("start_time", time.time()),
            }

        if task_id in self._tasks:
            task = self._tasks[task_id]
            meta = self._metadata.get(task_id, {})
            if task.done():
                try:
                    task.result()
                except Exception as e:
                    return {
                        "status": "failed",
                        "tool": meta.get("tool"),
                        "error": str(e),
                        "elapsed": time.time() - meta.get("start_time", time.time()),
                    }
                # Result should now be in _results
                if task_id in self._results:
                    return {
                        "status": "completed",
                        "tool": meta.get("tool"),
                        "result": self._results[task_id].data,
                        "elapsed": time.time() - meta.get("start_time", time.time()),
                    }
                return {"status": "unknown", "tool": meta.get("tool")}
            return {
                "status": "running",
                "tool": meta.get("tool"),
                "elapsed": time.time() - meta.get("start_time", time.time()),
            }

        return {"status": "not_found", "task_id": task_id}

    def get_all_results(self) -> Dict[str, Any]:
        """Get all completed background task results."""
        self._auto_clear()
        return {
            tid: {
                "tool": self._metadata.get(tid, {}).get("tool"),
                "result": r.data,
                "elapsed": time.time() - self._metadata.get(tid, {}).get("start_time", time.time()),
            }
            for tid, r in self._results.items()
        }

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all background tasks with their status."""
        self._auto_clear()
        result = []
        for tid, meta in self._metadata.items():
            status_info = self.get_status(tid)
            result.append({
                "task_id": tid,
                "tool": meta.get("tool"),
                "status": status_info.get("status"),
                "elapsed": status_info.get("elapsed", 0),
            })
        return result

    def clear_completed(self) -> int:
        """Clear completed/failed tasks and return count cleared."""
        cleared = 0
        for tid in list(self._metadata.keys()):
            status = self.get_status(tid).get("status")
            if status in ("completed", "failed", "not_found"):
                if tid in self._tasks:
                    if not self._tasks[tid].done():
                        self._tasks[tid].cancel()
                    del self._tasks[tid]
                self._results.pop(tid, None)
                del self._metadata[tid]
                cleared += 1
        return cleared


class BackgroundSubmitTool(BaseTool):
    """Submit any tool to run in the background.

    Useful for long-running EDA operations (spectre simulation, calibre DRC/LVS,
    Monte Carlo, etc.) that would otherwise block the conversation.
    Returns a task_id that can be used with background_status to check progress.
    """

    name = "background_submit"
    aliases = ["bg_submit", "run_background"]
    input_schema = {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Name of the tool to run in background (e.g., 'bash', 'simulation_run', 'drc_run').",
            },
            "args": {
                "type": "object",
                "description": "Arguments to pass to the tool.",
            },
        },
        "required": ["tool", "args"],
    }

    def description(self) -> str:
        return (
            "Submit any tool to run in the background. Ideal for long EDA operations "
            "(simulation, DRC, LVS, Monte Carlo) that take minutes. Returns a task_id. "
            "Use 'background_status' to poll for completion."
        )

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        tool = args.get("tool")
        tool_args = args.get("args")
        if not tool or not isinstance(tool, str) or not tool.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'tool'. Example: {'tool': 'bash', 'args': {'command': 'sleep 5'}}. NEVER call background_submit without 'tool'."
            )
        if tool_args is None or not isinstance(tool_args, dict):
            return ValidationResult(
                result=False,
                message="Missing required parameter 'args'. Example: {'tool': 'bash', 'args': {'command': 'sleep 5'}}. NEVER call background_submit without 'args'."
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        tool_name = args.get("tool", "")
        tool_args = args.get("args", {})

        bg_mgr = getattr(context, "background_task_manager", None)
        if bg_mgr is None:
            return ToolResult(data={"error": "Background task manager not available in context"})

        registry = getattr(context, "tool_registry", None)
        if registry is None:
            return ToolResult(data={"error": "Tool registry not available in context"})

        task_id = await bg_mgr.submit(tool_name, tool_args, registry, context)
        return ToolResult(data={
            "task_id": task_id,
            "status": "submitted",
            "tool": tool_name,
            "message": f"Background task '{tool_name}' started with ID {task_id}",
        })


class BackgroundStatusTool(BaseTool):
    """Check the status of a background task or list all running tasks."""

    name = "background_status"
    aliases = ["bg_status", "check_background"]
    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID to check. If omitted, lists all background tasks.",
            },
        },
    }

    def description(self) -> str:
        return (
            "Check the status of a background task by task_id, or list all running/completed "
            "background tasks if no task_id is provided."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        bg_mgr = getattr(context, "background_task_manager", None)
        if bg_mgr is None:
            return ToolResult(data={"error": "Background task manager not available"})

        task_id = args.get("task_id")
        if task_id:
            return ToolResult(data=bg_mgr.get_status(task_id))
        return ToolResult(data={"tasks": bg_mgr.list_tasks()})


class BackgroundResultsTool(BaseTool):
    """Get results of completed background tasks and optionally clear them."""

    name = "background_results"
    aliases = ["bg_results", "get_background_results"]
    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Specific task ID to retrieve. If omitted, returns all completed results.",
            },
            "clear": {
                "type": "boolean",
                "description": "Whether to clear completed tasks after retrieving results.",
                "default": False,
            },
        },
    }

    def description(self) -> str:
        return (
            "Get results from completed background tasks. Optionally clear them to free memory. "
            "Use this after 'background_status' shows a task is completed."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        bg_mgr = getattr(context, "background_task_manager", None)
        if bg_mgr is None:
            return ToolResult(data={"error": "Background task manager not available"})

        task_id = args.get("task_id")
        clear = args.get("clear", False)

        if task_id:
            status = bg_mgr.get_status(task_id)
            if status.get("status") == "completed":
                result = {"task_id": task_id, **status}
                if clear:
                    bg_mgr.clear_completed()
                return ToolResult(data=result)
            return ToolResult(data={"task_id": task_id, **status})

        all_results = bg_mgr.get_all_results()
        if clear:
            cleared = bg_mgr.clear_completed()
            return ToolResult(data={"results": all_results, "cleared": cleared})
        return ToolResult(data={"results": all_results})
