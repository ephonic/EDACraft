# GPGPU Software Stack Boundary

This directory is the software-stack side of the GPGPU flagship effort.

It is intentionally **not** a second orchestration framework.

Its purpose is to provide the software artifacts that a real compute-oriented
GPGPU accelerator needs around `rtlgen_x`:

1. runtime
2. driver
3. compiler / lowering
4. operator library
5. workload trace generation
6. kernel metadata and launch ABI

## What belongs here

This stack should own:

1. command descriptor formats
2. kernel launch metadata
3. memory layout conventions
4. runtime-side scheduling policy
5. workload traces that feed architecture exploration
6. operator/kernel lowering experiments

## What does not belong here

This stack should not take ownership of:

1. hardware DSL authoring
2. RTL emission
3. detailed hardware simulation runtimes
4. CDC / UVM / PPA / cosim implementation
5. monolithic design-flow orchestration

Those remain in `rtlgen_x`.

## Boundary with `rtlgen_x`

The intended contract is:

```text
gpgpu_stack
  -> kernel metadata / command descriptors / workload traces
  -> archsim reports
  -> agent/designer edits hardware
  -> rtlgen_x DSL / RTL / verify / PPA
```

The key shared artifacts should be:

1. CSR / MMIO map
2. command descriptor schema
3. kernel metadata schema
4. memory layout / address map
5. perf counter schema
6. workload trace format

The current code now covers all six as explicit software-side objects:

1. `KernelMetadata` / `KernelLaunch`
2. `CommandDescriptor`
3. `AddressRegion` / `AddressMap`
4. `PerfCounterSpec` / `PerfCounterSchema`
5. `WorkloadTrace` / `WorkloadTraceEvent`
6. seed-specific helpers in `gpgpu_stack.contracts`

## Near-term goal

The first milestone is not a full compiler/runtime.

It is:

1. enough metadata to describe a kernel launch
2. enough workload description to drive `rtlgen_x.archsim`
3. enough command ABI to connect a real hardware command processor later
4. a tiny runtime/queue stub that can turn launch intent into reports

## What already works

The current minimal closed loop is:

1. describe a kernel launch with `KernelMetadata` / `KernelLaunch`
2. describe software-visible workload pressure with `WorkloadTrace`
3. convert that trace into `rtlgen_x.archsim.Workload`
4. run behavior-level and cycle-level architecture analysis
5. emit a compact Markdown report for the agent/designer

For the current `gpu_sm` seed, there is already a canonical trace builder and
report bridge. A useful first study is a deliberately memory-throttled variant,
so the sweep evidence is easy to see:

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
sweep = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(8, 16, 32, 64))
upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))
evaluation = evaluate_workload_trace(trace, model, sweep_reports=(sweep,), upgrade_candidates=upgrades)

print(evaluation.markdown)
```

That gives the software side a concrete way to feed architecture exploration
without turning the trace into another mandatory hardware IR layer.

There is now a second seed entry point one level up in scope:

1. `build_gpu_sm_cluster_workload_trace(...)`
2. `command_to_gpu_sm_cluster_trace(...)`
3. `run_gpu_sm_cluster_seed_flow(...)`

These helpers keep the same software-side contract style, but target a
multi-SM cluster architecture study instead of a single SM seed block.

## Minimal runtime stub

`gpgpu_stack.runtime` now provides a deliberately small queue/runtime shim:

1. `RuntimeQueueStub.submit(...)` builds `CommandDescriptor`
2. `command_to_gpu_sm_seed_trace(...)` converts that launch into a canonical
   `gpu_sm` workload trace
3. `evaluate_gpu_sm_command(...)` runs the normal architecture-report flow

Example:

```python
from gpgpu_stack import (
    GpuSmProfileHint,
    RuntimeQueueStub,
    command_to_gpu_sm_seed_trace,
    evaluate_gpu_sm_command,
)
from gpgpu_stack.abi import KernelMetadata, workload_trace_to_archsim_workload
from gpu_sm.arch import build_gpu_sm_architecture_model
from rtlgen_x.archsim import rank_bandwidth_upgrades, run_stage_bandwidth_sweep

queue = RuntimeQueueStub(queue_name="compute")
command = queue.submit(
    KernelMetadata(kernel_name="gpu_sm_seed"),
    launch_id="launch0",
    metadata_overrides={"scenario": "memory_pressure"},
)

model = build_gpu_sm_architecture_model(shared_mem_bandwidth_bytes_per_cycle=8)
trace = command_to_gpu_sm_seed_trace(command, profile=GpuSmProfileHint(memory_tokens=16))
workload = workload_trace_to_archsim_workload(trace)
sweep = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(8, 16, 32, 64))
upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))
evaluation = evaluate_gpu_sm_command(command, model, sweep_reports=(sweep,), upgrade_candidates=upgrades)

