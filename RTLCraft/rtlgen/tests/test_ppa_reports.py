import pytest

from rtlgen.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload
from rtlgen.dsl import DslLoweringReport, LoweredDslModule
from rtlgen.dsl import (
    APBRegisterBank,
    AXI4LiteRegisterBank,
    DualPortRAM,
    LUT,
    ReadyValidFIFO,
    ReadyValidRegister,
    RegisterFile,
    ReqRspQueue,
    SkidBuffer,
    WishboneRegisterBank,
)
from rtlgen.ppa import (
    PpaGoals,
    advise_ppa,
    build_architecture_ppa_calibration_sample,
    build_module_ppa_calibration_sample,
    emit_ppa_report_markdown,
    fit_architecture_ppa_calibration,
    fit_module_ppa_calibration,
    load_implementation_report_bundle,
    parse_area_report,
    parse_power_report,
    parse_timing_report,
    summarize_ppa_report,
)
from rtlgen.sim import Assignment, BinaryExpr, Memory, MemoryWrite, Signal, SignalRef, SimModule


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


def test_parse_timing_area_and_power_reports(tmp_path):
    timing_text = "Clock period = 2.00\nWNS = -0.25\nTNS = -1.50\n"
    area_text = "Total area = 12345.0\nCombinational area = 4567.0\nSequential area = 3210.0\n"
    power_text = "Dynamic Power = 0.72\nLeakage Power = 0.08\n"

    timing = parse_timing_report(timing_text)
    area = parse_area_report(area_text)
    power = parse_power_report(power_text)

    assert timing.wns_ns == -0.25
    assert timing.tns_ns == -1.5
    assert timing.clock_period_ns == 2.0
    assert timing.fmax_mhz == 500.0
    assert timing.critical_path_ns == 2.25
    assert area.total_area == 12345.0
    assert area.combinational_area == 4567.0
    assert power.dynamic_mw == 0.72
    assert power.total_mw == 0.8

    timing_path = tmp_path / "timing.rpt"
    area_path = tmp_path / "area.rpt"
    power_path = tmp_path / "power.rpt"
    timing_path.write_text(timing_text, encoding="utf-8")
    area_path.write_text(area_text, encoding="utf-8")
    power_path.write_text(power_text, encoding="utf-8")

    bundle = load_implementation_report_bundle((timing_path, area_path, power_path))
    assert bundle.timing.wns_ns == -0.25
    assert bundle.timing.clock_period_ns == 2.0
    assert bundle.area.total_area == 12345.0
    assert bundle.power.total_mw == 0.8
    assert len(bundle.sources) == 3


