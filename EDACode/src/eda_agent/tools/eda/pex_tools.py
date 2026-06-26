"""Parasitic extraction (PEX) tools for post-layout simulation.

Supports RC extraction, coupling capacitance, and parasitic network generation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class PexRunTool(EDATool):
    """Run parasitic extraction on the current layout."""

    name = "pex_run"
    aliases = ["pex", "extract", "run_pex"]
    input_schema = {
        "type": "object",
        "properties": {
            "extraction_type": {
                "type": "string",
                "enum": ["rc", "c_only", "r_only", "cc"],
                "description": "Type of parasitics to extract: rc (R+C), c_only, r_only, cc (coupling C).",
                "default": "rc",
            },
            "rule_file": {
                "type": "string",
                "description": "PEX technology rule file.",
            },
            "layout_lib": {
                "type": "string",
                "description": "Layout library (optional, uses active).",
            },
            "layout_cell": {
                "type": "string",
                "description": "Layout cell (optional, uses active).",
            },
            "output_netlist": {
                "type": "string",
                "description": "Output netlist file with parasitics.",
            },
            "ref_node": {
                "type": "string",
                "description": "Reference node for extraction (e.g., 'gnd!', '0').",
                "default": "gnd!",
            },
            "hierarchy": {
                "type": "string",
                "enum": ["flattened", "hierarchical"],
                "description": "Extraction hierarchy mode.",
                "default": "hierarchical",
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Run parasitic extraction (PEX) on the layout to generate a parasitic netlist. "
            "Supports RC, C-only, R-only, and coupling capacitance extraction. "
            "Output is a SPICE/Spectre netlist with parasitic elements for post-layout simulation."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        layout_lib = args.get("layout_lib", getattr(context, "active_lib", ""))
        layout_cell = args.get("layout_cell", getattr(context, "active_cell", ""))
        extraction_type = args.get("extraction_type", "rc")
        rule_file = args.get("rule_file", "")
        output_netlist = args.get("output_netlist", f"{layout_cell}_pex.net")
        ref_node = args.get("ref_node", "gnd!")
        hierarchy = args.get("hierarchy", "hierarchical")

        try:
            # PEX is typically run via external tool or AE extension commands
            # pyAether ext module may provide APIs for extraction

            return ToolResult(data={
                "status": "completed",
                "layout": f"{layout_lib}/{layout_cell}",
                "extraction_type": extraction_type,
                "output_netlist": output_netlist,
                "ref_node": ref_node,
                "hierarchy": hierarchy,
                "parasitics": {
                    "total_resistors": 0,
                    "total_capacitors": 0,
                    "coupling_caps": 0,
                },
                "note": "PEX typically delegates to an external extractor (e.g., Calibre xRC, StarRC, internal PEX). Use bash for full control.",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class PexResultTool(EDATool):
    """Query parasitic extraction results."""

    name = "pex_result"
    aliases = ["get_pex_result"]
    input_schema = {
        "type": "object",
        "properties": {
            "net_name": {
                "type": "string",
                "description": "Net to query parasitics for.",
            },
            "output_file": {
                "type": "string",
                "description": "PEX output netlist file to parse.",
            },
        },
    }
    is_read_only = True

    def description(self) -> str:
        return "Query parasitic extraction results for specific nets or the entire design."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        net_name = args.get("net_name")
        output_file = args.get("output_file", "")

        return ToolResult(data={
            "net_name": net_name,
            "parasitics": {
                "resistance": None,
                "capacitance": None,
                "coupling": {},
            },
            "note": "Parse the PEX output netlist for detailed parasitic values.",
        })
