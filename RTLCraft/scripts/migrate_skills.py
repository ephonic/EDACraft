"""
Migrate all skills to the four-layer behavioral structure.

For each skill:
  Layer 1: Functional (combinatorial, no timing)
  Layer 2: Cycle-Level (register-accurate, RTL-matching)
  Layer 3: Skeleton Decomposition (sub-module breakdown)
  Layer 4: RTL-to-DSL Reference (ref_rtl mapping)

Usage:
    python scripts/migrate_skills.py          # migrate all skills
    python scripts/migrate_skills.py --list    # list skills only
"""
import ast
import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")
REF_RTL_DIR = os.path.join(PROJECT_ROOT, "ref_rtl")

# =====================================================================
# Skill definitions
# =====================================================================

SKILL_DEFS: Dict[str, Dict[str, Any]] = {
    "riscv64_soc": {
        "name": "64-Core RISC-V SoC",
        "modules": ["RV64Core", "L1Cache", "CoherenceDir", "L2CacheSlice", "NoCRouter", "NoCBuffer"],
        "ref_rtl": [("cpu", "CPU RISC-V cores"), ("NoC", "Mesh NoC")],
        "done": True,
    },
    "cpu": {
        "name": "T-Head C910 Superscalar CPU",
        "modules": ["IFU", "IDU", "IU", "LSU", "RTU", "PRegFile", "MMU", "VFPU"],
        "ref_rtl": [("cpu/C910_RTL_FACTORY", "C910 out-of-order CPU")],
        "done": False,
    },
    "gpgpu": {
        "name": "Ventus GPGPU",
        "modules": ["CTA_Scheduler", "WarpScheduler", "SM_Wrapper", "SIMD_Pipe"],
        "ref_rtl": [("gpgpu", "Ventus GPGPU")],
        "done": False,
    },
    "npu": {
        "name": "FPGA-NPU AI Accelerator",
        "modules": ["MVU", "MFU", "eVRF", "LD", "NPUTop"],
        "ref_rtl": [("fpga-npu", "Intel FPGA-NPU")],
        "done": False,
    },
    "noc": {
        "name": "8x8 Mesh NoC",
        "modules": ["Router", "Buffer", "CrossBar", "Network"],
        "ref_rtl": [("NoC", "2D mesh NoC")],
        "done": False,
    },
    "fft": {
        "name": "R2^2SDF FFT Accelerator",
        "modules": ["R22SDF_Top", "Butterfly", "DelayLine", "TwiddleROM"],
        "ref_rtl": [("fft", "R2^2SDF FFT")],
        "done": False,
    },
    "dsp": {
        "name": "DSP Library",
        "modules": ["Mult", "DDS", "CIC", "I2S"],
        "ref_rtl": [("dsp", "Alex Forencich DSP")],
        "done": False,
    },
    "codec/ldpc": {
        "name": "LDPC Decoder",
        "modules": ["LDPC_Decoder", "VarNode", "CheckNode"],
        "ref_rtl": [("LDPC_Decoder", "WiMax LDPC")],
        "done": False,
    },
    "codec/video": {
        "name": "H.265/HEVC Encoder",
        "modules": ["CTU", "IntraPred", "InterPred", "Deblock"],
        "ref_rtl": [("xk265", "H.265 encoder")],
        "done": False,
    },
    "image/isp": {
        "name": "ISP Pipeline",
        "modules": ["Bayer", "RGB", "YUV", "Debayer"],
        "ref_rtl": [("ISP", "Infinite-ISP")],
        "done": False,
    },
    "interfaces/axi": {
        "name": "AXI Bus",
        "modules": ["AXI_Arbiter", "AXI_Crossbar", "AXI_Register"],
        "ref_rtl": [("interfaces/axi", "Forencich AXI")],
        "done": False,
    },
    "interfaces/uart": {
        "name": "UART Controller",
        "modules": ["UART_TX", "UART_RX"],
        "ref_rtl": [("interfaces/uart", "Forencich UART")],
        "done": False,
    },
    "interfaces/spi": {
        "name": "SPI Controller",
        "modules": ["SPI_Master", "SPI_Slave", "SPI_Controller"],
        "ref_rtl": [("interfaces/spi", "Cadence SPI")],
        "done": False,
    },
    "interfaces/ethernet": {
        "name": "Ethernet MAC",
        "modules": ["EthMAC", "EthPHY"],
        "ref_rtl": [("interfaces/ethernet", "Forencich Ethernet")],
        "done": False,
    },
    "interfaces/pcie": {
        "name": "PCIe Controller",
        "modules": ["PCIe_TLP", "PCIe_DMA", "PCIe_Config"],
        "ref_rtl": [("interfaces/pcie", "Forencich PCIe")],
        "done": False,
    },
    "mem/ddr3": {
        "name": "DDR3 Memory Controller",
        "modules": ["DDR3_Ctrl", "DFI_Seq", "PHY"],
        "ref_rtl": [("core_ddr3_controller", "Lightweight DDR3")],
        "done": False,
    },
    "mem/cam": {
        "name": "Content-Addressable Memory",
        "modules": ["CamSRL", "CamBRAM", "PriorityEncoder"],
        "ref_rtl": [("cam", "Forencich CAM")],
        "done": False,
    },
}

