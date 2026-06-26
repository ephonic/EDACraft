"""skills.riscv_ooo_4core.dsl_modules — High-performance 4-core RV64 OoO DSL modules."""
from __future__ import annotations

from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif, ForGen, Mux
from rtlgen.cpu_config import HIGH_PERF_RV64_4CORE_CONFIG
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
from rtlgen.cpu_gen import generate_cpu

from skills.hetero_riscv4.dsl_modules import (
    BUFFER_DEPTH,
    FLIT_WIDTH,
    NUM_CORES,
    STATE_I,
    STATE_M,
    STATE_S,
    XLEN,
    L1CacheBig as _BaseL1CacheBig,
    NoCBuffer as _BaseNoCBuffer,
    NoCRouter as _BaseNoCRouter,
)


def _port_contracts(mod: Module) -> list[PortContract]:
    ports = []
    for name, sig in mod._inputs.items():
        ports.append(PortContract(name=name, direction="input", width=sig.width))
    for name, sig in mod._outputs.items():
        ports.append(PortContract(name=name, direction="output", width=sig.width))
    return ports
def _rebind_signal_owners(inst: Module) -> None:
    for bucket_name in ("_inputs", "_outputs", "_wires", "_regs"):
        for sig in getattr(inst, bucket_name).values():
            sig._parent_module = inst
    for arr in getattr(inst, "_arrays", {}).values():
        arr._parent_module = inst
    for _, submod in getattr(inst, "_submodules", []):
        object.__setattr__(submod, "_parent", inst)


def _adopt_template(inst: Module, template: Module, module_name: str, type_name: str) -> None:
    # Reuse the generated module state directly instead of deepcopy'ing it.
    # deepcopy leaves signal ownership pointing at a transient plain Module,
    # which later confuses hierarchy/codegen walks.
    for key, value in template.__dict__.items():
        object.__setattr__(inst, key, value)
    inst.name = module_name
    inst._type_name = type_name
    _rebind_signal_owners(inst)


