"""Design data management tools for the EDA SDK.

Handles library, cell, and view operations — the foundation of all EDA workflows.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class DesignOpenTool(EDATool):
    """Open or create a design (lib/cell/view) in the EDA SDK database."""

    name = "design_open"
    aliases = ["open_design", "open_cv"]
    input_schema = {
        "type": "object",
        "properties": {
            "lib": {
                "type": "string",
                "description": "Library name.",
            },
            "cell": {
                "type": "string",
                "description": "Cell name.",
            },
            "view": {
                "type": "string",
                "description": "View name (e.g., 'schematic', 'layout', 'symbol').",
                "default": "schematic",
            },
            "view_type": {
                "type": "string",
                "description": "View type category (e.g., 'schematic', 'layout', 'schematicSymbol').",
                "default": "schematic",
            },
            "mode": {
                "type": "string",
                "description": "Open mode: 'r' (read), 'w' (write/new), 'a' (append/edit).",
                "enum": ["r", "w", "a"],
                "default": "a",
            },
            "tech_lib": {
                "type": "string",
                "description": "Technology library name (required when creating new library).",
            },
        },
        "required": ["lib", "cell"],
    }

    def description(self) -> str:
        return (
            "Open or create a design (lib/cell/view) in the EDA SDK database. "
            "This is the entry point for all schematic, layout, and symbol editing operations. "
            "If the library doesn't exist, provide 'tech_lib' to create it."
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
            return ToolResult(data={"error": "pyAether is not installed or not available in this environment."})

        lib = args["lib"]
        cell = args["cell"]
        view = args.get("view", "schematic")
        view_type = args.get("view_type", "schematic")
        mode = args.get("mode", "a")
        tech_lib = args.get("tech_lib")

        try:
            # Initialize EDA SDK if needed
            if not hasattr(context, "_eda_initialized") or not context._eda_initialized:
                pyAether.emyInitDb()
                context._eda_initialized = True

            namespace = getattr(context, "namespace", None)
            if namespace is None:
                namespace = pyAether.emyUnixNS()
                context.namespace = namespace

            # Create library if needed
            if tech_lib:
                try:
                    pyAether.dbCreateLib(lib, attachTechLib=tech_lib)
                except Exception as e:
                    # Library may already exist
                    pass

            lib_scl = pyAether.emyScalarName(namespace, lib)
            cell_scl = pyAether.emyScalarName(namespace, cell)
            view_scl = pyAether.emyScalarName(namespace, view)

            reserved_view = pyAether.emyReservedViewType(view_type)
            new_view_type = pyAether.emyViewType.get(reserved_view)

            design = pyAether.emyDesign.open(lib_scl, cell_scl, view_scl, new_view_type, mode)

            # Store in context
            context.active_design = design
            context.active_lib = lib
            context.active_cell = cell
            context.active_view = view

            block = design.getTopBlock()
            if block is None and mode in ("w", "a"):
                block = pyAether.emyBlock.create(design)
                context.active_block = block
            else:
                context.active_block = block

            return ToolResult(data={
                "lib": lib,
                "cell": cell,
                "view": view,
                "mode": mode,
                "block_exists": block is not None,
                "status": "opened",
            })

        except Exception as e:
            return ToolResult(data={"error": str(e)})


class DesignSaveTool(EDATool):
    """Save the currently open design."""

    name = "design_save"
    aliases = ["save", "save_design"]
    input_schema = {
        "type": "object",
        "properties": {
            "lib": {
                "type": "string",
                "description": "Library name (optional, uses active design if not provided).",
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return "Save the currently open design to disk."

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

        design = getattr(context, "active_design", None)
        if design is None:
            return ToolResult(data={"error": "No active design to save."})

        try:
            design.save()
            return ToolResult(data={
                "lib": getattr(context, "active_lib", ""),
                "cell": getattr(context, "active_cell", ""),
                "view": getattr(context, "active_view", ""),
                "status": "saved",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class DesignCloseTool(EDATool):
    """Close the currently open design."""

    name = "design_close"
    aliases = ["close", "close_design"]
    input_schema = {
        "type": "object",
        "properties": {
            "save": {
                "type": "boolean",
                "description": "Whether to save before closing.",
                "default": True,
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return "Close the currently open design, optionally saving first."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        design = getattr(context, "active_design", None)
        if design is None:
            return ToolResult(data={"error": "No active design to close."})

        save = args.get("save", True)

        try:
            if save:
                design.save()
            design.close()

            # Clear context
            context.active_design = None
            context.active_block = None
            context.active_lib = None
            context.active_cell = None
            context.active_view = None

            return ToolResult(data={"status": "closed", "saved": save})
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class DesignDeleteTool(EDATool):
    """Delete a library, cell, or view from the EDA SDK database."""

    name = "design_delete"
    aliases = ["delete_design", "remove_lib", "remove_cell", "remove_view"]
    input_schema = {
        "type": "object",
        "properties": {
            "lib": {
                "type": "string",
                "description": "Library name to delete (required for lib/cell/view deletion).",
            },
            "cell": {
                "type": "string",
                "description": "Cell name to delete (optional; if omitted, deletes the entire library).",
            },
            "view": {
                "type": "string",
                "description": "View name to delete (optional; if provided, only this view is deleted).",
            },
        },
        "required": ["lib"],
    }

    def description(self) -> str:
        return (
            "Delete a library, cell, or view from the EDA SDK database. "
            "Requires user approval. Specify 'lib' only to delete the entire library, "
            "'lib' + 'cell' to delete a cell, or 'lib' + 'cell' + 'view' to delete a specific view."
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

        lib = args["lib"]
        cell = args.get("cell")
        view = args.get("view")

        try:
            namespace = getattr(context, "namespace", None)
            if namespace is None:
                namespace = pyAether.emyUnixNS()
                context.namespace = namespace

            lib_scl = pyAether.emyScalarName(namespace, lib)

            if view and cell:
                cell_scl = pyAether.emyScalarName(namespace, cell)
                view_scl = pyAether.emyScalarName(namespace, view)
                pyAether.dbDeleteView(lib_scl, cell_scl, view_scl)
                return ToolResult(data={
                    "action": "delete",
                    "target": "view",
                    "lib": lib,
                    "cell": cell,
                    "view": view,
                    "status": "deleted",
                })
            elif cell:
                cell_scl = pyAether.emyScalarName(namespace, cell)
                pyAether.dbDeleteCell(lib_scl, cell_scl)
                return ToolResult(data={
                    "action": "delete",
                    "target": "cell",
                    "lib": lib,
                    "cell": cell,
                    "status": "deleted",
                })
            else:
                pyAether.dbDeleteLib(lib_scl)
                return ToolResult(data={
                    "action": "delete",
                    "target": "library",
                    "lib": lib,
                    "status": "deleted",
                })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class DesignQueryTool(EDATool):
    """Query information about the current design or library."""

    name = "design_query"
    aliases = ["query", "info"]
    input_schema = {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": ["cells", "views", "instances", "nets", "pins", "lpps", "properties"],
                "description": "What to query in the current design.",
            },
            "lib": {
                "type": "string",
                "description": "Library to query (optional, uses active design's library).",
            },
        },
        "required": ["query_type"],
    }
    is_read_only = True

    def description(self) -> str:
        return "Query information about the current design: cells, views, instances, nets, pins, etc."

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

        query_type = args["query_type"]
        design = getattr(context, "active_design", None)
        block = getattr(context, "active_block", None)

        if design is None and query_type not in ("cells", "views"):
            return ToolResult(data={"error": "No active design. Open a design first."})

        try:
            result: Dict[str, Any] = {"query_type": query_type}

            if query_type == "cells":
                lib = args.get("lib") or getattr(context, "active_lib", None)
                # Use db command to list cells
                # This is a simplified placeholder; actual implementation depends on pyAether API
                result["cells"] = []

            elif query_type == "views":
                lib = args.get("lib") or getattr(context, "active_lib", None)
                cell = getattr(context, "active_cell", None)
                result["views"] = []

            elif query_type == "instances" and block is not None:
                insts = []
                # Iterate over instances in block
                # pyAether API specific iteration
                result["instances"] = insts

            elif query_type == "nets" and block is not None:
                nets = []
                result["nets"] = nets

            elif query_type == "pins" and block is not None:
                pins = []
                result["pins"] = pins

            elif query_type == "lpps" and design is not None:
                lpps = []
                if hasattr(design, "lpps"):
                    for lpp in design.lpps:
                        lpps.append({
                            "layerName": getattr(lpp, "layerName", ""),
                            "purpose": getattr(lpp, "purpose", ""),
                            "shape_count": len(getattr(lpp, "shapes", [])),
                        })
                result["lpps"] = lpps

            return ToolResult(data=result)

        except Exception as e:
            return ToolResult(data={"error": str(e)})
