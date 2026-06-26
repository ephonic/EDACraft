"""
Flow Stage Definitions — defines the default backend flow with all stages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..db.design_state import FlowStage


@dataclass
class FlowStageDefinition:
    """Defines a single flow stage."""
    name: str
    description: str
    tool: str
    flow_stage: FlowStage
    dependencies: list[str] = field(default_factory=list)
    sub_stage: str | None = None
    tool_family: str = ""      # Maps to EDAEnvironment.get_script()
    env_script: str | None = None  # Fallback if EDAEnvironment not configured


# Default flow: DC → ICC2 (6 stages) → PT → Calibre (DRC/LVS)
DEFAULT_FLOW_STAGES: list[FlowStageDefinition] = [
    FlowStageDefinition(
        name="synthesis",
        description="Logic synthesis with Design Compiler",
        tool="DesignCompiler",
        flow_stage=FlowStage.SYNTHESIS,
        dependencies=[],
        tool_family="dc",
    ),
    FlowStageDefinition(
        name="create_lib",
        description="Create ICC2 NDM library",
        tool="ICC2",
        flow_stage=FlowStage.INIT,
        dependencies=["synthesis"],
        sub_stage="create_lib",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="floorplan",
        description="Floorplan definition and macro placement",
        tool="ICC2",
        flow_stage=FlowStage.FLOORPLAN,
        dependencies=["create_lib"],
        sub_stage="floorplan",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="placement",
        description="Standard cell placement with timing-driven optimization",
        tool="ICC2",
        flow_stage=FlowStage.PLACEMENT,
        dependencies=["floorplan"],
        sub_stage="placement",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="cts",
        description="Clock tree synthesis and optimization",
        tool="ICC2",
        flow_stage=FlowStage.CTS,
        dependencies=["placement"],
        sub_stage="cts",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="routing",
        description="Global, track, and detail routing with SI analysis",
        tool="ICC2",
        flow_stage=FlowStage.ROUTING,
        dependencies=["cts"],
        sub_stage="routing",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="route_opt",
        description="Post-route optimization and SPEF extraction",
        tool="ICC2",
        flow_stage=FlowStage.ROUTE_OPT,
        dependencies=["routing"],
        sub_stage="route_opt",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="primetime",
        description="Sign-off static timing analysis with PrimeTime",
        tool="PrimeTime",
        flow_stage=FlowStage.STA_SIGNOFF,
        dependencies=["route_opt"],
        tool_family="pt",
    ),
    FlowStageDefinition(
        name="drc",
        description="Design rule check with Calibre",
        tool="Calibre",
        flow_stage=FlowStage.PV_DRC,
        dependencies=["route_opt"],
        sub_stage="drc",
        tool_family="calibre",
    ),
    FlowStageDefinition(
        name="lvs",
        description="Layout vs schematic verification with Calibre",
        tool="Calibre",
        flow_stage=FlowStage.PV_LVS,
        dependencies=["route_opt"],
        sub_stage="lvs",
        tool_family="calibre",
    ),
]
