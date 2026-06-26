"""skills.riscv64_soc.dsl_modules — Native four-core RV64 SoC DSL wrappers."""
from __future__ import annotations

from rtlgen.core import Module, Input, Output, Wire, Const
from rtlgen.logic import Mux
from rtlgen.contracts import (
    FunctionalObjective,
    Layer,
    ModuleContract,
    PerfCheck,
    PerformanceObjective,
    PortContract,
    VerificationHook,
)

from skills.hetero_riscv4.dsl_modules import NUM_CORES, XLEN
from skills.riscv_ooo_4core.dsl_modules import (
    DRAMCtrl as _BaseDRAMCtrl,
    L1Cache as _BaseL1Cache,
    L2CacheSlice as _BaseL2CacheSlice,
    NoCBuffer as _BaseNoCBuffer,
    NoCRouter as _BaseNoCRouter,
    OoOCore as _BaseOoOCore,
    CoherenceDir as _BaseCoherenceDir,
)


def _rename_wrapper(inst: Module, module_name: str, type_name: str) -> None:
    inst.name = module_name
    inst._type_name = type_name


def _port_contracts(mod: Module) -> list[PortContract]:
    ports = []
    for name, sig in mod._inputs.items():
        ports.append(PortContract(name=name, direction="input", width=sig.width))
    for name, sig in mod._outputs.items():
        ports.append(PortContract(name=name, direction="output", width=sig.width))
    return ports


class RV64Core(_BaseOoOCore):
    """High-performance RV64 OoO core exported under the riscv64_soc skill name."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "rv64_core", "RV64Core")
        self._module_contract = ModuleContract(
            module_name="RV64Core",
            role="riscv64_soc skill-level exported reusable RV64 OoO core master.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["u_frontend", "u_decode_rename", "u_backend", "u_commit"],
            timing_assumptions=[
                "Wrapper preserves the underlying OoOCore contract and interfaces.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="soc_core_export",
                    description="Expose a single reusable RV64Core master for SoC integration.",
                    invariants=[
                        "RV64Core remains a single exported master, not per-instance replicated master definitions",
                        "memory and retirement interfaces match the underlying OoOCore boundary",
                    ],
                    corner_cases=["reset release", "simultaneous icache/dcache activity"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="inherit pilot OoOCore wrapper latency",
                throughput_target="inherit high-performance RV64 core provisioning",
                structural_budget={"exported_core_masters": 1},
                optimization_knobs=["wrapper interface stability", "core-to-soc attachment policy"],
                checks=[
                    PerfCheck(
                        name="frontend_wrapper_presence",
                        kind="structural_budget",
                        description="The exported RV64Core master must contain exactly one frontend wrapper.",
                        budget_key="frontend_unit_count",
                        required_value=1,
                        metadata={"submodule_type": "FrontendUnit"},
                    ),
                    PerfCheck(
                        name="backend_wrapper_presence",
                        kind="structural_budget",
                        description="The exported RV64Core master must contain exactly one backend wrapper.",
                        budget_key="backend_unit_count",
                        required_value=1,
                        metadata={"submodule_type": "BackendUnit"},
                    ),
                    PerfCheck(
                        name="rv64core_retire_activity_rate",
                        kind="throughput",
                        description="The exported RV64Core should expose some retire activity under sustained default stimulation.",
                        sink_signals=["retire_valid"],
                        min_rate=0.10,
                        sample_cycles=8,
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="rv64core_export_trace",
                    kind="trace",
                    description="Observe the exported memory-side and retirement-side activity.",
                    signals=["icache_req", "dcache_req", "retire_valid", "retire_count", "core_stall"],
                )
            ],
            allowed_submodules=["FrontendUnit", "DecodeRenameUnit", "BackendUnit", "CommitUnit"],
            notes=["This wrapper intentionally exposes one master definition used by many instances."],
        )


class L1Cache(_BaseL1Cache):
    """Private unified L1 cache wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "l1_cache", "L1Cache")


class CoherenceDir(_BaseCoherenceDir):
    """Shared coherence directory wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "coherence_dir", "CoherenceDir")


class L2CacheSlice(_BaseL2CacheSlice):
    """Shared L2 slice wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "l2_cache_slice", "L2CacheSlice")


class NoCBuffer(_BaseNoCBuffer):
    """Router input buffer wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "noc_buffer", "NoCBuffer")


class NoCRouter(_BaseNoCRouter):
    """Mesh router wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "noc_router", "NoCRouter")


class DRAMCtrl(_BaseDRAMCtrl):
    """Backing DRAM controller wrapper."""

    def __init__(self):
        super().__init__()
        _rename_wrapper(self, "dram_ctrl", "DRAMCtrl")


