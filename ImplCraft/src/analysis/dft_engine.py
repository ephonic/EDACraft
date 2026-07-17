"""
DFT Engine — Design-for-Test support.

Provides configurable interfaces for:
  1. SRAM BIST insertion (Memory BIST architecture)
  2. Memory repair logic (spare row/col, repair registers)
  3. DFT scan chain generation (scan insertion, chain stitching)
  4. Test pattern generation (ATPG interface)

Design philosophy:
  - Each capability is a separate, composable interface
  - Scripts are generated per tool (DFT Compiler, Tessent, etc.)
  - User configures all parameters via DFTConfig
  - Agent orchestrates the flow
"""
from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, List, Dict, Optional

logger = logging.getLogger("ic_backend")


# =====================================================================
# Configuration
# =====================================================================

class DFTTool(Enum):
    DFT_COMPILER = "dft_compiler"   # Synopsys
    TESSENT = "tessent"              # Siemens EDA
    GENUS_DFT = "genus_dft"          # Cadence
    CUSTOM = "custom"


class ScanArchitecture(Enum):
    FULL_SCAN = "full_scan"
    PARTIAL_SCAN = "partial_scan"
    SCAN_COMPRESSION = "scan_compression"


class BISTArchitecture(Enum):
    MARCH = "march"          # Standard March algorithm
    MBIST = "mbist"          # Mentor MBIST
    SMARTBIST = "smartbist"  # Synopsys SmartBIST


class RepairStrategy(Enum):
    ROW_ONLY = "row_only"
    COL_ONLY = "col_only"
    ROW_COL = "row_col"
    REDUNDANCY_FUSE = "redundancy_fuse"


@dataclass
class SRAMSpec:
    """SRAM macro specification for BIST/repair."""
    name: str
    depth: int
    width: int
    num_banks: int = 1
    has_redundancy: bool = False
    spare_rows: int = 0
    spare_cols: int = 0
    address_width: int = 0
    data_width: int = 0
    bist_controller: str = ""
    instance_path: str = ""

    def __post_init__(self):
        if self.address_width == 0:
            import math
            self.address_width = math.ceil(math.log2(max(self.depth, 2)))
        if self.data_width == 0:
            self.data_width = self.width


@dataclass
class ScanChainConfig:
    """Scan chain configuration."""
    architecture: ScanArchitecture = ScanArchitecture.FULL_SCAN
    num_chains: int = 1
    max_chain_length: int = 0           # 0 = auto
    clock_domain: str = "clk"
    scan_enable_signal: str = "scan_en"
    scan_input_prefix: str = "scan_in"
    scan_output_prefix: str = "scan_out"
    compression_ratio: int = 1           # For scan compression
    lockup_cell_type: str = "LATCH"      # Lockup cell type
    mixed_signal_handling: str = "skip"  # skip, isolate, wrap


@dataclass
class BISTConfig:
    """Memory BIST configuration."""
    architecture: BISTArchitecture = BISTArchitecture.MARCH
    algorithm: str = "march_c_plus"      # march_c, march_c_plus, march_lr, march_sr
    max_clock_freq_mhz: int = 200
    bist_controller_type: str = "shared"  # shared, dedicated, hierarchical
    max_srams_per_controller: int = 16
    diagnostic_mode: bool = True
    repair_enable: bool = False
    background_patterns: List[str] = field(
        default_factory=lambda: ["solid_0", "solid_1", "checkerboard", "walking_1"]
    )


@dataclass
class RepairConfig:
    """Memory repair configuration."""
    strategy: RepairStrategy = RepairStrategy.ROW_COL
    fuse_type: str = "efuse"              # efuse, laser, anti-fuse
    repair_register_width: int = 8
    repair_controller_name: str = "repair_ctrl"
    max_repair_attempts: int = 3
    yield_target: float = 0.95            # Target yield
    generate_repair_fuse_map: bool = True


@dataclass
class ATPGConfig:
    """ATPG (Automatic Test Pattern Generation) configuration."""
    fault_model: str = "stuck_at"          # stuck_at, transition
    coverage_target: float = 0.99          # 99% coverage
    max_patterns: int = 50000
    pattern_type: str = "basic_scan"       # basic_scan, compressed, atpg
    output_format: str = "stil"            # stil, verilog, wgl
    fault_simulation: bool = True
    bridging_faults: bool = False
    transition_delay: bool = False
    test_compression: bool = False


