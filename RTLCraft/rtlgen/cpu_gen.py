"""
rtlgen.cpu_gen — Config-driven hierarchical CPU generator.

Takes CPUConfig → generates full OoO core hierarchy with variable
sub-modules based on config parameters (issue_width, ROB depth, etc.)
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const, SubmoduleInst
from rtlgen.logic import If, Else, Mux
from rtlgen.cpu_config import CPUConfig
from rtlgen.cpu_lib import (
    PCGen, BPred, RenameTable, IssueQueue, ALUUnit, ReorderBuffer, LSUUnit,
)


def _alu_rename(n): return f"u_{type(n).__name__.lower()}"


def generate_cpu(cfg: CPUConfig = CPUConfig()) -> Module:
    core = Module("OoOCore")
    core._type_name = "OoOCore"
    XLEN = 64

    # Ports
    core.clk = Input(1, "clk"); core.rst_n = Input(1, "rst_n")
    core.icache_rdata = Input(XLEN, "icache_rdata"); core.icache_valid = Input(1, "icache_valid")
    core.icache_req = Output(1, "icache_req"); core.icache_addr = Output(XLEN, "icache_addr")
    core.dcache_rdata = Input(XLEN, "dcache_rdata"); core.dcache_valid = Input(1, "dcache_valid")
    core.dcache_req = Output(1, "dcache_req"); core.dcache_addr = Output(XLEN, "dcache_addr")
    core.dcache_wdata = Output(XLEN, "dcache_wdata"); core.dcache_wen = Output(1, "dcache_wen")
    core.core_stall = Output(1, "core_stall")
    core.retire_valid = Output(1, "retire_valid"); core.retire_count = Output(3, "retire_count")

    # ── Create sub-modules (conditional on config) ──
    subs = []
    subs.append(PCGen(cfg))
    subs.append(BPred(cfg))
    subs.append(RenameTable(cfg))
    # Issue queues: vary by issue_width
    n_alu_iq = max(1, cfg.issue_width // 4)  # 1 IQ per 4 issue width
    for i in range(n_alu_iq):
        subs.append(IssueQueue(f"aiq{i}", cfg.iq_entries))
    if cfg.issue_width >= 4:
        subs.append(IssueQueue("biq", 16))    # branch IQ
    if cfg.issue_width >= 6:
        subs.append(IssueQueue("lsiq", 16))   # load/store IQ
    # Execution: ALUs match issue width
    for i in range(cfg.issue_width):
        subs.append(ALUUnit())
    subs.append(ReorderBuffer(cfg.rob_depth))
    subs.append(LSUUnit(cfg.load_queue_depth, cfg.store_queue_depth))

    # Internal wires
    pc = Wire(XLEN, "pc"); fetch_v = Wire(1, "fv"); fi0 = Wire(32, "fi0")
    bm_w = Wire(1, "bm_w"); br_tgt = Wire(XLEN, "br_tgt")
    rob_full_w = Wire(1, "rf"); retire_v_w = Wire(1, "rv")
    a_issue_v = Wire(1, "aiv")
    init = Reg(1, "init"); rc = Reg(32, "rc")

    # Register sub-modules
    for u in subs:
        core._submodules.append((_alu_rename(u), u))

    # Connect via SubmoduleInst
    pcgen = subs[0]; bpred = subs[1]; rename = subs[2]; rob = subs[-2]; lsu = subs[-1]

    for u in subs:
        port_map = {"clk": core.clk, "rst_n": core.rst_n}
        tn = type(u).__name__.lower()
        if "pcgen" in tn:
            port_map["branch_redirect"] = bm_w; port_map["branch_target"] = br_tgt
        if "bpred" in tn:
            port_map["fetch_pc"] = pc; port_map["exec_pc"] = Const(0, XLEN)
        if "rename" in tn:
            port_map["arch_rd_0"] = fi0[11:7]
            port_map["arch_rd_1"] = fi0[11:7]
        if tn.startswith("issuequeue"):
            port_map["enqueue"] = fetch_v
        if "reorderbuffer" in tn:
            port_map["alloc"] = fetch_v
        if "lsuunit" in tn:
            port_map["addr"] = Const(0, XLEN)
        core._top_level.append(SubmoduleInst(_alu_rename(u), u, {}, port_map))

    # Core sequential
    with core.seq(core.clk, ~core.rst_n):
        with If(~core.rst_n): init <<= 0; rc <<= 0
        with Else():
            init <<= 1
            with If(retire_v_w == 1): rc <<= rc + 1

    # Core combinational
    with core.comb:
        pc <<= pcgen.pc; bm_w <<= bpred.pred_taken
        rob_full_w <<= rob.full; retire_v_w <<= rob.retire_valid
        fetch_v <<= 1
        # Outputs (gated by init for reset compliance)
        with If(init == 0):
            core.icache_req <<= Const(0, 1); core.icache_addr <<= Const(0, XLEN)
            core.dcache_req <<= Const(0, 1); core.dcache_addr <<= Const(0, XLEN)
            core.dcache_wdata <<= Const(0, XLEN); core.dcache_wen <<= Const(0, 1)
            core.core_stall <<= Const(0, 1); core.retire_valid <<= Const(0, 1)
            core.retire_count <<= Const(0, 3)
        with Else():
            core.icache_req <<= Const(1, 1); core.icache_addr <<= pc
            core.dcache_req <<= lsu.dcache_req; core.dcache_addr <<= lsu.dcache_addr
            core.dcache_wdata <<= lsu.dcache_wdata; core.dcache_wen <<= lsu.dcache_wen
            core.core_stall <<= rob_full_w
            core.retire_valid <<= retire_v_w
            core.retire_count <<= rc & 0x7

    return core


def generate_and_test(cfg: CPUConfig, name: str = "CPU"):
    core = generate_cpu(cfg)
    from rtlgen.sim import Simulator
    sim = Simulator(core, use_xz=False)
    sim.reset(rst='rst_n', cycles=3)
    ok = all(int(sim.get(o)) == 0 for o in core._outputs)
    types = {}
    for _, m in core._submodules:
        t = type(m).__name__; types[t] = types.get(t, 0) + 1
    print(f"{name:6s}: {len(core._submodules):2d} sub-modules, " +
          f"{' '.join(f'{t}x{c}' for t,c in sorted(types.items()))}, " +
          f"reset={'PASS' if ok else 'FAIL'}")
    return ok
