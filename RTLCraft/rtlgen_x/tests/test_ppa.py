from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload, calibrate_architecture_model
import json
import pytest
from rtlgen_x.dsl import DslLoweringReport, Else, If, Input, LoweredDslModule, Module, Output, Reg, lower_dsl_module_to_sim
from rtlgen_x.dsl import (
    APBRegisterBank,
    AXI4LiteRegisterBank,
    DualPortRAM,
    LUT,
    MAC,
    ReadyValidFIFO,
    ReadyValidRegister,
    RegisterFile,
    ReqRspQueue,
    SignedMultiplier,
    SkidBuffer,
    WishboneRegisterBank,
)
from rtlgen_x.ppa import (
    PpaGoals,
    apply_rewrite_proposal,
    advise_ppa,
    analyze_module_ppa,
    build_architecture_ppa_calibration_sample,
    build_module_ppa_calibration_sample,
    derive_architecture_calibration_targets,
    derive_rewrite_proposals,
    estimate_calibrated_architecture_ppa,
    estimate_calibrated_module_ppa,
    evaluate_rewrite_proposal,
    fit_architecture_ppa_calibration,
    fit_module_ppa_calibration,
    load_implementation_report_bundle,
    ModulePpaCalibrationModel,
    ArchitecturePpaCalibrationModel,
    validate_rewrite_proposal,
)
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


def _lowered(module: SimModule) -> LoweredDslModule:
    return LoweredDslModule(
        module=module,
        report=DslLoweringReport(
            source_module=module.name,
            flattened_module=module.name,
            signal_count=len(module.signals),
            assignment_count=len(module.assignments),
            outputs_post_state=module.outputs_post_state,
        ),
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
            Assignment("state0", SignalRef("out"), phase="seq", source_file="ppa_state.py", source_line=31),
            Assignment(
                "state1",
                BinaryExpr("^", SignalRef("state0"), SignalRef("out")),
                phase="seq",
                source_file="ppa_state.py",
                source_line=32,
            ),
        ),
        outputs=("out",),
        memories=(Memory("mem", width=32, depth=1024),),
        memory_writes=(
            MemoryWrite(
                "mem",
                SignalRef("addr"),
                SignalRef("out"),
                enable=SignalRef("we"),
                source_file="ppa_mem.py",
                source_line=41,
            ),
        ),
    )


def _multiplier_hotspot_module() -> SimModule:
    return SimModule(
        name="ppa_mult",
        signals=(
            Signal("a", width=64, kind="input"),
            Signal("b", width=64, kind="input"),
            Signal("c", width=64, kind="input"),
            Signal("d", width=64, kind="input"),
            Signal("prod0", width=128, kind="wire"),
            Signal("prod1", width=128, kind="wire"),
            Signal("out", width=129, kind="output"),
        ),
        assignments=(
            Assignment(
                "prod0",
                BinaryExpr("*", SignalRef("a"), SignalRef("b")),
                source_file="toy_mult.py",
                source_line=11,
            ),
            Assignment(
                "prod1",
                BinaryExpr("*", SignalRef("c"), SignalRef("d")),
                source_file="toy_mult.py",
                source_line=12,
            ),
            Assignment(
                "out",
                BinaryExpr("+", SignalRef("prod0"), SignalRef("prod1")),
                source_file="toy_mult.py",
                source_line=13,
            ),
        ),
        outputs=("out",),
    )


class DslPpaAccum(Module):
    def __init__(self):
        super().__init__("dsl_ppa_accum")
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


def test_analyze_module_ppa_rejects_raw_simmodule():
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        analyze_module_ppa(_deep_module())


