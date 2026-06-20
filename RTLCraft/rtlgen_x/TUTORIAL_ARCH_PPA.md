# Architecture Exploration to PPA Tutorial

This tutorial shows the recommended path from architecture exploration to
evidence-backed PPA guidance.

It is meant for early-stage design work where you want to answer questions like:

1. where is the bottleneck?
2. is the design bandwidth-bound, queue-bound, or latency-bound?
3. which architectural knob is worth turning first?
4. how should architecture findings feed back into detailed design work?

## When to use this tutorial

Use this flow when:

1. the detailed RTL is still fluid
2. you need fast architectural tradeoff exploration
3. you want lightweight cycle reasoning before full implementation
4. you want PPA guidance rooted in execution evidence rather than static guesswork

## Prerequisites

You need one of:

1. a preset architecture scenario
2. a custom `ArchitectureModel` plus `Workload`
3. optionally, a detailed executable `SimModule` if you also want module-side PPA analysis

## End-to-end path

```text
scenario or architecture model
  -> behavior-level simulation
  -> cycle-level simulation
  -> stage sweeps and ranked upgrades
  -> PPA advice
  -> optional module-side PPA and implementation evidence
  -> redesign and rerun
```

## Step 1: choose the starting point

You can start from:

1. a preset scenario
2. a custom architecture model
3. an inferred architecture model derived from a detailed executable module

### Option A: use a preset scenario

```python
from rtlgen_x.archsim import build_npu_systolic_scenario

scenario = build_npu_systolic_scenario(tiles=32, bytes_per_tile=128)
model = scenario.model
workload = scenario.workload
```

Preset coverage already includes:

1. CPU
2. GPU
3. NPU
4. controller
5. streaming datapath
6. cache hierarchy
7. DMA copy
8. warp cluster
9. dataflow array

### Option B: build a custom architecture model

```python
from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload

model = ArchitectureModel(
    (
        StageSpec("fetch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
        StageSpec("compute", kind="compute", latency=4, initiation_interval=1, capacity=2, queue_depth=4),
        StageSpec("dram", kind="memory", latency=12, initiation_interval=4, capacity=1, queue_depth=8),
        StageSpec("commit", kind="datapath", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
    )
)

workload = Workload.from_flows(
    FlowSpec("main", path=("fetch", "compute", "dram", "commit"), tokens=64, bytes_per_token=32),
)
```

### Option C: infer a rough architecture from a detailed module

If you already have a `SimModule`, you can use inference helpers to bootstrap a
first-pass architecture view.

```python
from rtlgen_x.archsim import infer_architecture_from_module, infer_flow_from_module

model = infer_architecture_from_module(sim_module)
workload = infer_flow_from_module(sim_module)
```

This is useful when you want to move from a concrete module toward coarse-grain
architecture reasoning without hand-writing the first model from scratch.

## Step 2: run behavior-level simulation

Behavior-level simulation gives fast throughput-oriented insight.

```python
from rtlgen_x.archsim import BehaviorSimulator

behavior = BehaviorSimulator().run(model, workload)

print(behavior.makespan_cycles)
for flow_name, metrics in behavior.flow_metrics.items():
    print(flow_name, metrics.throughput_tokens_per_cycle, metrics.bottleneck_stage)
```

What this is good for:

1. quick bottleneck identification
2. pipeline-latency estimation
3. steady-state throughput reasoning
4. comparing alternate topologies cheaply

## Step 3: run cycle-level simulation

Cycle-level simulation adds backpressure and queueing behavior.

```python
from rtlgen_x.archsim import CycleSimulator

cycle = CycleSimulator().run(model, workload)

print(cycle.total_cycles)
for stage_name, metrics in cycle.stage_metrics.items():
    print(stage_name, metrics.max_ready_depth, metrics.busy_token_cycles)
```

What this is good for:

1. observing queue pressure
2. spotting stalled flows
3. comparing ready-depth behavior
4. seeing where extra capacity might actually matter

## Step 4: classify the bottleneck

Before sweeping knobs, classify what kind of pressure you are seeing.

Look at:

