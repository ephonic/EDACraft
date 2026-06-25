# rtlgen_x

`rtlgen_x` is the clean-core reboot area for RTLCraft.

It is not a workflow framework. It is a compact toolbox of hard engineering
capabilities that an agent can call directly:

1. lightweight architecture exploration
2. executable hardware modeling
3. fast compiled simulation
4. verification generation and execution
5. PPA analysis and recommendation

Near-term, the project focus is intentionally narrower than the older roadmap:

1. make the DSL authoring surface predictable and readable
2. make `archsim` useful for early bottleneck analysis
3. make the stdlib trustworthy through executable closure
4. leave broader orchestration ideas out of the critical path for now

The agent is expected to orchestrate these capabilities. `rtlgen_x` provides
the engines.

One concrete worked example now lives in [../sfu/README.md](../sfu/README.md):
a fully pipelined FP16 SFU that uses LUT-backed second-order interpolation and
is regression-locked across the DSL simulator, lowered executable model,
and emitted RTL path.

## What `rtlgen_x` is

`rtlgen_x` is designed around a capability-first thesis:

1. `archsim/` helps reason about architecture tradeoffs early
2. `dsl/` helps build executable hardware descriptions
3. `sim/` turns those executable descriptions into trustworthy Python and C++
   simulation
4. `verify/` builds directed, streaming, Python-UVM, and SV/UVM verification on
   top of runnable behavior
5. `ppa/` analyzes structure and performance pressure, then produces actionable
   recommendations

The intended user experience is:

1. the agent writes or imports a design description
2. the design becomes executable quickly
3. simulation and verification happen early and often
4. architecture and PPA feedback can push changes back into the design
5. exported collateral can be used for deeper external verification when needed

## What `rtlgen_x` is not

`rtlgen_x` intentionally does not center the old framework ideas:

1. no document-driven orchestration core
2. no mandatory multi-layer authored IR pipeline
3. no approval-gate product workflow
4. no repo-wide `contract.py`
5. no forced coupling between architecture sim, detailed sim, verification, and
   PPA

Integration is done by the agent at the usage level, not by a heavyweight
control plane.

## Current package layout

```text
rtlgen_x/
  archsim/   lightweight architecture simulators and exploration helpers
  dsl/       executable modeling surfaces and DSL import/lowering
  sim/       Python runtime, C++ backend, parity, trace, benchmark, cosim
  verify/    directed tests, streaming checks, Python UVM, SV/UVM export
  ppa/       structural/runtime PPA analysis, calibration, report parsing
  tests/     regression coverage for the clean-core stack
```

## Design model and data flow

There is no single repo-wide IR, but there is a practical execution flow around
the detailed simulator stack.

### Main detailed-design path

```text
DSL module
  -> lowered internal executable model (`SimModule`)
  -> PythonSimulator
  -> compiled C++ simulator
  -> verification / cosim / benchmark / PPA consumers
```

### Main architecture path

```text
ArchitectureModel + Workload
  -> BehaviorSimulator
  -> CycleSimulator
  -> summarize_architecture_report / emit_architecture_report_markdown
  -> sweep / bottleneck ranking / architecture-side PPA analysis
```

### Feedback path

`rtlgen_x` is designed to make feedback cheap:

1. architecture exploration can suggest bandwidth, queue-depth, capacity,
   latency, or II changes
2. `rank_upgrade_opportunities(...)` can merge those explored moves into one
   ordered candidate list when the agent wants a compact bottleneck ranking
3. detailed simulation can expose semantic bugs, reset bugs, and state-update
   problems early
4. verification can surface failing transactions and replayable traces
5. PPA analysis can point at structural hotspots and possible rewrite targets
6. the agent can then update the model or RTL and rerun the loop

This is the intended replacement for a document-heavy framework loop: faster,
more executable, less ceremony.

## Current authoring guidance

For detailed hardware design, the intended public authoring surface is
`rtlgen_x.dsl.Module`.

For multi-clock designs:

1. declare clock/reset intent with `reset_domain(...)` and `clock_domain(...)`
2. bind sequential processes with `@self.seq_domain(...)`
3. prefer named domain authoring when it keeps the module clearer, for example
   `@self.seq_domain("write")`
4. when a reset domain is already declared, `clock_domain(...)` may also reuse
   it by name, for example `self.clock_domain("write", self.wr_clk, "wr_reset")`
5. if `clock_domain(...)` receives a raw reset signal whose semantics already
   match a declared reset domain, it now reuses that declared domain instead of
   silently creating a second reset-domain alias
6. unknown domain lookups now report the known declared clock/reset-domain
   names and clock aliases to make multi-clock authoring failures easier to fix
7. use CDC helpers such as `SyncCell`, `PulseSynchronizer`, `AsyncResetRel`,
   `AsyncFIFO`, and `ReadyValidAsyncBridge` instead of ad hoc crossings where
   possible
8. if a hand-written two-flop synchronizer is used, keep the sync chain simple;
   a final comb alias/observation wire is fine, but avoid mixing extra logic
   into the first-stage and second-stage transfer path
9. `seq_domain("write")` remains the preferred semantic authoring style, but
   `seq_domain("wr_clk")` is now also accepted when that clock alias resolves
   uniquely to one declared domain
10. lowered multi-clock executable models preserve both the declared domain
    name and the underlying clock signal; verification-facing `active_domains`
    should prefer declared names such as `write` / `read`, while raw clock names
    such as `wr_clk` / `rd_clk` remain accepted as compatibility aliases
11. CDC stdlib closure is intentionally explicit: `AsyncFIFO` is regression-
    covered for lowering, Python/C++ multi-clock simulation, Python-UVM, and
    generated directed multi-clock UVM collateral, while `ReadyValidAsyncBridge`
    builds one level higher on the same closure path
12. single-clock queue closure is also stronger now: `SyncFIFO` is no longer a
    stub-style helper, and its lowering, executable simulation, Python-UVM,
    and generated directed UVM paths are all regression-covered

Current static CDC scope is intentionally modest: it can recognize several
safe structural patterns, but it does not try to prove arbitrary pulse/toggle
protocol correctness from timing behavior alone. For event crossings, prefer
`PulseSynchronizer` or another explicit crossing primitive instead of relying on
the checker to infer intent from generic logic. In reports, single-bit signals
named like `*pulse*`, `*event*`, or `*toggle*` are treated as event-style
crossings and get pulse/toggle-oriented guidance instead of plain level-sync
guidance.

The public CDC and verification helpers are DSL-facing. They are meant to
point back to the DSL module and its source locations, not to expose raw
simulation internals as the main user workflow.

## Fully Pipelined RTL Pattern

When building a true throughput-1 pipeline in the DSL, use a valid-bit
shift chain plus per-stage payload gating. This is the RTL-stable pattern for
both bundled simulation and emitted RTL.

```python
@self.seq(self.clk, self.rst)
def _seq():
    with If(self.rst == 1):
        self.v0 <<= 0
        self.v1 <<= 0
        self.data0_q <<= 0
        self.data1_q <<= 0
    with Else():
        self.v0 <<= self.in_valid
        self.v1 <<= self.v0

        with If(self.in_valid == 1):
            self.data0_q <<= stage0_expr

        with If(self.v0 == 1):
            self.data1_q <<= stage1_expr
```

Rules of thumb:

1. shift `valid` bits every cycle
2. only update payload registers when the matching valid bit is high
3. source `out_valid` from the last valid bit
4. derive outputs from the last payload register, not directly from input ports
5. if stage `N+1` consumes data from stage `N`, register every payload that must
   stay aligned with that stage's valid bit

Without this pattern, bubble cycles can clobber in-flight data even when a
single directed transaction appears to work.

## Capability overview

### 1. Architecture simulation: `rtlgen_x.archsim`

`archsim` is a lightweight, general architecture simulator for:

1. CPU pipelines
2. GPGPU throughput machines
3. NPU / accelerator dataflows
4. controllers and protocol engines
5. generic datapaths, FIFOs, queues, and interconnects

It supports two levels:

1. behavior-level simulation with `BehaviorSimulator`
2. cycle-level simulation with `CycleSimulator`

Core model objects:

1. `ArchitectureModel`
2. `StageSpec`
3. `FlowSpec`
4. `Workload`

Common stage builders:

1. `queue_stage(...)`
2. `controller_stage(...)`
3. `memory_stage(...)`
4. `interconnect_stage(...)`
5. `compute_stage(...)`
6. `datapath_stage(...)`

Composite helpers:

1. `cache_hierarchy(...)`
2. `dma_engine(...)`
3. `warp_cluster(...)`
4. `dataflow_array(...)`
5. `compose_stage_groups(...)`
6. `linear_model(...)`

Reference scenarios:

1. `build_cpu_in_order_scenario(...)`
2. `build_gpu_throughput_scenario(...)`
3. `build_npu_systolic_scenario(...)`
4. `build_controller_scenario(...)`
5. `build_streaming_datapath_scenario(...)`
6. `build_cache_hierarchy_scenario(...)`
7. `build_dma_copy_scenario(...)`
8. `build_gpu_warp_cluster_scenario(...)`
9. `build_npu_dataflow_scenario(...)`
10. `build_all_reference_scenarios()`
11. `build_all_advanced_scenarios()`

