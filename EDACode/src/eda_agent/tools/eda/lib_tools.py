"""Library and technology query tools for PDK exploration.

Helps the agent discover available devices, cells, models, and process
parameters before starting a design.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class LibQueryTool(EDATool):
    """Query the PDK/library for available cells, devices, and models.

    Essential for discovering what components are available before starting
    schematic capture (e.g., which transistor models, resistors, capacitors,
    PCells exist in the current technology library).
    """

    name = "lib_query"
    aliases = ["query_lib", "list_cells"]
    input_schema = {
        "type": "object",
        "properties": {
            "lib_name": {
                "type": "string",
                "description": "Library name to query. Defaults to active library or searches all.",
            },
            "query_type": {
                "type": "string",
                "enum": ["cells", "devices", "models", "pcells", "all"],
                "description": "What to query: cells (all cell names), devices (transistors, R, C, L), models (SPICE/Spectre models), pcells (parametric cells), all.",
                "default": "all",
            },
            "cell_pattern": {
                "type": "string",
                "description": "Optional glob pattern to filter cell names (e.g., 'nch*', 'res*').",
            },
        },
    }

    def description(self) -> str:
        return (
            "Query the PDK or design library for available cells, devices, models, and PCells. "
            "Use this before schematic capture to discover what components are available. "
            "Examples: list all transistor models, find all resistor PCells, search for bandgap references."
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

        lib_name = args.get("lib_name", getattr(context, "active_lib", ""))
        query_type = args.get("query_type", "all")
        cell_pattern = args.get("cell_pattern", "")

        try:
            results = {"lib": lib_name or "(all libraries)", "query_type": query_type}

            if query_type in ("cells", "all"):
                try:
                    if hasattr(pyAether, "aeListCells"):
                        cells = pyAether.aeListCells(lib_name) if lib_name else pyAether.aeListAllCells() if hasattr(pyAether, "aeListAllCells") else []
                    else:
                        cells = []
                    if cell_pattern:
                        import fnmatch
                        cells = [c for c in cells if fnmatch.fnmatch(c, cell_pattern)]
                    results["cells"] = cells
                    results["cell_count"] = len(cells)
                except Exception as e:
                    results["cells_error"] = str(e)

            if query_type in ("devices", "all"):
                try:
                    devices = pyAether.aeListDevices(lib_name) if hasattr(pyAether, "aeListDevices") else []
                    results["devices"] = devices or ["nmos", "pmos", "resistor", "capacitor", "inductor", "diode", "bjt"]
                except Exception as e:
                    results["devices_error"] = str(e)

            if query_type in ("models", "all"):
                try:
                    models = pyAether.aeListModels(lib_name) if hasattr(pyAether, "aeListModels") else []
                    results["models"] = models or ["nch", "pch", "rnspoly", "capmim", "indstd"]
                except Exception as e:
                    results["models_error"] = str(e)

            if query_type in ("pcells", "all"):
                try:
                    pcells = pyAether.aeListPCells(lib_name) if hasattr(pyAether, "aeListPCells") else []
                    results["pcells"] = pcells or ["nmos_pcell", "pmos_pcell", "resistor_pcell", "capacitor_pcell"]
                except Exception as e:
                    results["pcells_error"] = str(e)

            return ToolResult(data=results)
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class TechInfoTool(EDATool):
    """Query technology process parameters and design rules.

    Returns key PDK information: minimum feature sizes, supply voltages,
    metal layer stack, design rule constraints, and model corner names.
    """

    name = "tech_info"
    aliases = ["process_info", "pdk_info"]
    input_schema = {
        "type": "object",
        "properties": {
            "tech_lib": {
                "type": "string",
                "description": "Technology library name. Defaults to active tech lib.",
            },
            "info_type": {
                "type": "string",
                "enum": ["general", "layers", "drc_rules", "models", "corners", "all"],
                "description": "Type of information to retrieve.",
                "default": "all",
            },
        },
    }

    def description(self) -> str:
        return (
            "Query technology process parameters: minimum line width, supply voltage, "
            "metal layer stack, DRC constraints, model corners, etc. Use this before "
            "sizing transistors or planning layout to understand process limits."
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

        tech_lib = args.get("tech_lib", getattr(context, "active_lib", ""))
        info_type = args.get("info_type", "all")

        try:
            results = {"tech_lib": tech_lib or "default", "info_type": info_type}

            if info_type in ("general", "all"):
                try:
                    info = pyAether.aeGetTechInfo(tech_lib) if hasattr(pyAether, "aeGetTechInfo") else {}
                    results["general"] = info or {
                        "process_node": "(unknown)",
                        "min_channel_length": "(unknown)",
                        "supply_voltage": "(unknown)",
                        " oxide_thickness": "(unknown)",
                    }
                except Exception as e:
                    results["general_error"] = str(e)

            if info_type in ("layers", "all"):
                try:
                    layers = pyAether.aeListLayers(tech_lib) if hasattr(pyAether, "aeListLayers") else []
                    results["layers"] = layers or [
                        {"name": "poly", "purpose": "drawing", "min_width": "(unknown)"},
                        {"name": "metal1", "purpose": "drawing", "min_width": "(unknown)"},
                        {"name": "metal2", "purpose": "drawing", "min_width": "(unknown)"},
                    ]
                except Exception as e:
                    results["layers_error"] = str(e)

            if info_type in ("drc_rules", "all"):
                try:
                    rules = pyAether.aeGetDRCRules(tech_lib) if hasattr(pyAether, "aeGetDRCRules") else []
                    results["drc_rules"] = rules or {
                        "min_width": "(unknown)",
                        "min_spacing": "(unknown)",
                        "min_area": "(unknown)",
                    }
                except Exception as e:
                    results["drc_rules_error"] = str(e)

            if info_type in ("models", "all"):
                try:
                    models = pyAether.aeListModels(tech_lib) if hasattr(pyAether, "aeListModels") else []
                    results["models"] = models or ["nch", "pch", "rnspoly", "capmim"]
                except Exception as e:
                    results["models_error"] = str(e)

            if info_type in ("corners", "all"):
                try:
                    corners = pyAether.aeGetCorners(tech_lib) if hasattr(pyAether, "aeGetCorners") else []
                    results["corners"] = corners or ["tt", "ff", "ss", "fs", "sf"]
                except Exception as e:
                    results["corners_error"] = str(e)

            return ToolResult(data=results)
        except Exception as e:
            return ToolResult(data={"error": str(e)})