class ClusterTop(Module):
    """Single RV64Core cluster built from riscv64_soc-native wrappers."""

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

        core = RV64Core()
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
            role="Single RV64Core plus private L1 cache cluster exported by riscv64_soc.",
            layer=Layer.L3_DSL,
            ports=_port_contracts(self),
            state_elements=["u_core", "u_l1", "icache_req", "dcache_req", "cache_valid", "cache_ready"],
            timing_assumptions=[
                "The cluster routes all core memory traffic through one private L1 cache.",
                "Probe handling terminates at the private-cache boundary.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="cluster_export_attachment",
                    description="Preserve the single-core cluster binding and its coherence-visible interfaces.",
                    invariants=[
                        "exactly one RV64Core and one L1Cache are instantiated per cluster",
                        "noc_write depends only on store-side dcache traffic",
                        "probe_ack is sourced from the L1 cache path",
                    ],
                    corner_cases=["probe during store miss", "idle memory path"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="one private-cache boundary hop from core to NoC path",
                throughput_target="one cluster memory request path active per cycle in pilot model",
                structural_budget={"core_instances": 1, "private_l1_instances": 1},
                optimization_knobs=["cache policy", "cluster arbitration", "probe sequencing"],
                checks=[
                    PerfCheck(
                        name="cluster_core_count",
                        kind="structural_budget",
                        description="Each cluster should contain exactly one RV64Core instance.",
                        budget_key="core_instances",
                        required_value=1,
                        metadata={"submodule_type": "RV64Core"},
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
                    name="cluster_export_trace",
                    kind="trace",
                    description="Observe cluster memory/coherence visible behavior.",
                    signals=["noc_req", "noc_addr", "noc_write", "probe_valid", "probe_ack", "retire_valid"],
                )
            ],
            allowed_submodules=["RV64Core", "L1Cache"],
            notes=["This is the cluster-level refinement boundary for riscv64_soc."],
        )


class MeshTop(Module):
    """Four-core RV64 SoC top level using riscv64_soc-native wrappers."""

    def __init__(self):
        super().__init__("mesh_top")
        self._type_name = "MeshTop"

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        for i in range(NUM_CORES):
            setattr(self, f"retire_valid_{i}", Output(1, f"retire_valid_{i}"))
            setattr(self, f"retire_count_{i}", Output(3, f"retire_count_{i}"))

        clusters = [ClusterTop() for _ in range(NUM_CORES)]
        coherence = CoherenceDir()
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
            role="Four-core RV64 SoC top integrating clusters, coherence, L2, and DRAM.",
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
                "One coherence grant drives the shared L2 request path in the pilot topology.",
                "DRAM is the sole backing memory controller for the shared L2.",
            ],
            functional_objectives=[
                FunctionalObjective(
                    name="soc_export_topology",
                    description="Preserve the 4-core shared-memory SoC topology and top-level probe/data distribution.",
                    invariants=[
                        "exactly four cluster instances are integrated",
                        "coherence grant selects the shared L2 request",
                        "probe masking is applied before each cluster sees a probe",
                    ],
                    corner_cases=["simultaneous cluster requests", "probe fanout", "shared refill traffic"],
                )
            ],
            performance_objective=PerformanceObjective(
                latency_target="one arbitration hop before shared L2 access",
                throughput_target="one granted shared-memory transaction at a time in pilot model",
                structural_budget={"cluster_count": NUM_CORES, "shared_l2_slices": 1, "dram_ctrls": 1},
                optimization_knobs=["coherence arbitration", "l2 banking", "response routing"],
                checks=[
                    PerfCheck(
                        name="mesh_cluster_count",
                        kind="structural_budget",
                        description="The SoC top should integrate exactly four clusters.",
                        budget_key="cluster_count",
                        required_value=NUM_CORES,
                        metadata={"submodule_type": "ClusterTop"},
                    ),
                    PerfCheck(
                        name="mesh_shared_l2_count",
                        kind="structural_budget",
                        description="The SoC top should integrate exactly one shared L2 slice.",
                        budget_key="shared_l2_slices",
                        required_value=1,
                        metadata={"submodule_type": "L2CacheSlice"},
                    ),
                ],
            ),
            verification_hooks=[
                VerificationHook(
                    name="soc_export_flow",
                    kind="trace",
                    description="Observe top-level grant/probe/refill/data activity.",
                    signals=["coh_grant_valid", "coh_grant_core", "l2_valid", "l2_dram_req", "dram_valid"],
                )
            ],
            allowed_submodules=["ClusterTop", "CoherenceDir", "L2CacheSlice", "DRAMCtrl"],
            notes=["This contract anchors system-level refinement in the riscv64_soc skill."],
        )