def test_ppa_module_analysis_surfaces_timing_area_and_power_flags():
    report = advise_ppa(
        module=_lowered(_deep_module()),
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


def test_module_ppa_stats_expose_area_power_breakdown_and_named_hotspots():
    stats = analyze_module_ppa(_lowered(_deep_module()))

    assert stats.largest_memory_name == "mem"
    assert stats.largest_memory_bits == 32 * 1024
    assert stats.largest_memory_width == 32
    assert stats.largest_memory_depth == 1024
    assert stats.largest_memory_source_file == "ppa_mem.py"
    assert stats.largest_memory_source_line == 41
    assert stats.largest_state_name in {"state0", "state1"}
    assert stats.largest_state_bits == 64
    assert stats.largest_state_source_file == "ppa_state.py"
    assert stats.largest_state_source_line in {31, 32}
    assert stats.area_state_score == float(stats.state_bits)
    assert stats.area_memory_score == 0.125 * stats.memory_bits
    assert stats.estimated_area_score == (
        stats.area_state_score
        + stats.area_memory_score
        + stats.area_io_score
        + stats.area_arithmetic_score
        + stats.area_compare_score
        + stats.area_mux_score
        + stats.area_memory_write_score
        + stats.area_comb_assignment_score
        + stats.area_seq_assignment_score
    )
    assert stats.estimated_power_score >= (
        stats.power_state_score
        + stats.power_memory_score
        + stats.power_arithmetic_score
        + stats.power_compare_score
        + stats.power_mux_score
        + stats.power_memory_write_score
    )
    assert stats.dominant_area_bucket == "memory"
    assert stats.dominant_power_bucket == "memory"


def test_ppa_area_power_recommendations_carry_breakdown_and_named_hotspots():
    report = advise_ppa(
        module=_lowered(_deep_module()),
        goals=PpaGoals(max_state_bits=64, max_memory_bits=4096),
    )

    assert report.module_stats is not None
    memory_rec = next(rec for rec in report.recommendations if rec.title == "Bank or isolate large memories")
    assert memory_rec.evidence["module"] == "ppa_deep"
    assert memory_rec.evidence["largest_memory_name"] == "mem"
    assert memory_rec.evidence["largest_memory_bits"] == 32 * 1024
    assert memory_rec.evidence["largest_memory_source_file"] == "ppa_mem.py"
    assert memory_rec.evidence["largest_memory_source_line"] == 41
    assert memory_rec.evidence["target_label"] == "ppa_deep.mem @ ppa_mem.py:41"
    assert memory_rec.evidence["dominant_area_bucket"] == "memory"
    assert memory_rec.evidence["area_breakdown"]["memory"] == report.module_stats.area_memory_score
    assert memory_rec.evidence["power_breakdown"]["memory"] == report.module_stats.power_memory_score

    state_rec = next(rec for rec in report.recommendations if rec.title == "Reduce or gate large sequential state")
    assert state_rec.evidence["module"] == "ppa_deep"
    assert state_rec.evidence["largest_state_bits"] == 64
    assert state_rec.evidence["state_bits"] == report.module_stats.state_bits
    assert state_rec.evidence["largest_state_source_file"] == "ppa_state.py"
    assert state_rec.evidence["largest_state_source_line"] in {31, 32}
    assert state_rec.evidence["area_breakdown"]["state"] == report.module_stats.area_state_score
    assert state_rec.evidence["power_breakdown"]["state"] == report.module_stats.power_state_score


def test_ppa_multiplier_recommendation_carries_breakdown_and_source_site():
    report = advise_ppa(module=_lowered(_multiplier_hotspot_module()))

    assert report.module_stats is not None
    multiplier_rec = next(rec for rec in report.recommendations if rec.title == "Audit multiplier-heavy stages")
    assert multiplier_rec.evidence["module"] == "ppa_mult"
    assert multiplier_rec.evidence["widest_multiplier_operand_widths"] == (64, 64)
    assert multiplier_rec.evidence["widest_multiplier_assignment_target"] == "prod0"
    assert multiplier_rec.evidence["widest_multiplier_source_file"] == "toy_mult.py"
    assert multiplier_rec.evidence["widest_multiplier_source_line"] == 11
    assert multiplier_rec.evidence["widest_multiplier_product_width"] == 128
    assert multiplier_rec.evidence["recommended_multiplier_tile_width"] == 16
    assert multiplier_rec.evidence["recommended_multiplier_strategy"] == "karatsuba_or_tiled"
    assert multiplier_rec.evidence["multiplier_pattern_hint"] == "multi_multiplier_datapath"
    assert multiplier_rec.evidence["target_label"] == "ppa_mult.prod0 @ toy_mult.py:11"
    assert multiplier_rec.evidence["rtl_anchor"] == "ppa_mult.prod0 @ toy_mult.py:11"
    assert multiplier_rec.evidence["area_breakdown"]["arithmetic"] == report.module_stats.area_arithmetic_score
    assert multiplier_rec.evidence["power_breakdown"]["arithmetic"] == report.module_stats.power_arithmetic_score
    assert multiplier_rec.severity == "high"
    assert any("16x16 partial products" in suggestion for suggestion in multiplier_rec.suggestions)
    assert any("Karatsuba/Ofman" in suggestion for suggestion in multiplier_rec.suggestions)


def test_ppa_multiplier_recommendation_hints_signed_multiplier_pattern_for_dsl_block():
    report = advise_ppa(module=SignedMultiplier(8, 3))

    multiplier_rec = next(rec for rec in report.recommendations if rec.title == "Audit multiplier-heavy stages")
    assert multiplier_rec.evidence["multiplier_pattern_hint"] == "signed_multiplier_pipeline"
    assert any("SignedMultiplier-style staged datapath" in suggestion for suggestion in multiplier_rec.suggestions)


def test_ppa_multiplier_recommendation_hints_mac_pattern_for_dsl_block():
    report = advise_ppa(module=MAC(8))

    multiplier_rec = next(rec for rec in report.recommendations if rec.title == "Audit multiplier-heavy stages")
    assert multiplier_rec.evidence["multiplier_pattern_hint"] == "mac_style"
    assert any("MAC-style pipeline" in suggestion for suggestion in multiplier_rec.suggestions)


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
    assert report.architecture_stats.estimated_area_proxy > 0.0
    assert report.architecture_stats.estimated_power_proxy > 0.0
    assert report.architecture_stats.dominant_area_stage is not None
    assert report.architecture_stats.dominant_power_stage is not None
    shared_mem = report.architecture_stats.stage_stats["shared_mem"]
    assert shared_mem.queue_capacity == 1
    assert shared_mem.activity_proxy > 0.0
    assert shared_mem.estimated_area_proxy > 0.0
    assert shared_mem.estimated_power_proxy > 0.0
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
    assert any(rec.evidence.get("stage_area_proxy", 0.0) > 0.0 for rec in shared_mem_recs)
    assert any(rec.evidence.get("stage_power_proxy", 0.0) > 0.0 for rec in shared_mem_recs)
    assert any(rec.evidence.get("stage_bytes_moved", 0) > 0 for rec in shared_mem_recs)
    assert any(rec.evidence.get("stage_transport_pressure_proxy", 0.0) > 0.0 for rec in shared_mem_recs)
    assert any(
        "Local sweep favors increasing bandwidth" in suggestion
        for rec in shared_mem_recs
        for suggestion in rec.suggestions
    )


def test_ppa_architecture_report_calls_out_area_and_power_proxy_hotspots():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
            StageSpec(
                "shared_mem",
                kind="memory",
                latency=3,
                initiation_interval=1,
                capacity=2,
                queue_depth=6,
                bandwidth_bytes_per_cycle=128,
            ),
            StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu"), tokens=16, bytes_per_token=128),
        FlowSpec("gpu", path=("dispatch", "shared_mem", "alu"), tokens=16, bytes_per_token=128, start_cycle=1),
    )

    report = advise_ppa(model=model, workload=workload)

    area_rec = next(rec for rec in report.recommendations if rec.title == "Area proxy concentrates at stage 'shared_mem'")
    power_rec = next(rec for rec in report.recommendations if rec.title == "Power proxy concentrates at stage 'shared_mem'")
    assert area_rec.evidence["target_label"] == "stage shared_mem"
    assert power_rec.evidence["target_label"] == "stage shared_mem"
    assert area_rec.evidence["dominant_area_share"] > 0.35
    assert power_rec.evidence["dominant_power_share"] > 0.35
    assert any("shared_mem" in suggestion for suggestion in area_rec.suggestions)
    assert any("shared_mem" in suggestion for suggestion in power_rec.suggestions)


