"""Lightweight PPA analysis helpers for rtlgen_x."""

from rtlgen_x.ppa.advisor import (
    ArchitecturePpaStats,
    FlowPpaStats,
    ModulePpaStats,
    PpaGoals,
    PpaRecommendation,
    PpaReport,
    StagePpaStats,
    advise_ppa,
    analyze_architecture_ppa,
    analyze_module_ppa,
)

__all__ = [
    "ArchitecturePpaStats",
    "FlowPpaStats",
    "ModulePpaStats",
    "PpaGoals",
    "PpaRecommendation",
    "PpaReport",
    "StagePpaStats",
    "advise_ppa",
    "analyze_architecture_ppa",
    "analyze_module_ppa",
]