Exploration helpers:

1. `run_stage_capacity_sweep(...)`
2. `run_stage_initiation_interval_sweep(...)`
3. `run_stage_latency_sweep(...)`
4. `run_stage_queue_depth_sweep(...)`
5. `run_stage_bandwidth_sweep(...)`
6. `rank_capacity_upgrades(...)`
7. `rank_initiation_interval_upgrades(...)`
8. `rank_latency_upgrades(...)`
9. `rank_queue_depth_upgrades(...)`
10. `rank_bandwidth_upgrades(...)`
11. `rank_upgrade_opportunities(...)`

Report helpers:

1. `summarize_architecture_report(...)`
2. `emit_architecture_report_markdown(...)`

Inference and calibration helpers:

1. `infer_architecture_from_module(...)`
2. `infer_flow_from_module(...)`
3. `calibrate_architecture_model(...)`

Notes:

1. `bytes_per_token` is modeled and affects memory/interconnect/datapath service
   pressure
2. behavior-level mode is fast and good for throughput reasoning
3. cycle-level mode is better for backpressure, queue pressure, and contention
4. `rank_upgrade_opportunities(...)` is the convenience entry point when the
   agent wants one merged list across capacity, II, latency, queue depth, and
   bandwidth instead of stitching several rankers together manually
4. `summarize_architecture_report(...)` condenses flow/stage/sweep evidence into
   one agent-friendly object
5. `emit_architecture_report_markdown(...)` turns that summary into a compact
   report for design review or agent feedback loops
6. `infer_architecture_from_module(...)` is intentionally heuristic: it is only
   a coarse bootstrap from executable structure, not a recovered real
   microarchitecture, and the emitted report now marks that scope explicitly

### 2. Executable design modeling: `rtlgen_x.dsl`

`rtlgen_x.dsl` is the supported hardware-authoring surface in `rtlgen_x`.
Designs are written in the DSL, then lowered into the internal executable model
(`SimModule`) for execution, verification, and PPA analysis.

The recommended public boundary is:

1. author designs as DSL `Module`
2. use `LoweredDslModule` only for lowering inspection/debug
3. treat raw `SimModule` as an internal low-level executable object
4. pass DSL `Module` or `LoweredDslModule` to public verify/PPA/UVM helpers;
   raw `SimModule` is intentionally rejected there

For the current stable/partial boundary, see:

1. [DSL support matrix](./DSL_SUPPORT_MATRIX.md)
2. [DSL semantic contract](./DSL_SEMANTICS.md)
3. [Stdlib support matrix](./STDLIB_SUPPORT_MATRIX.md)

For executable stdlib lookup, the package now also exposes a small public
catalog:

1. `get_stdlib_entry("APBRegisterBank")`
2. `list_stdlib_entries(kind="component")`
3. `list_stdlib_entries(kind="vip")`
4. `emit_stdlib_support_matrix_markdown()`

That catalog is the code-side source of truth for the current protocol /
component / VIP public surface and its conservative `stable` / `partial`
status. It now also tracks a separate `Readable RTL` dimension so review-profile
snapshot coverage is visible in the same matrix as lowering/simulation/verify
closure.

Important entry points:

1. `VerilogEmitter`
2. `lower_dsl_module_to_sim(...)`
3. `build_compiled_simulator_from_dsl(...)`

`VerilogEmitter` now has explicit readability/export profiles via `EmitProfile`:

1. `EmitProfile.review()`
   - review-first RTL
   - keeps fallback module header and auto block comments
   - disables CSE and prefers named extraction for very large expressions
   - emits stable, instance/port-named helper wires for complex submodule port
     expressions inside the structural wiring section
2. `EmitProfile.compact()`
   - terser RTL for export/handoff
   - suppresses fallback header and auto block comments
   - enables CSE and reduces blank spacer lines
3. `EmitProfile.systemverilog(...)`
   - convenience wrapper for SystemVerilog-style emit
   - enables `always_comb` / `always_ff`

Review-profile readability regression now has explicit snapshot coverage for
declared multi-clock mailbox structure, `SyncCell`, `PulseSynchronizer`,
`AsyncResetRel`, `AsyncFIFO`, `SyncFIFO`, `ReadyValidAsyncBridge`,
`RoundRobinArbiter`, `Divider`, `ShiftReg`, `ValidPipe`, `PipelineShift`,
`Counter`, `MultiCycleFSM`, `GrayCounter`, `Decoder`, `PriorityEncoder`,
`BarrelShifter`, `LFSR`, `EdgeDetector`, `PipelineInterlock`,
`BypassNetwork`, `MultiCyclePath`, `MAC`, `SignedMultiplier`, `RegisterFile`,
`DualPortRAM`, `LUT`, and the main register-bank / ready-valid stdlib helpers.
That gives emitter changes a concrete guardrail on CDC/FIFO/pipeline/control-
oriented and arithmetic/storage-oriented RTL readability instead of relying on
ad hoc visual inspection.

For review-profile readability specifically, emitter normalization now also
prefers target-local helper naming for repeated sub-expressions. In practice
that means review output will try to extract repeated medium-complexity terms
into `_target_exN` helpers before falling back to a flatter long expression,
while compact output still keeps the more mechanical `_cse_N` style.

Review output also now tries to split overly long associative `^` / `&` / `|`
chains into shorter `_target_exN` chunks. This keeps helper wires themselves
readable, instead of replacing one giant inlined expression with one giant
helper assignment.

Typical usage:

```python
from rtlgen_x.dsl import (
    EmitProfile,
    VerilogEmitter,
    analyze_emitted_readability,
    assert_emitted_rtl_contract,
    emit_readability_report_markdown,
)

review_rtl = VerilogEmitter(profile=EmitProfile.review()).emit(my_module)
compact_rtl = VerilogEmitter(profile=EmitProfile.compact()).emit(my_module)
sv_rtl = VerilogEmitter(profile=EmitProfile.systemverilog()).emit(my_module)

readability = analyze_emitted_readability(my_module, profile=EmitProfile.review())
print(emit_readability_report_markdown(readability))

review_rtl = assert_emitted_rtl_contract(
    my_module,
    profile=EmitProfile.review(),
    expected_markers=(
        "// Storage declarations",
        "// Internal declarations",
        "// Combinational logic",
        "// Sequential logic",
    ),
)
```

That readability pass is intentionally lightweight: it does not try to replace
snapshot regression, but it does make a few review-grade quality gates explicit,
including:

1. overlong lines
2. anonymous helper names such as `_cse_N` / `_tmpN` leaking into review RTL
3. duplicated review block prefixes
4. excessively deep ternary/mux chains left inside one `assign`

`assert_emitted_rtl_contract(...)` layers those checks with an optional ordered
marker contract, so stdlib or seed-design regressions can fail with one compact
Markdown report instead of many ad hoc assertions.

Agent-facing structural query helpers also now exist directly on DSL modules:

1. `module.describe_hierarchy()`
2. `module.analyze_connectivity()`

These return structured hierarchy, signal-driver, state-writer, memory-access,
and port-connection data so an agent can inspect a design semantically instead
of guessing only from emitted Verilog text.

Key constructs include:

1. `Module`, `Input`, `Output`, `Reg`, `Wire`, `Array`
2. `If`, `Else`, `Elif`, `Switch`, `When`
3. `FSM`, `Pipeline`, `SkidBuffer`, `ReadyValidRegister`, `ReadyValidFIFO`, `ReadyValidAsyncBridge`, `APBRegisterBank`, `AXI4LiteRegisterBank`, `WishboneRegisterBank`, `SyncFIFO`, `AsyncFIFO`
4. protocol/bundle helpers such as `ReadyValid`, `ReqRsp`, `AXI4Stream`,
   `APB`, `AXI4Lite`, `Wishbone`, and `AHBLite`

Protocol bundles are now slightly more first-class than plain signal groups:

1. they expose semantic field helpers such as
   `payload_fields()`, `forward_fields()`, `backward_fields()`,
   `request_payload_fields()`, and `response_payload_fields()`
2. handshake-oriented bundles expose `fire()` / `request_fire()` /
   `response_fire()` expressions directly in DSL space
3. `bundle.prefixed("foo")` creates a peer bundle with stable emitted signal
   names such as `foo_data`, `foo_valid`, ...
4. assigning a bundle to `self.<name>` on a `Module` now registers all of its
   member signals as ordinary module ports, so bundles can be authored as part
   of the public module surface instead of only as standalone helpers

There are now two intentionally distinct connection helpers:

1. `connect_port_map(...)`
   - protocol-semantic mapping
   - keeps the traditional field-name-keyed shape
   - useful for simple same-named bundle wiring and tests
2. `instantiate_port_map(...)`
   - submodule-instantiation mapping
   - keys use the peer bundle's actual port names
   - useful when the submodule bundle ports are prefixed, for example
     `u_sink_data`, `u_sink_valid`, `u_sink_ready`

