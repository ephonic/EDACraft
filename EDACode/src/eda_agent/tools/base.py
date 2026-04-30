"""Tool base classes and interfaces.

Inspired by Claude Code's agent-tools package, adapted for Python and EDA workflows.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union


T = TypeVar("T")


@dataclass
class ToolProgress:
    """Progress event from a tool execution."""

    tool_use_id: str
    data: Dict[str, Any]


@dataclass
class ToolResult:
    """Result returned by a tool's call() method."""

    data: Any
    new_messages: List[Dict[str, Any]] = field(default_factory=list)
    context_modifier: Optional[Callable[[Any], Any]] = None


@dataclass
class ValidationResult:
    """Result of tool input validation."""

    result: bool
    message: str = ""
    error_code: int = 0


@dataclass
class PermissionResult:
    """Result of a permission check for a tool invocation."""

    behavior: str  # 'allow', 'deny', 'passthrough'
    message: str = ""
    updated_input: Optional[Dict[str, Any]] = None


@dataclass
class ToolDescription:
    """Description of a tool for LLM consumption."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    is_read_only: bool = False
    is_destructive: bool = False


class BaseTool(abc.ABC):
    """Base class for all tools in the EDA Agent system.

    This defines the protocol-level contract for any tool — independent of
    specific context types or host infrastructure.
    """

    # ── Identity ──
    name: str
    aliases: List[str] = []
    search_hint: str = ""

    # ── Schema ──
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None

    # ── Behavioral properties ──
    is_read_only: bool = False
    is_destructive: bool = False
    requires_user_interaction: bool = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Skip validation for abstract intermediate classes (CodeTool, EDATool)
        if cls.__name__ in ("CodeTool", "EDATool"):
            return
        if not hasattr(cls, "name") or not cls.name:
            raise TypeError(f"Tool class {cls.__name__} must define a 'name' attribute")
        if not hasattr(cls, "input_schema") or not cls.input_schema:
            raise TypeError(f"Tool class {cls.__name__} must define an 'input_schema' attribute")

    @abc.abstractmethod
    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            args: Validated input arguments matching input_schema.
            context: Execution context (agent state, project info, etc.).
            on_progress: Optional callback for progress updates.

        Returns:
            ToolResult containing the execution output.
        """
        ...

    def description(self) -> str:
        """Return a human-readable description of this tool."""
        return self.__doc__ or f"Tool: {self.name}"

    def prompt_description(self) -> str:
        """Return a description suitable for inclusion in the system prompt."""
        return self.description()

    def is_concurrency_safe(self, args: Dict[str, Any]) -> bool:
        """Whether this tool call is safe to run concurrently with others."""
        return False

    def validate_input(
        self,
        args: Dict[str, Any],
        context: Any,
    ) -> ValidationResult:
        """Validate tool input before execution.

        Default implementation accepts all input. Override for custom validation.
        """
        return ValidationResult(result=True)

    def check_permissions(
        self,
        args: Dict[str, Any],
        context: Any,
    ) -> PermissionResult:
        """Check if the tool invocation is permitted.

        Default implementation allows all invocations.
        """
        return PermissionResult(behavior="allow")

    def to_dict(self, compact: bool = False) -> Dict[str, Any]:
        """Serialize tool metadata for LLM function calling.

        Args:
            compact: If True, removes verbose schema fields (defaults, long
                     descriptions) to reduce token count and API latency.
        """
        desc = self.description()
        if compact:
            desc = self._compact_description(desc)
        params = self._compact_schema(self.input_schema) if compact else self.input_schema
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": desc,
                "parameters": params,
            },
        }

    @staticmethod
    def _compact_description(desc: str) -> str:
        """Shorten a tool description for compact schema mode.

        Keeps the first sentence (up to 80 chars) which usually conveys
        the tool's purpose. Falls back to first 60 chars + ellipsis.
        """
        if len(desc) <= 60:
            return desc
        # Try to keep the first sentence
        sentence_end = desc.find(". ")
        if 10 < sentence_end <= 80:
            return desc[: sentence_end + 1]
        # Otherwise truncate at a word boundary near 60 chars
        truncated = desc[:60]
        last_space = truncated.rfind(" ")
        if last_space > 10:
            truncated = truncated[:last_space]
        return truncated + "..."

    @staticmethod
    def _compact_schema(schema: Any) -> Any:
        """Recursively strip verbose fields from a JSON schema."""
        if isinstance(schema, dict):
            result: Dict[str, Any] = {}
            for k, v in schema.items():
                # Skip default values — the code handles them, the model doesn't need them
                if k == "default":
                    continue
                # Truncate overly long descriptions to first sentence or 50 chars
                if k == "description" and isinstance(v, str) and len(v) > 50:
                    sentence_end = v.find(". ")
                    if 10 < sentence_end < 50:
                        result[k] = v[: sentence_end + 1]
                    else:
                        result[k] = v[:50] + "..."
                    continue
                result[k] = BaseTool._compact_schema(v)
            return result
        elif isinstance(schema, list):
            return [BaseTool._compact_schema(i) for i in schema]
        return schema

    def user_facing_name(self, args: Optional[Dict[str, Any]] = None) -> str:
        """Return a user-facing name for this tool invocation."""
        return self.name

    def get_activity_description(self, args: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Return a short description of what this tool is currently doing."""
        return None


class CodeTool(BaseTool):
    """Base class for code-related tools (file ops, bash, etc.)."""

    pass


class EDATool(BaseTool):
    """Base class for EDA-specific tools.

    EDA tools typically interact with the EDA SDK and may require:
    - An active design session
    - Technology library context
    - Simulator configuration
    """

    # EDA-specific attributes
    requires_design_open: bool = False
    requires_tech_lib: bool = False
    supported_view_types: List[str] = field(default_factory=list)

    def _ensure_design_context(self, context: Any) -> Any:
        """Ensure the execution context has an active design session.

        Raises:
            RuntimeError: If no design is open and requires_design_open is True.
        """
        if not self.requires_design_open:
            return context

        design = getattr(context, "active_design", None)
        if design is None:
            raise RuntimeError(
                f"Tool '{self.name}' requires an open design. "
                "Please open a design first using design_open."
            )
        return design
