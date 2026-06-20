from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload, calibrate_architecture_model
import json
from rtlgen_x.dsl import Else, If, Input, Module, Output, Reg
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


def test_ppa_recommendations_accept_implementation_report_evidence(tmp_path):
    timing = tmp_path / "timing.rpt"
    area = tmp_path / "area.rpt"
    power = tmp_path / "power.rpt"
    timing.write_text("WNS = -0.35\nTNS = -1.20\n", encoding="utf-8")
    area.write_text("Total area = 25000\nCombinational area = 9000\nSequential area = 7000\n", encoding="utf-8")
    power.write_text("Dynamic Power = 1.10\nLeakage Power = 0.20\n", encoding="utf-8")
    reports = load_implementation_report_bundle((timing, area, power))

    report = advise_ppa(
        module=_deep_module(),
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

    sample = build_module_ppa_calibration_sample(module, reports)
    calibration = fit_module_ppa_calibration((sample,))
    estimate = estimate_calibrated_module_ppa(module, calibration)

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

    calibration = fit_module_ppa_calibration((build_module_ppa_calibration_sample(module, reports),))
    report = advise_ppa(module=module, module_calibration=calibration)

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


def test_ppa_rewrite_proposals_can_be_derived_and_applied():
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=module, implementation_reports=reports)
    proposals = derive_rewrite_proposals(module, report)

    assert proposals
    rewritten = apply_rewrite_proposal(module, proposals[0])
    assert any(signal.name.endswith("_pipe_q") for signal in rewritten.signals)
    assert any(signal.name.endswith("_pipe_w") for signal in rewritten.signals)
    assert len(rewritten.assignments) >= len(module.assignments)


def test_ppa_rewrite_evaluation_reports_depth_improvement():
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=module, implementation_reports=reports)
    proposal = derive_rewrite_proposals(module, report)[0]
    evaluation = evaluate_rewrite_proposal(module, proposal)

    assert evaluation.proposal == proposal
    assert evaluation.original_depth == analyze_module_ppa(module).max_expr_depth
    assert evaluation.rewritten_depth < evaluation.original_depth
    assert evaluation.depth_delta < 0
    assert evaluation.rewritten_stats.max_expr_depth <= evaluation.original_stats.max_expr_depth


def test_ppa_rewrite_validation_detects_behavior_change_and_compiled_parity(tmp_path):
    timing = type("Timing", (), {"wns_ns": -0.35, "tns_ns": None})()
    area = type("Area", (), {"total_area": None, "combinational_area": None, "sequential_area": None})()
    power = type("Power", (), {"dynamic_mw": None, "leakage_mw": None, "total_mw": None})()
    reports = type("Bundle", (), {"timing": timing, "area": area, "power": power, "sources": ("inline",)})()
    module = _deep_module()
    report = advise_ppa(module=module, implementation_reports=reports)
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