At the module level, there is now also a bundle-oriented bulk-instantiation
path:

1. `self.instantiate_with_bundles(...)`
   - bundle-level sibling of `instantiate_with_ifaces(...)`
   - accepts `parent_bundles={...}` and optional `sub_bundles={...}`
   - can auto-discover same-named parent/submodule bundles by default
   - supports `bundle_includes={...}` / `bundle_excludes={...}` when only part
     of a protocol bundle should be connected
   - uses `instantiate_port_map(...)` under the hood
   - keeps emitted submodule hookups readable even when both sides use
     prefixed protocol bundles
4. `Bundle`, `ReadyValid`, `ReqRsp`, `Interface`, `Handshake`, `HandshakeInterface`
5. `AXI4`, `AXI4Lite`, `AXI4Stream`, `APB`, `AHBLite`, `Wishbone`
6. `SinglePortRAM`, `SimpleDualPortRAM`

Authoring-level domain helpers now also exist:

1. `reset_domain(...)`
2. `clock_domain(...)`
3. `seq_domain(...)`
4. `ClockDomainSpec`
5. `ResetDomainSpec`

The authoring helpers also fail earlier than before: conflicting reuse of the
same reset signal under different semantics is rejected at declaration time,
and missing domain-name lookups report the currently known declared domains.

The removed AST/JIT simulator surface and `DSLSimValidator` are no longer part
of `rtlgen_x`. DSL modules are expected to lower into the internal executable
model and run on `PythonSimulator` or the compiled C++ backend.

#### 2.2 Lowering semantics

DSL modules lower into the internal executable model used by the simulator
stack.

The lowering path currently supports:

1. combinational assignments
2. sequential state updates
3. memories and memory writes
4. init-block derived initial values
5. dynamic bit/slice/part-select updates
6. latch blocks

Current boundary:

1. single-clock lowering is the default and most mature path
2. authoring can now declare reusable domain intent explicitly with
   `clock_domain(...)` / `reset_domain(...)` and bind sequential logic through
   `seq_domain(...)`
3. declared clock/reset intent is now preserved into the executable model even
   for explicitly-declared single-clock modules, while multi-clock DSL modules
   lower with per-domain metadata when each sequential block cleanly belongs to
   one clock/reset domain
4. conflicting reset semantics on the same clock still fail fast during
   lowering
5. declared domain specs also fail fast if a later sequential block disagrees
   with the declared reset semantics for that clock
6. multi-clock verification support is intentionally split: local Python-UVM
   can run explicit domain-event sequences, while generated verification
   collateral and generic batch helpers remain intentionally constrained
7. generated Python reference models also support explicit multi-clock
   `predict_clocks(...)` / smoke execution, which helps validate generated
   predictors before any external simulator handoff
8. generated SV/UVM collateral now supports an explicit multi-clock
   event-driven path when you provide `directed_sequence` steps annotated with
   `active_domains`
9. emitted RTL plus an external simulator flow is still the preferred closure
   path for broader generated multi-clock UVM work beyond this directed mode
10. flattened lowering now preserves source-mapped assignment and memory-write
    locations through submodule inlining, so downstream diagnostics and
    hotspot reports can still point back to the original DSL file/line
10. generated DSL DUT runtime bundles preserve the module's original reset
   semantics, so a synchronous `@self.seq(clk, rst)` block stays synchronous and
   an explicit async-low `@self.seq(clk, ~rst_n)` block stays async-low after
   SV/UVM export
11. DSL values are not allowed to fall back into Python truthiness: `if sig`,
   `a and b`, `not sig`, and Python ternary expressions on DSL conditions are
   rejected with actionable errors so authoring stays inside the hardware DSL
   surface
12. public lowering and emitted-RTL entry points also enforce an authoring
   intent gate for patterns such as `@comb` writing a `Reg`, `@seq` directly
   writing an `Output`, or illegal hierarchical access into child internal
   state

Recent latch closure is important here:

1. DSL `with self.latch:` is preserved
2. latch assignments are represented with `phase="latch"`
3. Python runtime, compiled runtime, and generated reference models all support
   latch behavior
4. generated DSL DUT SystemVerilog now emits `always_latch` / `always_ff` /
   `always_comb` when exporting SV collateral
5. nested `Slice(Slice(...))` chains are flattened across multiple levels, and
   slices rooted at `BinOp` / `UnaryOp` / `Mux` / `Concat` expressions fall
   back to shift+mask emission when direct part-select syntax would break
   `iverilog`
6. `Memory(..., init_data=...)` now stays consistent across emitted RTL and
   lowered executable-model execution
7. `Memory(..., read_during_write=...)` now carries same-address read/write
   intent through lowering, Python simulation, compiled simulation, and
   generated Python reference models
8. `Memory(..., read_ports=..., write_ports=..., read_style=..., read_latency=...)`
   now makes storage intent explicit; the executable lowering path closes
   single-read/single-write `read_style="async"/read_latency=0` memories and
   also normalizes `read_style="sync"/read_latency=1` memories into explicit
   sampled executable state
9. `Memory(..., byte_enable_granularity=...)` and `mem.write(..., byte_enable=...)`
   now close through lowering, Python simulation, compiled simulation, emitted
   RTL, and RTL cosim for the executable single-read/single-write async-read
   subset
10. arithmetic right shift via `SRA(...)` lowers and emits consistently
11. combinational assignments are topologically ordered during lowering so
   dependent wire chains evaluate correctly in the executable model
12. lowered multiply expressions preserve full product width instead of truncating
   to the larger operand width

### 3. Detailed simulation: `rtlgen_x.sim`

`sim` is the detailed execution engine. It has two runtimes:

1. `PythonSimulator` for easy reference execution
2. `CompiledSimulator` for fast compiled execution via generated C++

Current multi-clock boundary inside `sim`:

1. lowered multi-clock DSL models can be executed on both `PythonSimulator`
   and `CompiledSimulator` through `step_clocks(...)`
2. lowered multi-clock DSL now preserves clock-domain metadata into the
   new runtime
3. multi-clock support is currently scalar-step oriented: `step(...)` and batch
   helpers stay fail-fast so callers do not accidentally assume a hidden clock
   schedule
4. local Python-UVM shares that same explicit event model through
   `PythonUvmSequenceItem(..., active_domains=(...))`

Core executable-model objects:

1. `SimModule`
2. `Signal`
3. `Memory`
4. `Assignment`
5. `MemoryWrite`
6. `ClockDomain`

Expression nodes:

1. `ConstExpr`
2. `SignalRef`
3. `UnaryExpr`
4. `BinaryExpr`
5. `MuxExpr`
6. `MaskExpr`
7. `MemoryReadExpr`

Compiler/backend entry points:

1. `CppBackendScaffold`
2. `CompiledSimulator`
3. `CppBuildError`

The detailed simulator stack is intended to be:

1. deterministic
2. width-aware
3. signedness-aware
4. reset-aware
5. usable in both scalar and batch modes

Current detailed-sim feature coverage includes:

1. combinational and sequential assignment semantics
2. state initialization and reset behavior
3. memory reads and writes
4. output recomputation after state updates
5. batch execution
6. latch-phase state holding/update semantics
7. LUT-heavy fixed-point pipelines that depend on signed multiply plus
   arithmetic right shift
8. sequential multiply inside `seq` blocks, preserving full product width
   through lowering, Python sim, and compiled sim

A unified `reset_simulator(...)` helper resets the `rtlgen_x` runtimes and can
also tolerate external compatibility-style simulators that still use a
`reset(rst=None, cycles=2)` signature.

High-throughput batch helpers:

1. `pack_u64_numpy(...)`
2. `pack_u64_numpy_rows(...)`
3. `pack_signal_values_u64_words(...)`
4. `pack_u64_words(...)`
5. `unpack_signal_values_u64_words(...)`

Performance helpers:

1. `build_stress_module(...)`
2. `generate_stress_inputs(...)`
3. `generate_stress_input_buffer(...)`
4. `iter_stress_input_rows(...)`
5. `benchmark_compiled_speedup(...)`
6. `benchmark_streaming_capacity(...)`
7. `run_stress_sweep(...)`
8. `write_stress_sweep_report(...)`

Trace and parity helpers:

1. `capture_execution_trace(...)`
2. `replay_execution_trace(...)`
3. `compare_python_and_compiled(...)`
4. `run_random_parity_fuzz(...)`
5. `build_fuzz_templates()`
6. `run_fuzz_suite(...)`

RTL differential checking:

1. `run_dsl_rtl_cosim(...)`
2. `run_dsl_multiclock_rtl_cosim(...)`

This path compares compiled execution against emitted RTL using `iverilog` when
available. For valid-gated pipelines, use `valid_signal`, `flush_cycles`, and
`flush_inputs` so the helper only checks architecturally meaningful output
beats.