def test_ppa_module_analysis_accepts_dsl_modules():
    stats = analyze_module_ppa(DslPpaAccum())

    assert stats.module_name == "dsl_ppa_accum"
    assert stats.state_bits == 8
    assert stats.comb_assignments >= 1
    assert stats.critical_assignment_target is not None
    assert stats.critical_assignment_phase in {"comb", "seq", "latch"}


def test_ppa_timing_recommendation_carries_assignment_location_for_dsl():
    report = advise_ppa(
        module=DslPpaAccum(),
        goals=PpaGoals(priority="timing_first", max_logic_depth=1),
    )

    timing_rec = next(rec for rec in report.recommendations if rec.category == "timing")
    assert timing_rec.evidence["module"] == "dsl_ppa_accum"
    assert timing_rec.evidence["critical_assignment_target"] in {"out", "acc"}
    assert timing_rec.evidence["critical_assignment_phase"] in {"comb", "seq"}
    assert timing_rec.evidence["critical_assignment_source_file"]
    assert isinstance(timing_rec.evidence["critical_assignment_source_line"], int)
    assert timing_rec.evidence["critical_expr_kind"] == "BinaryExpr"
    assert timing_rec.evidence["critical_expr_op"] == "+"
    assert timing_rec.evidence["critical_expr_operand_widths"] == (8, 8)


def test_ppa_recommendations_accept_implementation_report_evidence(tmp_path):
    timing = tmp_path / "timing.rpt"
    area = tmp_path / "area.rpt"
    power = tmp_path / "power.rpt"
    timing.write_text("WNS = -0.35\nTNS = -1.20\n", encoding="utf-8")
    area.write_text("Total area = 25000\nCombinational area = 9000\nSequential area = 7000\n", encoding="utf-8")
    power.write_text("Dynamic Power = 1.10\nLeakage Power = 0.20\n", encoding="utf-8")
    reports = load_implementation_report_bundle((timing, area, power))

    report = advise_ppa(
        module=_lowered(_deep_module()),
        implementation_reports=reports,
    )

    titles = [rec.title for rec in report.recommendations]
    assert "Close negative timing slack" in titles
    assert "Reduce implementation power hotspots" in titles
    assert "Revisit large implementation area" in titles


def test_module_ppa_calibration_fits_and_estimates_realistic_units(tmp_path):
    timing = tmp_path / "timing.rpt"
    area = tmp_path / "area.rpt"
    power = tmp_path / "power.rpt"
    timing.write_text("Clock period = 2.50\nWNS = -0.10\n", encoding="utf-8")
    area.write_text("Total area = 18000\nCombinational area = 7000\nSequential area = 5000\n", encoding="utf-8")
    power.write_text("Dynamic Power = 1.20\nLeakage Power = 0.30\n", encoding="utf-8")
    reports = load_implementation_report_bundle((timing, area, power))
    module = _deep_module()

    sample = build_module_ppa_calibration_sample(_lowered(module), reports)
    calibration = fit_module_ppa_calibration((sample,))
    estimate = estimate_calibrated_module_ppa(_lowered(module), calibration)

    assert calibration.timing_ns_per_depth is not None
    assert calibration.area_per_score is not None
    assert calibration.power_mw_per_score is not None
    assert estimate.module_name == module.name
    assert estimate.critical_path_ns == reports.timing.critical_path_ns
    assert estimate.total_area == reports.area.total_area
    assert estimate.total_power_mw == reports.power.total_mw
    assert estimate.fmax_mhz is not None and estimate.fmax_mhz > 0