def _mini_module() -> SimModule:
    return SimModule(
        name="ppa_report_demo",
        signals=(
            Signal("a", width=32, kind="input"),
            Signal("b", width=32, kind="input"),
            Signal("we", width=1, kind="input"),
            Signal("addr", width=6, kind="input"),
            Signal("acc", width=64, kind="state"),
            Signal("out", width=65, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", BinaryExpr("*", SignalRef("a"), SignalRef("b")), SignalRef("acc"))),
            Assignment("acc", SignalRef("out"), phase="seq", source_file="mini_state.py", source_line=12),
        ),
        outputs=("out",),
        memories=(Memory("lut", width=32, depth=64),),
        memory_writes=(
            MemoryWrite(
                "lut",
                SignalRef("addr"),
                SignalRef("a"),
                enable=SignalRef("we"),
                source_file="mini_mem.py",
                source_line=21,
            ),
        ),
    )


def _mini_architecture():
    model = ArchitectureModel(
        [
            StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=1),
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
    return model, workload


def test_ppa_report_summary_marks_heuristic_only_mode():
    report = advise_ppa(module=_lowered(_mini_module()), goals=PpaGoals(priority="timing_first", max_logic_depth=1))
    summary = summarize_ppa_report(report)
    markdown = emit_ppa_report_markdown(summary=summary, title="Heuristic PPA")

    assert summary.module_trust is not None
    assert summary.module_trust.mode == "heuristic_only"
    assert summary.module_trust.ranking_signal == "heuristic_score"
    assert summary.top_recommendations
    assert summary.findings
    assert markdown.startswith("# Heuristic PPA\n")
    assert "mode: `heuristic_only`" in markdown
    assert "preferred ranking signal: `heuristic_score`" in markdown
    assert "## Top Recommendations" in markdown
    assert any(rec.actions for rec in summary.top_recommendations)
    assert "  next: " in markdown


def test_ppa_report_summary_marks_directional_calibration_and_renders_guidance(tmp_path):
    timing = tmp_path / "timing.rpt"
    area = tmp_path / "area.rpt"
    power = tmp_path / "power.rpt"
    timing.write_text("Clock period = 2.50\nWNS = -0.10\n", encoding="utf-8")
    area.write_text("Total area = 18000\nCombinational area = 7000\nSequential area = 5000\n", encoding="utf-8")
    power.write_text("Dynamic Power = 1.20\nLeakage Power = 0.30\n", encoding="utf-8")
    reports = load_implementation_report_bundle((timing, area, power))

    module = _mini_module()
    model, workload = _mini_architecture()
    module_calibration = fit_module_ppa_calibration((build_module_ppa_calibration_sample(_lowered(module), reports),))
    baseline_arch = advise_ppa(model=model, workload=workload).architecture_stats
    assert baseline_arch is not None
    architecture_calibration = fit_architecture_ppa_calibration(
        (
            build_architecture_ppa_calibration_sample(
                model,
                workload,
                measured_total_cycles=baseline_arch.total_cycles * 1.2,
                measured_makespan_cycles=baseline_arch.makespan_cycles * 1.1,
                measured_flow_throughputs={
                    name: flow.throughput_tokens_per_cycle * 0.85
                    for name, flow in baseline_arch.flow_stats.items()
                },
                measured_flow_stall_ratios={
                    name: min(flow.stall_ratio * 1.1, 1.0)
                    for name, flow in baseline_arch.flow_stats.items()
                },
            ),
        )
    )

    report = advise_ppa(
        module=_lowered(module),
        model=model,
        workload=workload,
        module_calibration=module_calibration,
        architecture_calibration=architecture_calibration,
    )
    summary = summarize_ppa_report(report)
    markdown = emit_ppa_report_markdown(report, title="Calibrated PPA")

    assert summary.module_trust is not None
    assert summary.module_trust.mode == "directional_calibrated"
    assert summary.module_trust.metrics_available == ("timing", "area", "power")
    assert summary.architecture_trust is not None
    assert summary.architecture_trust.mode == "directional_calibrated"
    assert summary.architecture_trust.metrics_available == ("cycles", "makespan", "throughput", "stall")
    assert "mode: `directional_calibrated`" in markdown
    assert "preferred ranking signal: `calibrated_estimate`" in markdown
    assert "## Calibration Guidance" in markdown
    assert "Module" in markdown
    assert "Architecture" in markdown


def test_ppa_report_summary_prefers_precise_target_labels():
    module = SimModule(
        name="ppa_summary_mult",
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
                source_line=21,
            ),
            Assignment(
                "prod1",
                BinaryExpr("*", SignalRef("c"), SignalRef("d")),
                source_file="toy_mult.py",
                source_line=22,
            ),
            Assignment("out", BinaryExpr("+", SignalRef("prod0"), SignalRef("prod1"))),
        ),
        outputs=("out",),
    )

    report = advise_ppa(module=_lowered(module))
    summary = summarize_ppa_report(report)
    multiplier_summary = next(rec for rec in summary.top_recommendations if rec.title == "Audit multiplier-heavy stages")
    markdown = emit_ppa_report_markdown(summary=summary, title="Precise Target PPA")

    assert multiplier_summary.target == "ppa_summary_mult.prod0 @ toy_mult.py:21"
    assert any("16x16 partial products" in action for action in multiplier_summary.actions)
    assert "ppa_summary_mult.prod0 @ toy_mult.py:21" in markdown


def test_ppa_report_summary_uses_memory_source_mapping_when_available():
    report = advise_ppa(
        module=_lowered(_mini_module()),
        goals=PpaGoals(max_memory_bits=1024),
    )
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    markdown = emit_ppa_report_markdown(summary=summary, title="Memory Target PPA")

    assert memory_summary.target == "ppa_report_demo.lut @ mini_mem.py:21"
    assert "ppa_report_demo.lut @ mini_mem.py:21" in markdown