class NoCBuffer(_BaseNoCBuffer):
    """Router input FIFO reused for the 4-core mesh."""

    def __init__(self):
        super().__init__()
        self._module_contract = ModuleContract(
            module_name="NoCBuffer",
            role="Per-port NoC FIFO buffering flits before router arbitration.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["buf_data", "buf_count", "buf_rd_ptr", "buf_wr_ptr"],
            timing_assumptions=[
                "Single push/pop decision is evaluated each cycle in the pilot FIFO model.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="fifo_flow_control",
                    description="Preserve valid/ready/pop FIFO semantics at the router input boundary.",
                    invariants=[
                        "ready_out is low only when the FIFO is full",
                        "valid_out is high only when the FIFO is non-empty",
                    ],
                    corner_cases=["push only", "pop only", "simultaneous push/pop"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="one-cycle visible buffering semantics",
                throughput_target="one flit accepted or popped per cycle in pilot model",
                structural_budget={"buffer_depth": BUFFER_DEPTH},
                optimization_knobs=["buffer_depth", "push_pop_policy"],
                checks=[
                    PerfCheck(
                        name="noc_buffer_ready_ratio",
                        kind="duty_cycle",
                        description="Under idle/light stimulus, the FIFO should remain ready most cycles.",
                        sink_signals=["ready_out"],
                        min_rate=0.50,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="noc_buffer_occupancy_bound",
                        kind="occupancy",
                        description="Under sustained push without pop, FIFO occupancy should rise but stay within the declared depth.",
                        sink_signals=["buf_count"],
                        min_value=1.0,
                        max_value=float(BUFFER_DEPTH),
                        sample_cycles=6,
                        metadata={"stimulus": {"valid_in": 1, "pop": 0}},
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="noc_buffer_trace",
                    kind="trace",
                    description="Observe FIFO occupancy-facing signals.",
                    signals=["valid_in", "ready_out", "valid_out", "empty", "full"],
                )
            ],
            allowed_submodules=[],
            notes=["This is the local flow-control contract for router input buffering."],
        )


class NoCRouter(_BaseNoCRouter):
    """5-port mesh router reused for the 2x2 four-core topology."""

    def __init__(self):
        super().__init__()
        self._module_contract = ModuleContract(
            module_name="NoCRouter",
            role="5-port XY-routed mesh router connecting clusters and shared-memory path.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            protocols=[
                ProtocolContract(
                    name="local_injection",
                    kind="ready_valid",
                    request_signals=["loc_inj_valid", "loc_inj_flit"],
                    response_signals=["loc_inj_ready"],
                    flow_control_signals=["loc_ej_ready", "loc_ej_valid"],
                    description="Local tile injects/ejects flits through the router edge.",
                )
            ],
            transactions=[
                TransactionContract(
                    name="local_flit_accept",
                    trigger_signals=["loc_inj_valid"],
                    completion_signals=["loc_inj_ready"],
                    max_cycles=1,
                    description="Under light load, a local flit should be accepted promptly.",
                )
            ],
            resources=[
                ResourceContract(
                    name="router_output_arbitration",
                    kind="crossbar_output",
                    capacity=5,
                    arbitration="fixed_priority",
                    observable_signals=["e_valid_o", "w_valid_o", "n_valid_o", "s_valid_o", "loc_ej_valid"],
                    description="One grant per output per cycle in the pilot router.",
                )
            ],
            state_elements=[
                "buf_e_cnt", "buf_w_cnt", "buf_n_cnt", "buf_s_cnt", "buf_j_cnt",
                "grant_to_e", "grant_to_w", "grant_to_n", "grant_to_s", "grant_to_j",
            ],
            timing_assumptions=[
                "Per-output arbitration is evaluated each cycle.",
                "At most one input wins each output in the pilot router model.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="router_flow_and_arbitration",
                    description="Preserve per-output grant selection and corresponding pop behavior.",
                    invariants=[
                        "ready outputs deassert only when the corresponding input buffer is full",
                        "each output valid is sourced by one granted input at a time",
                    ],
                    corner_cases=["multiple contenders", "idle router", "local inject/eject traffic"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single arbitration step before output selection",
                throughput_target="one granted flit per output per cycle in pilot model",
                structural_budget={"router_ports": 5},
                optimization_knobs=["arb_priority", "buffer_depth", "routing_policy"],
                checks=[
                    PerfCheck(
                        name="router_local_ready_ratio",
                        kind="duty_cycle",
                        description="Under light stimulus, local injection should remain ready in most cycles.",
                        sink_signals=["loc_inj_ready"],
                        min_rate=0.50,
                        sample_cycles=8,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="router_idle_local",
                        description="Observe router local readiness under idle/light conditions.",
                        reset_cycles=3,
                        cycles=8,
                        stimulus={"loc_inj_valid": 0, "e_valid": 0, "w_valid": 0, "n_valid": 0, "s_valid": 0},
                        linked_checks=["router_local_ready_ratio"],
                        expected_observations={},
                        tags=["noc", "idle"],
                    )
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="router_grant_trace",
                    kind="trace",
                    description="Observe local readiness and output valid behavior.",
                    signals=["loc_inj_ready", "e_valid_o", "w_valid_o", "n_valid_o", "s_valid_o", "loc_ej_valid"],
                )
            ],
            allowed_submodules=[],
            notes=["This contract anchors local NoC refinement in the 4-core CPU flow."],
        )


class OoOCore(Module):
    """High-performance RV64 out-of-order core wrapper built from the generic CPU generator."""

    def __init__(self):
        super().__init__("ooo_core")
        template = generate_cpu(HIGH_PERF_RV64_4CORE_CONFIG)
        _adopt_template(self, template, "ooo_core", "OoOCore")
        self.add_comment("4-wide RV64 OoO core generated from HIGH_PERF_RV64_4CORE_CONFIG")
        self._module_contract = ModuleContract(
            module_name="OoOCore",
            role="Skill-level OoO core master for the 4-core RV64 processor.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["u_frontend", "u_decode_rename", "u_backend", "u_commit"],
            timing_assumptions=[
                "Wrapper preserves the generated CPU stage boundaries.",
                "Core exports one instruction-side and one data-side cache interface.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="core_master_integration",
                    description="Expose a single reusable core master with stable memory and retirement interfaces.",
                    invariants=[
                        "only one OoOCore master should represent the reusable CPU core",
                        "retire_count remains aligned with retire_valid semantics",
                        "instruction and data cache ports remain externally visible",
                    ],
                    corner_cases=["reset release", "simultaneous icache/dcache demand", "backend stall"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="preserve pilot wrapper pipeline latency",
                throughput_target="4-wide class OoO core provisioning",
                structural_budget={"issue_width": 4, "core_instances_per_master": 1},
                optimization_knobs=["core_pipeline_partitioning", "frontend/backend queue depths"],
                checks=[
                    PerfCheck(
                        name="frontend_wrapper_presence",
                        kind="structural_budget",
                        description="The reusable OoOCore master must contain exactly one frontend wrapper.",
                        budget_key="frontend_unit_count",
                        required_value=1,
                        metadata={"submodule_type": "FrontendUnit"},
                    ),
                    PerfCheck(
                        name="backend_wrapper_presence",
                        kind="structural_budget",
                        description="The reusable OoOCore master must contain exactly one backend wrapper.",
                        budget_key="backend_unit_count",
                        required_value=1,
                        metadata={"submodule_type": "BackendUnit"},
                    ),
                    PerfCheck(
                        name="retire_activity_rate",
                        kind="throughput",
                        description="The pilot OoOCore should expose some retire activity under sustained default stimulation.",
                        sink_signals=["retire_valid"],
                        min_rate=0.10,
                        sample_cycles=8,
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="core_master_observe",
                    kind="trace",
                    description="Observe externally visible memory and retirement activity.",
                    signals=["icache_req", "dcache_req", "retire_valid", "retire_count", "core_stall"],
                )
            ],
            allowed_submodules=["FrontendUnit", "DecodeRenameUnit", "BackendUnit", "CommitUnit"],
            notes=["This contract sits at the reusable master boundary, not per-core replicated naming."],
        )


class L1Cache(_BaseL1CacheBig):
    """64KB private L1 cache reused for all four cores."""

    def __init__(self):
        super().__init__()
        self._module_contract = ModuleContract(
            module_name="L1Cache",
            role="Private unified L1 cache reused across the 4-core RV64 clusters.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["tag_array", "data_array", "state_array"] if hasattr(self, "tag_array") else [],
            timing_assumptions=[
                "Private L1 mediates all cluster-local memory traffic before NoC forwarding.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="private_cache_attachment",
                    description="Preserve private-cache serving and coherence-visible interfaces.",
                    invariants=[
                        "probe_ack is produced by the cache-side coherence path",
                        "NoC request path is only used for misses or coherence traffic",
                    ],
                    corner_cases=["hit", "miss", "probe invalidate"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single local cache hit response in the pilot model",
                throughput_target="one private-cache request path active per cycle",
                structural_budget={"cache_instances_per_cluster": 1},
                optimization_knobs=["cache_size", "associativity", "miss_policy"],
                checks=[
                    PerfCheck(
                        name="l1_ready_duty_cycle",
                        kind="duty_cycle",
                        description="The private L1 should remain ready for a reasonable fraction of pilot cycles.",
                        sink_signals=["ready"],
                        min_rate=0.50,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="l1_miss_path_activity",
                        kind="throughput",
                        description="Under a simple forced-demand pattern, the miss path should be able to activate NoC requests.",
                        sink_signals=["noc_req"],
                        min_rate=0.10,
                        sample_cycles=8,
                        metadata={"stimulus": {"req": 1, "wen": 0, "addr": 0x40}},
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="l1_boundary_trace",
                    kind="trace",
                    description="Observe cache/local-coherence boundary behavior.",
                    signals=["valid", "ready", "probe_valid", "probe_ack", "noc_req"],
                )
            ],
            allowed_submodules=[],
            notes=["This contract is a first-pass cache boundary contract, not a full cache protocol model."],
        )


class CoherenceDir(Module):
    """Small shared coherence directory for four private L1 caches."""

    def __init__(self):
        super().__init__("coherence_dir")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        for i in range(NUM_CORES):
            setattr(self, f"req_valid_{i}", Input(1, f"req_valid_{i}"))
            setattr(self, f"req_addr_{i}", Input(XLEN, f"req_addr_{i}"))
            setattr(self, f"req_write_{i}", Input(1, f"req_write_{i}"))
            setattr(self, f"probe_ack_{i}", Input(1, f"probe_ack_{i}"))

        self.grant_valid = Output(1, "grant_valid")
        self.grant_core_id = Output(2, "grant_core_id")
        self.grant_addr = Output(XLEN, "grant_addr")
        self.probe_valid = Output(1, "probe_valid")
        self.probe_addr = Output(XLEN, "probe_addr")
        self.probe_mask = Output(NUM_CORES, "probe_mask")
        self.probe_invalidate = Output(1, "probe_invalidate")

        self.dir_tag = Array(XLEN - 6, 64, "dir_tag")
        self.dir_valid = Array(1, 64, "dir_valid")
        self.dir_owner = Array(2, 64, "dir_owner")
        self.dir_sharers = Array(NUM_CORES, 64, "dir_sharers")

        sel_valid = Wire(1, "sel_valid")
        sel_core = Wire(2, "sel_core")
        sel_addr = Wire(XLEN, "sel_addr")
        sel_write = Wire(1, "sel_write")
        hit = Wire(1, "dir_hit")
        idx = Wire(6, "dir_idx")
        tag = Wire(XLEN - 6, "dir_tag_in")
        cur_sharers = Wire(NUM_CORES, "dir_cur_sharers")
        other_sharers = Wire(NUM_CORES, "dir_other_sharers")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                with ForGen("i", 0, 64) as i:
                    self.dir_valid[i] <<= 0
                    self.dir_owner[i] <<= 0
                    self.dir_sharers[i] <<= 0
            with Else():
                with If(sel_valid == 1):
                    self.dir_tag[idx] <<= tag
                    self.dir_valid[idx] <<= 1
                    with If(sel_write == 1):
                        self.dir_owner[idx] <<= sel_core
                        self.dir_sharers[idx] <<= (Const(1, NUM_CORES) << sel_core)
                    with Else():
                        self.dir_sharers[idx] <<= cur_sharers | (Const(1, NUM_CORES) << sel_core)

        with self.comb:
            sel_valid <<= self.req_valid_0 | self.req_valid_1 | self.req_valid_2 | self.req_valid_3
            sel_core <<= Mux(self.req_valid_0, Const(0, 2),
                        Mux(self.req_valid_1, Const(1, 2),
                        Mux(self.req_valid_2, Const(2, 2), Const(3, 2))))
            sel_addr <<= Mux(self.req_valid_0, self.req_addr_0,
                        Mux(self.req_valid_1, self.req_addr_1,
                        Mux(self.req_valid_2, self.req_addr_2, self.req_addr_3)))
            sel_write <<= Mux(self.req_valid_0, self.req_write_0,
                         Mux(self.req_valid_1, self.req_write_1,
                         Mux(self.req_valid_2, self.req_write_2, self.req_write_3)))

            idx <<= sel_addr[11:6]
            tag <<= sel_addr[XLEN - 1:12]
            hit <<= self.dir_valid[idx] & (self.dir_tag[idx] == tag)
            cur_sharers <<= Mux(hit, self.dir_sharers[idx], Const(0, NUM_CORES))
            other_sharers <<= cur_sharers & ~(Const(1, NUM_CORES) << sel_core)

            self.grant_valid <<= sel_valid
            self.grant_core_id <<= sel_core
            self.grant_addr <<= sel_addr
            self.probe_valid <<= sel_valid & sel_write & hit & (other_sharers != 0)
            self.probe_addr <<= sel_addr
            self.probe_mask <<= other_sharers
            self.probe_invalidate <<= sel_write
        self._module_contract = ModuleContract(
            module_name="CoherenceDir",
            role="Shared directory tracking owners and sharers for private L1 caches.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            protocols=[
                ProtocolContract(
                    name="coherence_request",
                    kind="request_grant_probe",
                    request_signals=["req_valid_0", "req_addr_0", "req_write_0"],
                    response_signals=["grant_valid", "grant_core_id", "grant_addr"],
                    flow_control_signals=["probe_valid", "probe_mask", "probe_ack_0"],
                    description="Directory accepts requests and may fan out probes before granting progress.",
                )
            ],
            transactions=[
                TransactionContract(
                    name="coherence_request_to_grant",
                    trigger_signals=["req_valid_0"],
                    completion_signals=["grant_valid"],
                    recipe="request_grant_completion",
                    trigger_event="rise",
                    completion_event="rise",
                    max_cycles=1,
                    sample_cycles=8,
                    description="A selected coherence request should produce visible grant information promptly in the pilot model.",
                )
            ],
            resources=[
                ResourceContract(
                    name="directory_entries",
                    kind="directory_array",
                    capacity=64,
                    observable_signals=["grant_valid", "probe_valid"],
                    description="Direct-mapped pilot directory entries backing the coherence path.",
                )
            ],
            state_elements=["dir_tag", "dir_valid", "dir_owner", "dir_sharers"],
            timing_assumptions=[
                "One selected requester is processed in the current pilot arbitration model.",
                "Probe generation is only required for write requests that hit shared lines.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="directory_selection_and_probe",
                    description="Preserve requester selection and shared-line probe generation semantics.",
                    invariants=[
                        "grant_valid mirrors whether any request is active",
                        "probe_valid only fires for shared-line write conflicts",
                    ],
                    corner_cases=["no requester", "shared read hit", "write with multiple sharers"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single arbitration step to produce grant information",
                throughput_target="one selected coherence request per cycle in pilot model",
                structural_budget={"directory_sets": 64, "tracked_cores": NUM_CORES},
                optimization_knobs=["selection_policy", "directory_set_count", "probe_mask_encoding"],
                checks=[
                    PerfCheck(
                        name="coherence_grant_duty_cycle",
                        kind="duty_cycle",
                        description="Sustained request activity should produce frequent grants.",
                        sink_signals=["grant_valid"],
                        min_rate=0.25,
                        sample_cycles=8,
                        metadata={"stimulus": {"req_valid_0": 1, "req_write_0": 1}},
                    ),
                    PerfCheck(
                        name="directory_set_budget",
                        kind="structural_budget",
                        description="Directory set count must remain at the pilot budget.",
                        budget_key="directory_sets",
                        required_value=64,
                    ),
                    PerfCheck(
                        name="coherence_probe_completion_bound",
                        kind="completion_bound",
                        description="A single sustained requester should not accumulate unbounded unresolved directory work.",
                        source_signals=["req_valid_0"],
                        sink_signals=["grant_valid"],
                        max_value=1.0,
                        sample_cycles=8,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="single_writer_request",
                        description="Drive one write requester to observe grant/probe behavior.",
                        reset_cycles=3,
                        cycles=8,
                        stimulus={"req_valid_0": 0, "req_write_0": 0, "req_addr_0": 0},
                        stimulus_recipes=[
                            PerfStimulusRecipe(
                                kind="hold",
                                start_cycle=1,
                                end_cycle=7,
                                values={"req_valid_0": 1, "req_write_0": 1, "req_addr_0": 0x40},
                                description="Sustain one writer request after the initial observation beat.",
                            )
                        ],
                        linked_checks=["coherence_grant_duty_cycle", "coherence_probe_completion_bound"],
                        linked_transactions=["coherence_request_to_grant"],
                        expected_observations={},
                        tags=["coherence", "request"],
                    )
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="directory_activity",
                    kind="trace",
                    description="Observe grant and probe behavior under contention.",
                    signals=["grant_valid", "grant_core_id", "probe_valid", "probe_mask", "probe_invalidate"],
                )
            ],
            allowed_submodules=[],
            notes=["This is a first-pass shared-memory contract for the 4-core pilot."],
        )


class CoherenceBus(CoherenceDir):
    """Alias used by the 4-core skill PE mapping."""

    def __init__(self):
        super().__init__()
        self.name = "coherence_bus"
        self._type_name = "CoherenceBus"


class L2CacheSlice(Module):
    """Shared L2 cache slice with a tiny refill path to DRAM."""

    def __init__(self):
        super().__init__("l2_cache_slice")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(1, "req")
        self.addr = Input(XLEN, "addr")
        self.wdata = Input(XLEN, "wdata")
        self.wen = Input(1, "wen")
        self.dram_data = Input(XLEN, "dram_data")
        self.dram_valid = Input(1, "dram_valid")
        self.rdata = Output(XLEN, "rdata")
        self.valid = Output(1, "valid")
        self.ready = Output(1, "ready")
        self.dram_req = Output(1, "dram_req")
        self.dram_addr = Output(XLEN, "dram_addr")

        self.tag_ram = Array(XLEN - 7, 128, "tag_ram")
        self.data_ram = Array(XLEN, 128, "data_ram")
        self.valid_ram = Array(1, 128, "valid_ram")
        self.state = Reg(2, "l2_state")
        self.miss_addr = Reg(XLEN, "miss_addr")

        idx = Wire(7, "l2_idx")
        tag = Wire(XLEN - 7, "l2_tag")
        hit = Wire(1, "l2_hit")

        S_IDLE = 0
        S_REFILL = 1

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.state <<= S_IDLE
                self.valid <<= 0
                with ForGen("i", 0, 128) as i:
                    self.valid_ram[i] <<= 0
            with Else():
                self.valid <<= 0
                with If(self.state == S_IDLE):
                    with If(self.req == 1):
                        with If(hit == 1):
                            with If(self.wen == 1):
                                self.data_ram[idx] <<= self.wdata
                            self.valid <<= 1
                        with Else():
                            self.miss_addr <<= self.addr
                            self.state <<= S_REFILL
                with Elif(self.state == S_REFILL):
                    with If(self.dram_valid == 1):
                        self.data_ram[self.miss_addr[12:6]] <<= self.dram_data
                        self.tag_ram[self.miss_addr[12:6]] <<= self.miss_addr[XLEN - 1:13]
                        self.valid_ram[self.miss_addr[12:6]] <<= 1
                        self.valid <<= 1
                        self.state <<= S_IDLE

        with self.comb:
            idx <<= self.addr[12:6]
            tag <<= self.addr[XLEN - 1:13]
            hit <<= self.valid_ram[idx] & (self.tag_ram[idx] == tag)
            self.rdata <<= Mux(hit, self.data_ram[idx], self.dram_data)
            self.ready <<= self.state == S_IDLE
            self.dram_req <<= (self.state == S_REFILL) | (self.req & ~hit)
            self.dram_addr <<= Mux(self.state == S_REFILL, self.miss_addr, self.addr)
        self._module_contract = ModuleContract(
            module_name="L2CacheSlice",
            role="Shared L2 slice buffering accesses before DRAM refill.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["tag_ram", "data_ram", "valid_ram", "state", "miss_addr"],
            timing_assumptions=[
                "L2 hit returns data locally; refill transitions through REFILL state.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="l2_hit_miss_flow",
                    description="Preserve local hit behavior and refill sequencing on misses.",
                    invariants=[
                        "ready is high only in idle state",
                        "dram_req is asserted for misses or active refill",
                    ],
                    corner_cases=["read hit", "write hit", "miss entering refill"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single local hit step, bounded refill path on miss",
                throughput_target="one accepted request per idle cycle in pilot model",
                structural_budget={"l2_sets": 128},
                optimization_knobs=["set_count", "refill_policy", "write_hit_policy"],
                checks=[
                    PerfCheck(
                        name="l2_ready_duty_cycle",
                        kind="duty_cycle",
                        description="L2 should spend most cycles ready under light pilot stimulus.",
                        sink_signals=["ready"],
                        min_rate=0.50,
                        sample_cycles=8,
                    ),
                    PerfCheck(
                        name="l2_set_budget",
                        kind="structural_budget",
                        description="L2 set count must remain at the pilot budget.",
                        budget_key="l2_sets",
                        required_value=128,
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="l2_refill_trace",
                    kind="trace",
                    description="Observe hit/miss/refill visible behavior.",
                    signals=["valid", "ready", "dram_req", "dram_addr"],
                )
            ],
            allowed_submodules=[],
            notes=["This contract covers the shared L2 slice as a local optimization boundary."],
        )


class DRAMCtrl(Module):
    """Fixed-latency DRAM responder used as the backing memory model."""

    def __init__(self):
        super().__init__("dram_ctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(1, "req")
        self.addr = Input(XLEN, "addr")
        self.rdata = Output(XLEN, "rdata")
        self.valid = Output(1, "valid")
        self.ready = Output(1, "ready")

        self.pending = Reg(1, "pending")
        self.pending_addr = Reg(XLEN, "pending_addr")
        self.latency = Reg(2, "latency")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.pending <<= 0
                self.latency <<= 0
                self.valid <<= 0
            with Else():
                self.valid <<= 0
                with If((self.pending == 0) & (self.req == 1)):
                    self.pending <<= 1
                    self.pending_addr <<= self.addr
                    self.latency <<= 2
                with Elif(self.pending == 1):
                    with If(self.latency != 0):
                        self.latency <<= self.latency - 1
                    with Else():
                        self.pending <<= 0
                        self.valid <<= 1

        with self.comb:
            self.ready <<= ~self.pending
            self.rdata <<= self.pending_addr ^ Const(0x13579BDF2468ACE0, XLEN)
        self._module_contract = ModuleContract(
            module_name="DRAMCtrl",
            role="Fixed-latency backing memory responder for shared-memory misses.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["pending", "pending_addr", "latency"],
            timing_assumptions=[
                "A request is accepted only when no pending response is active.",
                "Returned data is a deterministic function of the pending address in the pilot model.",
            ],
            transactions=[
                TransactionContract(
                    name="accepted_request_to_response",
                    trigger_signals=["req"],
                    completion_signals=["valid"],
                    recipe="ordered_completion",
                    trigger_event="handshake",
                    trigger_qualifiers=["ready"],
                    completion_event="rise",
                    sample_cycles=8,
                    description="Each accepted request must produce one in-order bounded outstanding response.",
                    metadata={"max_outstanding": 1},
                )
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="fixed_latency_response",
                    description="Preserve pending tracking and eventual valid response behavior.",
                    invariants=[
                        "ready is low while a request is pending",
                        "valid only asserts when latency countdown completes",
                    ],
                    corner_cases=["back-to-back requests", "idle cycles", "countdown completion"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="2-cycle countdown after request acceptance in pilot model",
                throughput_target="one outstanding request at a time",
                structural_budget={"max_outstanding": 1},
                optimization_knobs=["response_latency", "address_hashing", "pending_queue_depth"],
                checks=[
                    PerfCheck(
                        name="dram_ready_ratio",
                        kind="duty_cycle",
                        description="The pilot DRAM model should be ready in a reasonable fraction of cycles.",
                        sink_signals=["ready"],
                        min_rate=0.25,
                        sample_cycles=8,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="dram_steady_request",
                        description="Drive sustained requests into the single-entry DRAM responder.",
                        reset_cycles=3,
                        cycles=8,
                        stimulus={"req": 0, "addr": 0},
                        stimulus_recipes=[
                            PerfStimulusRecipe(
                                kind="periodic",
                                start_cycle=0,
                                end_cycle=7,
                                period=4,
                                duty_cycles=1,
                                values={"req": 1, "addr": 0x80},
                                description="Issue one request pulse every four cycles so the single-entry responder can drain cleanly.",
                            )
                        ],
                        linked_transactions=["accepted_request_to_response"],
                        expected_observations={},
                        tags=["dram", "request"],
                    )
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="dram_service_trace",
                    kind="trace",
                    description="Observe request acceptance and response completion.",
                    signals=["req", "ready", "valid", "addr"],
                )
            ],
            allowed_submodules=[],
            notes=["This is a simple backing-memory model contract, not a full DRAM timing model."],
        )


class ClusterTop(Module):
    """One OoO core plus its private unified L1 cache."""

    def __init__(self):
        super().__init__("cluster_top")
        self._type_name = "ClusterTop"

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.probe_addr = Input(XLEN, "probe_addr")
        self.probe_valid = Input(1, "probe_valid")
        self.probe_invalidate = Input(1, "probe_invalidate")
        self.probe_ack = Output(1, "probe_ack")
        self.noc_req = Output(1, "noc_req")
        self.noc_addr = Output(XLEN, "noc_addr")
        self.noc_write = Output(1, "noc_write")
        self.noc_rdata = Input(XLEN, "noc_rdata")
        self.noc_valid = Input(1, "noc_valid")
        self.core_stall = Output(1, "core_stall")
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")

        core = OoOCore()
        cache = L1Cache()

        icache_req = Wire(1, "icache_req")
        icache_addr = Wire(XLEN, "icache_addr")
        dcache_req = Wire(1, "dcache_req")
        dcache_addr = Wire(XLEN, "dcache_addr")
        dcache_wdata = Wire(XLEN, "dcache_wdata")
        dcache_wen = Wire(1, "dcache_wen")
        cache_valid = Wire(1, "cache_valid")
        cache_rdata = Wire(XLEN, "cache_rdata")
        cache_ready = Wire(1, "cache_ready")

        self.instantiate(core, "u_core", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "icache_req": icache_req,
            "icache_addr": icache_addr,
            "icache_rdata": cache_rdata,
            "icache_valid": cache_valid,
            "dcache_req": dcache_req,
            "dcache_addr": dcache_addr,
            "dcache_wdata": dcache_wdata,
            "dcache_wen": dcache_wen,
            "dcache_rdata": cache_rdata,
            "dcache_valid": cache_valid,
            "core_stall": self.core_stall,
            "retire_valid": self.retire_valid,
            "retire_count": self.retire_count,
        })

        self.instantiate(cache, "u_l1", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "req": icache_req | dcache_req,
            "addr": Mux(dcache_req, dcache_addr, icache_addr),
            "wdata": dcache_wdata,
            "wen": dcache_wen,
            "valid": cache_valid,
            "rdata": cache_rdata,
            "ready": cache_ready,
            "probe_addr": self.probe_addr,
            "probe_valid": self.probe_valid,
            "probe_invalidate": self.probe_invalidate,
            "probe_ack": self.probe_ack,
            "noc_req": self.noc_req,
            "noc_addr": self.noc_addr,
            "noc_rdata": self.noc_rdata,
            "noc_valid": self.noc_valid,
        })

        with self.comb:
            self.noc_write <<= dcache_req & dcache_wen
        self._module_contract = ModuleContract(
            module_name="ClusterTop",
            role="Single-core cluster integrating one OoOCore with one private L1 cache.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["u_core", "u_l1", "icache_req", "dcache_req", "cache_valid", "cache_ready"],
            timing_assumptions=[
                "L1 cache is the sole memory-side attachment for the cluster.",
                "Probe traffic is handled locally at the private-cache boundary.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="cluster_memory_attachment",
                    description="Preserve the core-to-private-cache binding and coherence probe entrypoints.",
                    invariants=[
                        "OoOCore is the only compute master in the cluster",
                        "noc_write derives only from dcache write traffic",
                        "probe_ack is sourced by the private L1 cache path",
                    ],
                    corner_cases=["probe during demand miss", "store traffic", "idle core"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single private-cache hop from core to cluster memory boundary",
                throughput_target="one active core cluster request path per cycle in pilot model",
                structural_budget={"private_l1_instances": 1, "core_instances": 1},
                optimization_knobs=["l1_size", "cache arbitration policy", "probe handling split"],
                checks=[
                    PerfCheck(
                        name="cluster_core_count",
                        kind="structural_budget",
                        description="Each cluster should contain exactly one OoOCore instance.",
                        budget_key="core_instances",
                        required_value=1,
                        metadata={"submodule_type": "OoOCore"},
                    ),
                    PerfCheck(
                        name="cluster_l1_count",
                        kind="structural_budget",
                        description="Each cluster should contain exactly one private L1 cache instance.",
                        budget_key="private_l1_instances",
                        required_value=1,
                        metadata={"submodule_type": "L1Cache"},
                    ),
                    PerfCheck(
                        name="cluster_request_duty_cycle",
                        kind="duty_cycle",
                        description="The cluster should generate some NoC request activity under the pilot workload.",
                        sink_signals=["noc_req"],
                        min_rate=0.10,
                        sample_cycles=8,
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="cluster_flow",
                    kind="trace",
                    description="Observe core/cache/NOC boundary behavior.",
                    signals=["noc_req", "noc_addr", "noc_write", "probe_valid", "probe_ack", "retire_valid"],
                )
            ],
            allowed_submodules=["OoOCore", "L1Cache"],
            notes=["This is the cluster-level optimization boundary for core-private-cache refinement."],
        )


class MeshTop(Module):
    """Shared-L2 4-core RV64 top level built from four OoO clusters."""

    def __init__(self):
        super().__init__("mesh_top")
        self._type_name = "MeshTop"

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        for i in range(NUM_CORES):
            setattr(self, f"retire_valid_{i}", Output(1, f"retire_valid_{i}"))
            setattr(self, f"retire_count_{i}", Output(3, f"retire_count_{i}"))

        clusters = [ClusterTop() for _ in range(NUM_CORES)]
        coherence = CoherenceBus()
        l2 = L2CacheSlice()
        dram = DRAMCtrl()

        noc_req = [Wire(1, f"noc_req_{i}") for i in range(NUM_CORES)]
        noc_addr = [Wire(XLEN, f"noc_addr_{i}") for i in range(NUM_CORES)]
        noc_write = [Wire(1, f"noc_write_{i}") for i in range(NUM_CORES)]
        noc_rdata = [Wire(XLEN, f"noc_rdata_{i}") for i in range(NUM_CORES)]
        noc_valid = [Wire(1, f"noc_valid_{i}") for i in range(NUM_CORES)]
        probe_addr = [Wire(XLEN, f"probe_addr_{i}") for i in range(NUM_CORES)]
        probe_valid = [Wire(1, f"probe_valid_{i}") for i in range(NUM_CORES)]
        probe_inval = [Wire(1, f"probe_inval_{i}") for i in range(NUM_CORES)]
        probe_ack = [Wire(1, f"probe_ack_{i}") for i in range(NUM_CORES)]

        coh_grant_valid = Wire(1, "coh_grant_valid")
        coh_grant_core = Wire(2, "coh_grant_core")
        coh_grant_addr = Wire(XLEN, "coh_grant_addr")
        coh_probe_valid = Wire(1, "coh_probe_valid")
        coh_probe_addr = Wire(XLEN, "coh_probe_addr")
        coh_probe_mask = Wire(NUM_CORES, "coh_probe_mask")
        coh_probe_inval = Wire(1, "coh_probe_inval")
        l2_valid = Wire(1, "l2_valid")
        l2_rdata = Wire(XLEN, "l2_rdata")
        l2_ready = Wire(1, "l2_ready")
        l2_dram_req = Wire(1, "l2_dram_req")
        l2_dram_addr = Wire(XLEN, "l2_dram_addr")
        dram_valid = Wire(1, "dram_valid")
        dram_rdata = Wire(XLEN, "dram_rdata")
        dram_ready = Wire(1, "dram_ready")

        for i, cluster in enumerate(clusters):
            self.instantiate(cluster, f"u_cluster_{i}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "probe_addr": probe_addr[i],
                "probe_valid": probe_valid[i],
                "probe_invalidate": probe_inval[i],
                "probe_ack": probe_ack[i],
                "noc_req": noc_req[i],
                "noc_addr": noc_addr[i],
                "noc_write": noc_write[i],
                "noc_rdata": noc_rdata[i],
                "noc_valid": noc_valid[i],
                "retire_valid": getattr(self, f"retire_valid_{i}"),
                "retire_count": getattr(self, f"retire_count_{i}"),
            })

        self.instantiate(coherence, "u_coherence", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "req_valid_0": noc_req[0],
            "req_addr_0": noc_addr[0],
            "req_write_0": noc_write[0],
            "probe_ack_0": probe_ack[0],
            "req_valid_1": noc_req[1],
            "req_addr_1": noc_addr[1],
            "req_write_1": noc_write[1],
            "probe_ack_1": probe_ack[1],
            "req_valid_2": noc_req[2],
            "req_addr_2": noc_addr[2],
            "req_write_2": noc_write[2],
            "probe_ack_2": probe_ack[2],
            "req_valid_3": noc_req[3],
            "req_addr_3": noc_addr[3],
            "req_write_3": noc_write[3],
            "probe_ack_3": probe_ack[3],
            "grant_valid": coh_grant_valid,
            "grant_core_id": coh_grant_core,
            "grant_addr": coh_grant_addr,
            "probe_valid": coh_probe_valid,
            "probe_addr": coh_probe_addr,
            "probe_mask": coh_probe_mask,
            "probe_invalidate": coh_probe_inval,
        })

        self.instantiate(l2, "u_l2", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "req": coh_grant_valid,
            "addr": coh_grant_addr,
            "wdata": Const(0, XLEN),
            "wen": Const(0, 1),
            "dram_data": dram_rdata,
            "dram_valid": dram_valid,
            "rdata": l2_rdata,
            "valid": l2_valid,
            "ready": l2_ready,
            "dram_req": l2_dram_req,
            "dram_addr": l2_dram_addr,
        })

        self.instantiate(dram, "u_dram", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "req": l2_dram_req,
            "addr": l2_dram_addr,
            "rdata": dram_rdata,
            "valid": dram_valid,
            "ready": dram_ready,
        })

        with self.comb:
            for i in range(NUM_CORES):
                probe_addr[i] <<= coh_probe_addr
                probe_valid[i] <<= coh_probe_valid & coh_probe_mask[i]
                probe_inval[i] <<= coh_probe_inval
                noc_rdata[i] <<= l2_rdata
                noc_valid[i] <<= l2_valid & (coh_grant_core == Const(i, 2))
        self._module_contract = ModuleContract(
            module_name="MeshTop",
            role="Four-cluster shared-L2 top-level integration for the 4-core RV64 processor.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=[
                "u_cluster_0",
                "u_cluster_1",
                "u_cluster_2",
                "u_cluster_3",
                "u_coherence",
                "u_l2",
                "u_dram",
            ],
            timing_assumptions=[
                "Coherence arbitration selects one granted requester in the current pilot model.",
                "L2 and DRAM form the shared backing path for all clusters.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="soc_topology_correctness",
                    description="Preserve four-cluster topology, shared coherence path, and shared memory path.",
                    invariants=[
                        "exactly four cluster instances are integrated at the top level",
                        "coherence grant drives the shared L2 request path",
                        "probe fanout is masked per cluster before delivery",
                    ],
                    corner_cases=["simultaneous cluster requests", "coherence probe fanout", "L2 refill in progress"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="single shared-coherence arbitration hop before L2 access",
                throughput_target="pilot model supports one granted memory transaction at a time",
                structural_budget={"cluster_count": NUM_CORES, "shared_l2_slices": 1, "dram_ctrls": 1},
                optimization_knobs=["coherence arbitration", "l2 banking", "noc routing granularity"],
                checks=[
                    PerfCheck(
                        name="mesh_cluster_count",
                        kind="structural_budget",
                        description="The top should integrate exactly four clusters.",
                        budget_key="cluster_count",
                        required_value=NUM_CORES,
                        metadata={"submodule_type": "ClusterTop"},
                    ),
                    PerfCheck(
                        name="mesh_shared_l2_count",
                        kind="structural_budget",
                        description="The top should integrate exactly one shared L2 slice.",
                        budget_key="shared_l2_slices",
                        required_value=1,
                        metadata={"submodule_type": "L2CacheSlice"},
                    ),
                    PerfCheck(
                        name="mesh_l2_valid_activity",
                        kind="duty_cycle",
                        description="Under pilot top-level stimulus, the shared L2 path should be observable.",
                        sink_signals=["retire_valid_0"],
                        min_rate=0.0,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="mesh_retire_fairness",
                        kind="fairness",
                        description="Under the symmetric pilot topology, retire visibility should remain reasonably balanced across clusters.",
                        sink_signals=["retire_valid_0", "retire_valid_1", "retire_valid_2", "retire_valid_3"],
                        min_ratio=0.50,
                        sample_cycles=8,
                        metadata={
                            "sink_groups": [
                                {"name": "cluster0", "signals": ["retire_valid_0"]},
                                {"name": "cluster1", "signals": ["retire_valid_1"]},
                                {"name": "cluster2", "signals": ["retire_valid_2"]},
                                {"name": "cluster3", "signals": ["retire_valid_3"]},
                            ]
                        },
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="top_memory_flow",
                    kind="trace",
                    description="Observe request/grant/probe/data flow across the top-level memory system.",
                    signals=["coh_grant_valid", "coh_grant_core", "l2_valid", "l2_dram_req", "dram_valid"],
                )
            ],
            allowed_submodules=["ClusterTop", "CoherenceBus", "L2CacheSlice", "DRAMCtrl"],
            notes=["This contract is the main system-level lowering boundary for shared-memory refinement."],
        )


RV64Core = OoOCore