def test_ppa_report_exposes_calibrated_module_estimate_and_guidance(tmp_path):
    timing = tmp_path / "timing.rpt"
    area = tmp_path / "area.rpt"
    power = tmp_path / "power.rpt"
    timing.write_text("Clock period = 2.50\nWNS = -0.10\n", encoding="utf-8")
    area.write_text("Total area = 18000\nCombinational area = 7000\nSequential area = 5000\n", encoding="utf-8")
    power.write_text("Dynamic Power = 1.20\nLeakage Power = 0.30\n", encoding="utf-8")
    reports = load_implementation_report_bundle((timing, area, power))
    module = _deep_module()

    calibration = fit_module_ppa_calibration((build_module_ppa_calibration_sample(_lowered(module), reports),))
    report = advise_ppa(module=_lowered(module), module_calibration=calibration)

    assert report.calibrated_module_estimate is not None
    assert report.calibrated_module_estimate.total_area == reports.area.total_area
    assert "Use calibration-backed module PPA estimate" in [rec.title for rec in report.recommendations]


def test_architecture_ppa_calibration_scales_cycles_throughput_and_stalls():
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
    stats = advise_ppa(model=model, workload=workload).architecture_stats
    assert stats is not None

    sample = build_architecture_ppa_calibration_sample(
        model,
        workload,
        measured_total_cycles=stats.total_cycles * 1.5,
        measured_makespan_cycles=stats.makespan_cycles * 1.25,
        measured_flow_throughputs={
            name: flow.throughput_tokens_per_cycle * 0.8
            for name, flow in stats.flow_stats.items()
        },
        measured_flow_stall_ratios={
            name: min(flow.stall_ratio * 1.2, 1.0)
            for name, flow in stats.flow_stats.items()
        },
    )
    calibration = fit_architecture_ppa_calibration((sample,))
    estimate = estimate_calibrated_architecture_ppa(stats=stats, calibration=calibration)

    assert calibration.cycle_scale == 1.5
    assert calibration.makespan_scale == 1.25
    assert calibration.throughput_scale == 0.8
    assert estimate.total_cycles == stats.total_cycles * 1.5
    assert estimate.makespan_cycles == stats.makespan_cycles * 1.25
    for name, flow in stats.flow_stats.items():
        assert estimate.flow_estimates[name].throughput_tokens_per_cycle == flow.throughput_tokens_per_cycle * 0.8
        assert estimate.flow_estimates[name].stall_ratio == sample.measured_flow_stall_ratios[name]


def test_ppa_report_exposes_calibrated_architecture_estimate_and_guidance():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
            StageSpec("shared_mem", kind="memory", latency=2, initiation_interval=2, capacity=1, queue_depth=2),
            StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu"), tokens=6),
        FlowSpec("gpu", path=("dispatch", "shared_mem", "alu"), tokens=6, start_cycle=1),
    )
    stats = advise_ppa(model=model, workload=workload).architecture_stats
    assert stats is not None

    calibration = fit_architecture_ppa_calibration(
        (
            build_architecture_ppa_calibration_sample(
                model,
                workload,
                measured_total_cycles=stats.total_cycles * 1.4,
                measured_makespan_cycles=stats.makespan_cycles * 1.2,
                measured_flow_throughputs={
                    name: flow.throughput_tokens_per_cycle * 0.75
                    for name, flow in stats.flow_stats.items()
                },
            ),
        )
    )
    report = advise_ppa(model=model, workload=workload, architecture_calibration=calibration)

    assert report.calibrated_architecture_estimate is not None
    assert report.calibrated_architecture_estimate.total_cycles == stats.total_cycles * 1.4
    assert "Use calibration-backed architecture estimate" in [rec.title for rec in report.recommendations]


def test_architecture_calibration_feedback_derives_stage_targets():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=4, queue_depth=4),
            StageSpec(
                "shared_mem",
                kind="memory",
                latency=2,
                initiation_interval=1,
                capacity=1,
                queue_depth=8,
                bandwidth_bytes_per_cycle=32,
            ),
            StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=2, queue_depth=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu"), tokens=8, bytes_per_token=128),
        FlowSpec("gpu", path=("dispatch", "shared_mem", "alu"), tokens=8, bytes_per_token=128, start_cycle=1),
    )
    baseline = advise_ppa(model=model, workload=workload).architecture_stats
    assert baseline is not None

    sample = build_architecture_ppa_calibration_sample(
        model,
        workload,
        measured_total_cycles=baseline.total_cycles * 1.6,
        measured_makespan_cycles=baseline.makespan_cycles * 1.4,
        measured_flow_throughputs={
            name: flow.throughput_tokens_per_cycle * 0.5
            for name, flow in baseline.flow_stats.items()
        },
        measured_flow_stall_ratios={
            name: max(flow.stall_ratio * 1.5, 0.2)
            for name, flow in baseline.flow_stats.items()
        },
    )
    targets = derive_architecture_calibration_targets(model, sample)
    target_map = {target.stage_name: target for target in targets}

    assert "shared_mem" in target_map
    shared_mem_target = target_map["shared_mem"]
    assert shared_mem_target.latency is not None and shared_mem_target.latency > model.stage("shared_mem").latency
    assert (
        shared_mem_target.bandwidth_bytes_per_cycle is not None
        and shared_mem_target.bandwidth_bytes_per_cycle < model.stage("shared_mem").bandwidth_bytes_per_cycle
    )
    assert shared_mem_target.queue_depth is not None and shared_mem_target.queue_depth < model.stage("shared_mem").queue_depth

    calibrated = calibrate_architecture_model(model, targets)
    calibrated_stats = advise_ppa(model=calibrated, workload=workload).architecture_stats
    assert calibrated_stats is not None
    assert calibrated_stats.total_cycles >= baseline.total_cycles
    assert (
        calibrated_stats.flow_stats["cpu"].throughput_tokens_per_cycle
        <= baseline.flow_stats["cpu"].throughput_tokens_per_cycle
    )


