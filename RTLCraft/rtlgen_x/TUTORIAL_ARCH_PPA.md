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
3. optionally, a DSL module if you also want module-side PPA analysis

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

`archsim` and `ppa` are report-oriented in this flow. They do not emit an
explicit DSL handoff IR. The agent or designer reads the reports, then edits the
DSL or RTL structure directly.

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

If you already have a DSL module, lower it first and then use inference helpers
to bootstrap a first-pass architecture view. This is a low-level executable
helper path; it is separate from the DSL-facing public PPA helpers.

```python
from rtlgen_x.archsim import infer_architecture_from_module, infer_flow_from_module
from rtlgen_x.dsl import lower_dsl_module_to_sim

sim_module = lower_dsl_module_to_sim(module).module
model = infer_architecture_from_module(sim_module)
workload = infer_flow_from_module(sim_module)
```

This is useful when you want to move from a concrete module toward coarse-grain
architecture reasoning without hand-writing the first model from scratch.
Treat it as a bootstrap only: the inferred model is a heuristic early estimate
from executable structure, not a recovered true microarchitecture. Prefer
hand-authored `ArchitectureModel` instances before making architectural
tradeoff decisions, and use inferred reports mainly for first-pass triage.

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

## Step 6.5: collapse raw evidence into one report

Before moving on to PPA, it is often useful to collapse the raw behavior,
cycle, and sweep artifacts into one summary that an agent or reviewer can read
quickly.

```python
from rtlgen_x.archsim import (
    emit_architecture_report_markdown,
    rank_bandwidth_upgrades,
    summarize_architecture_report,
)

summary = summarize_architecture_report(
    model,
    workload,
    behavior_report=behavior,
    cycle_report=cycle,
    sweep_reports=(bandwidth_sweep, capacity_sweep, latency_sweep, queue_sweep, ii_sweep),
    upgrade_candidates=rank_bandwidth_upgrades(model, workload),
)

markdown = emit_architecture_report_markdown(summary, title="Architecture Exploration Report")
print(markdown)
```

The summary object is intended to answer, in one place:

1. which flow is throughput-limited
2. which stage has the most queue pressure or utilization
3. which explored knob actually moved total cycles
4. which ranked upgrade is the best next experiment

On the PPA side, the matching architecture stats now also carry lightweight
stage proxies for:

1. bytes moved
2. activity pressure
3. queue occupancy pressure
4. compute pressure
5. stage-level area/power proxy totals

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

If you also have a DSL module, add structural analysis. Public module-side PPA
helpers are DSL-facing: pass the original DSL `Module`, or pass the full
`LoweredDslModule` wrapper if you already have it. Do not pass raw
`lowered.module` into `analyze_module_ppa(...)` or `advise_ppa(...)`.

```python
from rtlgen_x.ppa import analyze_module_ppa, advise_ppa

module_stats = analyze_module_ppa(module)
print(module_stats.max_expr_depth)
print(module_stats.state_bits)
print(module_stats.memory_bits)
print(module_stats.critical_assignment_target)
print(module_stats.critical_assignment_source_file)
print(module_stats.critical_assignment_source_line)
print(module_stats.critical_expr_op)
print(module_stats.critical_expr_operand_widths)
print(module_stats.largest_memory_name, module_stats.largest_memory_bits)
print(module_stats.largest_state_name, module_stats.largest_state_bits)
print(module_stats.dominant_area_bucket, module_stats.dominant_power_bucket)
print(module_stats.area_memory_score, module_stats.power_memory_score)

ppa_report = advise_ppa(
    module=module,
    model=model,
    workload=workload,
    behavior_report=behavior,
    cycle_report=cycle,
)
```

These hotspot fields are intentionally agent-friendly: they let you jump from a
PPA warning to a concrete module name, signal/assignment target, source file,
source line, and operator family before deciding how to rewrite the design.

Newer module-side stats also expose more structural hints that matter in real
datapaths:

1. `multiplier_ops`
2. `adder_ops`
3. `shift_ops`
4. `max_memory_width`
5. `max_memory_depth`
6. `small_memory_count`
7. `largest_memory_name`
8. `largest_memory_bits`
9. `largest_state_name`
10. `largest_state_bits`
11. `dominant_area_bucket`
12. `dominant_power_bucket`
13. `widest_multiplier_operand_widths`
14. `widest_multiplier_assignment_target`

