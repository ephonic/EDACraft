from gpgpu_stack import (
    build_gpu_sm_cluster_workload_trace,
    build_gpu_sm_seed_workload_trace,
    emit_workload_trace_architecture_report_markdown,
    evaluate_workload_trace,
    workload_trace_to_archsim_workload,
)
from gpu_sm.arch import build_gpu_sm_architecture_model, build_gpu_sm_cluster_architecture_model
from rtlgen_x.archsim import rank_bandwidth_upgrades, run_stage_bandwidth_sweep


def test_gpu_sm_seed_trace_analysis_generates_report_with_sweep_evidence():
    model = build_gpu_sm_architecture_model(shared_mem_bandwidth_bytes_per_cycle=8)
    trace = build_gpu_sm_seed_workload_trace()
    workload = workload_trace_to_archsim_workload(trace)
    sweep = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(8, 16, 32, 64))
    upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))

    evaluation = evaluate_workload_trace(
        trace,
        model,
        sweep_reports=(sweep,),
        upgrade_candidates=upgrades,
    )

    assert evaluation.summary.stage_count == 6
    assert evaluation.summary.flow_count == 4
    assert evaluation.summary.total_tokens == 64
    assert evaluation.summary.sweep_summaries
    assert evaluation.summary.sweep_summaries[0].stage_name == "shared_mem"
    assert evaluation.summary.sweep_summaries[0].recommended_value == 16
    assert evaluation.summary.sweep_summaries[0].cycle_reduction > 0
    assert "warp_memory" in evaluation.markdown
    assert "shared_mem" in evaluation.markdown
    assert evaluation.behavior_report.flow_metrics["warp_sfu"].pipeline_latency == 6


def test_gpu_sm_seed_trace_builder_can_prune_optional_flows():
    trace = build_gpu_sm_seed_workload_trace(memory_tokens=4, sfu_tokens=0, gemm_tokens=0)
    model = build_gpu_sm_architecture_model()
    markdown = emit_workload_trace_architecture_report_markdown(trace, model, title="Pruned Trace")

    assert tuple(event.flow_name for event in trace.events) == ("warp_compute", "warp_memory")
    assert trace.events[1].metadata["memory_space"] == "shared"
    assert markdown.startswith("# Pruned Trace\n")


def test_gpu_sm_cluster_trace_analysis_generates_cluster_report():
    model = build_gpu_sm_cluster_architecture_model(
        sm_count=2,
        cluster_mem_fabric_bandwidth_bytes_per_cycle=16,
    )
    trace = build_gpu_sm_cluster_workload_trace(
        sm_count=2,
        compute_tokens_per_sm=16,
        memory_tokens_per_sm=8,
        sfu_tokens_per_sm=4,
        gemm_tokens_per_sm=4,
    )
    workload = workload_trace_to_archsim_workload(trace)
    sweep = run_stage_bandwidth_sweep(model, workload, "cluster_mem_fabric", bandwidths=(16, 32, 64))
    upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))

    evaluation = evaluate_workload_trace(
        trace,
        model,
        sweep_reports=(sweep,),
        upgrade_candidates=upgrades,
        title="GPU SM Cluster Report",
    )

    assert evaluation.summary.stage_count == 15
    assert evaluation.summary.flow_count == 8
    assert "cluster_mem_fabric" in evaluation.markdown
    assert "sm1_warp_memory" in evaluation.markdown
    assert evaluation.summary.sweep_summaries[0].stage_name == "cluster_mem_fabric"