def test_ppa_calibration_models_round_trip_json(tmp_path):
    module_calibration = ModulePpaCalibrationModel(
        timing_ns_per_depth=0.5,
        area_per_score=10.0,
        power_mw_per_score=0.2,
        sample_count=3,
        timing_sample_count=3,
        area_sample_count=2,
        power_sample_count=1,
        sources=("a", "b"),
    )
    arch_calibration = ArchitecturePpaCalibrationModel(
        cycle_scale=1.5,
        makespan_scale=1.2,
        throughput_scale=0.8,
        stall_scale=1.1,
        sample_count=4,
        cycle_sample_count=4,
        makespan_sample_count=3,
        throughput_sample_count=2,
        stall_sample_count=1,
        sources=("measured",),
    )

    module_path = module_calibration.to_json_file(tmp_path / "module_calibration.json")
    arch_path = arch_calibration.to_json_file(tmp_path / "arch_calibration.json")
    loaded_module = ModulePpaCalibrationModel.from_json_file(module_path)
    loaded_arch = ArchitecturePpaCalibrationModel.from_json_file(arch_path)

    assert json.loads(module_path.read_text(encoding="utf-8"))["sample_count"] == 3
    assert json.loads(arch_path.read_text(encoding="utf-8"))["cycle_scale"] == 1.5
    assert loaded_module.area_per_score == 10.0
    assert loaded_arch.throughput_scale == 0.8


def test_ppa_report_exposes_transform_candidates():
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
    report = advise_ppa(model=model, workload=workload, goals=PpaGoals(min_throughput_tokens_per_cycle=1.0))

    assert report.transform_candidates
    assert any(candidate.suggested_knob == "bandwidth_bytes_per_cycle" for candidate in report.transform_candidates)


def test_ppa_report_exposes_registerfile_storage_transform_candidate():
    report = advise_ppa(module=RegisterFile(8, 4, 2, 1), goals=PpaGoals(max_state_bits=8))

    assert report.transform_candidates
    candidate = next(c for c in report.transform_candidates if c.suggested_value == "register_file_to_ram_wrapper")
    assert candidate.suggested_knob == "storage_impl"
    assert "RegisterFile.rf_" in candidate.target


def test_ppa_report_exposes_dualportram_storage_transform_candidate():
    report = advise_ppa(module=DualPortRAM(8, 8), goals=PpaGoals(max_memory_bits=16))

    assert report.transform_candidates
    candidate = next(c for c in report.transform_candidates if c.suggested_value == "compare_ram_wrapper_vs_flops")
    assert candidate.suggested_knob == "storage_impl"
    assert "DualPortRAM.mem" in candidate.target


def test_ppa_report_exposes_lut_storage_transform_candidate():
    report = advise_ppa(module=LUT(8, depth=8), goals=PpaGoals(max_memory_bits=16))

    assert report.transform_candidates
    candidate = next(c for c in report.transform_candidates if c.suggested_value == "pack_rows_or_share_banks")
    assert candidate.suggested_knob == "table_layout"
    assert "LUT.lut" in candidate.target


def test_ppa_report_exposes_signed_multiplier_transform_candidate():
    report = advise_ppa(module=SignedMultiplier(8, 3))

    assert report.transform_candidates
    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "retime_product_stages_keep_valid_shell"
    )
    assert candidate.suggested_knob == "pipeline_partition"
    assert "SignedMultiplier.mpd_0" in candidate.target


def test_ppa_report_exposes_mac_transform_candidate():
    report = advise_ppa(module=MAC(8))

    assert report.transform_candidates
    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "split_operands_product_accumulate"
    )
    assert candidate.suggested_knob == "pipeline_partition"
    assert "MAC.prod" in candidate.target


def test_ppa_report_exposes_multi_multiplier_datapath_transform_candidate():
    report = advise_ppa(module=_lowered(_multiplier_hotspot_module()))

    assert report.transform_candidates
    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "tile_or_share_wide_multipliers"
    )
    assert candidate.suggested_knob == "multiplier_impl"
    assert "ppa_mult.prod0" in candidate.target


def test_ppa_report_exposes_handshake_payload_state_candidate():
    report = advise_ppa(module=SkidBuffer(16), goals=PpaGoals(max_state_bits=16))
    recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")

    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "update_payload_only_on_handshake"
    )
    assert candidate.suggested_knob == "payload_gating"
    assert "SkidBuffer.buf_data" in candidate.target
    assert recommendation.evidence["handshake_payload_targets"] == ("buf_data", "buf_valid")
    assert recommendation.evidence["handshake_payload_anchors"][0].startswith("SkidBuffer.buf_data @ ")
    assert recommendation.evidence["handshake_payload_anchors"][1].startswith("SkidBuffer.buf_valid @ ")