The recommendation evidence now also carries `area_breakdown` and
`power_breakdown`, so an agent can tell whether a warning is being driven more
by state, memory, arithmetic, muxing, or write activity before deciding what to
rewrite.

When you render the report through `summarize_ppa_report(...)` or
`emit_ppa_report_markdown(...)`, those hotspots are also collapsed into a
precise target label such as `module.signal @ file:line` plus the first
concrete next actions. This makes it much easier to hand the result back to an
editing agent without another custom adapter layer.

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
    module=module,
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

Typical calibration loop:

```python
from rtlgen_x.ppa import (
    build_architecture_ppa_calibration_sample,
    build_module_ppa_calibration_sample,
    emit_ppa_report_markdown,
    fit_architecture_ppa_calibration,
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
    (build_module_ppa_calibration_sample(module, reports),)
)
architecture_calibration = fit_architecture_ppa_calibration(
    (
        build_architecture_ppa_calibration_sample(
            model,
            workload,
            measured_total_cycles=cycle.total_cycles * 1.10,
            measured_makespan_cycles=behavior.makespan_cycles * 1.05,
        ),
    )
)

calibrated_report = advise_ppa(
    module=module,
    model=model,
    workload=workload,
    behavior_report=behavior,
    cycle_report=cycle,
    module_calibration=module_calibration,
    architecture_calibration=architecture_calibration,
)

print(emit_ppa_report_markdown(calibrated_report, title="Calibrated PPA Report"))
```

Practical trust rule:

1. no calibration samples: use heuristic scores and hotspot attribution only for relative triage
2. one calibration sample: use calibrated estimates directionally inside the same flow
3. two calibration samples: prefer calibrated ranking for similar variants, but keep checking new reports
4. three or more samples: calibrated estimates can be the default ranking signal for nearby designs

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
6. pack multiple lock-step coefficient tables into one wider ROM word
7. audit the widest multiplier site before adding more pipeline or LUT depth

After every change:

1. rerun behavior-level sim
2. rerun cycle-level sim
3. rerun `advise_ppa(...)`
4. if the executable design changed, rerun verification

## Step 11.5: read one protocol-aware refinement loop end to end

For protocol-heavy stdlib blocks, the most useful flow is often:

1. render the markdown report
2. read the `focus:` anchors under the top recommendation
3. read the scaffold proposal `origin:` anchor
4. make a small DSL edit around that exact hotspot
5. rerun PPA and verification

`ReqRspQueue` is a good example because it now surfaces queue-control anchors
and a scaffold-only sideband-bundling proposal.

```python
from rtlgen_x.dsl import ReqRspQueue
from rtlgen_x.ppa import PpaGoals, advise_ppa, emit_ppa_report_markdown

module = ReqRspQueue(
    req_width=8,
    rsp_width=8,
    depth=4,
    addr_width=4,
    write_enable=True,
    strobe_width=2,
)

report = advise_ppa(module=module, goals=PpaGoals(max_memory_bits=32))
print(emit_ppa_report_markdown(report, title="ReqRspQueue PPA"))
```

Typical output shape now looks like:

1. recommendation target:
   `ReqRspQueue.req_storage`
2. recommendation `focus:` anchors:
   `ReqRspQueue.count @ ...`, `ReqRspQueue.wr_ptr @ ...`,
   `ReqRspQueue.rd_ptr @ ...`
3. scaffold proposal:
   `Bank or isolate large memories (req_storage)`
4. scaffold `origin:` anchor:
   `ReqRspQueue.req_storage`

How to act on that report:

1. the queue-control anchors tell you where occupancy and pointer bookkeeping
   currently live
2. the sideband-bundling scaffold tells you the storage layout is the first
   thing to simplify
3. the intended DSL move is to replace parallel shallow arrays such as
   `req_storage`, `addr_storage`, `write_storage`, and `strb_storage` with one
   packed per-entry bundle when they are always enqueued and dequeued together
