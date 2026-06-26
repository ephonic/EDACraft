"""
rtlgen.cpu_gen — Config-driven hierarchical CPU generator.

Takes CPUConfig → generates full OoO core hierarchy with variable
sub-modules based on config parameters (issue_width, ROB depth, etc.)
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const, SubmoduleInst
from rtlgen.logic import If, Else, Mux
from rtlgen.cpu_config import CPUConfig
from rtlgen.contracts import (
    FunctionalObjective,
    Layer,
    ModuleContract,
    PerfCheck,
    PerfScenario,
    PerfStimulusRecipe,
    PerfStimulusStep,
    PerformanceObjective,
    PortContract,
    ProtocolContract,
    ResourceContract,
    TransactionContract,
    VerificationHook,
)
from rtlgen.cpu_lib import (
    PCGen, BPred, RenameTable, IssueQueue, ALUUnit, ReorderBuffer, LSUUnit,
)


def _alu_rename(n): return f"u_{type(n).__name__.lower()}"


def _attach_submodule(parent: Module, inst_name: str, submodule: Module, port_map: dict):
    """Register a child module onto a generated parent without relying on ambient Context."""
    parent._submodules.append((inst_name, submodule))
    object.__setattr__(submodule, "_parent", parent)
    parent._top_level.append(SubmoduleInst(inst_name, submodule, {}, port_map))


def _port_contracts(mod: Module) -> list[PortContract]:
    ports = []
    for name, sig in mod._inputs.items():
        ports.append(PortContract(name=name, direction="input", width=sig.width))
    for name, sig in mod._outputs.items():
        ports.append(PortContract(name=name, direction="output", width=sig.width))
    return ports


class FrontendUnit(Module):
    """Frontend wrapper: branch prediction + PC generation + fetch slice."""

    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("frontend")
        self._type_name = "FrontendUnit"
        XLEN = 64

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.icache_rdata = Input(XLEN, "icache_rdata")
        self.branch_redirect = Input(1, "branch_redirect")
        self.branch_target = Input(XLEN, "branch_target")
        self.icache_req = Output(1, "icache_req")
        self.icache_addr = Output(XLEN, "icache_addr")
        self.fetch_valid = Output(1, "fetch_valid")
        self.fetch_instr = Output(32, "fetch_instr")
        self.fetch_pc = Output(XLEN, "fetch_pc")
        self.pred_taken = Output(1, "pred_taken")
        self.pred_target = Output(XLEN, "pred_target")
        pred_target_w = Wire(XLEN, "pred_target_w")

        pcgen = PCGen(cfg)
        bpred = BPred(cfg)
        init_done = Reg(1, "init_done")

        self.instantiate(pcgen, "u_pcgen", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "branch_redirect": self.branch_redirect,
            "branch_target": self.branch_target,
            "btb_hit": bpred.btb_hit,
            "btb_target": pred_target_w,
            "pc": self.fetch_pc,
        })

        self.instantiate(bpred, "u_bpred", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "fetch_pc": self.fetch_pc,
            "exec_pc": Const(0, XLEN),
            "branch_taken": Const(0, 1),
            "branch_target": Const(0, XLEN),
            "pred_taken": self.pred_taken,
            "pred_target": pred_target_w,
        })

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                init_done <<= 0
            with Else():
                init_done <<= 1

        with self.comb:
            with If(init_done == 0):
                self.icache_req <<= Const(0, 1)
                self.icache_addr <<= Const(0, XLEN)
                self.fetch_valid <<= Const(0, 1)
                self.fetch_instr <<= Const(0, 32)
            with Else():
                self.icache_req <<= Const(1, 1)
                self.icache_addr <<= self.fetch_pc
                self.fetch_valid <<= Const(1, 1)
                self.fetch_instr <<= self.icache_rdata[31:0]
            self.pred_target <<= pred_target_w

        self._module_contract = ModuleContract(
            module_name="FrontendUnit",
            role="Fetch, branch prediction, and redirect-aware instruction delivery.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            protocols=[
                ProtocolContract(
                    name="icache_request",
                    kind="request_response",
                    request_signals=["icache_req", "icache_addr"],
                    response_signals=["icache_rdata"],
                    description="Frontend issues instruction fetch requests to the instruction-side memory path.",
                )
            ],
            transactions=[
                TransactionContract(
                    name="redirect_to_fetch",
                    trigger_signals=["branch_redirect"],
                    completion_signals=["fetch_valid"],
                    max_cycles=1,
                    description="A redirect should re-establish visible fetch activity quickly.",
                )
            ],
            resources=[
                ResourceContract(
                    name="frontend_fetch_slot",
                    kind="pipeline_slot",
                    capacity=1,
                    observable_signals=["fetch_valid", "icache_req"],
                    description="Frontend exposes one fetch issue opportunity per cycle in the pilot model.",
                )
            ],
            state_elements=["init_done", "pred_target_w"],
            timing_assumptions=[
                "Sustain one fetch request per cycle after reset deassertion.",
                "Redirect visible at the PC generator input in the same lowered stage.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="redirect_correctness",
                    description="Deliver fetch PC and instruction slice consistent with redirect and predictor outputs.",
                    invariants=[
                        "fetch_valid must be low during reset initialization",
                        "icache_addr follows fetch_pc when initialized",
                    ],
                    corner_cases=["reset release", "branch redirect", "cold predictor state"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="1 cycle fetch issue after init",
                throughput_target="1 fetch bundle / cycle",
                structural_budget={"max_logic_depth": 6, "max_predictor_levels": 2},
                optimization_knobs=["btb_entries", "bht_entries", "redirect_pipe_split"],
                checks=[
                    PerfCheck(
                        name="fetch_enable_latency",
                        kind="latency",
                        description="After reset release, fetch_valid should become visible quickly.",
                        sink_signals=["fetch_valid"],
                        max_cycles=1,
                        sample_cycles=4,
                        metadata={"reset_release_check": True},
                    ),
                    PerfCheck(
                        name="fetch_request_duty_cycle",
                        kind="duty_cycle",
                        description="Once initialized, icache_req should stay active most cycles in the pilot frontend.",
                        sink_signals=["icache_req"],
                        min_rate=0.75,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="frontend_logic_depth_budget",
                        kind="structural_budget",
                        description="Frontend logic depth must stay under the local budget.",
                        budget_key="max_logic_depth",
                        required_value=6,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="post_reset_fetch",
                        description="Observe fetch becoming active after reset release under idle redirect conditions.",
                        reset_cycles=3,
                        cycles=6,
                        stimulus={"branch_redirect": 0, "branch_target": 0, "icache_rdata": 0},
                        linked_checks=["fetch_enable_latency", "fetch_request_duty_cycle"],
                        expected_observations={},
                        tags=["reset", "fetch"],
                    )
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="fetch_activity",
                    kind="counter",
                    description="Observe fetch_valid duty cycle and redirect response.",
                    signals=["fetch_valid", "fetch_pc", "pred_taken"],
                )
            ],
            allowed_submodules=["PCGen", "BPred"],
            notes=["Local optimization should preserve redirect semantics before widening fetch."],
        )


class DecodeRenameUnit(Module):
    """Decode + rename wrapper for frontend outputs."""

    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("decode_rename")
        self._type_name = "DecodeRenameUnit"

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.fetch_valid = Input(1, "fetch_valid")
        self.fetch_instr = Input(32, "fetch_instr")
        self.rename_done = Output(1, "rename_done")
        self.rename_rd_0 = Output(max(cfg.phys_int_regs - 1, 1).bit_length(), "rename_rd_0")
        self.rename_rd_1 = Output(max(cfg.phys_int_regs - 1, 1).bit_length(), "rename_rd_1")

        rename = RenameTable(cfg)
        self.instantiate(rename, "u_rename", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "rename_req": self.fetch_valid,
            "arch_rd_0": self.fetch_instr[11:7],
            "arch_rd_1": self.fetch_instr[11:7],
            "rename_done": self.rename_done,
            "phys_rd_0": self.rename_rd_0,
            "phys_rd_1": self.rename_rd_1,
        })

        self._module_contract = ModuleContract(
            module_name="DecodeRenameUnit",
            role="Decode architectural destinations and allocate physical destinations.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            protocols=[
                ProtocolContract(
                    name="fetch_to_rename",
                    kind="valid_response",
                    request_signals=["fetch_valid", "fetch_instr"],
                    response_signals=["rename_done", "rename_rd_0", "rename_rd_1"],
                    description="Frontend instruction visibility drives rename completion and destination allocation.",
                )
            ],
            state_elements=["rename_rd_0", "rename_rd_1"],
            timing_assumptions=[
                "Decode and rename complete in one local stage under no stall.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="rename_safety",
                    description="Preserve destination register semantics and avoid invalid rename completion.",
                    invariants=[
                        "rename_done implies fetch_valid",
                        "physical destination widths match configured physical register file",
                    ],
                    corner_cases=["x0 destination", "back-to-back destination reuse"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="1 cycle decode+rename",
                throughput_target="1 rename group / cycle",
                structural_budget={"max_logic_depth": 5},
                optimization_knobs=["rename_map_impl", "freelist_depth", "decode_split"],
                checks=[
                    PerfCheck(
                        name="rename_response_latency",
                        kind="latency",
                        description="rename_done should appear quickly after sustained fetch_valid.",
                        source_signals=["fetch_valid"],
                        sink_signals=["rename_done"],
                        max_cycles=1,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="rename_throughput",
                        kind="throughput",
                        description="Under sustained fetch_valid, rename_done should sustain near one event per cycle.",
                        source_signals=["fetch_valid"],
                        sink_signals=["rename_done"],
                        min_rate=0.75,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="rename_logic_depth_budget",
                        kind="structural_budget",
                        description="Decode/rename logic depth must stay under the local budget.",
                        budget_key="max_logic_depth",
                        required_value=5,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="steady_rename",
                        description="Drive a sustained fetch stream to observe rename throughput.",
                        reset_cycles=3,
                        cycles=8,
                        stimulus={"fetch_valid": 0, "fetch_instr": 0x00000013},
                        stimulus_recipes=[
                            PerfStimulusRecipe(
                                kind="hold",
                                start_cycle=0,
                                end_cycle=7,
                                values={"fetch_valid": 1},
                                description="Sustain one fetch-valid beat per cycle across the observation window.",
                            )
                        ],
                        linked_checks=["rename_response_latency", "rename_throughput"],
                        expected_observations={},
                        tags=["rename", "throughput"],
                    )
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="rename_trace",
                    kind="trace",
                    description="Track rename completion and allocated physical destinations.",
                    signals=["rename_done", "rename_rd_0", "rename_rd_1"],
                )
            ],
            allowed_submodules=["RenameTable"],
            notes=["Pilot contract should later expand with explicit decoder semantics."],
        )


class BackendUnit(Module):
    """Issue/execute/backend wrapper for renamed micro-ops."""

    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("backend")
        self._type_name = "BackendUnit"
        XLEN = 64

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.dispatch_valid = Input(1, "dispatch_valid")
        self.dcache_rdata = Input(XLEN, "dcache_rdata")
        self.dcache_valid = Input(1, "dcache_valid")
        self.rob_full = Output(1, "rob_full")
        self.retire_valid = Output(1, "retire_valid")
        self.dcache_req = Output(1, "dcache_req")
        self.dcache_addr = Output(XLEN, "dcache_addr")
        self.dcache_wdata = Output(XLEN, "dcache_wdata")
        self.dcache_wen = Output(1, "dcache_wen")

        iq_units = []
        n_alu_iq = max(1, cfg.issue_width // 4)
        for i in range(n_alu_iq):
            iq_units.append(IssueQueue(f"aiq{i}", cfg.iq_entries))
        if cfg.issue_width >= 4:
            iq_units.append(IssueQueue("biq", 16))
        if cfg.issue_width >= 6:
            iq_units.append(IssueQueue("lsiq", 16))
        alu_units = [ALUUnit() for _ in range(cfg.issue_width)]
        rob = ReorderBuffer(cfg.rob_depth)
        lsu = LSUUnit(cfg.load_queue_depth, cfg.store_queue_depth)

        for idx, iq in enumerate(iq_units):
            self.instantiate(iq, f"u_iq_{idx}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "enqueue": self.dispatch_valid,
                "uop_in": Const(0, 160),
            })

        for idx, alu in enumerate(alu_units):
            self.instantiate(alu, f"u_alu_{idx}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "opcode": Const(0x33, 7),
                "funct3": Const(0, 3),
                "funct7": Const(0, 7),
                "src0": Const(0, XLEN),
                "src1": Const(idx, XLEN),
            })

        self.instantiate(rob, "u_rob", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "alloc": self.dispatch_valid,
            "uop_data": Const(0, 192),
            "commit_ready": Const(1, 1),
            "full": self.rob_full,
            "retire_valid": self.retire_valid,
        })

        self.instantiate(lsu, "u_lsu", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "ld_req": self.dispatch_valid,
            "st_req": Const(0, 1),
            "addr": Const(0, XLEN),
            "wdata": Const(0, XLEN),
            "dcache_rdata": self.dcache_rdata,
            "dcache_valid": self.dcache_valid,
            "dcache_req": self.dcache_req,
            "dcache_addr": self.dcache_addr,
            "dcache_wdata": self.dcache_wdata,
            "dcache_wen": self.dcache_wen,
        })

        self._module_contract = ModuleContract(
            module_name="BackendUnit",
            role="Dispatch renamed work into issue, execute, ROB, and LSU resources.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["rob_full", "retire_valid"],
            timing_assumptions=[
                "Issue queues may absorb one dispatch group per cycle when not full.",
                "ROB retirement signal is the backend-visible completion source.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="backend_flow_control",
                    description="Preserve dispatch, execution, and retirement handoff semantics without dropping work.",
                    invariants=[
                        "rob_full must reflect ROB backpressure",
                        "dcache_wen only asserted on store path",
                    ],
                    corner_cases=["ROB near full", "LSU-only traffic", "idle dispatch"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="bounded by configured issue/ROB/LSU pipelines",
                throughput_target=f"{cfg.issue_width} backend issue slots provisioned",
                structural_budget={
                    "max_issue_queues": max(1, cfg.issue_width // 4) + (1 if cfg.issue_width >= 4 else 0) + (1 if cfg.issue_width >= 6 else 0),
                    "rob_depth": cfg.rob_depth,
                },
                optimization_knobs=["issue_queue_partitioning", "alu_count", "rob_depth", "lsu_queue_depths"],
                checks=[
                    PerfCheck(
                        name="dispatch_to_retire_activity",
                        kind="throughput",
                        description="Sustained dispatch_valid should produce visible retire activity in the pilot backend.",
                        source_signals=["dispatch_valid"],
                        sink_signals=["retire_valid"],
                        min_rate=0.5,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="rob_backpressure_ratio",
                        kind="stall_ratio",
                        description="ROB full should not dominate under the pilot backend stimulus.",
                        sink_signals=["rob_full"],
                        max_ratio=0.75,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="backend_issue_queue_budget",
                        kind="structural_budget",
                        description="Issue queue count must stay within the configured structural budget.",
                        budget_key="max_issue_queues",
                        required_value=max(1, cfg.issue_width // 4) + (1 if cfg.issue_width >= 4 else 0) + (1 if cfg.issue_width >= 6 else 0),
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="backend_pressure",
                    kind="counter",
                    description="Observe dispatch pressure, ROB fullness, and retire activity.",
                    signals=["dispatch_valid", "rob_full", "retire_valid", "dcache_req"],
                )
            ],
            allowed_submodules=["IssueQueue", "ALUUnit", "ReorderBuffer", "LSUUnit"],
            notes=["This is the main local PPA tuning surface for width/depth tradeoffs."],
        )


class CommitUnit(Module):
    """Commit wrapper: retire accounting and top-level visible counters."""

    def __init__(self):
        super().__init__("commit")
        self._type_name = "CommitUnit"

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.retire_in = Input(1, "retire_in")
        self.rob_full = Input(1, "rob_full")
        self.core_stall = Output(1, "core_stall")
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")

        rc = Reg(32, "rc")
        init_done = Reg(1, "init_done")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                init_done <<= 0
                rc <<= 0
            with Else():
                init_done <<= 1
                with If(self.retire_in == 1):
                    rc <<= rc + 1

        with self.comb:
            with If(init_done == 0):
                self.core_stall <<= Const(0, 1)
                self.retire_valid <<= Const(0, 1)
                self.retire_count <<= Const(0, 3)
            with Else():
                self.core_stall <<= self.rob_full
                self.retire_valid <<= self.retire_in
                self.retire_count <<= rc & 0x7

        self._module_contract = ModuleContract(
            module_name="CommitUnit",
            role="Expose architectural retirement progress and stall signaling.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["rc", "init_done"],
            timing_assumptions=[
                "Commit visibility is updated every cycle after initialization.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="retire_accounting",
                    description="Retire count reflects completed retire events and stall follows ROB backpressure.",
                    invariants=[
                        "retire_valid mirrors retire_in once initialized",
                        "core_stall mirrors rob_full once initialized",
                    ],
                    corner_cases=["reset release", "continuous retire stream", "full ROB stall"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="1 cycle retire visibility",
                throughput_target="1 retire event accounting / cycle",
                structural_budget={"max_logic_depth": 3, "counter_width": 32},
                optimization_knobs=["retire_counter_width", "stall_signal_registration"],
                checks=[
                    PerfCheck(
                        name="retire_visibility_latency",
                        kind="latency",
                        description="retire_valid should follow retire_in quickly after initialization.",
                        source_signals=["retire_in"],
                        sink_signals=["retire_valid"],
                        max_cycles=1,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="stall_visibility_latency",
                        kind="latency",
                        description="core_stall should reflect rob_full quickly after initialization.",
                        source_signals=["rob_full"],
                        sink_signals=["core_stall"],
                        max_cycles=1,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="commit_logic_depth_budget",
                        kind="structural_budget",
                        description="Commit logic depth must stay under the local budget.",
                        budget_key="max_logic_depth",
                        required_value=3,
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="commit_progress",
                    kind="counter",
                    description="Observe retire events and visible stall behavior.",
                    signals=["retire_in", "retire_valid", "retire_count", "core_stall"],
                )
            ],
            allowed_submodules=[],
            notes=["Commit policy should stay simple until precise exceptions are modeled."],
        )


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

    frontend = FrontendUnit(cfg)
    decode_rename = DecodeRenameUnit(cfg)
    backend = BackendUnit(cfg)
    commit = CommitUnit()

    core.fetch_valid = Wire(1, "fetch_valid")
    core.fetch_instr = Wire(32, "fetch_instr")
    core.fetch_pc = Wire(XLEN, "fetch_pc")
    core.pred_taken = Wire(1, "pred_taken")
    core.pred_target = Wire(XLEN, "pred_target")
    rename_w = max(cfg.phys_int_regs - 1, 1).bit_length()
    core.rename_done = Wire(1, "rename_done")
    core.rename_rd_0 = Wire(rename_w, "rename_rd_0")
    core.rename_rd_1 = Wire(rename_w, "rename_rd_1")
    core.rob_full_w = Wire(1, "rf")
    core.retire_v_w = Wire(1, "rv")

    _attach_submodule(core, "u_frontend", frontend, {
        "clk": core.clk,
        "rst_n": core.rst_n,
        "icache_rdata": core.icache_rdata,
        "branch_redirect": core.pred_taken,
        "branch_target": core.pred_target,
        "icache_req": core.icache_req,
        "icache_addr": core.icache_addr,
        "fetch_valid": core.fetch_valid,
        "fetch_instr": core.fetch_instr,
        "fetch_pc": core.fetch_pc,
        "pred_taken": core.pred_taken,
        "pred_target": core.pred_target,
    })

    _attach_submodule(core, "u_decode_rename", decode_rename, {
        "clk": core.clk,
        "rst_n": core.rst_n,
        "fetch_valid": core.fetch_valid,
        "fetch_instr": core.fetch_instr,
        "rename_done": core.rename_done,
        "rename_rd_0": core.rename_rd_0,
        "rename_rd_1": core.rename_rd_1,
    })

    _attach_submodule(core, "u_backend", backend, {
        "clk": core.clk,
        "rst_n": core.rst_n,
        "dispatch_valid": core.rename_done,
        "dcache_rdata": core.dcache_rdata,
        "dcache_valid": core.dcache_valid,
        "rob_full": core.rob_full_w,
        "retire_valid": core.retire_v_w,
        "dcache_req": core.dcache_req,
        "dcache_addr": core.dcache_addr,
        "dcache_wdata": core.dcache_wdata,
        "dcache_wen": core.dcache_wen,
    })

    _attach_submodule(core, "u_commit", commit, {
        "clk": core.clk,
        "rst_n": core.rst_n,
        "retire_in": core.retire_v_w,
        "rob_full": core.rob_full_w,
        "core_stall": core.core_stall,
        "retire_valid": core.retire_valid,
        "retire_count": core.retire_count,
    })

    core._module_contract = ModuleContract(
        module_name="OoOCore",
        role="Top-level RV64 out-of-order core integrating frontend, rename, backend, and commit domains.",
        layer=Layer.L3_DSL,
        ports=_port_contracts(core),
        state_elements=[
            "fetch_valid",
            "fetch_instr",
            "fetch_pc",
            "pred_taken",
            "pred_target",
            "rename_done",
            "rename_rd_0",
            "rename_rd_1",
            "rob_full_w",
            "retire_v_w",
        ],
        timing_assumptions=[
            "Frontend, decode/rename, backend, and commit wrappers define the current pilot pipeline cuts.",
            "Rename completion is the dispatch enable for backend lowering in the current integration model.",
        ],
        functional_objectives=[
            FunctionalObjective(
                name="pipeline_connectivity",
                description="Preserve handoff semantics between major core pipeline domains.",
                invariants=[
                    "frontend fetch outputs must drive decode/rename inputs",
                    "rename_done is the only backend dispatch enable in this pilot core",
                    "retire_valid and core_stall are sourced from the commit domain outputs",
                ],
                corner_cases=[
                    "reset release",
                    "branch redirect activity",
                    "ROB full backpressure",
                ],
            )
        ],
        performance_objective=PerformanceObjective(
            latency_target="single-cycle local handoff between wrapper stages in the pilot model",
            throughput_target=f"provisioned around {cfg.issue_width} backend issue slots",
            structural_budget={
                "issue_width": cfg.issue_width,
                "rob_depth": cfg.rob_depth,
                "phys_int_regs": cfg.phys_int_regs,
            },
            optimization_knobs=[
                "fetch_width",
                "rename_width",
                "issue_width",
                "rob_depth",
                "queue_partitioning",
            ],
            checks=[
                PerfCheck(
                    name="core_issue_width_budget",
                    kind="structural_budget",
                    description="The integrated core should preserve the configured issue width budget.",
                    budget_key="issue_width",
                    required_value=cfg.issue_width,
                ),
                PerfCheck(
                    name="core_rob_depth_budget",
                    kind="structural_budget",
                    description="The integrated core should preserve the configured ROB depth budget.",
                    budget_key="rob_depth",
                    required_value=cfg.rob_depth,
                ),
            ],
        ),
        verification_hooks=[
            VerificationHook(
                name="core_flow_trace",
                kind="trace",
                description="Observe stage-to-stage handoff and retirement visibility.",
                signals=[
                    "fetch_valid",
                    "rename_done",
                    "rob_full_w",
                    "retire_v_w",
                    "retire_valid",
                    "core_stall",
                ],
            )
        ],
        allowed_submodules=[
            "FrontendUnit",
            "DecodeRenameUnit",
            "BackendUnit",
            "CommitUnit",
        ],
        notes=[
            "This contract anchors local refinement before introducing finer-grained dispatch/issue/execute decomposition.",
        ],
    )

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