def test_ppa_report_exposes_readyvalid_register_payload_state_candidate():
    report = advise_ppa(module=ReadyValidRegister(16), goals=PpaGoals(max_state_bits=16))
    recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")

    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "update_payload_only_on_handshake"
    )
    assert candidate.suggested_knob == "payload_gating"
    assert "ReadyValidRegister.data_reg" in candidate.target
    assert recommendation.evidence["handshake_payload_targets"] == ("data_reg", "valid_reg")
    assert recommendation.evidence["handshake_payload_anchors"][0].startswith("ReadyValidRegister.data_reg @ ")
    assert recommendation.evidence["handshake_payload_anchors"][1].startswith("ReadyValidRegister.valid_reg @ ")


def test_ppa_readyvalid_register_payload_gating_candidate_drops_after_hold_payload():
    report = advise_ppa(module=ReadyValidRegister(16, hold_payload=True), goals=PpaGoals(max_state_bits=16))
    recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")

    assert recommendation.evidence["state_pattern_hint"] == "handshake_payload_state"
    assert recommendation.evidence["payload_gating_already_applied"] is True
    assert not any(
        candidate.suggested_value == "update_payload_only_on_handshake"
        for candidate in report.transform_candidates
    )


def test_ppa_report_exposes_fifo_storage_candidate():
    report = advise_ppa(module=ReadyValidFIFO(width=16, depth=4), goals=PpaGoals(max_memory_bits=32))

    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "compare_fifo_storage_impls"
    )
    assert candidate.suggested_knob == "storage_impl"
    assert "ReadyValidFIFO.storage" in candidate.target


def test_ppa_report_exposes_queue_metadata_layout_candidate():
    report = advise_ppa(
        module=ReqRspQueue(req_width=8, rsp_width=8, depth=4, addr_width=4, write_enable=True, strobe_width=2),
        goals=PpaGoals(max_memory_bits=32),
    )
    recommendation = next(r for r in report.recommendations if r.title == "Bank or isolate large memories")

    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "bundle_queue_sideband_fields"
    )
    assert candidate.suggested_knob == "metadata_layout"
    assert "ReqRspQueue.req_storage" in candidate.target
    assert recommendation.evidence["queue_control_targets"] == ("count", "wr_ptr", "rd_ptr", "push_fire", "pop_fire")
    assert recommendation.evidence["queue_sideband_targets"] == (
        "req_storage",
        "addr_storage",
        "write_storage",
        "strb_storage",
    )
    assert recommendation.evidence["queue_control_anchors"][0].startswith("ReqRspQueue.count @ ")
    assert recommendation.evidence["queue_control_anchors"][1].startswith("ReqRspQueue.wr_ptr @ ")
    assert recommendation.evidence["queue_control_anchors"][2].startswith("ReqRspQueue.rd_ptr @ ")
    assert recommendation.evidence["queue_sideband_anchors"] == (
        "ReqRspQueue.req_storage",
        "ReqRspQueue.addr_storage",
        "ReqRspQueue.write_storage",
        "ReqRspQueue.strb_storage",
    )


def test_ppa_queue_metadata_candidate_drops_after_bundling_sideband_storage():
    baseline = advise_ppa(
        module=ReqRspQueue(req_width=8, rsp_width=8, depth=4, addr_width=4, write_enable=True, strobe_width=2),
        goals=PpaGoals(max_memory_bits=32),
    )
    bundled = advise_ppa(
        module=ReqRspQueue(
            req_width=8,
            rsp_width=8,
            depth=4,
            addr_width=4,
            write_enable=True,
            strobe_width=2,
            bundle_sideband=True,
        ),
        goals=PpaGoals(max_memory_bits=32),
    )

    baseline_memory = next(rec for rec in baseline.recommendations if rec.title == "Bank or isolate large memories")
    bundled_memory = next(rec for rec in bundled.recommendations if rec.title == "Bank or isolate large memories")

    assert baseline_memory.evidence["memory_pattern_hint"] == "queue_metadata_arrays"
    assert bundled_memory.evidence["memory_pattern_hint"] == "generic_storage"
    assert baseline_memory.evidence["queue_sideband_targets"] == (
        "req_storage",
        "addr_storage",
        "write_storage",
        "strb_storage",
    )
    assert "queue_sideband_targets" not in bundled_memory.evidence
    assert any(
        candidate.suggested_value == "bundle_queue_sideband_fields"
        for candidate in baseline.transform_candidates
    )
    assert not any(
        candidate.suggested_value == "bundle_queue_sideband_fields"
        for candidate in bundled.transform_candidates
    )

    bundled_sim = lower_dsl_module_to_sim(
        ReqRspQueue(
            req_width=8,
            rsp_width=8,
            depth=4,
            addr_width=4,
            write_enable=True,
            strobe_width=2,
            bundle_sideband=True,
        )
    ).module
    bundled_proposals = derive_rewrite_proposals(bundled_sim, bundled)
    assert not any(
        proposal.summary == "Bank or isolate large memories"
        and proposal.source_assignment == "entry_storage"
        for proposal in bundled_proposals
    )


def test_ppa_report_exposes_register_bank_layout_candidate():
    report = advise_ppa(module=APBRegisterBank(depth=8), goals=PpaGoals(max_memory_bits=32))

    candidate = next(
        c for c in report.transform_candidates
        if c.suggested_value == "partition_or_pack_register_bank"
    )
    assert candidate.suggested_knob == "register_layout"
    assert "APBRegisterBank.regmem" in candidate.target