4. after the DSL rewrite, rerun:
   `advise_ppa(...)`, local simulation, and the relevant verification harness
5. once the queue is rewritten around a single `entry_storage`, the follow-up
   PPA report should stop classifying it as `queue_metadata_arrays` and should
   no longer emit the scaffold candidate
   `bundle_queue_sideband_fields`

The same idea now applies to handshake payload state in stdlib pipeline
stages: when a report points at `data_reg` / `buf_data` with
`update_payload_only_on_handshake`, the first DSL-side move can be a standard
library option instead of a bespoke rewrite. For example,
`ReadyValidRegister(..., hold_payload=True)` keeps payload bits stable on drain
cycles, and the follow-up PPA report should stop emitting the
`update_payload_only_on_handshake` candidate for that block.

For control-plane register banks, the same reading pattern applies:

1. `focus:` anchors point at hot request/response state such as
   `w_data_latched`, `read_fire`, or `ack_state`
2. scaffold proposal helper names such as `capture_fire` are only handles
3. `origin:` tells you which original latched state or control signal the
   scaffold is trying to help you restructure

`AXI4LiteRegisterBank` is the clearest control-plane example because the PPA
report usually highlights both a timing hotspot (`write_commit`) and a wider
state-organization hotspot (`w_data_latched` plus handshake bookkeeping).

```python
from rtlgen_x.dsl import AXI4LiteRegisterBank
from rtlgen_x.ppa import PpaGoals, advise_ppa, emit_ppa_report_markdown

module = AXI4LiteRegisterBank(depth=8)
report = advise_ppa(module=module, goals=PpaGoals(max_memory_bits=32, max_state_bits=16))
print(emit_ppa_report_markdown(report, title="AXI4LiteRegisterBank PPA"))
```

Typical output shape now looks like:

1. timing recommendation target:
   `AXI4LiteRegisterBank.write_commit @ ...`
2. recommendation `focus:` anchors:
   `AXI4LiteRegisterBank.write_commit`, `AXI4LiteRegisterBank.w_data_latched @ ...`,
   `AXI4LiteRegisterBank.read_fire`
3. scaffold proposal:
   `Reduce or gate large sequential state (capture_fire)`
4. scaffold `origin:` anchor:
   `AXI4LiteRegisterBank.w_data_latched`

How to act on that report:

1. `write_commit` being hot means the combined AW/W capture and commit path is
   too coupled
2. `w_data_latched` showing up in `focus:` / `origin:` means the captured write
   payload is part of the always-hot control cone
3. the intended DSL move is to separate:
   - request capture state
   - write-response state
   - read-response state
4. in practice, that means reducing how much logic is directly gated by
   `_aw_seen`, `_w_seen`, `_write_commit`, `_bvalid`, and `_rvalid` in one block
5. a good first rewrite is to introduce one explicit capture-enable condition
   and then make each latched state update only in the narrow subcase that owns it

That first rewrite now also has a direct stdlib landing point:
`AXI4LiteRegisterBank(..., split_control_state=True)` makes `capture_fire`
explicit and moves response bookkeeping into a separate state-update group, so
the follow-up PPA report should stop emitting
`split_capture_and_response_state` for that block.

The same idea now also lands directly in the Wishbone stdlib helper:
`WishboneRegisterBank(..., split_control_state=True)` makes its registered-ack
capture path explicit and separates ack/read-response state from the request
capture bookkeeping, so the same candidate should also disappear on rerun there.

In code terms, the report is pointing you back at the `@self.seq(...)` block
around `_aw_seen`, `_w_seen`, `_w_data`, `_w_strb`, `_bvalid`, `_rvalid`, and
`_rdata`. A small but meaningful improvement is to rewrite that block so:

1. address/data capture is isolated from response-valid generation
2. write-response state only looks at the delayed commit handshake
3. read-response state only looks at the delayed read-fire handshake
4. payload registers hold by default instead of being reset or rewritten by
   unrelated control cases

The point is not to invent a brand-new protocol, only to make ownership of each
state update narrower.

### Before: one broad response-update block

The current shape mixes capture, delayed handshake bookkeeping, payload latching,
and response-valid generation in one sequential block:

