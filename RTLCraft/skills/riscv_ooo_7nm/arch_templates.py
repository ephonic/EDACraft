"""Architecture definition for the 7nm OoO RISC-V core.

Pipeline:
  Fetch (3-stage) → Decode (2-stage) → Rename → Issue Queue → Execute → Commit

Architecture parameters (from high_perf preset):
  - 8-wide fetch, 6-wide decode/rename/dispatch/commit
  - 256-entry ROB, 192 physical registers
  - 4 ALU pipes, 2 load pipes, 2 store pipes, 4 FPU pipes
  - 48-entry IBUF, 80-entry LQ, 64-entry SQ
  - 7nm, 2GHz target
"""

from rtlgen.arch_def import ArchDefinition, ProcessingElement, PortDesc, StateDesc

from skills.riscv_ooo_7nm.cycle_level import (
    fetch_stage_cycle,
    decode_stage_cycle,
    issue_queue_cycle,
    alu_exec_cycle,
    lsu_cycle,
    rob_cycle,
)
from skills.riscv_ooo_7nm.params import ooo_7nm_params


def build_ooo_arch() -> ArchDefinition:
    """Build the full OoO core architecture definition."""
    params = ooo_7nm_params()
    arch = ArchDefinition(
        name="RiscvOoO_7nm",
        description="8-wide out-of-order RISC-V core, 7nm, 2GHz",
        isa="riscv64",
    )

    pes = []

    # ── Frontend: Fetch ──
    pes.append(ProcessingElement(
        name="Fetch", pe_type="fetch",
        behavior=fetch_stage_cycle(),
        description="3-stage fetch: PCGen → I-Cache → IBUF",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst_n", "input", 1),
            PortDesc("branch_redirect", "input", 1),
            PortDesc("branch_target", "input", 64),
            PortDesc("icache_ready", "input", 1),
        ],
        outputs=[
            PortDesc("fetch_valid", "output", 1),
            PortDesc("fetch_pc", "output", 64),
            PortDesc("fetch_instr", "output", 32),
            PortDesc("ibuf_write", "output", 1),
            PortDesc("ibuf_data", "output", 32),
        ],
        state=[
            StateDesc("pc", 64), StateDesc("stall", 1),
            StateDesc("branch_redirect", 1),
        ],
        latency=3, can_stall=True, is_pipeline_stage=True,
        children=[
            ProcessingElement(name="pcgen", pe_type="pcgen",
                inputs=[PortDesc("branch_redirect","input",1),
                        PortDesc("branch_target","input",64)],
                outputs=[PortDesc("pc_out","output",64)],
            ),
            ProcessingElement(name="icache", pe_type="icache",
                latency=2, can_stall=True,
            ),
        ],
    ))

    # ── Frontend: Branch Predictor ──
    pes.append(ProcessingElement(
        name="BPred", pe_type="bpred",
        description="TAGE-SC branch predictor + BTB + RAS",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("fetch_pc","input",64),
        ],
        outputs=[
            PortDesc("pred_taken","output",1),
            PortDesc("pred_target","output",64),
        ],
        state=[StateDesc("bht"), StateDesc("btb"), StateDesc("ras")],
        latency=1,
    ))

    # ── Backend: Decode & Rename ──
    pes.append(ProcessingElement(
        name="Decode", pe_type="decode",
        behavior=decode_stage_cycle(),
        description="2-stage decode + register rename",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("fetch_valid","input",1),
            PortDesc("instr","input",32),
            PortDesc("pipeline_stall","input",1),
        ],
        outputs=[
            PortDesc("rename_valid","output",1),
            PortDesc("rd","output",5), PortDesc("rs1","output",5),
            PortDesc("rs2","output",5), PortDesc("funct3","output",3),
            PortDesc("opcode_out","output",7),
            PortDesc("is_alu","output",1), PortDesc("is_branch","output",1),
            PortDesc("is_load","output",1), PortDesc("is_store","output",1),
            PortDesc("is_mul","output",1), PortDesc("is_fpu","output",1),
        ],
        state=[StateDesc("decode_valid"), StateDesc("opcode")],
        latency=2,
        children=[
            ProcessingElement(name="decoder", pe_type="decoder"),
            ProcessingElement(name="rename", pe_type="rename"),
        ],
    ))

    # ── Backend: Issue Queues (×6: 2 ALU, 1 Branch, 1 Load, 1 Store, 1 FPU) ──
    for name, qtype in [("IQ_ALU0", "alu"), ("IQ_ALU1", "alu"),
                         ("IQ_Branch", "branch"), ("IQ_Load", "load"),
                         ("IQ_Store", "store"), ("IQ_FPU", "fpu")]:
        pes.append(ProcessingElement(
            name=name, pe_type=f"issue_queue_{qtype}",
            behavior=issue_queue_cycle(),
            description=f"16-entry {qtype} issue queue with wakeup+select",
            inputs=[
                PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                PortDesc("enqueue","input",1),
                PortDesc("wakeup_pdst","input",8),
                PortDesc("wakeup_valid","input",1),
            ],
            outputs=[
                PortDesc("issue_valid","output",1),
                PortDesc("issue_pdst","output",8),
            ],
            state=[StateDesc("q_valid"), StateDesc("q_ready"),
                   StateDesc("q_pdst"), StateDesc("q_ready_count")],
            latency=1,
        ))

    # ── Backend: Execution Units ──
    for i in range(4):  # 4 ALU pipes
        pes.append(ProcessingElement(
            name=f"ALU{i}", pe_type="alu",
            behavior=alu_exec_cycle(),
            description="Single-cycle arithmetic/logic execution",
            inputs=[
                PortDesc("clk","input",1), PortDesc("rst_n","input",1),
                PortDesc("issue_valid","input",1),
                PortDesc("opcode","input",7), PortDesc("funct3","input",3),
                PortDesc("funct7","input",7),
                PortDesc("src0","input",64), PortDesc("src1","input",64),
            ],
            outputs=[
                PortDesc("result_valid","output",1),
                PortDesc("result","output",64),
            ],
            state=[StateDesc("busy")],
            latency=1,
        ))

    # Branch execution unit
    pes.append(ProcessingElement(
        name="BJU", pe_type="bju",
        description="Branch execution: resolves conditional branches",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("issue_valid","input",1),
            PortDesc("src0","input",64), PortDesc("src1","input",64),
            PortDesc("funct3","input",3),
        ],
        outputs=[
            PortDesc("branch_taken","output",1),
            PortDesc("branch_target","output",64),
        ],
        latency=1,
    ))

    # Load/Store Unit
    pes.append(ProcessingElement(
        name="LSU", pe_type="lsu",
        behavior=lsu_cycle(),
        description="Load/store execution with address generation",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("ld_req","input",1), PortDesc("st_req","input",1),
            PortDesc("addr","input",64),
            PortDesc("st_data","input",64),
            PortDesc("funct3","input",3),
        ],
        outputs=[
            PortDesc("ld_result","output",64),
            PortDesc("ld_result_valid","output",1),
            PortDesc("st_done","output",1),
            PortDesc("st_addr_out","output",64),
            PortDesc("st_data_out","output",64),
        ],
        state=[StateDesc("st_addr")],
        latency=2,
        children=[
            ProcessingElement(name="addrgen", pe_type="addrgen"),
            ProcessingElement(name="dcache", pe_type="dcache"),
        ],
    ))

    # Multiplier
    pes.append(ProcessingElement(
        name="MUL", pe_type="mul",
        description="3-cycle pipelined multiplier",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("issue_valid","input",1),
            PortDesc("src0","input",64), PortDesc("src1","input",64),
            PortDesc("is_signed","input",1),
        ],
        outputs=[
            PortDesc("result_valid","output",1),
            PortDesc("result_lo","output",64),
            PortDesc("result_hi","output",64),
        ],
        latency=3,
    ))

    # Divider
    pes.append(ProcessingElement(
        name="DIV", pe_type="div",
        description="Multi-cycle divider (restoring, up to 64 cycles)",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("issue_valid","input",1),
            PortDesc("src0","input",64), PortDesc("src1","input",64),
        ],
        outputs=[
            PortDesc("result_valid","output",1),
            PortDesc("result_quot","output",64),
            PortDesc("result_rem","output",64),
        ],
        latency=64, can_stall=True,
    ))

    # ── Backend: Reorder Buffer ──
    pes.append(ProcessingElement(
        name="ROB", pe_type="rob",
        behavior=rob_cycle(),
        description="256-entry reorder buffer with completion tracking",
        inputs=[
            PortDesc("clk","input",1), PortDesc("rst_n","input",1),
            PortDesc("dispatch_valid","input",1),
            PortDesc("dispatch_pc","input",64),
            PortDesc("dispatch_rd","input",5),
            PortDesc("dispatch_pdst","input",8),
            PortDesc("complete_valid","input",1),
            PortDesc("complete_pdst","input",8),
            PortDesc("complete_exception","input",1),
        ],
        outputs=[
            PortDesc("commit_valid","output",1),
            PortDesc("commit_pc","output",64),
            PortDesc("commit_rd","output",5),
            PortDesc("commit_pdst","output",8),
            PortDesc("full","output",1),
            PortDesc("empty","output",1),
        ],
        state=[
            StateDesc("rob_head"), StateDesc("rob_tail"),
            StateDesc("rob_count"),
            StateDesc("rob_pc"), StateDesc("rob_rd"),
            StateDesc("rob_pdst"), StateDesc("rob_completed"),
            StateDesc("rob_exception"),
        ],
        latency=1,
    ))

    arch.processing_elements = pes
    return arch
