"""CPU Architecture Definition — RISC-V 64 with FPU, targeting 12nm 2GHz."""
from rtlgen.arch_def import (
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec,
)
from rtlgen.registry import TemplateRegistry
from skills.cpu_riscv64 import *
import skills.cpu_riscv64.cycle_level


def build_cpu_arch() -> ArchDefinition:
    arch = ArchDefinition(
        name="Riscv64Fpu",
        description="RISC-V 64-bit single-core with FPU (12nm, 2GHz target)",
        isa="riscv64",
        ppa_targets={
            "max_area": AREA_BUDGET,
            "target_freq": TARGET_FREQ_MHZ * 1e6,
            "tech_node": TECH_NODE,
        },
    )

    pes = []

    # Fetch
    pes.append(ProcessingElement(
        name="Fetch", pe_type="fetch",
        behavior=TemplateRegistry.get("fetch")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("branch_taken","input",1),
                PortDesc("branch_target","input",XLEN),
                PortDesc("stall_fetch","input",1)],
        outputs=[PortDesc("fetch_pc","output",XLEN),
                 PortDesc("fetch_valid","output",1)],
        latency=2,
    ))

    # Execute
    pes.append(ProcessingElement(
        name="Execute", pe_type="execute",
        behavior=TemplateRegistry.get("execute")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("opcode","input",7), PortDesc("funct3","input",3),
                PortDesc("funct7","input",7),
                PortDesc("rs1_val","input",XLEN), PortDesc("rs2_val","input",XLEN),
                PortDesc("imm","input",XLEN), PortDesc("in_valid","input",1)],
        outputs=[PortDesc("result","output",XLEN),
                 PortDesc("out_valid","output",1)],
        latency=L_MUL,
    ))

    # FPU
    pes.append(ProcessingElement(
        name="FPU", pe_type="fpu",
        behavior=TemplateRegistry.get("fpu")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("funct7","input",7), PortDesc("in_valid","input",1),
                PortDesc("result","input",XLEN)],
        outputs=[PortDesc("result","output",XLEN),
                 PortDesc("out_valid","output",1)],
        latency=L_FMA,
    ))

    arch.processing_elements = pes
    return arch