print(evaluation.markdown)
```

This is enough to let a future runtime/compiler layer generate:

1. launch metadata
2. command descriptors
3. representative workload pressure
4. architecture-side reports

without pretending we already have a complete software stack.

For cluster-level studies:

```python
from gpgpu_stack import GpuSmProfileHint, run_gpu_sm_cluster_seed_flow

result = run_gpu_sm_cluster_seed_flow(
    launch_id="cluster0",
    sm_count=2,
    cluster_mem_fabric_bandwidth_bytes_per_cycle=16,
    profile=GpuSmProfileHint(memory_tokens=16, sfu_tokens=8, gemm_tokens=8),
)

print(result.architecture_markdown)
```

That gives us a concrete software-visible `SM -> cluster` study path without
pretending we already have a full cluster runtime or chip-level compiler flow.

## Current end-to-end seed flow

There is now a single helper that runs the current minimal flagship slice:

1. build a launch command
2. derive a software-side workload trace
3. bridge into `archsim`
4. emit an architecture report
5. run module+architecture PPA analysis on `gpu_sm`
6. emit a PPA report
7. project a software-visible perf-counter sample

```python
from gpgpu_stack import GpuSmProfileHint, run_gpu_sm_seed_flow

result = run_gpu_sm_seed_flow(
    launch_id="seed0",
    profile=GpuSmProfileHint(memory_tokens=16, sfu_tokens=8, gemm_tokens=8),
)

print(result.architecture_markdown)
print(result.ppa_markdown)
print(result.perf_counter_sample.values)
```

This is intentionally still lightweight. It does not claim to be:

1. a complete runtime
2. a complete compiler flow
3. an automatic hardware rewrite engine

What it does give us is a reproducible software-side entry point that already
meets the hardware-side seed design at two useful places:

1. architecture bottleneck exploration
2. PPA hotspot analysis
3. shared contract export for address map and perf counters

## Named workload profiles and perf projection

The current seed line now also includes:

1. named workload profiles such as `baseline`, `memory_pressure`,
   `compute_pressure`, and `sfu_pressure`
2. perf-counter projection from `archsim` summaries into the declared software
   counter schema

```python
from gpgpu_stack import (
    get_gpu_sm_named_profile,
    run_gpu_sm_seed_flow,
)

result = run_gpu_sm_seed_flow(
    launch_id="memory0",
    profile=get_gpu_sm_named_profile("memory_pressure"),
)

print(result.perf_counter_sample.values["shared_mem_stall_cycles"])
```

## Shared contract schemas

The current GPU-SM seed line also exports minimal shared-contract schemas for:

1. address map / MMIO windows
2. performance counter layout

```python
from gpgpu_stack.contracts import (
    build_gpu_sm_seed_address_map,
    build_gpu_sm_seed_perf_counter_schema,
)

addr_map = build_gpu_sm_seed_address_map()
perf = build_gpu_sm_seed_perf_counter_schema()

print(addr_map.region("cmdq").base)
print(perf.counter("shared_mem_stall_cycles").description)
```

For the cluster-side seed, the same contract style now exists one level up:

```python
from gpgpu_stack import (
    build_gpu_sm_cluster_address_map,
    build_gpu_sm_cluster_perf_counter_schema,
)

addr_map = build_gpu_sm_cluster_address_map(sm_count=2)
perf = build_gpu_sm_cluster_perf_counter_schema(sm_count=2)

print(addr_map.region("cluster_csr").base)
print(addr_map.region("sm1_shared_mem_window").base)
print(perf.counter("cluster_commit_commits").description)
print(perf.counter("sm0_sfu_busy_cycles").description)
```

These are intentionally still schema-level contracts. They let runtime/driver
and hardware meet on names, regions, and counter meanings before we commit to a
full command processor or MMIO implementation.

If you want both schemas as a single software-visible bundle for the current
seed target:

```python
from gpgpu_stack import build_gpu_sm_seed_device_contract

contract = build_gpu_sm_seed_device_contract()
print(contract.address_map.region("csr").base)
print(contract.perf_counters.counter("issued_warps").description)
```

And for the cluster seed target:

```python
from gpgpu_stack import build_gpu_sm_cluster_device_contract

contract = build_gpu_sm_cluster_device_contract(sm_count=2)
print(contract.address_map.region("cluster_csr").base)
print(contract.perf_counters.counter("cluster_mem_stall_cycles").description)
```

## Relationship to `gpu_sm`

`gpu_sm/` is currently the best seed for the hardware flagship line.

This software-stack directory is meant to grow next to it, so that:

1. `gpu_sm` drives the hardware-side structure
2. `gpgpu_stack` drives the software-side assumptions
3. both meet through a small, explicit contract instead of a giant framework
