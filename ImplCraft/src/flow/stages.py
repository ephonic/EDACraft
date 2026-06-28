"""
Flow Stage Definitions — defines the default backend flow with all stages.

Supports two complete P&R tool chains:
- Synopsys: DC → ICC2 (6 stages) → PT → Calibre
- Cadence:  DC → Innovus (6 stages) → Tempus → Pegasus
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


# =============================================================================
# Synopsys Flow: DC → ICC2 (6 stages) → PT → Calibre
# =============================================================================
SYNOPSYS_FLOW_STAGES: list[FlowStageDefinition] = [
    FlowStageDefinition(
        name="synthesis",
        description="Logic synthesis with Design Compiler",
        tool="DesignCompiler",
        flow_stage=FlowStage.SYNTHESIS,
        dependencies=[],
        tool_family="dc",
    ),
    FlowStageDefinition(
        name="dft_insertion",
        description="DFT scan chain insertion, BIST, and repair logic",
        tool="DFTCompiler",
        flow_stage=FlowStage.DFT_INSERTION,
        dependencies=["synthesis"],
        tool_family="dft",
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
        name="finish",
        description="Write GDS/DEF/SDF and final netlist for sign-off",
        tool="ICC2",
        flow_stage=FlowStage.TAPEOUT,
        dependencies=["route_opt"],
        sub_stage="finish",
        tool_family="icc2",
    ),
    FlowStageDefinition(
        name="starrc_extraction",
        description="Parasitic extraction with StarRC (SPEF generation)",
        tool="StarRC",
        flow_stage=FlowStage.PARASITIC_EXTRACTION,
        dependencies=["route_opt"],
        sub_stage="spef",
        tool_family="starrc",
    ),
    FlowStageDefinition(
        name="primetime",
        description="Sign-off static timing analysis with PrimeTime",
        tool="PrimeTime",
        flow_stage=FlowStage.STA_SIGNOFF,
        dependencies=["starrc_extraction"],
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


# =============================================================================
# Cadence Flow: DC → Innovus (6 stages) → Tempus → Pegasus
# =============================================================================
CADENCE_FLOW_STAGES: list[FlowStageDefinition] = [
    FlowStageDefinition(
        name="synthesis",
        description="Logic synthesis with Design Compiler",
        tool="DesignCompiler",
        flow_stage=FlowStage.SYNTHESIS,
        dependencies=[],
        tool_family="dc",
    ),
    FlowStageDefinition(
        name="dft_insertion",
        description="DFT scan chain insertion, BIST, and repair logic",
        tool="DFTCompiler",
        flow_stage=FlowStage.DFT_INSERTION,
        dependencies=["synthesis"],
        tool_family="dft",
    ),
    FlowStageDefinition(
        name="create_lib",
        description="Import design into Innovus database",
        tool="Innovus",
        flow_stage=FlowStage.INIT,
        dependencies=["synthesis"],
        sub_stage="create_lib",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="floorplan",
        description="Floorplan, power plan, and pin assignment",
        tool="Innovus",
        flow_stage=FlowStage.FLOORPLAN,
        dependencies=["create_lib"],
        sub_stage="floorplan",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="placement",
        description="Timing-driven placement with congestion optimization",
        tool="Innovus",
        flow_stage=FlowStage.PLACEMENT,
        dependencies=["floorplan"],
        sub_stage="placement",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="cts",
        description="Clock tree synthesis with CCOPT",
        tool="Innovus",
        flow_stage=FlowStage.CTS,
        dependencies=["placement"],
        sub_stage="cts",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="routing",
        description="NanoRoute global + detail routing with SI analysis",
        tool="Innovus",
        flow_stage=FlowStage.ROUTING,
        dependencies=["cts"],
        sub_stage="routing",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="route_opt",
        description="Post-route optimization with ECO opt",
        tool="Innovus",
        flow_stage=FlowStage.ROUTE_OPT,
        dependencies=["routing"],
        sub_stage="route_opt",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="finish",
        description="Write GDS/DEF/Verilog/SDF for sign-off",
        tool="Innovus",
        flow_stage=FlowStage.TAPEOUT,
        dependencies=["route_opt"],
        sub_stage="finish",
        tool_family="innovus",
    ),
    FlowStageDefinition(
        name="starrc_extraction",
        description="Parasitic extraction with StarRC (SPEF generation)",
        tool="StarRC",
        flow_stage=FlowStage.PARASITIC_EXTRACTION,
        dependencies=["finish"],
        sub_stage="spef",
        tool_family="starrc",
    ),
    FlowStageDefinition(
        name="tempus",
        description="Sign-off static timing analysis with Tempus",
        tool="Tempus",
        flow_stage=FlowStage.STA_SIGNOFF,
        dependencies=["starrc_extraction"],
        tool_family="tempus",
    ),
    FlowStageDefinition(
        name="drc",
        description="Design rule check with Pegasus",
        tool="Pegasus",
        flow_stage=FlowStage.PV_DRC,
        dependencies=["finish"],
        sub_stage="drc",
        tool_family="pegasus",
    ),
    FlowStageDefinition(
        name="lvs",
        description="Layout vs schematic verification with Pegasus",
        tool="Pegasus",
        flow_stage=FlowStage.PV_LVS,
        dependencies=["route_opt"],
        sub_stage="lvs",
        tool_family="pegasus",
    ),
]


# Default flow (backward compatible)
DEFAULT_FLOW_STAGES = SYNOPSYS_FLOW_STAGES


def get_flow_stages(flow: str = "synopsys") -> list[FlowStageDefinition]:
    """Get flow stage definitions for the specified tool chain.

    Args:
        flow: 'synopsys' for DC/ICC2/PT/Calibre, 'cadence' for DC/Innovus/Tempus/Pegasus

    Returns:
        List of FlowStageDefinition for the selected flow.
    """
    flows = {
        "synopsys": SYNOPSYS_FLOW_STAGES,
        "cadence": CADENCE_FLOW_STAGES,
    }
    if flow not in flows:
        raise ValueError(f"Unknown flow: {flow}. Available: {list(flows.keys())}")
    return flows[flow]