@dataclass
class DFTConfig:
    """Complete DFT configuration."""
    tool: DFTTool = DFTTool.DFT_COMPILER
    scan: ScanChainConfig = field(default_factory=ScanChainConfig)
    bist: BISTConfig = field(default_factory=BISTConfig)
    repair: RepairConfig = field(default_factory=RepairConfig)
    atpg: ATPGConfig = field(default_factory=ATPGConfig)
    srams: List[SRAMSpec] = field(default_factory=list)

    # Technology
    tech_node_nm: int = 28
    library_path: str = ""
    scan_cell_prefix: str = "SDFF"

    # Output
    output_dir: str = "dft_output"
    design_name: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> DFTConfig:
        """Load DFT config from YAML/JSON."""
        import yaml
        path = Path(path)
        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _parse_enum(cls, enum_cls, val):
        """Parse enum from serialized value (handles 'EnumClass.MEMBER' or 'value')."""
        if isinstance(val, str):
            # Try as value first (e.g., "dft_compiler")
            try:
                return enum_cls(val)
            except ValueError:
                pass
            
            # Try extracting member name (e.g., "DFTTool.DFT_COMPILER" -> "DFT_COMPILER")
            if "." in val:
                member_name = val.split(".")[-1]
                try:
                    return enum_cls[member_name]
                except KeyError:
                    pass
            
            # Try as member name directly
            try:
                return enum_cls[val]
            except KeyError:
                pass
        
        # Fallback: return first enum value
        return list(enum_cls)[0]
    
    @classmethod
    def _from_dict(cls, data: dict) -> DFTConfig:
        cfg = cls()
        if "tool" in data:
            cfg.tool = cls._parse_enum(DFTTool, data["tool"])
        if "scan" in data:
            scan_data = dict(data["scan"])
            if "architecture" in scan_data and isinstance(scan_data["architecture"], str):
                scan_data["architecture"] = cls._parse_enum(ScanArchitecture, scan_data["architecture"])
            cfg.scan = ScanChainConfig(**scan_data)
        if "bist" in data:
            bist_data = dict(data["bist"])
            if "architecture" in bist_data and isinstance(bist_data["architecture"], str):
                bist_data["architecture"] = cls._parse_enum(BISTArchitecture, bist_data["architecture"])
            cfg.bist = BISTConfig(**bist_data)
        if "repair" in data:
            repair_data = dict(data["repair"])
            if "strategy" in repair_data and isinstance(repair_data["strategy"], str):
                repair_data["strategy"] = cls._parse_enum(RepairStrategy, repair_data["strategy"])
            cfg.repair = RepairConfig(**repair_data)
        if "atpg" in data:
            cfg.atpg = ATPGConfig(**data["atpg"])
        if "srams" in data:
            cfg.srams = [SRAMSpec(**s) for s in data["srams"]]
        for k in ("tech_node_nm", "library_path", "scan_cell_prefix",
                   "output_dir", "design_name"):
            if k in data:
                setattr(cfg, k, data[k])
        return cfg

    def save(self, path: str | Path):
        """Save config to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)


# =====================================================================
# Script Generators
# =====================================================================

class ScanInsertionEngine:
    """
    Generate scan insertion scripts for various tools.
    """

    def __init__(self, config: DFTConfig):
        self.config = config

    def generate_script(self, tool: DFTTool | None = None) -> str:
        tool = tool or self.config.tool
        generators = {
            DFTTool.DFT_COMPILER: self._gen_dft_compiler_scan,
            DFTTool.TESSENT: self._gen_tessent_scan,
            DFTTool.GENUS_DFT: self._gen_genus_scan,
        }
        gen = generators.get(tool, self._gen_dft_compiler_scan)
        return gen()

    def _gen_dft_compiler_scan(self) -> str:
        cfg = self.config
        scan = cfg.scan

        lines = [
            f"/* DFT Compiler - Scan Insertion Script */",
            f"/* Design: {cfg.design_name} */",
            f"/* Architecture: {scan.architecture.value} */",
            "",
            f"/* Read design */",
            f"read_ddc {cfg.design_name}.ddc",
            "",
            f"/* Configure scan */",
            f"set_scan_configuration \\",
            f"  -chain_count {scan.num_chains} \\",
        ]

        if scan.max_chain_length > 0:
            lines.append(f"  -max_length {scan.max_chain_length} \\")

        if scan.architecture == ScanArchitecture.SCAN_COMPRESSION:
            lines.append(f"  -dft_compression \\")
            lines.append(f"  -compression_ratio {scan.compression_ratio} \\")

        lines.extend([
            f"  -clock_mixing {scan.clock_domain} \\",
            f"  -create_test_protocol",
            "",
            f"/* Scan replacement - replace flip-flops with scan cells */",
            f"set_scan_configuration \\",
            f"  -replace TRUE \\",
            f"  -scan_cell_prefix {cfg.scan_cell_prefix}",
            "",
            f"/* Insert scan chains */",
            f"insert_scan",
            "",
            f"/* Configure scan I/O */",
            f"set_scan_configuration \\",
            f"  -scan_input {scan.scan_input_prefix}[0:{scan.num_chains-1}] \\",
            f"  -scan_output {scan.scan_output_prefix}[0:{scan.num_chains-1}] \\",
            f"  -scan_enable {scan.scan_enable_signal}",
            "",
            f"/* Stitch scan chains */",
            f"set_scan_configuration \\",
            f"  -internal_chain_order auto \\",
            f"  -lockup_cell_type {scan.lockup_cell_type}",
            "",
            f"/* Create scan test protocol */",
            f"create_test_protocol -inputs -clock {scan.clock_domain}",
            "",
            f"/* Verify scan chains */",
            f"report_scan_path -cells",
            f"report_scan_path -chains",
            f"check_scan",
            "",
            f"/* Write scan-inserted netlist */",
            f"write -format verilog -hierarchy -output {cfg.design_name}_scan.v",
            f"write_scan_def -output {cfg.design_name}_scan.def",
            "",
            f"exit",
        ])
        return "\n".join(lines)

    def _gen_tessent_scan(self) -> str:
        cfg = self.config
        scan = cfg.scan

        lines = [
            f"# Tessent Scan Insertion Script",
            f"# Design: {cfg.design_name}",
            "",
            f"SetContextDesign {cfg.design_name}",
            f"SetContextModule {cfg.design_name}",
            "",
            f"# Set scan architecture",
            f"SetScanConfiguration \\",
            f"  -ChainCount {scan.num_chains} \\",
            f"  -ClockDomain {scan.clock_domain} \\",
            f"  -ScanEnable {scan.scan_enable_signal}",
            "",
            f"# Insert scan chains",
            f"AddScanCells -Replace TRUE",
            "",
            f"# Configure scan I/O",
        ]

        for i in range(scan.num_chains):
            lines.append(f"AddScanInput  -Pin {scan.scan_input_prefix}_{i}")
            lines.append(f"AddScanOutput -Pin {scan.scan_output_prefix}_{i}")

        lines.extend([
            "",
            f"# Stitch scan chains",
            f"StitchScanChains",
            "",
            f"# Verify",
            f"ReportScanChains",
            f"VerifyScanChains",
            "",
            f"# Export",
            f"WriteDesign -Format Verilog {cfg.design_name}_scan.v",
            "",
            f"Exit",
        ])
        return "\n".join(lines)

    def _gen_genus_scan(self) -> str:
        cfg = self.config
        scan = cfg.scan

        lines = [
            f"# Genus DFT - Scan Insertion",
            f"# Design: {cfg.design_name}",
            "",
            f"set_db dft_scan_style {scan.architecture.value}",
            f"set_db dft_scan_chains {scan.num_chains}",
            f"set_db dft_scan_clock {scan.clock_domain}",
            f"set_db dft_scan_enable {scan.scan_enable_signal}",
            "",
            f"# Insert scan",
            f"check_dft_rules",
            f"set_scan -enable",
            f"connect_scan_chains",
            "",
            f"# Export",
            f"write_hdl -sv -mapped > {cfg.design_name}_scan.v",
            "",
        ]
        return "\n".join(lines)


class BISTInsertionEngine:
    """
    Generate BIST insertion scripts.
    """

    def __init__(self, config: DFTConfig):
        self.config = config

    def generate_script(self, tool: DFTTool | None = None) -> str:
        tool = tool or self.config.tool
        if tool == DFTTool.TESSENT:
            return self._gen_tessent_bist()
        return self._gen_synopsys_bist()

    def _gen_synopsys_bist(self) -> str:
        cfg = self.config
        bist = cfg.bist
        srams = cfg.srams

        lines = [
            f"/* Memory BIST Insertion Script */",
            f"/* Design: {cfg.design_name} */",
            f"/* Architecture: {bist.architecture.value} */",
            f"/* Algorithm: {bist.algorithm} */",
            f"/* SRAMs: {len(srams)} */",
            "",
            f"/* Read design */",
            f"read_ddc {cfg.design_name}.ddc",
            "",
            f"/* Configure MBIST */",
            f"set_bist_configuration \\",
            f"  -architecture {bist.architecture.value} \\",
            f"  -algorithm {bist.algorithm} \\",
            f"  -max_clock_frequency {bist.max_clock_freq_mhz}",
            "",
        ]

        # Group SRAMs by controller
        if bist.bist_controller_type == "shared":
            groups = self._group_srams(srams, bist.max_srams_per_controller)
            for i, group in enumerate(groups):
                controller_name = f"bist_ctrl_{i}"
                lines.append(f"/* BIST Controller {i}: {len(group)} SRAMs */")
                lines.append(f"create_bist_controller -name {controller_name} \\")
                lines.append(f"  -srams {{")
                for sram in group:
                    lines.append(f"    {sram.instance_path or sram.name}")
                lines.append(f"  }}")
                lines.append("")
        else:
            # Dedicated controller per SRAM
            for sram in srams:
                controller_name = f"bist_ctrl_{sram.name}"
                lines.append(f"create_bist_controller -name {controller_name} \\")
                lines.append(f"  -srams {{ {sram.instance_path or sram.name} }}")
                lines.append("")

        # Diagnostic mode
        if bist.diagnostic_mode:
            lines.extend([
                f"/* Enable diagnostic mode */",
                f"set_bist_configuration -diagnostic_mode TRUE",
                f"set_bist_configuration -fail_data_collection ALL",
                "",
            ])

        # Background patterns
        lines.append(f"/* Background patterns */")
        for pattern in bist.background_patterns:
            lines.append(f"add_bist_pattern -name {pattern}")
        lines.append("")

        # Insert BIST
        lines.extend([
            f"/* Insert BIST logic */",
            f"insert_bist",
            "",
            f"/* Verify */",
            f"report_bist -controllers",
            f"report_bist -srams",
            f"check_bist",
            "",
            f"/* Export */",
            f"write -format verilog -hierarchy -output {cfg.design_name}_bist.v",
            "",
            f"exit",
        ])
        return "\n".join(lines)

    def _gen_tessent_bist(self) -> str:
        cfg = self.config
        bist = cfg.bist
        srams = cfg.srams

        lines = [
            f"# Tessent MemoryBIST Insertion Script",
            f"# Design: {cfg.design_name}",
            f"# SRAMs: {len(srams)}",
            "",
            f"SetContextDesign {cfg.design_name}",
            "",
            f"# Configure BIST",
            f"SetMemoryBistConfiguration \\",
            f"  -Algorithm {bist.algorithm} \\",
            f"  -ClockFrequency {bist.max_clock_freq_mhz}",
            "",
        ]

        # Add SRAMs
        for sram in srams:
            lines.extend([
                f"AddMemoryBist -Instance {sram.instance_path or sram.name} \\",
                f"  -Depth {sram.depth} -Width {sram.width}",
            ])

        lines.extend([
            "",
            f"# Insert BIST",
            f"InsertMemoryBist",
            "",
            f"# Verify",
            f"ReportMemoryBist",
            f"VerifyMemoryBist",
            "",
            f"# Export",
            f"WriteDesign -Format Verilog {cfg.design_name}_bist.v",
            "",
            f"Exit",
        ])
        return "\n".join(lines)

    def _group_srams(self, srams: List[SRAMSpec], max_per_group: int) -> List[List[SRAMSpec]]:
        """Group SRAMs for shared controller."""
        groups = []
        for i in range(0, len(srams), max_per_group):
            groups.append(srams[i:i + max_per_group])
        return groups


class RepairLogicEngine:
    """
    Generate memory repair logic scripts.
    """

    def __init__(self, config: DFTConfig):
        self.config = config

    def generate_script(self) -> str:
        cfg = self.config
        repair = cfg.repair
        srams = [s for s in cfg.srams if s.has_redundancy]

        lines = [
            f"/* Memory Repair Logic Insertion */",
            f"/* Design: {cfg.design_name} */",
            f"/* Strategy: {repair.strategy.value} */",
            f"/* Fuse type: {repair.fuse_type} */",
            f"/* Repairable SRAMs: {len(srams)} */",
            "",
            f"/* Read design */",
            f"read_ddc {cfg.design_name}.ddc",
            "",
            f"/* Configure repair */",
            f"set_repair_configuration \\",
            f"  -strategy {repair.strategy.value} \\",
            f"  -fuse_type {repair.fuse_type} \\",
            f"  -register_width {repair.repair_register_width} \\",
            f"  -controller_name {repair.repair_controller_name}",
            "",
        ]

        # Generate repair wrapper for each repairable SRAM
        for sram in srams:
            lines.extend([
                f"/* Repair wrapper for {sram.name} */",
                f"create_repair_wrapper \\",
                f"  -sram {sram.instance_path or sram.name} \\",
                f"  -spare_rows {sram.spare_rows} \\",
                f"  -spare_cols {sram.spare_cols} \\",
                f"  -address_width {sram.address_width} \\",
                f"  -data_width {sram.data_width}",
                "",
            ])

        # Generate repair controller
        lines.extend([
            f"/* Repair controller */",
            f"create_repair_controller \\",
            f"  -name {repair.repair_controller_name} \\",
            f"  -fuse_map_file {cfg.design_name}_fuse_map.dat \\",
            f"  -max_attempts {repair.max_repair_attempts}",
            "",
        ])

        # Generate fuse map
        if repair.generate_repair_fuse_map:
            lines.extend([
                f"/* Generate fuse map */",
                f"generate_fuse_map \\",
                f"  -output {cfg.design_name}_fuse_map.dat \\",
                f"  -format {repair.fuse_type}",
                "",
            ])

        # Insert repair logic
        lines.extend([
            f"/* Insert repair logic */",
            f"insert_repair_logic",
            "",
            f"/* Verify */",
            f"report_repair -srams",
            f"report_repair -controllers",
            f"report_repair -fuse_map",
            f"check_repair",
            "",
            f"/* Export */",
            f"write -format verilog -hierarchy -output {cfg.design_name}_repair.v",
            "",
            f"exit",
        ])
        return "\n".join(lines)

    def generate_verilog_wrapper(self, sram: SRAMSpec) -> str:
        """Generate Verilog wrapper for SRAM repair logic."""
        repair = self.config.repair
        name = sram.name

        lines = [
            f"// SRAM Repair Wrapper for {name}",
            f"// Spare rows: {sram.spare_rows}, Spare cols: {sram.spare_cols}",
            f"module {name}_repair_wrapper (",
            f"  input  wire                   clk,",
            f"  input  wire                   rst_n,",
            f"  input  wire                   repair_mode,",
            f"  input  wire [{sram.address_width-1}:0] addr,",
            f"  input  wire [{sram.data_width-1}:0]    data_in,",
            f"  input  wire                   write_en,",
            f"  output wire [{sram.data_width-1}:0]    data_out,",
            f"  input  wire [{repair.repair_register_width-1}:0] repair_fuse,",
            f"  output wire                   repair_pass",
            f");",
            "",
            f"  // Repair logic",
            f"  wire [{sram.address_width-1}:0] remapped_addr;",
            f"  wire [{sram.data_width-1}:0]    remapped_data;",
            "",
            f"  // Address remapping based on fuse values",
            f"  {name}_addr_remap u_addr_remap (",
            f"    .addr(addr),",
            f"    .fuse(repair_fuse),",
            f"    .remapped_addr(remapped_addr)",
            f"  );",
            "",
            f"  // Data remapping for column repair",
            f"  {name}_data_remap u_data_remap (",
            f"    .data_in(data_in),",
            f"    .fuse(repair_fuse),",
            f"    .data_out(remapped_data)",
            f"  );",
            "",
            f"  // Original SRAM instance",
            f"  {name} u_sram (",
            f"    .clk(clk),",
            f"    .addr(remapped_addr),",
            f"    .data_in(remapped_data),",
            f"    .write_en(write_en),",
            f"    .data_out(data_out)",
            f"  );",
            "",
            f"  // Repair status",
            f"  assign repair_pass = ~|repair_fuse;  // Pass if no repairs used",
            "",
            f"endmodule",
        ]
        return "\n".join(lines)


class ATPGEngine:
    """
    Generate ATPG scripts for test pattern generation.
    """

    def __init__(self, config: DFTConfig):
        self.config = config

    def generate_script(self, tool: DFTTool | None = None) -> str:
        tool = tool or self.config.tool
        if tool == DFTTool.TESSENT:
            return self._gen_tessent_atpg()
        return self._gen_dft_compiler_atpg()

    def _gen_dft_compiler_atpg(self) -> str:
        cfg = self.config
        atpg = cfg.atpg

        lines = [
            f"/* ATPG - Test Pattern Generation */",
            f"/* Design: {cfg.design_name} */",
            f"/* Fault model: {atpg.fault_model} */",
            f"/* Coverage target: {atpg.coverage_target:.1%} */",
            "",
            f"/* Read scan-inserted design */",
            f"read_ddc {cfg.design_name}_scan.ddc",
            "",
            f"/* Read test protocol */",
            f"read_test_protocol {cfg.design_name}_scan.spf",
            "",
            f"/* Configure ATPG */",
            f"set_atpg_configuration \\",
            f"  -fault_model {atpg.fault_model} \\",
            f"  -coverage_target {atpg.coverage_target} \\",
            f"  -max_patterns {atpg.max_patterns}",
            "",
        ]

        if atpg.transition_delay:
            lines.extend([
                f"/* Transition delay fault ATPG */",
                f"set_atpg_configuration \\",
                f"  -add_fault_model transition \\",
                f"  -transition_delay TRUE",
                "",
            ])

        if atpg.bridging_faults:
            lines.extend([
                f"/* Bridging fault ATPG */",
                f"set_atpg_configuration \\",
                f"  -add_fault_model bridging",
                "",
            ])

        lines.extend([
            f"/* Create faults */",
            f"create_faults -all",
            "",
            f"/* Generate test patterns */",
            f"create_patterns",
            "",
            f"/* Fault simulation */",
        ])

        if atpg.fault_simulation:
            lines.append(f"simulate_patterns -fault_coverage")
        else:
            lines.append(f"# Fault simulation disabled")

        lines.extend([
            "",
            f"/* Pattern compaction */",
            f"compact_patterns",
            "",
            f"/* Reports */",
            f"report_atpg -summary",
            f"report_atpg -coverage",
            f"report_atpg -patterns",
            "",
            f"/* Export patterns */",
        ])

        # Export based on format
        if atpg.output_format == "stil":
            lines.append(f"write_patterns -format stil -output {cfg.design_name}.stil")
        elif atpg.output_format == "verilog":
            lines.append(f"write_patterns -format verilog -output {cfg.design_name}_patterns.v")
        elif atpg.output_format == "wgl":
            lines.append(f"write_patterns -format wgl -output {cfg.design_name}.wgl")

        lines.extend([
            "",
            f"exit",
        ])
        return "\n".join(lines)

    def _gen_tessent_atpg(self) -> str:
        cfg = self.config
        atpg = cfg.atpg

        lines = [
            f"# Tessent ATPG Script",
            f"# Design: {cfg.design_name}",
            "",
            f"SetContextDesign {cfg.design_name}",
            f"SetContextModule {cfg.design_name}",
            "",
            f"# Configure ATPG",
            f"SetAtpgConfiguration \\",
            f"  -FaultModel {atpg.fault_model} \\",
            f"  -Coverage {atpg.coverage_target} \\",
            f"  -MaxPatterns {atpg.max_patterns}",
            "",
            f"# Create faults",
            f"CreateFaults -All",
            "",
            f"# Generate patterns",
            f"CreatePatterns",
            "",
        ]

        if atpg.fault_simulation:
            lines.append(f"SimulatePatterns -FaultCoverage")

        lines.extend([
            "",
            f"# Reports",
            f"ReportCoverage",
            f"ReportPatterns",
            "",
            f"# Export patterns",
            f"WritePatterns -Format {atpg.output_format.upper()} {cfg.design_name}.{atpg.output_format}",
            "",
            f"Exit",
        ])
        return "\n".join(lines)

    def generate_verilog_testbench(self) -> str:
        """Generate Verilog testbench for ATPG patterns."""
        cfg = self.config

        lines = [
            f"// ATPG Testbench for {cfg.design_name}",
            f"`timescale 1ns/1ps",
            "",
            f"module {cfg.design_name}_atpg_tb;",
            "",
            f"  // Clock",
            f"  reg clk;",
            f"  initial begin",
            f"    clk = 0;",
            f"    forever #5 clk = ~clk;",
            f"  end",
            "",
            f"  // Scan control",
            f"  reg scan_en;",
            f"  reg scan_in;",
            f"  reg scan_out;",
            "",
            f"  // DUT",
            f"  {cfg.design_name} dut (",
            f"    .clk(clk),",
            f"    .scan_en(scan_en),",
            f"    .scan_in(scan_in),",
            f"    .scan_out(scan_out)",
            f"  );",
            "",
            f"  // Apply ATPG patterns",
            f"  initial begin",
            f"    $readmemh(\"{cfg.design_name}_patterns.hex\", pattern_mem);",
            f"    // Shift-in patterns and capture responses",
            f"    // (Auto-generated from ATPG tool)",
            f"    #1000;",
            f"    $finish;",
            f"  end",
            "",
            f"endmodule",
        ]
        return "\n".join(lines)


# =====================================================================
# Main DFT Engine
# =====================================================================

class DFTEngine:
    """
    Main DFT Engine — orchestrates all DFT operations.

    Usage:
        config = DFTConfig(
            design_name="my_soc",
            srams=[SRAMSpec(name="sram_256x32", depth=256, width=32)],
        )

        engine = DFTEngine(config)

        # Generate scan insertion script
        scan_script = engine.scan.generate_script()

        # Generate BIST insertion script
        bist_script = engine.bist.generate_script()

        # Generate repair logic script
        repair_script = engine.repair.generate_script()

        # Generate ATPG script
        atpg_script = engine.atpg.generate_script()

        # Write all scripts
        engine.write_all_scripts("output/dft")
    """

    def __init__(self, config: DFTConfig):
        self.config = config
        self.scan = ScanInsertionEngine(config)
        self.bist = BISTInsertionEngine(config)
        self.repair = RepairLogicEngine(config)
        self.atpg = ATPGEngine(config)

    def write_all_scripts(self, output_dir: str | Path) -> Dict[str, Path]:
        """Generate and write all DFT scripts."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        scripts = {}

        # Scan insertion
        scan_script = self.scan.generate_script()
        scan_path = output_dir / "scan_insertion.tcl"
        scan_path.write_text(scan_script)
        scripts["scan"] = scan_path

        # BIST insertion
        if self.config.srams:
            bist_script = self.bist.generate_script()
            bist_path = output_dir / "bist_insertion.tcl"
            bist_path.write_text(bist_script)
            scripts["bist"] = bist_path

            # Repair logic
            repair_script = self.repair.generate_script()
            repair_path = output_dir / "repair_insertion.tcl"
            repair_path.write_text(repair_script)
            scripts["repair"] = repair_path

            # Per-SRAM repair wrappers
            for sram in self.config.srams:
                if sram.has_redundancy:
                    wrapper = self.repair.generate_verilog_wrapper(sram)
                    wrapper_path = output_dir / f"{sram.name}_repair_wrapper.v"
                    wrapper_path.write_text(wrapper)
                    scripts[f"repair_wrapper_{sram.name}"] = wrapper_path

        # ATPG
        atpg_script = self.atpg.generate_script()
        atpg_path = output_dir / "atpg_patterns.tcl"
        atpg_path.write_text(atpg_script)
        scripts["atpg"] = atpg_path

        # ATPG testbench
        tb_script = self.atpg.generate_verilog_testbench()
        tb_path = output_dir / f"{self.config.design_name}_atpg_tb.v"
        tb_path.write_text(tb_script)
        scripts["atpg_testbench"] = tb_path

        # Flow script (runs all in order)
        flow_script = self._generate_flow_script(output_dir)
        flow_path = output_dir / "dft_flow.tcl"
        flow_path.write_text(flow_script)
        scripts["flow"] = flow_path

        # Save config
        self.config.save(output_dir / "dft_config.json")

        return scripts

    def _generate_flow_script(self, output_dir: Path) -> str:
        """Generate master flow script that runs all DFT stages."""
        lines = [
            f"# DFT Master Flow Script",
            f"# Design: {self.config.design_name}",
            f"# Generated: {output_dir}",
            "",
            f"# Stage 1: Scan Insertion",
            f"source scan_insertion.tcl",
            "",
        ]

        if self.config.srams:
            lines.extend([
                f"# Stage 2: BIST Insertion",
                f"source bist_insertion.tcl",
                "",
                f"# Stage 3: Repair Logic Insertion",
                f"source repair_insertion.tcl",
                "",
            ])

        lines.extend([
            f"# Stage 4: ATPG Pattern Generation",
            f"source atpg_patterns.tcl",
            "",
            f"# Done",
            f"echo 'DFT flow completed'",
        ])
        return "\n".join(lines)

    def get_summary(self) -> str:
        """Generate DFT configuration summary."""
        cfg = self.config
        lines = [
            f"DFT Configuration Summary",
            f"{'=' * 60}",
            f"Design: {cfg.design_name}",
            f"Tool: {cfg.tool.value}",
            f"Tech node: {cfg.tech_node_nm}nm",
            "",
            f"Scan Configuration:",
            f"  Architecture: {cfg.scan.architecture.value}",
            f"  Chains: {cfg.scan.num_chains}",
            f"  Clock: {cfg.scan.clock_domain}",
            f"  Scan enable: {cfg.scan.scan_enable_signal}",
            "",
        ]

        if cfg.srams:
            lines.extend([
                f"SRAMs ({len(cfg.srams)}):",
            ])
            for sram in cfg.srams:
                repair_info = ""
                if sram.has_redundancy:
                    repair_info = f", {sram.spare_rows}R/{sram.spare_cols}C spare"
                lines.append(f"  {sram.name}: {sram.depth}x{sram.width}{repair_info}")
            lines.append("")

            lines.extend([
                f"BIST Configuration:",
                f"  Architecture: {cfg.bist.architecture.value}",
                f"  Algorithm: {cfg.bist.algorithm}",
                f"  Controller: {cfg.bist.bist_controller_type}",
                f"  Max per controller: {cfg.bist.max_srams_per_controller}",
                f"  Diagnostic mode: {cfg.bist.diagnostic_mode}",
                "",
            ])

            repairable = [s for s in cfg.srams if s.has_redundancy]
            if repairable:
                lines.extend([
                    f"Repair Configuration:",
                    f"  Strategy: {cfg.repair.strategy.value}",
                    f"  Fuse type: {cfg.repair.fuse_type}",
                    f"  Repairable SRAMs: {len(repairable)}/{len(cfg.srams)}",
                    "",
                ])

        lines.extend([
            f"ATPG Configuration:",
            f"  Fault model: {cfg.atpg.fault_model}",
            f"  Coverage target: {cfg.atpg.coverage_target:.1%}",
            f"  Max patterns: {cfg.atpg.max_patterns}",
            f"  Output format: {cfg.atpg.output_format}",
            f"  Transition delay: {cfg.atpg.transition_delay}",
            f"  Bridging faults: {cfg.atpg.bridging_faults}",
        ])

        return "\n".join(lines)
