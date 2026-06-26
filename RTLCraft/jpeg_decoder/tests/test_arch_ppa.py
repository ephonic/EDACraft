"""Architecture simulation and PPA analysis for the JPEG decoder."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json

from rtlgen.archsim import (
    ArchitectureModel,
    BehaviorSimulator,
    CycleSimulator,
    FlowSpec,
    StageSpec,
    Workload,
    emit_architecture_report_markdown,
    run_stage_capacity_sweep,
    run_stage_initiation_interval_sweep,
    run_stage_latency_sweep,
    run_stage_queue_depth_sweep,
    summarize_architecture_report,
)
from rtlgen.ppa import PpaGoals, advise_ppa, analyze_module_ppa, emit_ppa_report_markdown

from jpeg_decoder.dsl_modules import JpegDecoder, JpegDequantZigzag, JpegEntropyDecoder, JpegIdct8x8


def build_model():
    """Build a coarse architecture model of the decoder pipeline.

    The baseline decoder processes one 8x8 block at a time:
      * entropy  - byte-wide input, ~16 bytes per block in the reference stream
      * dequant  - 64 coefficients, one per cycle
      * idct     - 64 load + 64 row + 64 column cycles (~192 total)
    """
    return ArchitectureModel([
        StageSpec(
            "entropy",
            kind="control",
            latency=1,
            initiation_interval=1,
            capacity=1,
            queue_depth=4,
            bandwidth_bytes_per_cycle=1,
        ),
        StageSpec(
            "dequant",
            kind="compute",
            latency=64,
            initiation_interval=64,
            capacity=1,
            queue_depth=2,
        ),
        StageSpec(
            "idct",
            kind="compute",
            latency=192,
            initiation_interval=192,
            capacity=1,
            queue_depth=2,
        ),
    ])


def build_workload(blocks=1):
    """One flow per decoded block: 64 pixels produced from entropy bytes."""
    return Workload.from_flows(
        FlowSpec(
            "decode_block",
            path=("entropy", "dequant", "idct"),
            tokens=64 * blocks,
            bytes_per_token=0,
        )
    )


def main():
    model = build_model()
    workload = build_workload(blocks=4)

    print("=== Architecture behavior simulation ===")
    behavior = BehaviorSimulator().run(model, workload)
    flow_metric = behavior.flow_metrics["decode_block"]
    print(f"  throughput (tokens/cycle): {flow_metric.throughput_tokens_per_cycle:.4f}")
    print(f"  pipeline latency (cycles): {flow_metric.pipeline_latency}")
    print(f"  steady-state II:           {flow_metric.steady_state_ii:.2f}")
    print(f"  bottleneck stage:          {flow_metric.bottleneck_stage}")
    print(f"  makespan (cycles):         {behavior.makespan_cycles}")

    print("\n=== Architecture cycle simulation ===")
    cycle = CycleSimulator().run(model, workload)
    cycle_flow = cycle.flow_metrics["decode_block"]
    stall_ratio = cycle_flow.stalled_cycles / max(1, cycle_flow.total_cycles)
    print(f"  simulated cycles:          {cycle.total_cycles}")
    print(f"  flow stall cycles:         {cycle_flow.stalled_cycles}")
    print(f"  flow total cycles:         {cycle_flow.total_cycles}")
    print(f"  stall ratio:               {stall_ratio:.4f}")

    print("\n=== Stage capacity sweep (idct) ===")
    capacity_sweep = run_stage_capacity_sweep(model, workload, "idct", [1, 2, 4])
    for p in capacity_sweep.points:
        print(f"  capacity={p.capacity:2d}  cycles={p.cycle_total_cycles:6d}  "
              f"throughput={p.aggregate_throughput_tokens_per_cycle:.6f}  speedup={p.speedup_vs_baseline:.3f}")

    print("\n=== Stage II sweep (idct) ===")
    ii_sweep = run_stage_initiation_interval_sweep(model, workload, "idct", [64, 96, 128, 192])
    for p in ii_sweep.points:
        print(f"  ii={p.initiation_interval:3d}  cycles={p.cycle_total_cycles:6d}  "
              f"throughput={p.aggregate_throughput_tokens_per_cycle:.6f}  speedup={p.speedup_vs_baseline:.3f}")

    print("\n=== Module structural PPA ===")
    for module in [JpegEntropyDecoder, JpegDequantZigzag, JpegIdct8x8, JpegDecoder]:
        stats = analyze_module_ppa(module())
        print(f"\n{module.__name__}:")
        print(f"  state bits:      {stats.state_bits}")
        print(f"  memory bits:     {stats.memory_bits}")
        print(f"  max expr depth:  {stats.max_expr_depth}")
        print(f"  multipliers:     {stats.multiplier_ops}")
        print(f"  adders:          {stats.adder_ops}")

    print("\n=== Unified PPA advice (JpegDecoder) ===")
    goals = PpaGoals(
        priority="balanced",
        min_throughput_tokens_per_cycle=0.25,
        max_stall_ratio=0.30,
        max_logic_depth=20,
        max_state_bits=50000,
        max_memory_bits=50000,
    )
    report = advise_ppa(
        module=JpegDecoder(),
        model=model,
        workload=workload,
        behavior_report=behavior,
        cycle_report=cycle,
        goals=goals,
    )
    print(emit_ppa_report_markdown(report))

    print("\n=== Architecture report markdown ===")
    arch_report = summarize_architecture_report(
        model, workload, behavior_report=behavior, cycle_report=cycle
    )
    print(emit_architecture_report_markdown(arch_report))


if __name__ == "__main__":
    main()
