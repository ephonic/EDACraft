from rtlgen_x.archsim import (
    FlowSpec,
    Workload,
    BehaviorSimulator,
    CycleSimulator,
    emit_architecture_report_markdown,
    infer_architecture_from_module,
    linear_model,
    compute_stage,
    controller_stage,
    datapath_stage,
    memory_stage,
    rank_bandwidth_upgrades,
    rank_queue_depth_upgrades,
    run_stage_bandwidth_sweep,
    run_stage_queue_depth_sweep,
    summarize_architecture_report,
)
from rtlgen_x.sim import Assignment, ClockDomain, Signal, SignalRef, SimModule


def _report_model():
    model = linear_model(
        [
            controller_stage("dispatch", latency=1, initiation_interval=1, slots=1, queue_depth=2),
            memory_stage(
                "shared_mem",
                latency=3,
                initiation_interval=1,
                banks=1,
                queue_depth=2,
                bandwidth_bytes_per_cycle=16,
            ),
            compute_stage("alu", latency=1, initiation_interval=1, lanes=2, queue_depth=2),
            datapath_stage("commit", latency=1, initiation_interval=1, lanes=2, queue_depth=2),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu", "commit"), tokens=6, bytes_per_token=64),
        FlowSpec(
            "gpu",
            path=("dispatch", "shared_mem", "alu", "commit"),
            tokens=10,
            bytes_per_token=64,
            start_cycle=1,
        ),
    )
    return model, workload


def test_architecture_report_summary_condenses_flow_stage_and_sweep_evidence():
    model, workload = _report_model()
    behavior = BehaviorSimulator().run(model, workload)
    cycle = CycleSimulator().run(model, workload)
    bandwidth = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(16, 32, 64))
    queue = run_stage_queue_depth_sweep(model, workload, "dispatch", queue_depths=(2, 4, 8))
    upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64)) + rank_queue_depth_upgrades(
        model,
        workload,
        candidate_queue_depths=(4, 8),
    )

    summary = summarize_architecture_report(
        model,
        workload,
        behavior_report=behavior,
        cycle_report=cycle,
        sweep_reports=(bandwidth, queue),
        upgrade_candidates=upgrades,
    )

    assert summary.stage_count == 4
    assert summary.flow_count == 2
    assert summary.total_tokens == 16
    assert summary.aggregate_throughput_tokens_per_cycle > 0.0
    assert [flow.name for flow in summary.flow_summaries] == ["cpu", "gpu"]
    assert all(flow.bottleneck_stage == "shared_mem" for flow in summary.flow_summaries)
    shared_mem = next(stage for stage in summary.stage_summaries if stage.name == "shared_mem")
    assert shared_mem.bandwidth_bytes_per_cycle == 16
    assert shared_mem.initiation_interval == 1
    assert shared_mem.queue_pressure > 0.0
    assert shared_mem.utilization > 0.0
    assert summary.sweep_summaries[0].stage_name == "shared_mem"
    assert summary.sweep_summaries[0].knob == "bandwidth_bytes_per_cycle"
    assert summary.sweep_summaries[0].recommended_value == 64
    assert summary.sweep_summaries[0].cycle_reduction > 0
    assert summary.upgrade_candidates
    assert summary.upgrade_candidates[0].stage_name == "shared_mem"
    assert any("shared_mem" in finding for finding in summary.findings)


def test_architecture_report_markdown_renders_agent_facing_summary():
    model, workload = _report_model()
    behavior = BehaviorSimulator().run(model, workload)
    cycle = CycleSimulator().run(model, workload)
    bandwidth = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(16, 32, 64))

    markdown = emit_architecture_report_markdown(
        model=model,
        workload=workload,
        behavior_report=behavior,
        cycle_report=cycle,
        sweep_reports=(bandwidth,),
        upgrade_candidates=rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64)),
        title="GPU SM Architecture Report",
    )

    assert markdown.startswith("# GPU SM Architecture Report\n")
    assert "## Executive Summary" in markdown
    assert "## Flows" in markdown
    assert "## Stages" in markdown
    assert "## Sweep Evidence" in markdown
    assert "## Ranked Upgrades" in markdown
    assert "dispatch -> shared_mem -> alu -> commit" in markdown
    assert "shared_mem" in markdown
    assert "bandwidth_bytes_per_cycle" in markdown
    assert "| Stage | Kind | Lat | II | Cap | Queue | BW | Util | Queue Pressure | Bytes | Flows |" in markdown


def test_architecture_report_markdown_surfaces_inference_scope_for_heuristic_models():
    sim_module = SimModule(
        name="toy_infer",
        signals=(
            Signal("clk", width=1, kind="input"),
            Signal("rst", width=1, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("state", width=8, kind="state"),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", SignalRef("state"), phase="comb"),
            Assignment("state", SignalRef("inp"), phase="seq", clock_domain="clk"),
        ),
        outputs=("out",),
        clock_domains=(ClockDomain("clk", reset_signal="rst"),),
    )
    model = infer_architecture_from_module(sim_module)
    workload = Workload.from_flows(
        FlowSpec("main", path=("toy_infer_ingress", "toy_infer_compute", "toy_infer_egress"), tokens=4),
    )

    markdown = emit_architecture_report_markdown(model=model, workload=workload, title="Inference Scope")

    assert "### Modeling Scope" in markdown
    assert "heuristic early-estimate inferred from executable-module structure" in markdown