For explicit multi-clock event stepping, use
`run_dsl_multiclock_rtl_cosim(...)`. Each vector is either a plain input
mapping, a structured step mapping such as
`{"inputs": {...}, "active_domains": {"write": True, "read": False}}`,
or an `(inputs, active_domains)` tuple, where `active_domains` identifies
which clock domains receive one edge on that step. This keeps RTL cosim
aligned with `PythonSimulator.step_clocks(...)` and
`CompiledSimulator.step_clocks(...)`. For DSL modules that declare semantic
clock-domain names, prefer those names in `active_domains`; raw signal names
remain accepted as compatibility aliases.

Storage initialization boundary:

1. `Memory(..., init_zero=True)` and `Memory(..., init_data=...)` export
   explicit RTL initialization and stay aligned with lowered execution
2. `Array(...)` is convenient for unpacked register-file style storage, but its
   emitted RTL does not inject implicit initialization
3. `Memory(..., read_during_write="write_first" | "read_first")` controls
   same-address read/write behavior in the lowered Python simulator, compiled
   simulator, and generated Python reference model
4. `Memory(..., read_ports=..., write_ports=..., read_style=..., read_latency=...)`
   is now explicit metadata on the DSL/storage model; executable lowering
   accepts `read_ports=1`, `write_ports=1`, and either
   `read_style="async"/read_latency=0` or `read_style="sync"/read_latency=1`
5. emitted RTL does not yet infer sync-read storage behavior automatically, so
   `VerilogEmitter` keeps fail-fast behavior for `read_style="sync"` memories
6. `Memory(..., byte_enable_granularity=...)` plus
   `mem.write(addr, value, byte_enable=...)` now make byte-enable intent
   explicit and now close across lowered Python simulation, compiled
   simulation, emitted RTL, and `iverilog` cosim for the executable storage
   subset
7. lowered Python and compiled simulators still start from concrete storage
   values, so local RTL cosim may expose `x/z` on an early read even when the
   executable model returns a number
8. when that happens, `run_dsl_multiclock_rtl_cosim(...)` now raises
   `CosimUnknownValueError` with the signal and cycle instead of failing with an
   opaque missing-key error
9. if initial contents matter for RTL parity, prefer
   `Memory(..., init_zero=True)`, explicit init blocks, or reset/write coverage
   before the first architecturally meaningful read
10. `read_during_write`, byte-enable partial writes, and normalized
   `sync-read/read_latency=1` executable behavior are now available on the main
   lowering/simulation path; richer port-count, broader style/latency
   combinations, and emitted RTL closure for sync-read memories remain partial

For hand-written or generated streaming RTL cosim, keep two practical rules in
mind:

1. size expected-value storage from the actual vector count, not from a fixed
   historical constant
2. use per-run artifact names when repeated or parallel cosim invocations may
   share the same build directory

### 4. Verification capability: `rtlgen_x.verify`

`verify` provides three layers of verification.

#### 4.0 CDC preflight for clock/reset-domain hazards

Before local UVM, emitted RTL cosim, or remote VCS/UVM on a multi-clock DUT,
run the static CDC check first. Also run it on single-clock DUTs that use
asynchronous reset, because reset release is analyzed too.

Core entry points:

1. `analyze_cdc(...)`
2. `emit_cdc_report_markdown(...)`

This CDC pass is analysis-first. It does not rewrite the DUT for you. Instead
it points at likely hazards and suggests the right primitive or protocol shape.

Current checks include:

1. `single_bit_crossing`
2. `pulse_crossing`
3. `multi_bit_crossing`
4. `memory_crossing`
5. `multi_writer_state`
6. `multi_writer_memory`
7. `reset_release_crossing`

Current safe-pattern recognition includes:

1. `SyncCell`
2. `PulseSynchronizer`
3. `AsyncFIFO`
4. `AsyncResetRel`
5. `ReadyValidAsyncBridge`
6. hand-written two-flop level synchronizers
7. hand-written toggle-sync-edge pulse synchronizers, including a final comb
   alias / observation tap on the synchronized side
8. hand-written async-assert / sync-release reset synchronizers, including
   deeper multi-stage release chains, active-low release variants, and a final
   comb alias / observation tap on the synchronized reset side
9. hand-written shift-register / pipe style reset-release synchronizers where
   one small state register shifts out the release value across cycles
10. reset-release safety is tracked per destination clock domain; reusing one
   domain's synchronized reset as another domain's async reset still reports a
   CDC warning

Practical guidance:

1. run `analyze_cdc(...)` on the original DSL `Module` when you have it;
   that path has the best visibility into safe CDC helper instances
2. the checker also runs on the lowered multi-clock executable model
3. when source metadata exists, findings carry file/line context for the
   producer and consumer side of the crossing
4. `reset_release_crossing` is a `warning` that specifically asks you to add a
   per-domain reset-release synchronizer or move the raw async reset behind an
   existing one; the report also names affected sequential targets, recommends
   an `AsyncResetRel` instance name plus synchronized-reset signal name, and,
   when available, points back to target source sites
5. same-clock DSL designs are allowed to use one raw-reset block to
   build `rst_sync` and separate functional blocks that consume that
   synchronized reset
6. the lowered executable model may point `ClockDomain.reset_signal` at a
   locally generated synchronized reset, not only a top-level input
7. treat `error` findings as redesign-required and `warning` findings as
   synchronizer/protocol-review-required

Minimal example:

```python
from rtlgen_x.verify import analyze_cdc, emit_cdc_report_markdown

report = analyze_cdc(module)
print(report.error_count, report.warning_count)
print(emit_cdc_report_markdown(report, title="CDC Preflight"))
```

#### 4.1 Directed and streaming checks

For fast local closure on large vector sets:

1. `run_directed_test(...)`
2. `run_streaming_test(...)`
3. `run_streaming_check(...)`
4. `run_streaming_check_adaptive(...)`

Useful report objects:

1. `DirectedTestReport`
2. `StreamingVerificationReport`
3. `VerificationFailure`
4. `TraceSample`

This layer is useful when the agent already has vectors or an online expected
function and just wants fast checking on the compiled simulator.

#### 4.2 Python-side UVM-style verification

For a lightweight but structured local verification environment:

1. `run_python_uvm_test(...)`
2. `PythonUvmSequenceItem`
3. `PythonUvmSequenceLibrary`
4. `PythonUvmCoverage`
5. `PythonUvmReferenceModel`
6. `dump_python_uvm_triage(...)`

This environment can run on:

1. `PythonSimulator`
2. `CompiledSimulator`
3. lowered DSL modules

It supports:

1. explicit expected values
2. online `expected_fn`
3. local reference-model prediction
4. optional batch execution
5. coverage collection
6. triage JSON export
7. explicit multi-clock event sequences when each item names `active_domains`

For multi-clock local Python-UVM, drive transactions as explicit domain events:

```python
from rtlgen_x.verify import PythonUvmSequenceItem, run_python_uvm_test

sequence = (
    PythonUvmSequenceItem(
        inputs={"wr_rst": 1, "rd_rst": 1},
        active_domains=("write", "read"),
        label="reset",
    ),
    PythonUvmSequenceItem(
        inputs={"wr_en": 1, "din": 11},
        active_domains=("write",),
        label="write0",
    ),
    PythonUvmSequenceItem(
        inputs={"rd_en": 1},
        active_domains=("read",),
        label="read0",
    ),
)

report = run_python_uvm_test(module, sequence, name="multiclk_local_uvm")
```

When `active_domains` is present, the driver and default local reference model
step via `step_clocks(...)`. Batch execution intentionally falls back to
per-item stepping for such sequences so the event order stays explicit.
If a multi-clock sequence omits `active_domains`, the public helpers now point
you directly at `PythonUvmSequenceItem(..., active_domains=(...))` or
`UvmSequenceStep(..., active_domains=(...))` so the fix is local and explicit.
The same explicit schedule can also be authored as a structured step mapping,
for example `{"inputs": {...}, "active_domains": ("write",), "label": "write0"}`,
or `{"inputs": {...}, "active_domains": {"write": True, "read": False}}`,
which keeps local Python-UVM, generated UVM collateral, and remote UVM payloads
aligned on one multi-clock step shape. Raw `SimModule` users can continue to
use physical names such as `wr_clk` / `rd_clk`.

#### 4.3 Protocol-aware sequences and reference models

The verification layer already includes reusable protocol adapters:

1. `ready_valid_sequence(...)`
2. `apb_sequence(...)`
3. `apb_reference_model(...)`
4. `wishbone_sequence(...)`
5. `wishbone_protocol_sequence(...)`
6. `wishbone_clocked_protocol_sequence(...)`
7. `ahblite_sequence(...)`
8. `ahblite_reference_model(...)`
9. `axilite_sequence(...)`
10. `axilite_protocol_sequence(...)`
11. `axilite_reference_model(...)`
12. `axi4_sequence(...)`
13. `axistream_sequence(...)`
14. `csr_sequence(...)`
15. `interrupt_sequence(...)`

For stdlib/VIP-oriented lookup, these helpers now also have a unified registry
surface:

1. `get_protocol_vip_kit("apb")`
2. `get_protocol_vip_kit("axilite")`
3. `get_protocol_vip_kit("axis")`
4. `get_protocol_vip_kit("wishbone")`
5. `get_protocol_vip_kit("wishbone_clocked")`
6. `get_protocol_vip_kit("ready_valid")`
7. `get_protocol_vip_kit("req_rsp")`
8. `get_protocol_vip_kit("ahb_lite")`
9. `list_protocol_vip_kits()`

At the broader stdlib level, you can also query the official catalog surface:

1. `get_stdlib_entry("APB")`
2. `get_stdlib_entry("APBRegisterBank")`
3. `get_stdlib_entry("APBVIP")`
4. `list_stdlib_entries(kind="protocol")`
5. `list_stdlib_entries(kind="component")`
6. `list_stdlib_entries(kind="vip")`

The same stdlib catalog query surface is also re-exported from
`rtlgen_x.verify`, so verification-side workflows can stay inside the verify
namespace when choosing protocol/component/VIP objects.

Each `ProtocolVipKit` bundles:

1. transaction type
2. sequence builder
3. reference-model builder
4. trace checker

If you want to reuse those protocol transactions as generated-SV/UVM directed
stimulus, use:

1. `protocol_transfers_to_uvm_sequence_steps("apb", transfers)`
2. `protocol_transfers_to_uvm_sequence_steps("axilite", transfers)`
3. `protocol_transfers_to_uvm_sequence_steps("wishbone", transfers)`
4. `protocol_transfers_to_uvm_sequence_steps("wishbone_clocked", transfers)`
5. `protocol_transfers_to_uvm_sequence_steps("axis", transfers)`

That bridge intentionally converts protocol transfers into
`UvmSequenceStep(inputs=...)` stimulus only. It does not carry over the
Python-UVM-side `expected={...}` payload verbatim; generated UVM continues to
close the loop through the DUT, generated reference model, and scoreboard. For
non-DSL executable modules, generated runtime bundles still require explicit
`dut_source=...` / `dut_module_name=...`.

Reference models include:

1. `ready_valid_reference_model(...)`
2. `register_reference_model(...)`
3. `apb_reference_model(...)`
4. `wishbone_reference_model(...)`
5. `wishbone_clocked_reference_model(...)`
6. `ahblite_reference_model(...)`
7. `axilite_reference_model(...)`
8. `axi_memory_reference_model(...)`
9. `csr_reference_model(...)`
10. `interrupt_reference_model(...)`
11. `axistream_reference_model(...)`

Supported transaction types include:

1. `AhbLiteTransfer`
2. `ApbTransfer`
3. `WishboneTransfer`
4. `AxiLiteTransfer`
5. `Axi4Transfer`
6. `AxiStreamTransfer`
7. `CsrTransfer`
8. `InterruptEvent`

For `APB`, `AXI4Lite`, `ReadyValid`, `ReqRsp`, `AXI4-Stream`, and now `Wishbone`, the
stdlib exposes both DSL-side protocol bundles and verify-side helper APIs with
matching semantic groupings, so agents can move between bundle construction,
port mapping, and Python-UVM stimulus with less naming drift.

`ReqRsp` is the current minimal request/response channel surface: it exposes
request fields, request/response handshake signals, protocol-aware bundle
connection helpers, and a matching Python-UVM sequence/reference-model path.
That gives control-plane and transaction-style datapaths a lighter alternative
to jumping directly into a full bus protocol.

On top of that channel, `ReqRspQueue` now provides a first lightweight
component: it buffers the request path with explicit queue depth while keeping
the response path as a direct passthrough. That is enough to decouple upstream
request injection from downstream service latency without yet turning the block
into a full response-reordering fabric. When request sideband fields are always
enqueued and dequeued together, `ReqRspQueue(..., bundle_sideband=True)` also
lets the stdlib collapse parallel shallow arrays into one packed `entry_storage`
array so the emitted RTL and the PPA report both reflect the denser layout.

On the component side, `SkidBuffer`, `ReadyValidRegister`,
`ReadyValidFIFO`, `APBRegisterBank`, `AXI4LiteRegisterBank`, and `WishboneRegisterBank` are explicit
protocol-aware stdlib blocks: they lower through the executable path, emit
RTL, and can be checked directly with the protocol helpers already used by the
Python-UVM flow.

For the three single-clock ready/valid buffering blocks specifically,
`SkidBuffer`, `ReadyValidRegister`, and `ReadyValidFIFO` now also have local
generated-UVM closure locked into regression: we exercise their emitted
interface/sequence/scoreboard collateral and their generated runtime bundles,
while still keeping the public `SV/UVM` support level conservative until the
same paths are routinely exercised on external simulators as a standard part of
the project flow.

Their intended roles are slightly different:

1. `SkidBuffer`: 1-entry elastic buffer with empty-state bypass
2. `ReadyValidRegister`: fixed 1-stage registered slice with backpressure
3. `ReadyValidFIFO`: multi-beat queue with occupancy tracking via `level`
4. `APBRegisterBank`: zero-wait-state APB register bank with byte-enable-backed
   storage updates
5. `AXI4LiteRegisterBank`: byte-enable-backed control-plane slave with
   registered AXI-Lite responses
6. `WishboneRegisterBank`: byte-enable-backed registered-ack Wishbone slave
   with next-cycle response timing

That separation makes it easier for an agent to choose whether a datapath wants
timing decoupling, a true registered stage, or queueing capacity.

For protocol-stage payload state, `ReadyValidRegister(..., hold_payload=True)`
is now the standard-library realization of the PPA guidance
`update_payload_only_on_handshake`: it keeps payload bits stable on drain /
idle cycles while leaving valid/ready control structure explicit and readable.

For control-plane bookkeeping, `AXI4LiteRegisterBank(..., split_control_state=True)`
is now the standard-library realization of the PPA guidance
`split_capture_and_response_state`: it separates request-capture state updates
from response-valid/data state updates while preserving the same AXI-Lite
transaction behavior.

`WishboneRegisterBank(..., split_control_state=True)` now follows the same
pattern for registered-ack Wishbone control logic: it isolates request-capture
and delayed fire bookkeeping from ack / read-response state updates while
preserving the existing transaction timing expected by the clocked Wishbone VIP.

For `APBRegisterBank` specifically, the control-plane closure is strong on
lowering, executable simulation, emitted RTL, and generated-UVM smoke flows,
but `analyze_cdc(...)` will still report the raw asynchronous `presetn`
release path until the design is wrapped with an explicit per-domain
reset-release synchronizer.

`AXI4LiteRegisterBank` and `WishboneRegisterBank` currently avoid that specific
warning because their reset handling is synchronous in the stdlib
implementation, so `analyze_cdc(...)` sees no reset-release crossing on those
two helpers today.

The APB / AXI-Lite / Wishbone control-plane side is also slightly more
realistic now: the generated/local components and the Python reference-model
paths all honor byte-lane writes (`pstrb` / `wstrb` / `sel_i`) instead of
assuming every control-plane write is always a full-word overwrite.

The Wishbone side is now split more explicitly into two usage modes:

1. `wishbone_sequence(...)` / `wishbone_protocol_sequence(...)` /
   `wishbone_reference_model(...)` remain the simple same-step helper path
2. `WishboneRegisterBank` closes with
   `wishbone_clocked_protocol_sequence(...)` and
   `wishbone_clocked_reference_model(...)` for registered-ack timing

It also now includes trace-oriented protocol checkers:

1. `check_ready_valid_trace(...)`
2. `check_apb_trace(...)`
3. `check_axistream_trace(...)`
4. `check_wishbone_trace(...)`
5. `check_axilite_trace(...)`
6. `check_ahblite_trace(...)`
7. `check_reqrsp_trace(...)`
8. `emit_protocol_check_report_markdown(...)`

These consume `PythonUvmReport.traces` or any iterable of `TraceSample` and
return explicit rule violations, so protocol debug can be driven from observed
execution rather than only scoreboard mismatches.

#### 4.4 SystemVerilog/UVM collateral generation

For external simulator flows and integration with standard SV/UVM environments:

1. `describe_verification_interface(...)`
2. `emit_python_reference_model(...)`
3. `generate_uvm_collateral(...)`
4. `write_uvm_collateral(...)`
5. `generate_uvm_runtime_bundle(...)`
6. `write_uvm_runtime_bundle(...)`
7. `load_generated_reference_model(...)`
8. `smoke_test_generated_reference_model(...)`
9. `probe_iverilog_uvm_collateral(...)`

Generated collateral includes:

1. interface
2. transaction item
3. sequencer
4. smoke or directed sequence
5. driver
6. monitor
7. agent
8. scoreboard
9. env
10. test
11. generated Python reference model
12. generated local reference runtime
13. Python DPI helper
14. C DPI bridge

Generated reference-model boundary:

1. generated Python reference models now support explicit multi-clock
   `predict_clocks(...)` when the lowered/executable model carries
   `clock_domains`
2. `smoke_test_generated_reference_model(...)` can exercise that path with an
   explicit `active_domains=(...)` schedule