def test_ppa_report_exposes_register_bank_control_partition_candidates():
    for module_name, module in (
        ("AXI4LiteRegisterBank", AXI4LiteRegisterBank(depth=8)),
        ("WishboneRegisterBank", WishboneRegisterBank(depth=8)),
    ):
        report = advise_ppa(module=module, goals=PpaGoals(max_state_bits=16))
        recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")
        candidate = next(
            c for c in report.transform_candidates
            if c.suggested_value == "split_capture_and_response_state"
        )
        assert candidate.suggested_knob == "control_partition"
        assert module_name in candidate.target
        assert "register_bank_control_targets" in recommendation.evidence
        assert recommendation.evidence["register_bank_control_anchors"]


def test_ppa_axilite_register_bank_control_partition_candidate_drops_after_split_control_state():
    report = advise_ppa(
        module=AXI4LiteRegisterBank(depth=8, split_control_state=True),
        goals=PpaGoals(max_memory_bits=32, max_state_bits=16),
    )
    recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")

    assert recommendation.evidence["state_pattern_hint"] == "register_bank_control_state"
    assert recommendation.evidence["control_partition_already_applied"] is True
    assert not any(
        candidate.suggested_value == "split_capture_and_response_state"
        for candidate in report.transform_candidates
    )


def test_ppa_wishbone_register_bank_control_partition_candidate_drops_after_split_control_state():
    report = advise_ppa(
        module=WishboneRegisterBank(depth=8, split_control_state=True),
        goals=PpaGoals(max_memory_bits=32, max_state_bits=16),
    )
    recommendation = next(r for r in report.recommendations if r.title == "Reduce or gate large sequential state")

    assert recommendation.evidence["state_pattern_hint"] == "register_bank_control_state"
    assert recommendation.evidence["control_partition_already_applied"] is True
    assert not any(
        candidate.suggested_value == "split_capture_and_response_state"
        for candidate in report.transform_candidates
    )


def test_ppa_rewrite_proposals_can_be_derived_and_applied():
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=_lowered(module), implementation_reports=reports)
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    assert proposals[0].applicability == "direct_apply"
    assert proposals[0].applicability_reason is None
    rewritten = apply_rewrite_proposal(module, proposals[0])
    assert any(signal.name.endswith("_pipe_q") for signal in rewritten.signals)
    assert any(signal.name.endswith("_pipe_w") for signal in rewritten.signals)
    assert len(rewritten.assignments) >= len(module.assignments)


def test_ppa_rewrite_proposals_can_be_derived_for_mac_candidate():
    module = lower_dsl_module_to_sim(MAC(8)).module
    report = advise_ppa(module=MAC(8))
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    proposal = next(p for p in proposals if p.source_assignment == "prod")
    assert proposal.summary == "Audit multiplier-heavy stages"
    assert proposal.applicability == "direct_apply"
    rewritten = apply_rewrite_proposal(module, proposal)
    assert any(signal.name == "prod_pipe_q" for signal in rewritten.signals)
    assert any(signal.name == "prod_pipe_w" for signal in rewritten.signals)


def test_ppa_rewrite_proposals_can_be_derived_for_signed_multiplier_candidate():
    module = lower_dsl_module_to_sim(SignedMultiplier(8, 3)).module
    report = advise_ppa(module=SignedMultiplier(8, 3))
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    proposal = next(p for p in proposals if p.source_assignment == "mpd_0")
    assert proposal.summary == "Audit multiplier-heavy stages"
    assert proposal.applicability == "direct_apply"
    rewritten = apply_rewrite_proposal(module, proposal)
    assert any(signal.name == "mpd_0_pipe_q" for signal in rewritten.signals)
    assert any(signal.name == "mpd_0_pipe_w" for signal in rewritten.signals)


def test_ppa_rewrite_proposals_can_be_derived_for_registerfile_storage_candidate():
    module = lower_dsl_module_to_sim(RegisterFile(8, 4, 2, 1)).module
    report = advise_ppa(module=RegisterFile(8, 4, 2, 1), goals=PpaGoals(max_state_bits=8))
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    proposal = next(p for p in proposals if p.summary == "Reduce or gate large sequential state")
    assert proposal.applicability == "scaffold_only"
    assert proposal.applicability_reason is not None
    assert any(edit.kind == "insert_memory" and edit.target == "rf_wrap" for edit in proposal.edits)


def test_ppa_rewrite_proposals_can_be_derived_for_dualportram_storage_candidate():
    module = lower_dsl_module_to_sim(DualPortRAM(8, 8)).module
    report = advise_ppa(module=DualPortRAM(8, 8), goals=PpaGoals(max_memory_bits=16))
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    proposal = next(p for p in proposals if p.summary == "Bank or isolate large memories")
    assert proposal.applicability == "direct_apply"
    assert any(edit.kind == "insert_memory" and edit.target == "mem_bank0" for edit in proposal.edits)
    assert any(edit.kind == "insert_memory" and edit.target == "mem_bank1" for edit in proposal.edits)
    rewritten = apply_rewrite_proposal(module, proposal)
    assert any(memory.name == "mem_bank0" for memory in rewritten.memories)
    assert any(memory.name == "mem_bank1" for memory in rewritten.memories)