1. `behavior.flow_metrics[flow].bottleneck_stage`
2. `cycle.flow_metrics[flow].stalled_cycles`
3. `cycle.stage_metrics[stage].max_ready_depth`
4. `behavior.stage_metrics[stage].bytes_moved`
5. stage kind: `memory`, `interconnect`, `compute`, `datapath`, `control`

Quick heuristics:

1. high `bytes_moved` plus memory/interconnect bottleneck often means bandwidth pressure
2. large `max_ready_depth` often means queue pressure or downstream congestion
3. high `stalled_cycles` with moderate queue depth often means II or capacity pressure
4. little queue buildup but long completion time can still mean latency pressure

## Step 5: sweep the likely knobs

Now convert hypotheses into measured evidence.

### Sweep bandwidth

```python
from rtlgen_x.archsim import run_stage_bandwidth_sweep

bandwidth_sweep = run_stage_bandwidth_sweep(model, workload, "dram", [16, 32, 64, 128])
print(bandwidth_sweep.best_point)
```

### Sweep capacity

```python
from rtlgen_x.archsim import run_stage_capacity_sweep

capacity_sweep = run_stage_capacity_sweep(model, workload, "compute", [2, 4, 8])
print(capacity_sweep.best_point)
```

### Sweep latency

```python
from rtlgen_x.archsim import run_stage_latency_sweep

latency_sweep = run_stage_latency_sweep(model, workload, "dram", [12, 10, 8, 6])
print(latency_sweep.best_point)
```

### Sweep queue depth or II

```python
from rtlgen_x.archsim import run_stage_queue_depth_sweep, run_stage_initiation_interval_sweep

queue_sweep = run_stage_queue_depth_sweep(model, workload, "dram", [8, 16, 32])
ii_sweep = run_stage_initiation_interval_sweep(model, workload, "dram", [4, 2, 1])

print(queue_sweep.best_point)
print(ii_sweep.best_point)
```

## Step 6: rank upgrades globally

If you want to know which upgrade matters most across the whole system, use the
rankers rather than hand-checking every stage.

```python
from rtlgen_x.archsim import (
    rank_bandwidth_upgrades,
    rank_capacity_upgrades,
    rank_initiation_interval_upgrades,
    rank_latency_upgrades,
    rank_queue_depth_upgrades,
)

print(rank_bandwidth_upgrades(model, workload))
print(rank_capacity_upgrades(model, workload))
print(rank_initiation_interval_upgrades(model, workload))
print(rank_latency_upgrades(model, workload))
print(rank_queue_depth_upgrades(model, workload))
```

These rankers are useful for triage when the design space is large and you need
to prioritize only the top few next experiments.

## Step 7: turn the evidence into PPA advice

Now feed the simulation evidence into the PPA advisor.

```python
from rtlgen_x.ppa import PpaGoals, advise_ppa

goals = PpaGoals(
    priority="balanced",
    min_throughput_tokens_per_cycle=1.0,
    max_stall_ratio=0.25,
)

ppa_report = advise_ppa(
    model=model,
    workload=workload,
    behavior_report=behavior,
    cycle_report=cycle,
    goals=goals,
    include_sweep_evidence=True,
)

for rec in ppa_report.recommendations:
    print(rec.severity, rec.title)
    print(rec.rationale)
```

This is the point where raw simulator output becomes design guidance.

## Step 8: combine architecture and module-side analysis

If you also have a detailed executable module, add structural analysis.

```python
from rtlgen_x.ppa import analyze_module_ppa, advise_ppa

module_stats = analyze_module_ppa(sim_module)
print(module_stats.max_expr_depth)
print(module_stats.state_bits)
print(module_stats.memory_bits)
print(module_stats.critical_assignment_target)
print(module_stats.critical_assignment_source_file)
print(module_stats.critical_assignment_source_line)
print(module_stats.critical_expr_op)
print(module_stats.critical_expr_operand_widths)

ppa_report = advise_ppa(
    module=sim_module,
    model=model,
    workload=workload,
    behavior_report=behavior,
    cycle_report=cycle,
)
```

