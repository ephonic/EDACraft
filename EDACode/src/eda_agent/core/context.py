"""Execution context for the EDA Agent.

Holds agent state, active design sessions, tool configurations, and project metadata.
Inspired by Claude Code's AppState, simplified for EDA workflows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentContext:
    """Context object passed to all tool executions.

    Maintains state across the agent session, including:
    - Project root and configuration
    - Active EDA SDK design session
    - Simulator configurations
    - Conversation history references
    """

    # ── Project ──
    project_root: str = field(default_factory=os.getcwd)
    project_name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    # ── EDA SDK Session State ──
    _eda_initialized: bool = False
    namespace: Optional[Any] = None
    active_design: Optional[Any] = None
    active_block: Optional[Any] = None
    active_lib: Optional[str] = None
    active_cell: Optional[str] = None
    active_view: Optional[str] = None

    # ── Simulation State ──
    sim_config: Optional[Dict[str, Any]] = None
    mde_session: Optional[Any] = None
    last_sim_result: Optional[Dict[str, Any]] = None

    # ── Conversation State ──
    session_id: str = ""
    message_count: int = 0

    # ── Tool State ──
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
    pending_background_tasks: Dict[str, Any] = field(default_factory=dict)
    _MAX_TOOL_OUTPUTS: int = field(default=100, repr=False)

    # ── Active Task Plan ──
    active_plan: Optional[Dict[str, Any]] = None

    # ── Todo List ──
    todo_list: List[Dict[str, Any]] = field(default_factory=list)

    # ── Design State Tracking ──
    recent_actions: List[str] = field(default_factory=list)

    # ── Permissions ──
    file_access_approved: bool = False
    eda_access_approved: bool = False
    session_approved: bool = False

    def get_active_design_info(self) -> Dict[str, Optional[str]]:
        """Return information about the currently active design."""
        return {
            "lib": self.active_lib,
            "cell": self.active_cell,
            "view": self.active_view,
            "design_open": self.active_design is not None,
        }

    def reset_design_state(self) -> None:
        """Clear the active design state."""
        self.active_design = None
        self.active_block = None
        self.active_lib = None
        self.active_cell = None
        self.active_view = None

    def add_tool_output(self, output: Dict[str, Any]) -> None:
        """Add a tool output, keeping the list bounded."""
        self.tool_outputs.append(output)
        if len(self.tool_outputs) > self._MAX_TOOL_OUTPUTS:
            # Remove oldest entries (leave headroom of 10 to avoid thrashing)
            self.tool_outputs = self.tool_outputs[-self._MAX_TOOL_OUTPUTS:]

    def cleanup_background_tasks(self, completed_ids: List[str]) -> None:
        """Remove completed background tasks from pending map."""
        for tid in completed_ids:
            self.pending_background_tasks.pop(tid, None)

    def set_active_plan(self, plan: Dict[str, Any]) -> None:
        """Set the active task plan."""
        self.active_plan = plan

    def update_plan_progress(self, tool_name: str) -> None:
        """Update plan phase status based on executed tool name."""
        if not self.active_plan or "phases" not in self.active_plan:
            return
        phases = self.active_plan["phases"]
        # Mark the first matching pending phase as done
        for phase in phases:
            if phase.get("status") == "pending" and tool_name in phase.get("suggested_tools", []):
                phase["status"] = "done"
                break
        # Mark the next pending phase as active
        for phase in phases:
            if phase.get("status") == "pending":
                phase["status"] = "active"
                break

    def to_prompt_context(self) -> str:
        """Generate a string representation for inclusion in the system prompt."""
        lines = [
            f"Project: {self.project_name or self.project_root}",
            f"Active Design: {self.active_lib}/{self.active_cell}/{self.active_view}" if self.active_design else "No active design",
        ]
        if self.sim_config:
            lines.append(f"Simulation Configured: {self.sim_config.get('simulator', 'none')}")
        return "\n".join(lines)