def test_ppa_rewrite_proposals_can_be_derived_for_lut_storage_candidate():
    module = lower_dsl_module_to_sim(LUT(8, depth=8)).module
    report = advise_ppa(module=LUT(8, depth=8), goals=PpaGoals(max_memory_bits=16))
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    proposal = next(p for p in proposals if p.summary == "Bank or isolate large memories")
    assert proposal.applicability == "direct_apply"
    assert any(edit.kind == "insert_memory" and edit.target == "lut_packed" for edit in proposal.edits)
    rewritten = apply_rewrite_proposal(module, proposal)
    assert any(memory.name == "lut_packed" for memory in rewritten.memories)


def test_ppa_rewrite_proposals_can_be_derived_for_handshake_payload_gating_candidates():
    for module, source_assignment in (
        (SkidBuffer(16), "buf_data"),
        (ReadyValidRegister(16), "data_reg"),
    ):
        sim = lower_dsl_module_to_sim(module).module
        report = advise_ppa(module=module, goals=PpaGoals(max_state_bits=16))
        proposal = next(
            p for p in derive_rewrite_proposals(sim, report)
            if p.summary == "Reduce or gate large sequential state"
        )

        assert proposal.applicability == "scaffold_only"
        assert proposal.source_assignment == source_assignment
        assert proposal.applicability_reason is not None
        assert any(edit.kind == "insert_wire" and edit.target.endswith("_hold_en") for edit in proposal.edits)


def test_ppa_rewrite_proposals_can_be_derived_for_queue_and_register_bank_scaffolds():
    queue_module = ReqRspQueue(req_width=8, rsp_width=8, depth=4, addr_width=4, write_enable=True, strobe_width=2)
    queue_sim = lower_dsl_module_to_sim(queue_module).module
    queue_report = advise_ppa(module=queue_module, goals=PpaGoals(max_memory_bits=32))
    queue_proposal = next(
        p for p in derive_rewrite_proposals(queue_sim, queue_report)
        if p.summary == "Bank or isolate large memories"
    )
    assert queue_proposal.applicability == "scaffold_only"
    assert queue_proposal.source_assignment == "req_storage"
    assert any(edit.target == "entry_bundle" for edit in queue_proposal.edits)

    regbank_module = AXI4LiteRegisterBank(depth=8)
    regbank_sim = lower_dsl_module_to_sim(regbank_module).module
    regbank_report = advise_ppa(module=regbank_module, goals=PpaGoals(max_state_bits=16))
    regbank_proposal = next(
        p for p in derive_rewrite_proposals(regbank_sim, regbank_report)
        if p.summary == "Reduce or gate large sequential state"
    )
    assert regbank_proposal.applicability == "scaffold_only"
    assert regbank_proposal.source_assignment == "w_data_latched"
    assert any(edit.target == "capture_fire" for edit in regbank_proposal.edits)


def test_ppa_rewrite_evaluation_reports_depth_improvement():
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=_lowered(module), implementation_reports=reports)
    proposal = derive_rewrite_proposals(module, report)[0]
    evaluation = evaluate_rewrite_proposal(module, proposal)

    assert evaluation.proposal == proposal
    assert evaluation.original_depth == analyze_module_ppa(_lowered(module)).max_expr_depth
    assert evaluation.rewritten_depth < evaluation.original_depth
    assert evaluation.depth_delta < 0
    assert evaluation.rewritten_stats.max_expr_depth <= evaluation.original_stats.max_expr_depth


def test_ppa_rewrite_validation_detects_behavior_change_and_compiled_parity(tmp_path):
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=_lowered(module), implementation_reports=reports)
    proposal = derive_rewrite_proposals(module, report)[0]
    validation = validate_rewrite_proposal(
        module,
        proposal,
        vectors=(
            {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "we": 0, "addr": 0},
            {"a": 9, "b": 10, "c": 11, "d": 12, "e": 13, "f": 14, "g": 15, "h": 16, "we": 1, "addr": 3},
        ),
        include_compiled_parity=True,
        build_dir=tmp_path / "rewrite_validate",
    )

    assert validation.evaluation.proposal == proposal
    assert validation.evaluation.rewritten_depth < validation.evaluation.original_depth
    assert validation.behavior_preserved is False
    assert validation.output_mismatches
    assert validation.rewritten_parity is not None
    assert validation.rewritten_parity.matched is True


def test_ppa_rewrite_apply_rejects_scaffold_only_proposal():
    module = lower_dsl_module_to_sim(RegisterFile(8, 4, 2, 1)).module
    report = advise_ppa(module=RegisterFile(8, 4, 2, 1), goals=PpaGoals(max_state_bits=8))
    proposal = next(
        p for p in derive_rewrite_proposals(module, report)
        if p.summary == "Reduce or gate large sequential state"
    )

    with pytest.raises(ValueError, match="scaffold_only"):
        apply_rewrite_proposal(module, proposal)


def test_ppa_rewrite_validate_rejects_scaffold_only_proposal():
    module = lower_dsl_module_to_sim(RegisterFile(8, 4, 2, 1)).module
    report = advise_ppa(module=RegisterFile(8, 4, 2, 1), goals=PpaGoals(max_state_bits=8))
    proposal = next(
        p for p in derive_rewrite_proposals(module, report)
        if p.summary == "Reduce or gate large sequential state"
    )

    with pytest.raises(ValueError, match="scaffold_only"):
        validate_rewrite_proposal(module, proposal)