These hotspot fields are intentionally agent-friendly: they let you jump from a
PPA warning to a concrete module name, signal/assignment target, source file,
source line, and operator family before deciding how to rewrite the design.

This is especially useful when:

1. architecture says bandwidth is the main problem
2. module structure says timing depth is also unhealthy
3. the real best next change is a combination of architectural and structural edits

## Step 9: bring in implementation evidence

When synthesis or implementation reports exist, use them to anchor advice more
tightly.

```python
from rtlgen_x.ppa import load_implementation_report_bundle, advise_ppa

reports = load_implementation_report_bundle(
    (
        "path/to/timing.rpt",
        "path/to/area.rpt",
        "path/to/power.rpt",
    )
)

ppa_report = advise_ppa(
    module=sim_module,
    model=model,
    workload=workload,
    behavior_report=behavior,
    cycle_report=cycle,
    implementation_reports=reports,
)
```

This can elevate an abstract recommendation such as "reduce queue pressure" into
something more grounded like "timing is already negative on the same path that
sweep evidence identifies as the bottleneck".

## Step 10: optionally calibrate the estimator

If you have recurring report data across designs, fit calibration models.

Common helpers:

1. `build_module_ppa_calibration_sample(...)`
2. `build_architecture_ppa_calibration_sample(...)`
3. `fit_module_ppa_calibration(...)`
4. `fit_architecture_ppa_calibration(...)`
5. `estimate_calibrated_module_ppa(...)`
6. `estimate_calibrated_architecture_ppa(...)`

Use calibration when:

1. you want better prediction before running the next implementation job
2. you already have a body of prior synthesis or signoff evidence
3. design families are similar enough for scaling laws to help

## Step 11: push changes back into the design

The framework should tell you what to try next. The actual rewrite should usually
be owned by the agent or designer.

Typical architecture-side changes:

1. increase memory bandwidth
2. widen compute capacity
3. reduce initiation interval
4. deepen queues
5. reduce stage latency
6. split or reorder dataflow

Typical module-side changes:

1. insert a register boundary
2. bank or isolate a large memory
3. gate cold state
4. reduce logic depth in a hot path
5. share or serialize low-duty arithmetic

After every change:

1. rerun behavior-level sim
2. rerun cycle-level sim
3. rerun `advise_ppa(...)`
4. if the executable design changed, rerun verification

## How to read recommendations

A good practical rule:

1. architecture recommendation says where throughput is being lost
2. module recommendation says where structure is likely to hurt timing/area/power
3. implementation evidence says whether the current cost is already real

For module-side timing work, prefer recommendations that identify all of:

1. hotspot target name
2. source file and line
3. operator kind and operand widths

That level of attribution makes it much easier for an agent to decide whether a
path wants pipelining, decomposition, banking, or a different arithmetic
structure.

Treat these three views as complementary, not competing.

## Failure and feedback map

### Exploration results are unstable or surprising

Likely fix points:

1. the workload is unrealistic
2. bytes-per-token assumptions are wrong
3. queue depths or II values do not reflect the intended microarchitecture

### Sweeps show no meaningful improvement

Likely interpretation:

1. you are changing the wrong knob
2. the system is bottlenecked elsewhere
3. the workload is not exercising the intended path

### Architecture says one thing, module stats say another

Likely next move:

1. keep both views
2. identify which one is on the critical path for the current product goal
3. change one variable at a time and rerun

### PPA advice looks vague

Likely next move:

1. add implementation reports
2. run more focused sweeps
3. add module-side analysis if only architecture-side evidence is present

## Recommended completion checklist

Before trusting the conclusion, check off:

1. the workload is representative
2. both behavior-level and cycle-level runs were examined
3. at least one targeted sweep was run on the apparent bottleneck
4. ranked upgrade candidates were inspected
5. `advise_ppa(...)` was run with explicit goals
6. module-side analysis was added if a detailed executable design exists
7. implementation evidence was loaded when available
8. the chosen change was rerun through the same loop

## Related docs

1. [README.md](./README.md)
2. [TUTORIAL_UVM.md](./TUTORIAL_UVM.md)
