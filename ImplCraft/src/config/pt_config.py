"""
PrimeTime Stage Configuration — standalone, YAML-loadable.

This config object contains ALL PrimeTime sign-off STA options.
It does not depend on DesignState or any runtime objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PTStageConfig:
    """
    Complete PrimeTime stage configuration.
    
    Covers:
      - Library and netlist setup
      - Multi-VT with dont_use control
      - SPEF back-annotation
      - CPPR and SI analysis
      - Path group timing analysis (setup/hold)
      - Power analysis (VCD/SAIF)
      - ECO fixing (timing, DRC, power, leakage)
      - Model extraction
      - Session management
    """

    # ---- General ----
    design_name: str = "top"
    num_cores: int = 8
    significant_digits: int = 3

    # ---- Inputs ----
    netlist_file: str = ""
    sdc_file: str = ""
    spef_file: str = ""
    spef_format: str = "auto"          # auto, SPEF, DSPF, SPEF_GZ

    # ---- Libraries ----
    search_path: list[str] = field(default_factory=list)
    target_library: list[str] = field(default_factory=list)
    link_library: list[str] = field(default_factory=list)
    symbol_library: list[str] = field(default_factory=list)

    # ---- Multi-VT and dont_use ----
    vt_groups: dict[str, str] = field(default_factory=dict)
    dont_use_patterns: list[str] = field(default_factory=list)
    custom_dont_use: list[str] = field(default_factory=list)
    custom_remove_dontuse: list[str] = field(default_factory=list)

    # ---- Timing ----
    timing_derate_late: float = 1.0
    timing_derate_early: float = 1.0
    enable_cppr: bool = True
    cppr_threshold_ps: float = 1.0
    enable_si_analysis: bool = True
    save_pin_arrival_and_slack: bool = True
    delay_calc_mode: str = "full_design"

    # ---- Power Analysis ----
    enable_power_analysis: bool = True
    power_mode: str = "averaged"       # averaged, time_based
    vcd_file: str = ""
    vcd_strip_path: str = ""
    vcd_time_range: list[float] = field(default_factory=list)
    saif_file: str = ""
    saif_strip_path: str = ""

    # ---- Path Group Analysis ----
    max_paths: int = 200
    nworst: int = 1
    report_transition: bool = True
    report_net: bool = True
    report_capacitance: bool = True
    slack_lesser_than: float = 0.0

    # ---- ECO Fixing ----
    enable_eco: bool = False
    eco_physical_mode: str = "placement"
    lef_library: str = ""
    final_def: str = ""
    eco_scripts_output: str = ""
    fix_setup: bool = False
    fix_hold: bool = False
    fix_drc: bool = False
    fix_power: bool = False
    fix_leakage: bool = False
    setup_opt_margin: float = 0.0
    hold_opt_margin: float = 0.0
    setup_opt_slack: float = 0.0
    hold_opt_slack: float = 0.0
    power_opt_margin: float = 0.0
    fix_setup_groups: list[str] = field(default_factory=list)
    fix_hold_groups: list[str] = field(default_factory=list)
    fix_drc_buffer_list: list[str] = field(default_factory=list)
    fix_hold_buffer_list: list[str] = field(default_factory=list)
    eco_power_priority: list[str] = field(default_factory=list)

    # ---- Model Extraction ----
    enable_model_extraction: bool = False
    input_transition: float = 0.3

    # ---- Reports and Session ----
    save_session: bool = True
    session_name: str = ""
    report_path: str = "./PT/report"
    output_path: str = "./PT/out"
    enable_analysis_coverage: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "PTStageConfig":
        """Create from dict, ignoring unknown keys."""
        valid = {k for k in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "PTStageConfig":
        """Load directly from a YAML file (pt section)."""
        import yaml
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
        pt_data = raw.get("pt", raw)
        return cls.from_dict(pt_data)
