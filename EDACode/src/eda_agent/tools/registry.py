"""Tool registry for managing and discovering tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from eda_agent.tools.base import BaseTool


class ToolRegistry:
    """Central registry for all tools in the EDA Agent system.

    Supports dynamic tool registration, discovery, and lookup by name or alias.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._aliases: Dict[str, str] = {}  # alias -> primary name

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Args:
            tool: The tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

        # Register aliases
        for alias in tool.aliases:
            if alias in self._aliases or alias in self._tools:
                raise ValueError(f"Alias '{alias}' conflicts with existing tool/alias")
            self._aliases[alias] = tool.name

    def unregister(self, name: str) -> Optional[BaseTool]:
        """Unregister a tool by name.

        Args:
            name: Tool name or alias.

        Returns:
            The removed tool instance, or None if not found.
        """
        primary_name = self._aliases.get(name, name)
        tool = self._tools.pop(primary_name, None)
        if tool:
            for alias in tool.aliases:
                self._aliases.pop(alias, None)
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name or alias.

        Args:
            name: Tool name or alias.

        Returns:
            The tool instance, or None if not found.
        """
        primary_name = self._aliases.get(name, name)
        return self._tools.get(primary_name)

    def find(self, name: str) -> BaseTool:
        """Find a tool by name or alias, raising if not found.

        Args:
            name: Tool name or alias.

        Returns:
            The tool instance.

        Raises:
            KeyError: If no tool with the given name exists.
        """
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return tool

    def list_tools(
        self,
        filter_prefix: Optional[str] = None,
        eda_only: bool = False,
        code_only: bool = False,
    ) -> List[BaseTool]:
        """List registered tools, optionally filtered.

        Args:
            filter_prefix: Only return tools whose name starts with this prefix.
            eda_only: Only return EDA-specific tools.
            code_only: Only return code/general tools.

        Returns:
            List of matching tool instances.
        """
        from eda_agent.tools.base import CodeTool, EDATool

        tools = list(self._tools.values())

        if filter_prefix:
            tools = [t for t in tools if t.name.startswith(filter_prefix)]

        if eda_only:
            tools = [t for t in tools if isinstance(t, EDATool)]
        elif code_only:
            tools = [t for t in tools if isinstance(t, CodeTool)]

        return tools

    def get_all_schemas(self, compact: bool = False) -> List[Dict[str, Any]]:
        """Get function schemas for all registered tools.

        Args:
            compact: If True, returns stripped-down schemas to reduce tokens.

        Returns:
            List of tool schemas suitable for LLM function calling.
        """
        return [tool.to_dict(compact=compact) for tool in self._tools.values()]

    def get_schemas_for_tools(
        self, names: List[str], compact: bool = False
    ) -> List[Dict[str, Any]]:
        """Get schemas for a specific subset of tools by name.

        Args:
            names: List of tool names to include.
            compact: If True, returns stripped-down schemas.

        Returns:
            List of matching tool schemas.
        """
        schemas: List[Dict[str, Any]] = []
        for name in names:
            tool = self.get(name)
            if tool:
                schemas.append(tool.to_dict(compact=compact))
        return schemas

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        primary_name = self._aliases.get(name, name)
        return primary_name in self._tools

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)


# Global default registry instance
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """Get or create the default global tool registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def register_tool(tool: BaseTool, registry: Optional[ToolRegistry] = None) -> None:
    """Register a tool to a registry (default global)."""
    reg = registry or get_default_registry()
    reg.register(tool)


def find_tool(name: str, registry: Optional[ToolRegistry] = None) -> BaseTool:
    """Find a tool by name in a registry (default global)."""
    reg = registry or get_default_registry()
    return reg.find(name)