def test_ppa_report_summary_surfaces_registerfile_state_pattern_hint():
    report = advise_ppa(module=RegisterFile(8, 4, 2, 1), goals=PpaGoals(max_state_bits=8))
    summary = summarize_ppa_report(report)
    state_summary = next(rec for rec in summary.top_recommendations if rec.title == "Reduce or gate large sequential state")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "rd_data_0")
    markdown = emit_ppa_report_markdown(summary=summary, title="RegisterFile PPA")

    assert state_summary.pattern_hint == "register_file_rows"
    assert rewrite_summary.applicability == "scaffold_only"
    assert rewrite_summary.applicability_reason is not None
    assert "insert_memory" in rewrite_summary.edit_kinds
    assert "register_file_rows" in markdown
    assert any("denser RAM-style wrapper" in action for action in state_summary.actions)
    assert "## Rewrite Proposals" in markdown
    assert "[scaffold_only]" in markdown
    assert "current executable memory subset does not model this multi-read or multi-write register-file wrapper directly" in markdown


def test_ppa_report_summary_surfaces_dualportram_memory_pattern_hint():
    report = advise_ppa(module=DualPortRAM(8, 8), goals=PpaGoals(max_memory_bits=16))
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "a_rdata")
    markdown = emit_ppa_report_markdown(summary=summary, title="DualPortRAM PPA")

    assert memory_summary.pattern_hint == "small_ram"
    assert rewrite_summary.applicability == "direct_apply"
    assert "insert_memory" in rewrite_summary.edit_kinds
    assert "small_ram" in markdown
    assert "[direct_apply] Bank or isolate large memories (a_rdata)" in markdown


def test_ppa_report_summary_surfaces_lut_memory_pattern_hint():
    report = advise_ppa(module=LUT(8, depth=8), goals=PpaGoals(max_memory_bits=16))
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "dout")
    markdown = emit_ppa_report_markdown(summary=summary, title="LUT PPA")

    assert memory_summary.pattern_hint == "lut_rom"
    assert rewrite_summary.applicability == "direct_apply"
    assert "lut_rom" in markdown
    assert any("coefficient ROM" in action for action in memory_summary.actions)
    assert "[direct_apply] Bank or isolate large memories (dout)" in markdown


def test_ppa_report_summary_surfaces_handshake_payload_state_pattern_hint():
    report = advise_ppa(module=SkidBuffer(16), goals=PpaGoals(max_state_bits=16))
    summary = summarize_ppa_report(report)
    state_summary = next(rec for rec in summary.top_recommendations if rec.title == "Reduce or gate large sequential state")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "buf_data_hold_en")
    markdown = emit_ppa_report_markdown(summary=summary, title="SkidBuffer PPA")

    assert state_summary.pattern_hint == "handshake_payload_state"
    assert state_summary.focus_anchors[0].startswith("SkidBuffer.buf_data @ ")
    assert any("accepted transfers" in action for action in state_summary.actions)
    assert rewrite_summary.applicability == "scaffold_only"
    assert rewrite_summary.origin_anchor is not None
    assert rewrite_summary.origin_anchor.startswith("SkidBuffer.buf_data @ ")
    assert "hold by default" in (rewrite_summary.applicability_reason or "")
    assert "handshake_payload_state" in markdown
    assert "  focus: SkidBuffer.buf_data @" in markdown
    assert "  origin: SkidBuffer.buf_data @" in markdown
    assert "[scaffold_only] Reduce or gate large sequential state (buf_data_hold_en)" in markdown


def test_ppa_report_summary_surfaces_fifo_storage_pattern_hint():
    report = advise_ppa(module=ReadyValidFIFO(width=16, depth=4), goals=PpaGoals(max_memory_bits=32))
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    markdown = emit_ppa_report_markdown(summary=summary, title="ReadyValidFIFO PPA")

    assert memory_summary.pattern_hint == "fifo_queue_storage"
    assert any("FIFO payload storage" in action for action in memory_summary.actions)
    assert "fifo_queue_storage" in markdown


