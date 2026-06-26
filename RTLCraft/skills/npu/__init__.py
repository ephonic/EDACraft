"""
skills.npu — NPU Design Skill

Neural Processing Unit micro-architecture design using the Spec2RTL
flow. Covers configurable compute arrays, instruction schedulers,
activation function units, and load/store pipelines.

Modules:
  - behaviors.py: Cycle-accurate behavior templates (schedulers, datapaths)
  - models.py: NPU behavioral model (MAC array, activation functions)
  - arch_templates.py: Extensible architecture templates (basic, dual_pipeline, multi_tile)
  - skeleton_templates.py: PE type → implementation steps
  - design_flow.py: Full Spec2RTL flow script
  - design_wizard.py: Interactive design wizard with markdown template reports
"""

# Import behaviors to register templates
import skills.npu.behaviors  # noqa: F401

from skills.npu.models import NPUModel, NPUState, MACArrayModel
from skills.npu.arch_templates import (
    NpuArchParams, NpuArchTemplate,
    NpuPeBuilder, NpuPeCatalog,
    BasicTemplate, DualPipelineTemplate, MultiTileTemplate,
    CustomNpuArchTemplate,
    get_template, list_templates, register_template,
)
# design_flow and design_wizard are optional — skip if not available
try:
    from skills.npu.design_flow import NPUConfig, run_npu_design_flow
except ImportError:
    NPUConfig = None  # type: ignore[misc,assignment]
    run_npu_design_flow = None  # type: ignore[misc,assignment]
from skills.npu.skeleton_templates import register_npu_skeleton_steps

from skills.npu.dsl_modules import (
    TopScheduler,
    GenericScheduler,
    MVUScheduler,
    EVRFScheduler,
    MFUScheduler,
    LDScheduler,
    MVU,
    MFU,
    EVRF,
    LD,
    NPUTop,
)

__all__ = [
    "TopScheduler", "GenericScheduler", "MVUScheduler", "EVRFScheduler", "MFUScheduler", "LDScheduler", "MVU", "MFU", "EVRF", "LD", "NPUTop",
    "NPUModel", "NPUState", "MACArrayModel",
    "NpuArchParams", "NpuArchTemplate",
    "NpuPeBuilder", "NpuPeCatalog",
    "BasicTemplate", "DualPipelineTemplate", "MultiTileTemplate",
    "CustomNpuArchTemplate",
    "get_template", "list_templates", "register_template",
    "NPUConfig", "run_npu_design_flow",  # may be None
    "register_npu_skeleton_steps",
]
