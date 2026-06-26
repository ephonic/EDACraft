# GPU SM seed program

This directory contains a compact worked example of a GPU-style streaming
compute block validated through `rtlgen_x`.

It should no longer be read as just a throwaway example. In the current
`plan0624` direction, `gpu_sm/` is the **seed program** for a more serious
compute-oriented GPGPU flagship line.

It is still intentionally much smaller than a full GPU, but it already serves
as a realistic anchor for:

1. build the design directly in DSL
2. validate behavior through the lowered executable model
3. emit RTL and run local cosim
4. build an architecture-side report
5. run PPA and calibration-oriented reporting
6. feed the conclusions back into the DSL manually
7. expose which stdlib / CDC / PPA / archsim capabilities matter in a real
   mixed compute-memory design

The point is not to freeze this block as-is. The point is to let it evolve into
the hardware-side spine of a broader GPGPU effort.

## What the design contains

`GpuSm` in [dsl.py](./dsl.py) includes:

1. instruction issue and decode
2. per-warp register files
3. shared memory
4. SIMD arithmetic lanes
5. an SFU-style LUT path
6. a small GEMM-like datapath
7. writeback arbitration

That already makes it a useful seed for mixed compute, memory, and control
pressure.

## Why this is the seed program

This block is the right scale to expose the framework's real strengths without
requiring a full graphics-GPU buildout on day one.

It naturally exercises:

1. throughput-oriented architecture exploration
2. multi-stage compute/memory balance
3. shared-memory and writeback pressure
4. reference-model / lowered-runtime / emitted-RTL agreement
5. module-side PPA analysis with real hotspots
6. future runtime / compiler / workload contracts

So the intended roadmap is:

```text
gpu_sm example
  -> gpu_sm seed program
  -> warp-cluster / SM subsystem
  -> compute-oriented GPGPU accelerator chip
```

The roadmap is now executable on the architecture side as well:

1. single-SM seed studies use `build_gpu_sm_architecture_model(...)`
2. cluster-side seed studies use `build_gpu_sm_cluster_architecture_model(...)`
3. both remain report-oriented and do not introduce another hardware IR layer

## Validation path

Recommended local checks:

```bash
python -m pytest gpu_sm/tests/test_functional.py -q
python gpu_sm/iverilog_cosim.py
```

The current regression covers:

1. golden reference directed behavior
2. lowered `SimModule` parity on `PythonSimulator`
3. emitted RTL compile and cosim under `iverilog`
4. generated SV/UVM collateral packaging
5. module-side PPA structural analysis

That is exactly why this block is useful as a seed: it already crosses several
of the framework's real closure boundaries instead of existing only as a
standalone HDL toy.

## Architecture-side view

`archsim` is not a handoff IR for this design. It is a report engine that lets
the agent explore likely bottlenecks before rewriting `dsl.py`.

This is where behavior-level simulation earns its keep in the broader roadmap:
not by replacing detailed RTL validation, but by making it much cheaper to
decide whether the next rewrite should target lane count, memory bandwidth,
queue depth, SFU pressure, or writeback contention.

A useful first-pass memory-pressure architecture study for this block is:

```python
from gpgpu_stack import (
    build_gpu_sm_seed_workload_trace,
    evaluate_workload_trace,
    workload_trace_to_archsim_workload,
)
from gpu_sm.arch import build_gpu_sm_architecture_model
from rtlgen_x.archsim import rank_bandwidth_upgrades, run_stage_bandwidth_sweep

trace = build_gpu_sm_seed_workload_trace()
model = build_gpu_sm_architecture_model(shared_mem_bandwidth_bytes_per_cycle=8)
workload = workload_trace_to_archsim_workload(trace)
bandwidth_sweep = run_stage_bandwidth_sweep(model, workload, "shared_mem", (8, 16, 32, 64))
evaluation = evaluate_workload_trace(
    trace,
    model,
    sweep_reports=(bandwidth_sweep,),
    upgrade_candidates=rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64)),
    title="GPU SM Architecture Report",
)

print(evaluation.markdown)
```

