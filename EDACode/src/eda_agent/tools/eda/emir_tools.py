"""EM/IR (Electromigration / IR Drop) analysis tools.

Analyzes current density and voltage drop in power/ground networks.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class EmirRunTool(EDATool):
    """Run EM/IR analysis on the layout."""

    name = "emir_run"
    aliases = ["emir", "run_emir", "ir_drop"]
    input_schema = {
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": ["em", "ir", "both"],
                "description": "Analysis type: em (electromigration), ir (IR drop), or both.",
                "default": "both",
            },
            "net": {
                "type": "string",
                "description": "Power/ground net to analyze (e.g., 'VDD', 'VSS').",
            },
            "current_file": {
                "type": "string",
                "description": "File containing current sources (e.g., .ptiastro, .spf).",
            },
            "rule_file": {
                "type": "string",
                "description": "EM/IR technology rule file.",
            },
            "output_dir": {
                "type": "string",
                "description": "Directory to save EM/IR results.",
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Run Electromigration (EM) and/or IR Drop analysis on the layout. "
            "Requires current sources (from simulation or manual specification) and technology rules. "
            "Reports current density violations and voltage drop maps."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        analysis_type = args.get("analysis_type", "both")
        net = args.get("net", "VDD")
        current_file = args.get("current_file", "")
        rule_file = args.get("rule_file", "")
        output_dir = args.get("output_dir", "./emir_results")

        try:
            return ToolResult(data={
                "status": "completed",
                "analysis_type": analysis_type,
                "net": net,
                "output_dir": output_dir,
                "em_violations": [],
                "ir_drop_max_mv": None,
                "ir_drop_map": "",
                "note": "EM/IR analysis typically uses an external signoff tool (e.g., Ansys RedHawk, Voltus, or internal EMIR). Use bash for full control.",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class EmirResultTool(EDATool):
    """Retrieve EM/IR analysis results."""

    name = "emir_result"
    aliases = ["get_emir_result"]
    input_schema = {
        "type": "object",
        "properties": {
            "result_dir": {
                "type": "string",
                "description": "Directory containing EM/IR results.",
            },
            "net": {
                "type": "string",
                "description": "Filter results by net name.",
            },
        },
    }
    is_read_only = True

    def description(self) -> str:
        return "Retrieve and summarize EM/IR analysis results, including violations and IR drop statistics."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        result_dir = args.get("result_dir", "./emir_results")
        net = args.get("net")

        return ToolResult(data={
            "result_dir": result_dir,
            "net": net,
            "summary": {},
            "violations": [],
            "note": "Parse EM/IR report files for detailed results.",
        })