def test_ppa_report_summary_surfaces_queue_metadata_pattern_hint():
    report = advise_ppa(
        module=ReqRspQueue(req_width=8, rsp_width=8, depth=4, addr_width=4, write_enable=True, strobe_width=2),
        goals=PpaGoals(max_memory_bits=32),
    )
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "req_storage")
    markdown = emit_ppa_report_markdown(summary=summary, title="ReqRspQueue PPA")

    assert memory_summary.pattern_hint == "queue_metadata_arrays"
    assert memory_summary.focus_anchors[0].startswith("ReqRspQueue.count @ ")
    assert any("queue metadata storage" in action for action in memory_summary.actions)
    assert rewrite_summary.applicability == "scaffold_only"
    assert rewrite_summary.origin_anchor == "ReqRspQueue.req_storage"
    assert "per-entry payload bundle" in (rewrite_summary.applicability_reason or "")
    assert "queue_metadata_arrays" in markdown
    assert "  focus: ReqRspQueue.count @" in markdown
    assert "  origin: ReqRspQueue.req_storage" in markdown
    assert "[scaffold_only] Bank or isolate large memories (req_storage)" in markdown


def test_ppa_report_summary_surfaces_control_register_bank_patterns():
    report = advise_ppa(module=AXI4LiteRegisterBank(depth=8), goals=PpaGoals(max_memory_bits=32, max_state_bits=16))
    summary = summarize_ppa_report(report)
    memory_summary = next(rec for rec in summary.top_recommendations if rec.title == "Bank or isolate large memories")
    state_summary = next(rec for rec in summary.top_recommendations if rec.title == "Reduce or gate large sequential state")
    rewrite_summary = next(proposal for proposal in summary.rewrite_proposals if proposal.target == "capture_fire")
    markdown = emit_ppa_report_markdown(summary=summary, title="AXI4LiteRegisterBank PPA")

    assert memory_summary.pattern_hint == "control_register_bank"
    assert state_summary.pattern_hint == "register_bank_control_state"
    assert state_summary.focus_anchors
    assert rewrite_summary.applicability == "scaffold_only"
    assert rewrite_summary.origin_anchor == "AXI4LiteRegisterBank.w_data_latched"
    assert "protocol capture and response bookkeeping" in (rewrite_summary.applicability_reason or "")
    assert "control_register_bank" in markdown
    assert "register_bank_control_state" in markdown
    assert "  focus: AXI4LiteRegisterBank.w_data_latched @" in markdown
    assert "  origin: AXI4LiteRegisterBank.w_data_latched" in markdown
    assert "[scaffold_only] Reduce or gate large sequential state (capture_fire)" in markdown


def test_ppa_report_markdown_supports_protocol_refinement_walkthrough_shape():
    report = advise_ppa(
        module=ReqRspQueue(req_width=8, rsp_width=8, depth=4, addr_width=4, write_enable=True, strobe_width=2),
        goals=PpaGoals(max_memory_bits=32),
    )
    markdown = emit_ppa_report_markdown(report, title="ReqRspQueue PPA")

    assert "ReqRspQueue.req_storage" in markdown
    assert "  focus: ReqRspQueue.count @" in markdown
    assert "  focus: ReqRspQueue.wr_ptr @" in markdown
    assert "  origin: ReqRspQueue.req_storage" in markdown
    assert "[scaffold_only] Bank or isolate large memories (req_storage)" in markdown


def test_ppa_report_markdown_supports_axi4lite_refinement_walkthrough_shape():
    report = advise_ppa(module=AXI4LiteRegisterBank(depth=8), goals=PpaGoals(max_memory_bits=32, max_state_bits=16))
    markdown = emit_ppa_report_markdown(report, title="AXI4LiteRegisterBank PPA")

    assert "AXI4LiteRegisterBank.write_commit" in markdown
    assert "  focus: AXI4LiteRegisterBank.w_data_latched @" in markdown
    assert "  focus: AXI4LiteRegisterBank.read_fire" in markdown
    assert "  origin: AXI4LiteRegisterBank.w_data_latched" in markdown
    assert "[scaffold_only] Reduce or gate large sequential state (capture_fire)" in markdown


def test_ppa_report_summary_rejects_raw_simmodule():
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        advise_ppa(module=_mini_module())