# =====================================================================
# Generator: produces a 4-layer behaviors.py for any skill
# =====================================================================

def generate_behaviors(skill_key: str) -> str:
    """Generate a 4-layer behaviors.py for a given skill."""
    info = SKILL_DEFS.get(skill_key, {})
    modules = info.get("modules", [])
    refs = info.get("ref_rtl", [])
    skill_name = skill_key.replace("/", "_")
    title = info.get("name", skill_key)

    lines = []
    lines.append(f'"""')
    lines.append(f'skills.{skill_key}.behaviors — Four-Layer Behavioral Models')
    lines.append(f'')
    lines.append(f'{title}')
    lines.append(f'')
    lines.append(f'Layer 1 — Functional (no timing):')
    lines.append(f'  Pure combinatorial functions. inputs → outputs.')
    lines.append(f'')
    lines.append(f'Layer 2 — Cycle-Level (register-accurate):')
    lines.append(f'  CycleContext models with pipeline registers, FSM states.')
    lines.append(f'  Match RTL timing exactly.')
    lines.append(f'')
    lines.append(f'Layer 3 — Module Skeleton Decomposition:')
    lines.append(f'  Sub-module breakdown with port interfaces.')
    lines.append(f'')
    lines.append(f'Layer 4 — RTL-to-DSL Reference:')
    lines.append(f'  DSL module classes converted from ref_rtl Verilog.')
    lines.append(f'"""')

    # Boilerplate imports
    lines.extend([
        "from __future__ import annotations",
        "from typing import Any, Callable, Dict, List, Optional, Tuple",
        "from rtlgen.arch_def import CycleContext",
        "from rtlgen.behaviors import TemplateRegistry",
        "",
    ])

    # ── Layer 1: Functional Models ──
    lines.append("#" + "=" * 75)
    lines.append("# Layer 1: Functional Models (combinatorial, no timing)")
    lines.append("#" + "=" * 75)
    lines.append("")

    for mod in modules:
        name_lower = mod.lower()
        lines.append(f'')
        lines.append(f'def {name_lower}_functional(**kwargs) -> Callable:')
        lines.append(f'    """Functional {mod}. Golden reference for {name_lower}."""')
        lines.append(f'    def func(**inputs) -> Dict:')
        lines.append(f'        """')
        lines.append(f'        {mod} functional behavior.')
        lines.append(f'        Override with actual module logic.')
        lines.append(f'        """')
        lines.append(f'        return {{"valid": True}}')
        lines.append(f'    return func')
        lines.append(f'')

    # ── Layer 2: Cycle-Level Models ──
    lines.append("#" + "=" * 75)
    lines.append("# Layer 2: Cycle-Level Models (register-accurate)")
    lines.append("#" + "=" * 75)
    lines.append("")

    for mod in modules:
        name_lower = mod.lower()
        lines.append(f'')
        lines.append(f'def {name_lower}_cycle(**kwargs) -> Callable[[CycleContext], None]:')
        lines.append(f'    """Cycle-accurate {mod}.')
        lines.append(f'    ')
        lines.append(f'    Override with actual pipeline/FSM logic.')
        lines.append(f'    """')
        lines.append(f'    def behavior(ctx: CycleContext) -> None:')
        lines.append(f'        rst_n = ctx.get_input("rst_n", 1)')
        lines.append(f'        if rst_n == 0:')
        lines.append(f'            # Reset state')
        lines.append(f'            ctx.state["init"] = True')
        lines.append(f'            return')
        lines.append(f'        # TODO: implement cycle-accurate behavior')
        lines.append(f'    return behavior')
        lines.append(f'')

    # ── Layer 3: Skeleton Decomposition ──
    lines.append("#" + "=" * 75)
    lines.append("# Layer 3: Module Skeleton Decomposition")
    lines.append("#" + "=" * 75)
    lines.append("")
    lines.append(f'{skill_name.upper()}_SUBMODULES: Dict[str, Dict] = {{}}')
    lines.append(f'# TODO: add sub-module decomposition')
    lines.append(f'')

    # ── Layer 4: RTL-to-DSL Reference ──
    lines.append("#" + "=" * 75)
    lines.append("# Layer 4: RTL-to-DSL Reference")
    lines.append("#" + "=" * 75)
    lines.append("")
    lines.append(f'# Reference Verilog → DSL module mapping:')
    for ref_path, ref_desc in refs:
        lines.append(f'#   ref_rtl/{ref_path}/  →  skills/{skill_key}/dsl_modules.py  ({ref_desc})')
    lines.append(f'')

    # ── Template Registry ──
    lines.append("#" + "=" * 75)
    lines.append("# Template Registry")
    lines.append("#" + "=" * 75)
    lines.append("")
    lines.append("_template_map = {")
    for mod in modules:
        name_lower = mod.lower()
        pe_type = name_lower
        lines.append(f'    "{pe_type}": {name_lower}_cycle,')
    lines.append("}")
    lines.append("")
    lines.append("for _name, _tmpl in _template_map.items():")
    lines.append("    TemplateRegistry.register(_name, _tmpl)")
    lines.append("")

    return "\n".join(lines)


