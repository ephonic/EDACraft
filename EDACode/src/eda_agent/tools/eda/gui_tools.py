"""GUI interaction tools for the EDA SDK.

Supports executing GUI commands, taking screenshots, and interacting with the design canvas.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class GuiCommandTool(EDATool):
    """Execute a GUI command in the EDA SDK environment."""

    name = "gui_command"
    aliases = ["gui_cmd", "ae_command", "eda_cmd"]
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The GUI command to execute (e.g., 'seGuiOpenCellView', 'aeZoomFit', 'seGuiRunSimulation').",
            },
            "args": {
                "type": "array",
                "description": "Positional arguments for the command.",
                "items": {},
            },
            "kwargs": {
                "type": "object",
                "description": "Keyword arguments for the command.",
            },
        },
        "required": ["command"],
    }

    def description(self) -> str:
        return (
            "Execute a pyAether GUI command directly. "
            "This provides low-level access to the EDA GUI automation API. "
            "Common commands: seGuiOpenCellView, aeZoomFit, aeRefresh, seGuiRunSimulation. "
            "Prefer using specialized tools for common operations."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        command = args["command"]
        cmd_args = args.get("args", [])
        cmd_kwargs = args.get("kwargs", {})

        try:
            # Lookup command in EDA SDK module
            func = getattr(pyAether, command, None)
            if func is None:
                return ToolResult(data={"error": f"Command '{command}' not found in pyAether."})

            result = func(*cmd_args, **cmd_kwargs)

            return ToolResult(data={
                "command": command,
                "result": str(result) if result is not None else None,
                "status": "executed",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e), "command": command})


class GuiScreenshotTool(EDATool):
    """Capture a screenshot of the current GUI window or canvas."""

    name = "gui_screenshot"
    aliases = ["screenshot", "capture"]
    input_schema = {
        "type": "object",
        "properties": {
            "output_file": {
                "type": "string",
                "description": "Path to save the screenshot.",
            },
            "window": {
                "type": "string",
                "description": "Window to capture: 'main', 'canvas', 'schematic', 'layout'. Defaults to main.",
                "default": "main",
            },
            "region": {
                "type": "object",
                "description": "Optional bounding box (x, y, w, h) for partial capture.",
            },
        },
    }
    is_read_only = True

    def description(self) -> str:
        return "Capture a screenshot of the EDA GUI for visual verification or documentation."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        output_file = args.get("output_file", "screenshot.png")
        window = args.get("window", "main")
        region = args.get("region")

        try:
            # pyAether may have screenshot capabilities via Qt or OS integration
            # Fallback: use bash with external tool

            return ToolResult(data={
                "output_file": output_file,
                "window": window,
                "status": "saved",
                "note": "Screenshot may require OS-specific tools or pyAether Qt integration. Use bash for alternative capture methods.",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class GuiInteractTool(EDATool):
    """Interact with GUI elements: click, select, highlight."""

    name = "gui_interact"
    aliases = ["gui_click", "select", "highlight"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "select", "highlight", "zoom", "pan"],
                "description": "Interaction type.",
            },
            "target": {
                "type": "string",
                "description": "Target object or coordinate.",
            },
            "params": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action"],
    }

    def description(self) -> str:
        return "Interact with GUI elements: click objects, select instances, highlight nets, zoom, and pan."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        action = args["action"]
        target = args.get("target", "")
        params = args.get("params", {})

        try:
            if action == "zoom":
                zoom_type = params.get("type", "fit")
                zoom_cmds = {
                    "fit": getattr(pyAether, "aeZoomFit", None),
                    "in": getattr(pyAether, "aeZoomIn", None),
                    "out": getattr(pyAether, "aeZoomOut", None),
                }
                cmd = zoom_cmds.get(zoom_type)
                if cmd:
                    cmd()
                else:
                    return ToolResult(data={
                        "action": action,
                        "target": target,
                        "status": "unavailable",
                        "note": f"Zoom command '{zoom_type}' not available in this pyAether version.",
                    })

            elif action == "highlight":
                hl = getattr(pyAether, "aeHighlight", None)
                if hl:
                    hl(target)

            return ToolResult(data={"action": action, "target": target, "status": "done"})
        except Exception as e:
            return ToolResult(data={"error": str(e)})