3. generated SV/UVM collateral now supports a directed multi-clock path where
   each generated `UvmSequenceStep` names explicit `active_domains`
4. randomized / generic multi-clock UVM collateral remains out of scope today,
   so broader multi-clock closure still prefers emitted RTL plus an external
   simulator flow

Runtime bundle generation adds:

1. `dut.sv`
2. `top.sv`
3. `filelist.f`
4. `run_vcs.sh`

Important current behavior:

1. generated reference models are self-contained and rely on emitted
   `rtlgen_x_ref_runtime.py`; if the model and runtime get separated, point the
   loader at the runtime via the `RTLGEN_X_REF_RUNTIME_PATH` environment
   variable or the `runtime_path=` argument of
   `load_generated_reference_model(...)`
2. generated scoreboards call the generated Python reference model through a DPI
   bridge hook
3. generated reset smoke sequences understand reset polarity when the executable
   model exposes it
4. DSL latch modules can now be exported through the runtime-bundle path
5. runtime bundles no longer require the DUT itself to expose a real clock input;
   a synthetic verification clock can drive the UVM environment while the DUT
   only sees its actual ports
6. DSL DUT export preserves reset semantics during runtime-bundle generation
   instead of forcing a profile-wide async-low reset style, which is important
   for correct multi-clock directed UVM closure around reset release

#### 4.5 Remote VCS/UVM execution

For real SV/UVM closure on a remote host with VCS:

0. `probe_remote_uvm_environment(...)`
1. `run_remote_uvm_probe(...)`
2. `run_remote_uvm_regression(...)`
3. `write_remote_uvm_regression_report(...)`
4. `default_remote_dir(...)`
5. `summarize_uvm_output(...)`
6. `load_module_instance(...)`

Helper scripts also exist:

1. [scripts/probe_remote_uvm_environment.py](../scripts/probe_remote_uvm_environment.py)
2. [scripts/run_remote_uvm_probe.py](../scripts/run_remote_uvm_probe.py)
3. [scripts/run_remote_uvm_regression.py](../scripts/run_remote_uvm_regression.py)

The helper scripts now accept JSON-driven directed sequences and target lists:

1. `run_remote_uvm_probe.py --directed-sequence-json path/to/steps.json`
2. `run_remote_uvm_regression.py --targets-json path/to/targets.json`
3. `run_remote_uvm_regression.py --directed-sequence-json path/to/shared_steps.json`

This matters for multi-clock closure, because generated SV/UVM collateral only
supports the explicit event-driven path when each step names `active_domains`.
The same path is regression-covered locally and through a real remote VCS probe,
so the intended usage is to keep reset/write/read ordering explicit instead of
assuming an implicit clock schedule.

Recommended remote order:

1. run `probe_remote_uvm_environment(...)` first to confirm SSH + `source_script`
   + `vcs`
2. run one `run_remote_uvm_probe(...)`
3. scale out with `run_remote_uvm_regression(...)`

Current practical split:

1. `probe_iverilog_uvm_collateral(...)` is good for local SV smoke and basic
   packaging checks
2. full UVM closure depends on an external UVM-capable simulator such as VCS

The probe report surfaces compile warnings: check `report.warnings`,
`report.has_warnings`, and `report.clean` so width-mismatch and other lint
diagnostics are not hidden behind a successful compile.

### 5. PPA capability: `rtlgen_x.ppa`

`ppa` is currently analysis-first. It helps the agent decide what to rewrite or
restructure.

Like `archsim`, `ppa` is report-oriented. It produces recommendations and
evidence for the agent or designer to read; it does not push structured changes
directly into the DSL layer.

Structural/runtime analysis:

1. `analyze_module_ppa(...)`
2. `analyze_architecture_ppa(...)`
3. `advise_ppa(...)`

Public module-side PPA helpers are DSL-facing:

1. pass the original DSL `Module` when you have it
2. pass `LoweredDslModule` only when you already have a lowering wrapper
3. keep raw `SimModule` for low-level executable helpers such as architecture
   inference or rewrite evaluation internals

Core report objects:

1. `PpaGoals`
2. `PpaReport`
3. `PpaReportSummary`
4. `PpaRecommendation`
5. `PpaRecommendationSummary`
6. `PpaTrustSummary`
7. `PpaTransformCandidate`
8. `RewriteProposalSummary`
9. `ModulePpaStats`
10. `ArchitecturePpaStats`

Report helpers:

1. `summarize_ppa_report(...)`
2. `emit_ppa_report_markdown(...)`

Calibration helpers:

1. `build_module_ppa_calibration_sample(...)`
2. `build_architecture_ppa_calibration_sample(...)`
3. `fit_module_ppa_calibration(...)`
4. `fit_architecture_ppa_calibration(...)`
5. `estimate_calibrated_module_ppa(...)`
6. `estimate_calibrated_architecture_ppa(...)`
7. `derive_architecture_calibration_targets(...)`

Implementation report parsing:

1. `parse_timing_report(...)`
2. `parse_area_report(...)`
3. `parse_power_report(...)`
4. `load_implementation_report_bundle(...)`

Rewrite-oriented helpers:

1. `derive_rewrite_proposals(...)`
2. `apply_rewrite_proposal(...)`
3. `evaluate_rewrite_proposal(...)`
4. `validate_rewrite_proposal(...)`

Current recommended usage is:

1. let `rtlgen_x` analyze and rank opportunities
2. let the agent decide whether and how to rewrite the design

Important current behavior:

1. module-side timing recommendations now carry hotspot attribution that is
   directly usable by an agent:
   `critical_assignment_target`, `critical_assignment_phase`,
   `critical_assignment_source_file`, `critical_assignment_source_line`,
   `critical_expr_kind`, `critical_expr_op`, and operand-width metadata
2. module-side area/power stats now carry explicit breakdown terms and named
   hotspots, including `largest_memory_name`, `largest_memory_bits`,
   `largest_state_name`, `dominant_area_bucket`, `dominant_power_bucket`,
   `area_breakdown`, and `power_breakdown`
3. architecture-side stage stats now also expose lightweight area/power proxies
   such as `stage_bytes_moved`, `stage_activity_proxy`,
   `stage_queue_occupancy_proxy`, `stage_area_proxy`, and `stage_power_proxy`
4. this makes it possible to point the agent at a concrete module/signal/site,
   storage hotspot, or architectural stage without giving rewrite authority to
   the tool itself
5. `summarize_ppa_report(...)` / `emit_ppa_report_markdown(...)` now preserve
   precise hotspot targets such as `module.signal @ file:line` and surface the
   first concrete follow-up actions directly in the report
6. multiplier/memory/state recommendations now also carry lightweight pattern
   hints such as `signed_multiplier_pipeline`, `mac_style`, `lut_rom`, or
   `register_file_rows`, and those hints now also appear in the summarized
   markdown report so the agent can choose a more fitting rewrite path
7. queue/control-plane stdlib blocks now also surface protocol-shaped pattern
   hints such as `handshake_payload_state`, `fifo_queue_storage`,
   `queue_metadata_arrays`, `control_register_bank`, and
   `register_bank_control_state`, so FIFO / ready-valid / register-bank reports
   read like hardware guidance instead of generic storage advice
8. those protocol-aware recommendations now also carry anchor lists such as
   `handshake_payload_anchors`, `queue_control_anchors`,
   `queue_sideband_anchors`, and `register_bank_control_anchors`, so an agent
   can jump straight to the most relevant named state, queue pointer/count
   logic, or register-bank capture state
9. module-side `transform_candidates` now also cover storage-oriented first
   moves such as `register_file_to_ram_wrapper`, `compare_ram_wrapper_vs_flops`,
   or `pack_rows_or_share_banks` for `RegisterFile` / `DualPortRAM` / `LUT`-like
   hotspots
10. arithmetic-oriented first moves are also surfaced now, for example
   `split_operands_product_accumulate`,
   `retime_product_stages_keep_valid_shell`, or
   `tile_or_share_wide_multipliers` for `MAC` / `SignedMultiplier` /
   multi-multiplier datapaths
11. queue/control-plane stdlib blocks now also get first-move transform
    candidates such as `update_payload_only_on_handshake`,
    `compare_fifo_storage_impls`, `bundle_queue_sideband_fields`,
    `partition_or_pack_register_bank`, and
    `split_capture_and_response_state`
12. some of those storage-layout suggestions now also map directly back into
    stdlib authoring knobs; for example, `ReqRspQueue(..., bundle_sideband=True)`
    is the standard-library realization of the
    `bundle_queue_sideband_fields` guidance
13. protocol-state power suggestions can also map directly back into stdlib
    authoring knobs; for example,
    `ReadyValidRegister(..., hold_payload=True)` is the standard-library
    realization of `update_payload_only_on_handshake`
14. control-plane partition suggestions can also map directly back into stdlib
    authoring knobs; for example,
    `AXI4LiteRegisterBank(..., split_control_state=True)` is the
    standard-library realization of `split_capture_and_response_state`
