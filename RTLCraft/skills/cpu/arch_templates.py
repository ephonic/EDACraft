"""
skills.cpu.arch_templates — C910-class CPU architecture definition.

Architecture:
  - 1 × OoO Core (4-wide fetch, 8-issue, 128-entry ROB)
  - 1 × IFU (pcgen + bht + btb + ras + icache_if + ibuf)
  - 1 × IDU (decoder + rename + aiq0 + aiq1 + biq + lsiq)
  - 1 × IU (alu ×2 + bju + mult + div)
  - 1 × LSU (load queue + store queue + dcache)
  - 1 × RTU (rob + pst_preg + retire)
"""
from rtlgen.arch_def import (
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
)
from skills.cpu.cycle_level import (
    ifu_cycle, iu_alu_cycle,
)

XLEN = 64


def build_cpu_arch() -> ArchDefinition:
    arch = ArchDefinition(
        name="RiscvOoO",
        description="RISC-V OoO out-of-order RISC-V CPU",
        isa="riscv64",
    )

    pes = []

    # IFU
    pes.append(ProcessingElement(
        name="IFU", pe_type="ifu",
        behavior=ifu_cycle(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                PortDesc("icache_rdata","input",XLEN), PortDesc("icache_valid","input",1)],
        outputs=[PortDesc("icache_req","output",1), PortDesc("icache_addr","output",XLEN),
                 PortDesc("fetch_valid","output",1), PortDesc("fetch_instr","output",32)],
        state=[StateDesc("pc"), StateDesc("if1_valid"), StateDesc("if2_valid")],
        latency=3, can_stall=True, is_pipeline_stage=True,
        children=[
            ProcessingElement(name="pcgen", pe_type="pcgen"),
            ProcessingElement(name="bht", pe_type="bht"),
            ProcessingElement(name="btb", pe_type="btb"),
            ProcessingElement(name="ras", pe_type="ras"),
        ],
    ))

    # IDU
    pes.append(ProcessingElement(
        name="IDU", pe_type="idu",
        behavior=idu_cycle(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                PortDesc("fetch_valid","input",1)],
        outputs=[PortDesc("decode_valid","output",1), PortDesc("rename_valid","output",1),
                 PortDesc("iq_enqueue","output",1)],
        latency=3, children=[
            ProcessingElement(name="decoder", pe_type="decoder"),
            ProcessingElement(name="rename", pe_type="rename"),
            ProcessingElement(name="aiq0", pe_type="issue_queue"),
            ProcessingElement(name="aiq1", pe_type="issue_queue"),
            ProcessingElement(name="biq", pe_type="issue_queue"),
            ProcessingElement(name="lsiq", pe_type="issue_queue"),
        ],
    ))

    # ALU (×2)
    for i in range(2):
        pes.append(ProcessingElement(
            name=f"ALU{i}", pe_type="iu_alu",
            behavior=iu_alu_cycle(),
            inputs=[PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                    PortDesc("opcode","input",7), PortDesc("src0","input",XLEN), PortDesc("src1","input",XLEN)],
            outputs=[PortDesc("result","output",XLEN)],
            latency=2,
        ))

    # LSU
    pes.append(ProcessingElement(
        name="LSU", pe_type="lsu",
        behavior=lsu_cycle(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                PortDesc("ld_req","input",1), PortDesc("st_req","input",1),
                PortDesc("addr","input",XLEN)],
        outputs=[PortDesc("dcache_req","output",1)],
    ))

    arch.processing_elements = pes
    return arch