This is a good fit when you want to answer questions like:

1. is the current pressure really shared-memory bandwidth?
2. does `writeback` queue pressure dominate after widening memory?
3. is the SFU path now the slowest flow?
4. which single knob is worth changing first?

For the next step up in scope, there is now also a cluster-side architecture
entry point. It lets us study front-end, memory-fabric, and commit pressure
across multiple SM-like slices before committing to a larger RTL composition:

```python
from gpgpu_stack import (
    build_gpu_sm_cluster_workload_trace,
    evaluate_workload_trace,
    workload_trace_to_archsim_workload,
)
from gpu_sm.arch import build_gpu_sm_cluster_architecture_model
from rtlgen_x.archsim import rank_bandwidth_upgrades, run_stage_bandwidth_sweep

trace = build_gpu_sm_cluster_workload_trace(sm_count=2)
model = build_gpu_sm_cluster_architecture_model(
    sm_count=2,
    cluster_mem_fabric_bandwidth_bytes_per_cycle=16,
)
workload = workload_trace_to_archsim_workload(trace)
sweep = run_stage_bandwidth_sweep(model, workload, "cluster_mem_fabric", (16, 32, 64))
evaluation = evaluate_workload_trace(
    trace,
    model,
    sweep_reports=(sweep,),
    upgrade_candidates=rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64)),
    title="GPU SM Cluster Report",
)

print(evaluation.markdown)
```

That gives the seed line a concrete `SM -> cluster` architecture boundary even
before we decide what the eventual cluster/chip RTL partition should look like.

## PPA and calibration view

For detailed-structure pressure, use the real DSL module:

```python
from rtlgen_x.ppa import advise_ppa, emit_ppa_report_markdown
from gpu_sm.dsl import GpuSm

report = advise_ppa(module=GpuSm(), model=model, workload=workload)
print(emit_ppa_report_markdown(report, title="GPU SM PPA Report"))
```

That report is where the agent should look for:

1. dominant module-side area/power buckets
2. largest memories or state groups
3. multiplier-heavy structural hotspots, including precise `module.signal @ file:line` targets
4. architecture-side stage proxies such as bytes moved, queue occupancy, and
   stage power proxy
5. first concrete next actions emitted directly by `emit_ppa_report_markdown(...)`

If implementation reports exist, calibrate before comparing close variants:

```python
from rtlgen_x.ppa import (
    build_module_ppa_calibration_sample,
    fit_module_ppa_calibration,
    load_implementation_report_bundle,
)

reports = load_implementation_report_bundle(
    (
        "path/to/timing.rpt",
        "path/to/area.rpt",
        "path/to/power.rpt",
    )
)
module_calibration = fit_module_ppa_calibration(
    (build_module_ppa_calibration_sample(GpuSm(), reports),)
)
calibrated_report = advise_ppa(
    module=GpuSm(),
    model=model,
    workload=workload,
    module_calibration=module_calibration,
)
print(emit_ppa_report_markdown(calibrated_report, title="GPU SM Calibrated PPA Report"))
```

The rule of thumb is simple:

1. heuristic only: good for triage
2. one calibration sample: directional
3. several calibration samples on similar blocks: good default ranking signal

## How feedback should flow

The intended feedback loop is:

```text
DSL design
  -> lowered executable model and local regression
  -> emitted RTL / cosim
  -> architecture report
  -> PPA report
  -> agent rewrites DSL manually
  -> rerun validation
```

Nothing here is passed automatically into the DSL. The reports are meant to help
the agent make better edits, not to constrain it with another rigid IR layer.

## What is still missing

As a flagship seed, `gpu_sm/` is promising but incomplete. The next layers that
still need to be built around or above it include:

1. a clearer command / launch ABI
2. perf-counter and workload-trace contracts
3. a stronger runtime / driver story
4. compiler/lowering experiments that can emit representative workloads
5. growth from one SM-like block toward a cluster or chip-level composition

Those should be added as adjacent layers, not by turning `gpu_sm/` itself into
another control framework.