15. the same control-plane partition path now also exists for Wishbone stdlib
    blocks; `WishboneRegisterBank(..., split_control_state=True)` is another
    standard-library realization of `split_capture_and_response_state`
16. `derive_rewrite_proposals(...)` can now turn part of those arithmetic timing
    candidates into concrete pipeline-style rewrite scaffolds that already target
    the reported multiply assignment instead of only the deepest generic path
17. some protocol-aware stdlib candidates now also produce scaffold-only rewrite
    proposals, for example handshake payload-hold enables, queue sideband
    bundling placeholders, or register-bank capture/response partition markers;
    these are intentionally advisory and point the agent at the exact payload or
    control state without pretending the whole protocol rewrite is automatic
18. storage-oriented candidates can also produce wrapper/banking/packing
    proposal scaffolds now; some of those, such as `RegisterFile`-to-RAM wrapper
    sketches, are intentionally scaffold-first and may sit outside the current
    executable-memory subset until the designer or agent completes the rewrite
19. each rewrite proposal now carries explicit applicability metadata:
    `direct_apply` proposals may be fed into `apply_rewrite_proposal(...)` /
    `validate_rewrite_proposal(...)`, while `scaffold_only` proposals are
    advisory skeletons with an explicit reason string describing what still
    needs manual completion
20. `advise_ppa(...)` now also attaches derived rewrite proposals to the
    returned `PpaReport`, and `summarize_ppa_report(...)` /
    `emit_ppa_report_markdown(...)` surface compact rewrite-proposal summaries
    so the report itself already tells the agent which ideas are directly
    applicable and which are scaffold-only
21. the markdown report now also prints protocol-aware `focus:` anchors under
    top recommendations and `origin:` anchors under rewrite proposals, so a
    human or agent can jump from a helper signal like `capture_fire` back to
    the original queue/control/payload hotspot immediately

## Recommended design flow

This is the recommended way to use the current framework.

### Flow A: architecture-first exploration

1. build or infer an `ArchitectureModel`
2. construct a `Workload`
3. run `BehaviorSimulator().run(...)`
4. run `CycleSimulator().run(...)`
5. sweep likely bottlenecks
6. generate `analyze_architecture_ppa(...)` or `advise_ppa(...)` reports
7. let the agent or designer read the report and edit the design manually

This is the preferred loop for early CPU/GPU/NPU/controller/datapath tradeoff
work.

### Flow B: executable detailed design

1. write a module in the DSL
2. lower it through `lower_dsl_module_to_sim(...)`
3. run `PythonSimulator` for quick semantics checks
4. build a `CompiledSimulator` for fast regression
5. run parity, fuzz, trace, and benchmark helpers as needed
6. export RTL or UVM collateral only when it helps downstream validation

This is the preferred loop for design development.

### Flow C: local verification closure

1. use `run_directed_test(...)` when you already have expected vectors
2. use `run_streaming_check(...)` or `run_streaming_check_adaptive(...)` for
   large regressions
3. use `run_python_uvm_test(...)` when you want sequences, scoreboards,
   coverage, and triage output
4. for multi-clock local verification, express each transaction as an explicit
   domain event with `active_domains`
5. use protocol sequence builders when the interface matches one of the
   supported buses

This is the preferred loop for fast local bug finding.

### Flow D: external SV/UVM handoff

1. use `generate_uvm_collateral(...)` for static collateral
2. use `generate_uvm_runtime_bundle(...)` for runnable bundles
3. run `smoke_test_generated_reference_model(...)` locally
4. run `probe_iverilog_uvm_collateral(...)` for local compile smoke
5. run `run_remote_uvm_probe(...)` or `run_remote_uvm_regression(...)` on a VCS
   host for full UVM closure

This is the preferred loop when the generated collateral must stand on its own
in a standard simulator flow.

### Flow E: PPA-guided refinement

1. run `analyze_module_ppa(...)` on the original DSL module or a
   `LoweredDslModule`
2. run `analyze_architecture_ppa(...)` on the architecture model if applicable
3. use `advise_ppa(...)` to obtain recommendations and transform candidates
4. use `summarize_ppa_report(...)` or `emit_ppa_report_markdown(...)` to turn
   the result into an agent-readable report with precise hotspot targets and
   next actions, rewrite applicability, and scaffold-only notes
5. if you have implementation reports, parse and calibrate them
6. let the agent rewrite the design after reading the report, then rerun
   simulation and verification

This is the preferred loop for timing/area/power-driven iteration.

For concrete protocol-aware refinement walkthroughs that read `focus:` /
`origin:` anchors and turn them into DSL-side rewrite plans, see
[TUTORIAL_ARCH_PPA.md](./TUTORIAL_ARCH_PPA.md). It now includes both
`ReqRspQueue` and `AXI4LiteRegisterBank` examples.

## Minimal examples

### Example 1: run a preset architecture scenario

```python
from rtlgen_x.archsim import BehaviorSimulator, CycleSimulator, build_cpu_in_order_scenario

scenario = build_cpu_in_order_scenario()
behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
cycle = CycleSimulator().run(scenario.model, scenario.workload)

print(behavior.makespan_cycles)
print(cycle.total_cycles)
```

### Example 2: lower a DSL module into the executable model

```python
from rtlgen_x.dsl import lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

lowered = lower_dsl_module_to_sim(module)
sim = PythonSimulator(lowered.module)

print(sim.step({"inp": 5}))  # {'out': 8}
print(sim.step({"inp": 2}))  # {'out': 10}
```

### Example 3: build compiled simulation from a DSL module

```python
from rtlgen_x.dsl import build_compiled_simulator_from_dsl

# module is a DSL Module instance
with build_compiled_simulator_from_dsl(module, build_dir="build/my_module") as sim:
    sim.reset()
    print(sim.step({"clk": 0, "rst": 1, "inp": 0}))
    print(sim.step({"clk": 0, "rst": 0, "inp": 5}))
```

### Example 4: run Python-UVM style verification

```python
from rtlgen_x.verify import PythonUvmSequenceItem, run_python_uvm_test

sequence = (
    PythonUvmSequenceItem(inputs={"inp": 5}),
    PythonUvmSequenceItem(inputs={"inp": 2}),
    PythonUvmSequenceItem(inputs={"inp": 1}),
)

report = run_python_uvm_test(module, sequence, name="smoke")
print(report.passed, report.total_cycles)
```

Multi-clock local verification uses the same API, but each sequence item must
carry `active_domains`:

```python
sequence = (
    PythonUvmSequenceItem(
        inputs={"wr_rst": 1, "rd_rst": 1},
        active_domains=("write", "read"),
    ),
    PythonUvmSequenceItem(
        inputs={"wr_en": 1, "din": 11},
        active_domains=("write",),
    ),
    PythonUvmSequenceItem(
        inputs={"rd_en": 1},
        active_domains=("read",),
    ),
)

report = run_python_uvm_test(module, sequence, name="multiclk_smoke")
print(report.traces[-1].active_domains)
```

For DSL-authored multi-clock modules, prefer semantic names such as `write` /
`read` in `active_domains`. Keep physical signal names such as `wr_clk` in
places that must bind to a real DUT port, for example `clock_name="wr_clk"`.

### Example 5: generate runnable SV/UVM collateral

```python
from rtlgen_x.verify import generate_uvm_runtime_bundle, write_uvm_runtime_bundle

bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
write_uvm_runtime_bundle(bundle, "build/uvm_bundle", include_runtime_package=False)
```

### Example 6: fully pipelined FP16 SFU regression

The repository includes a nontrivial scalar SFU example in `../sfu/`:

1. FP16 input/output
2. `relu`, `sigmoid`, `tanh`, `sin`, `cos`
3. throughput 1, latency 5
4. second-order interpolation from compact LUTs

It is a good reference design when you want to sanity-check LUT initialization,
pipeline alignment, signed fixed-point math, and nonlinear verification flow.

Run the example regressions with:

```bash
python -m pytest sfu/tests/test_functional.py -q
python -m pytest rtlgen_x/tests/test_dsl_*.py sfu/tests/test_functional.py -q -rA
python sfu/iverilog_cosim.py
```

And emit the DUT RTL with:

```python
from rtlgen_x.dsl import EmitProfile, VerilogEmitter
from sfu.dsl import Fp16Sfu

rtl = VerilogEmitter(profile=EmitProfile.review()).emit(Fp16Sfu())
print(rtl[:400])
```

This example also acted as a framework stress test: the latest fixes for
`init_data`, `SRA`, combinational dependency ordering, and multiply-width
inference were all validated through this design.

For emitted RTL closure, the current best practice is:

1. use the dedicated `sfu/iverilog_cosim.py` harness for valid-aware streaming
   parity when you want DUT-specific checks or larger stress runs
2. use `run_dsl_rtl_cosim(...)` for both cycle-aligned interfaces and
   straightforward valid-gated streaming parity
3. use `run_dsl_multiclock_rtl_cosim(...)` when the DUT is multi-clock and
   you want an explicit domain-step event schedule rather than a custom harness

