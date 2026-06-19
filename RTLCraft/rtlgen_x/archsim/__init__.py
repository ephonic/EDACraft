"""Generic lightweight architecture simulation primitives."""

from rtlgen_x.archsim.behavior import BehaviorReport, BehaviorSimulator
from rtlgen_x.archsim.cycle import CycleReport, CycleSimulator
from rtlgen_x.archsim.model import ArchitectureModel, FlowSpec, StageSpec, Workload

__all__ = [
    "ArchitectureModel",
    "BehaviorReport",
    "BehaviorSimulator",
    "CycleReport",
    "CycleSimulator",
    "FlowSpec",
    "StageSpec",
    "Workload",
]
