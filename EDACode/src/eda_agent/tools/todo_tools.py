"""Todo list management tools for tracking design task progress.

Helps the agent maintain a structured todo list across conversation turns,
especially useful for multi-step analog circuit design workflows.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import BaseTool, ToolProgress, ToolResult, ValidationResult


class SetTodoListTool(BaseTool):
    """Manage a todo list for tracking design task progress.

    The agent can add items, update their status, list pending tasks,
    or clear the list. Useful for complex multi-step designs where
    tracking progress across turns is important.
    """

    name = "set_todo_list"
    aliases = ["todo", "todo_list"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "update", "list", "clear"],
                "description": "Action to perform on the todo list.",
            },
            "item": {
                "type": "string",
                "description": "Description of the todo item (for 'add').",
            },
            "index": {
                "type": "integer",
                "description": "0-based index of the item to update (for 'update').",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "done", "blocked"],
                "description": "New status for the item (for 'update').",
            },
        },
        "required": ["action"],
    }

    def description(self) -> str:
        return (
            "Manage a todo list to track design progress. Actions: add (create item), "
            "update (change status by index), list (show all items), clear (remove all). "
            "Statuses: pending, in_progress, done, blocked. Use this to organize complex "
            "multi-step designs (e.g., schematic → simulation → layout → verification)."
        )

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        action = args.get("action")
        if not action or not isinstance(action, str) or action not in ("add", "update", "list", "clear"):
            return ValidationResult(
                result=False,
                message="Missing or invalid 'action'. Must be one of: 'add', 'update', 'list', 'clear'. Example: {'action': 'add', 'item': 'Create inverter schematic'}."
            )
        if action == "add":
            item = args.get("item")
            if not item or not isinstance(item, str) or not item.strip():
                return ValidationResult(
                    result=False,
                    message="Missing 'item' for add action. Example: {'action': 'add', 'item': 'Create inverter schematic'}."
                )
        if action == "update":
            index = args.get("index")
            if index is None or not isinstance(index, int):
                return ValidationResult(
                    result=False,
                    message="Missing 'index' for update action. Example: {'action': 'update', 'index': 0, 'status': 'done'}."
                )
            status = args.get("status")
            if not status or not isinstance(status, str) or status not in ("pending", "in_progress", "done", "blocked"):
                return ValidationResult(
                    result=False,
                    message="Missing or invalid 'status' for update action. Must be one of: 'pending', 'in_progress', 'done', 'blocked'."
                )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        action = args.get("action", "list")
        todos: List[Dict[str, Any]] = getattr(context, "todo_list", [])

        if action == "add":
            item_text = args.get("item", "")
            if not item_text:
                return ToolResult(data={"error": "'item' is required for add action"})
            todos.append({"item": item_text, "status": "pending"})
            context.todo_list = todos
            return ToolResult(data={
                "message": f"Added: {item_text}",
                "index": len(todos) - 1,
                "todos": todos,
            })

        elif action == "update":
            idx = args.get("index", 0)
            new_status = args.get("status", "pending")
            if not isinstance(idx, int) or idx < 0 or idx >= len(todos):
                return ToolResult(data={
                    "error": f"Invalid index {idx}. List has {len(todos)} items.",
                    "todos": todos,
                })
            old = todos[idx]["status"]
            todos[idx]["status"] = new_status
            context.todo_list = todos
            return ToolResult(data={
                "message": f"Updated item {idx}: {todos[idx]['item']} ({old} → {new_status})",
                "todos": todos,
            })

        elif action == "list":
            return ToolResult(data={
                "count": len(todos),
                "pending": sum(1 for t in todos if t["status"] == "pending"),
                "in_progress": sum(1 for t in todos if t["status"] == "in_progress"),
                "done": sum(1 for t in todos if t["status"] == "done"),
                "blocked": sum(1 for t in todos if t["status"] == "blocked"),
                "todos": todos,
            })

        elif action == "clear":
            context.todo_list = []
            return ToolResult(data={"message": "Todo list cleared", "todos": []})

        return ToolResult(data={"error": f"Unknown action: {action}"})
