from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload
from rtlgen_x.dsl import Else, If, Input, Module, Output, Reg
from rtlgen_x.ppa import PpaGoals, advise_ppa, analyze_module_ppa
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    Signal,
    SignalRef,
    SimModule,
)


def _deep_module() -> SimModule:
    expr = BinaryExpr(
        "+",
        BinaryExpr(
            "+",
            BinaryExpr("+", SignalRef("a"), SignalRef("b")),
            BinaryExpr("+", SignalRef("c"), SignalRef("d")),
        ),
        BinaryExpr(
            "+",
            BinaryExpr("+", SignalRef("e"), SignalRef("f")),
            BinaryExpr("+", SignalRef("g"), SignalRef("h")),
        ),
    )
    return SimModule(
        name="ppa_deep",
        signals=(
            Signal("a", width=32, kind="input"),
            Signal("b", width=32, kind="input"),
            Signal("c", width=32, kind="input"),
            Signal("d", width=32, kind="input"),
            Signal("e", width=32, kind="input"),
            Signal("f", width=32, kind="input"),
            Signal("g", width=32, kind="input"),
            Signal("h", width=32, kind="input"),
            Signal("we", width=1, kind="input"),
            Signal("addr", width=10, kind="input"),
            Signal("state0", width=64, kind="state"),
            Signal("state1", width=64, kind="state"),
            Signal("out", width=32, kind="output"),
        ),
        assignments=(
            Assignment("out", expr),
            Assignment("state0", SignalRef("out"), phase="seq"),
            Assignment("state1", BinaryExpr("^", SignalRef("state0"), SignalRef("out")), phase="seq"),
        ),
        outputs=("out",),
        memories=(Memory("mem", width=32, depth=1024),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("out"), enable=SignalRef("we")),),
    )


class LegacyPpaAccum(Module):
    def __init__(self):
        super().__init__("legacy_ppa_accum")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")

        @self.comb
        def _comb():
            self.out <<= self.acc

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                self.acc <<= self.acc + self.inp


def test_ppa_module_analysis_surfaces_timing_area_and_power_flags():
    report = advise_ppa(
        module=_deep_module(),
        goals=PpaGoals(
            priority="timing_first",
            max_logic_depth=3,
            max_state_bits=64,
            max_memory_bits=4096,
        ),
    )

    assert report.module_stats is not None
    assert report.module_stats.max_expr_depth > 3
    assert report.module_stats.memory_bits == 32 * 1024
    titles = [rec.title for rec in report.recommendations]
    assert "Pipeline or rebalance deep combinational logic" in titles
    assert "Bank or isolate large memories" in titles
    assert "Reduce or gate large sequential state" in titles


def test_ppa_architecture_analysis_surfaces_bottlenecks_and_stalls():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
            StageSpec("shared_mem", kind="memory", latency=2, initiation_interval=2, capacity=1, queue_depth=1),
            StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu"), tokens=6),
        FlowSpec("gpu", path=("dispatch", "shared_mem", "alu"), tokens=6, start_cycle=1),
    )

    report = advise_ppa(
        model=model,
        workload=workload,
        goals=PpaGoals(min_throughput_tokens_per_cycle=0.8, max_stall_ratio=0.1),
    )

    assert report.architecture_stats is not None
    assert "shared_mem" in report.architecture_stats.stage_stats
    titles = [rec.title for rec in report.recommendations]
    assert any("shared_mem" in title for title in titles)
    assert any("stall" in title.lower() for title in titles)


def test_ppa_recommendations_include_sweep_backed_architecture_evidence():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=4, queue_depth=1),
            StageSpec(
                "shared_mem",
                kind="memory",
                latency=2,
                initiation_interval=1,
                capacity=1,
                queue_depth=2,
                bandwidth_bytes_per_cycle=16,
            ),
            StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=2, queue_depth=2),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu"), tokens=8, bytes_per_token=64),
        FlowSpec("gpu", path=("dispatch", "shared_mem", "alu"), tokens=8, bytes_per_token=64, start_cycle=1),
    )

    report = advise_ppa(
        model=model,
        workload=workload,
        goals=PpaGoals(min_throughput_tokens_per_cycle=1.0, max_stall_ratio=0.05),
    )

    shared_mem_recs = [rec for rec in report.recommendations if "shared_mem" in rec.title]
    assert shared_mem_recs
    assert any("sweep_knob" in rec.evidence for rec in shared_mem_recs)
    assert any(rec.evidence.get("sweep_knob") == "bandwidth_bytes_per_cycle" for rec in shared_mem_recs)
    assert any(
        "Local sweep favors increasing bandwidth" in suggestion
        for rec in shared_mem_recs
        for suggestion in rec.suggestions
    )


def test_ppa_module_analysis_accepts_legacy_dsl_modules():
    stats = analyze_module_ppa(LegacyPpaAccum())

    assert stats.module_name == "legacy_ppa_accum"
    assert stats.state_bits == 8
    assert stats.comb_assignments >= 1