```python
@self.seq(self.clk, self.rst)
def _response_updates():
    with If(self.rst == 1):
        ...
    with Else():
        self._write_commit_d <<= self._write_commit
        self._read_fire_d <<= self._read_fire
        with If(self._write_commit == 1):
            self.regmem.write(...)
            self._aw_seen <<= 0
            self._w_seen <<= 0
        with Else():
            with If(self._aw_capture == 1):
                self._aw_seen <<= 1
                self._aw_addr <<= self.awaddr
            with If(self._w_capture == 1):
                self._w_seen <<= 1
                self._w_data <<= self.wdata
                self._w_strb <<= self.wstrb
            with If(self._read_fire == 1):
                self._ar_addr <<= self.araddr
            with If((self._bvalid == 1) & (self.bready == 1)):
                self._bvalid <<= 0

        with If((self._write_commit_d == 1) & ...):
            self._bvalid <<= 1

        with If(self._read_fire_d == 1):
            self._rvalid <<= 1
            self._rdata <<= self.regmem[...]
        with Else():
            with If((self._rvalid == 1) & (self.rready == 1)):
                self._rvalid <<= 0
```

This is exactly why the report tends to show:

1. `write_commit` as a timing hotspot
2. `w_data_latched` as a control-state hotspot
3. `capture_fire` as a scaffold helper rather than a final answer

### After: split capture ownership from response ownership

The first useful rewrite is to separate the state updates by responsibility,
even if they still live in the same `@self.seq(...)` block:

```python
@self.seq(self.clk, self.rst)
def _response_updates():
    with If(self.rst == 1):
        ...
    with Else():
        self._write_commit_d <<= self._write_commit
        self._read_fire_d <<= self._read_fire

        # capture ownership
        with If(self._aw_capture == 1):
            self._aw_seen <<= 1
            self._aw_addr <<= self.awaddr
        with If(self._w_capture == 1):
            self._w_seen <<= 1
            self._w_data <<= self.wdata
            self._w_strb <<= self.wstrb
        with If(self._read_fire == 1):
            self._ar_addr <<= self.araddr

        # write commit ownership
        with If(self._write_commit == 1):
            self.regmem.write(...)
            self._aw_seen <<= 0
            self._w_seen <<= 0

        # write response ownership
        with If((self._bvalid == 1) & (self.bready == 1)):
            self._bvalid <<= 0
        with If(self._write_commit_d == 1):
            self._bvalid <<= 1

        # read response ownership
        with If(self._read_fire_d == 1):
            self._rvalid <<= 1
            self._rdata <<= self.regmem[...]
        with Else():
            with If((self._rvalid == 1) & (self.rready == 1)):
                self._rvalid <<= 0
```

This does not magically solve every timing issue, but it usually gives the
agent a much cleaner starting point:

1. `focus:` tells you the hot state names
2. `origin:` tells you which latched payload or response state the scaffold is
   really about
3. the rewrite itself stays conservative and local to the reported state cone

## How to read recommendations

A good practical rule:

1. architecture recommendation says where throughput is being lost
2. module recommendation says where structure is likely to hurt timing/area/power
3. implementation evidence says whether the current cost is already real

For module-side timing work, prefer recommendations that identify all of:

1. hotspot target name
2. source file and line
3. operator kind and operand widths
4. at least one concrete next action

That level of attribution makes it much easier for an agent to decide whether a
path wants pipelining, decomposition, banking, or a different arithmetic
structure.

For area/power work, also check:

1. `dominant_area_bucket` and `dominant_power_bucket`
2. `largest_memory_*` for storage-heavy modules
3. `largest_state_*` for register-heavy modules
4. `area_breakdown["arithmetic"]` plus multiplier hotspot evidence for wide
   fixed-point datapaths
5. architecture-side `dominant_area_stage` / `dominant_power_stage` when the
   report says one stage is carrying a disproportionate share of the proxy cost

For LUT-backed fixed-point units, the most useful rule of thumb is:

1. if tables are shallow and always read together, consolidate them first
2. if timing is still poor, look at the widest multiply or signed shift chain
   before adding more approximation table capacity
3. only reduce pipeline stages after the multiplier-heavy stages are no longer
   the dominant pressure point

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