# =====================================================================
# Generate ref_rtl mapping documentation for Layer 4
# =====================================================================

def generate_ref_rtl_map() -> str:
    """Generate a comprehensive ref_rtl → skill mapping."""
    lines = ["# ref_rtl to Skill Mapping", "#", "# Format: ref_rtl/path/ → skills/skill_name/"]
    for root, dirs, files in os.walk(REF_RTL_DIR):
        v_files = [f for f in files if f.endswith(".v")]
        if v_files:
            rel = os.path.relpath(root, REF_RTL_DIR)
            # Try to match to a skill
            matched_skill = None
            for sk, info in SKILL_DEFS.items():
                for ref_path, _ in info.get("ref_rtl", []):
                    if ref_path in rel or rel in ref_path:
                        matched_skill = sk
                        break
            if matched_skill:
                lines.append(f"#   {rel}/ ({len(v_files)} .v files) → skills/{matched_skill}/")
            else:
                lines.append(f"#   {rel}/ ({len(v_files)} .v files) [unmapped]")
    return "\n".join(lines)


# =====================================================================
# Migration
# =====================================================================

def migrate_skill(skill_key: str, dry_run: bool = False) -> bool:
    """Migrate a single skill to 4-layer structure."""
    skill_dir = os.path.join(SKILLS_DIR, skill_key)
    if not os.path.isdir(skill_dir):
        print(f"  [SKIP] {skill_key}: directory not found")
        return False

    behaviors_path = os.path.join(skill_dir, "behaviors.py")

    # Generate new behaviors.py
    new_content = generate_behaviors(skill_key)
    lines = new_content.count("\n") + 1

    if dry_run:
        print(f"  [DRY] {skill_key}: would generate {lines}-line behaviors.py")
        return True

    # Backup existing
    if os.path.isfile(behaviors_path):
        backup = behaviors_path + ".bak"
        if not os.path.isfile(backup):
            os.rename(behaviors_path, backup)
            print(f"  [BAK] {skill_key}: backed up to behaviors.py.bak")

    # Write new
    with open(behaviors_path, "w") as f:
        f.write(new_content)
    print(f"  [GEN] {skill_key}: {lines}-line behaviors.py with 4 layers")
    return True


def migrate_all(dry_run: bool = False):
    """Migrate all skills to 4-layer structure."""
    print(f"{'=' * 60}")
    print(f"Migrating all skills to 4-layer structure")
    print(f"{'=' * 60}")

    success = 0
    skipped = 0

    riscv64_soc_migrated = False

    for skill_key in sorted(SKILL_DEFS.keys()):
        info = SKILL_DEFS[skill_key]
        skill_dir = os.path.join(SKILLS_DIR, skill_key)

        if not os.path.isdir(skill_dir):
            print(f"  [SKIP] {skill_key}: directory not found")
            skipped += 1
            continue

        if info.get("done"):
            print(f"  [SKIP] {skill_key}: already migrated (riscv64_soc template)")
            skipped += 1
            continue

        if migrate_skill(skill_key, dry_run):
            success += 1
        else:
            skipped += 1

    print(f"\n{'=' * 60}")
    print(f"Migration complete: {success} migrated, {skipped} skipped")
    if dry_run:
        print("(dry run — no files written)")
    print(f"{'=' * 60}")


def list_skills():
    """List all skills and their migration status."""
    print(f"{'Skill Key':30s} {'Status':12s} {'Modules'}")
    print(f"{'-'*30} {'-'*12} {'-'*30}")
    for skill_key in sorted(SKILL_DEFS.keys()):
        info = SKILL_DEFS[skill_key]
        status = "MIGRATED" if info.get("done") else "PENDING"
        mods = ", ".join(info["modules"][:3])
        if len(info["modules"]) > 3:
            mods += f" +{len(info['modules'])-3}"
        print(f"{skill_key:30s} {status:12s} {mods}")


# =====================================================================
# CLI
# =====================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate skills to 4-layer structure")
    parser.add_argument("--list", action="store_true", help="List skills and status")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--skill", type=str, default=None, help="Migrate single skill")
    parser.add_argument("--ref-map", action="store_true", help="Generate ref_rtl mapping")
    args = parser.parse_args()

    if args.list:
        list_skills()
    elif args.ref_map:
        print(generate_ref_rtl_map())
    elif args.skill:
        migrate_skill(args.skill, dry_run=args.dry_run)
    else:
        migrate_all(dry_run=args.dry_run)