### Example 7: GPU-SM-style seed program plus PPA feedback

The repository also includes a mixed compute/memory seed program in
`../gpu_sm/`:

1. dispatch, shared memory, SIMD ALU, SFU, GEMM-style compute, and writeback
2. lowered executable simulation plus emitted RTL cosim
3. architecture reporting through `summarize_architecture_report(...)`
4. PPA and calibration reporting through `emit_ppa_report_markdown(...)`
5. a concrete bridge toward a larger compute-oriented GPGPU flagship effort

Start with:

```bash
python -m pytest gpu_sm/tests/test_functional.py -q
python gpu_sm/iverilog_cosim.py
```

And use [../gpu_sm/README.md](../gpu_sm/README.md) as the worked example for:

1. building an architecture-side model
2. generating a readable architecture report
3. generating a readable PPA and calibration report
4. deciding what to rewrite in the DSL next
5. understanding how a future runtime/compiler/workload layer should meet the
   hardware side without introducing another thick framework

## Tutorials

For full step-by-step flows, use the standalone tutorials:

1. [TUTORIAL_UVM.md](./TUTORIAL_UVM.md): DSL -> executable validation ->
   generated SV/UVM collateral -> remote VCS/UVM
2. [TUTORIAL_ARCH_PPA.md](./TUTORIAL_ARCH_PPA.md): architecture exploration ->
   stage sweeps -> PPA analysis -> design feedback loop

## Current validation status

`rtlgen_x/tests/` regression-locks the clean-core area.

The current stack has explicit test coverage across:

1. architecture simulation presets and sweeps
2. DSL lowering into the executable model
3. Python vs compiled simulator parity
4. dynamic slice and part-select lowering
5. init-block derived initialization
6. latch semantics through lowering, Python sim, compiled sim, and generated
   reference models
7. directed verification and streaming verification
8. Python-UVM protocol closure
9. generated SV/UVM collateral packaging
10. remote UVM report generation helpers
11. PPA analysis and report parsing

Recent regression locks also cover:

1. nested-slice Verilog emission on widened combinational expressions
2. back-to-back streaming verification on a real pipelined arithmetic DUT
3. module-side PPA hotspot attribution with file/line metadata
4. DSL memory `init_data` propagation through lowered executable simulation
   and emitted RTL
5. arithmetic right shift round-trip through lowering, simulation, and Verilog
   emission
6. a fully pipelined LUT-backed FP16 SFU across directed and random streaming
   verification
7. sequential multiply inside `seq` blocks across truncation, sliced-product,
   and full-width product-register forms (Python and compiled paths agree)
8. `DslLoweringError` diagnostics naming the offending port/kind and the
   recommended shadow-register pattern for Output targets in sequential blocks
9. generated reference models loading their runtime via an env override or the
   `runtime_path` kwarg when the model and runtime are separated
10. iverilog probe reports surfacing width-mismatch and other warning lines
11. a unified `reset_simulator(...)` adapter that resets the `rtlgen_x`
    runtimes and tolerates compatibility-style reset signatures when needed
12. module-side PPA area/power breakdowns and named memory/state/multiplier
    hotspot evidence

## Recent fixes (audit0621-kimi)

A closure pass against the GPU SM reference design surfaced several framework
friction points. The ones that translated into code changes are summarized here.

1. **Sequential multiply (`A * B` inside `seq` blocks)** is verified across the
   Python runtime, the compiled runtime, and a gpu_sm-style full-width
   product-register form. The product width is preserved during lowering and
   only truncated at the assignment target, so registered products no longer
   silently collapse to zero. Regression tests lock all three forms.

2. **`DslLoweringError` diagnostics** for unsupported assignment targets now
   report the signal kind (for example `output 'out'`) and, for an Output in a
   sequential block, spell out the recommended shadow-register pattern:

   ```python
   # inside seq:  self.out_reg <<= value
   # inside comb: self.out <<= self.out_reg
   ```

3. **Generated reference models** can now locate their runtime helper even when
   the model file and `rtlgen_x_ref_runtime.py` are not co-located. Set the
   `RTLGEN_X_REF_RUNTIME_PATH` environment variable, or pass `runtime_path=` to
   `load_generated_reference_model(...)`. `load_generated_reference_model(...)`
   also drops stale cached runtime modules so the override is always honored.

4. **`IverilogCollateralProbeReport`** now exposes `warnings`, `has_warnings`,
   and `clean`, so width-mismatch and other compile warnings are no longer
   buried in a successful compile. Treat `report.clean` as the stricter pass
   gate when lint discipline matters.

5. **`reset_simulator(...)`** (in `rtlgen_x.sim`) provides one entry point that
   resets the `rtlgen_x` runtimes and can also forward `rst` / `cycles` to
   external compatibility-style reset frontends when needed. Test harnesses no longer
   need to branch on the concrete simulator class.

The remaining audit note is a modeling-discipline item rather than a framework
bug: the Python-UVM scoreboard compares outputs cycle-by-cycle, so a reference
model must emit any "preview" output in the same cycle the DUT asserts
`out_valid`, deferring only the architectural state commit. See the pipelined
DUT guidance in [TUTORIAL_UVM.md](./TUTORIAL_UVM.md).

## Practical boundaries today

The current framework is strong, but it still has clear boundaries.

1. `archsim` is lightweight by design; it is for exploration, not full
   microarchitectural golden modeling
2. `rtlgen_x` no longer exposes the removed AST/JIT simulator path; the supported
   execution loop is lowering plus `PythonSimulator` / compiled simulation
3. `iverilog` can be used for local RTL/collateral smoke, but full UVM closure
   still depends on an external simulator environment
4. PPA is analysis-first; rewrite authority should remain with the agent or the
   human designer
5. there is no mandatory top-level SoC workflow engine here by design

## Multi-clock support snapshot

For the full construct-by-construct support matrix, see
[DSL_SUPPORT_MATRIX.md](./DSL_SUPPORT_MATRIX.md). For the stdlib-facing public
inventory, see [STDLIB_SUPPORT_MATRIX.md](./STDLIB_SUPPORT_MATRIX.md). For the
detailed semantic boundary, see [DSL_SEMANTICS.md](./DSL_SEMANTICS.md).

| Surface | Single-clock | Multi-clock | Notes |
| --- | --- | --- | --- |
| DSL authoring | Yes | Yes | Authoring surface can describe multiple domains |
| `lower_dsl_module_to_sim(...)` | Yes | Partial | Multi-clock lowers when reset semantics are consistent per domain; conflicting same-clock reset definitions fail fast |
| `PythonSimulator` | Yes | Partial | Multi-clock works via `step_clocks(...)`; generic `step(...)` and batch helpers stay single-clock |
| `CompiledSimulator` | Yes | Partial | Multi-clock works via `step_clocks(...)`; generic `step(...)` and batch helpers stay single-clock |
| Emitted RTL | Yes | Yes | Preferred path for multi-clock designs |
| `run_dsl_rtl_cosim(...)` | Yes | No | Intended for single-clock or simple valid-gated checks |
| `run_dsl_multiclock_rtl_cosim(...)` | No | Partial | Supports explicit domain-step event cosim for multi-clock DSL DUTs |
| `run_python_uvm_test(...)` | Yes | Partial | Multi-clock works for explicit `active_domains` event sequences on local Python/compiled simulators; batch remains single-clock |
| Generated Python reference model | Yes | Partial | Explicit multi-clock `predict_clocks(...)` / smoke is supported; batch remains single-clock |
| Generated SV/UVM collateral | Yes | Partial | Explicit directed multi-clock event closure works via `directed_sequence` + `active_domains`; randomized/generic multi-clock UVM remains out of scope |

For multi-clock designs today, the intended closure paths are:

```text
DSL -> lower_dsl_module_to_sim(...) -> explicit multi-clock stepping
DSL -> run_dsl_multiclock_rtl_cosim(...) -> lowered Python / compiled / emitted RTL parity
DSL -> run_python_uvm_test(...) with explicit `active_domains`
DSL -> emit_python_reference_model(...) -> predict_clocks(...) / multi-clock smoke
DSL -> generate_uvm_runtime_bundle(..., directed_sequence=[UvmSequenceStep(..., active_domains=...)]) -> directed multi-clock UVM bundle
DSL -> emitted RTL -> external simulator / UVM flow
```

Practical recommendation for multi-clock storage-heavy DUTs:

1. use `Array(...)` when the storage is naturally reset or overwritten before
   any architecturally meaningful read
2. use `Memory(..., init_zero=True)` or `init_data` when initial contents matter
   to RTL parity, local cosim, or remote UVM scoreboarding

## Bottom line

`rtlgen_x` is meant to be useful even when used in pieces:

1. use only `archsim` for architecture tradeoff work
2. use only `dsl` + `sim` for fast executable design iteration
3. use only `verify` for local regressions or SV/UVM collateral export
4. use only `ppa` for pressure analysis and recommendation

Or combine them into one fast loop:

```text
model -> simulate -> verify -> analyze -> revise
```

That loop is the center of the current framework.
