# rtlgen_x

`rtlgen_x` is the clean-core reboot area for RTLCraft.

It is not a workflow framework. It is a compact toolbox of hard engineering
capabilities that an agent can call directly:

1. lightweight architecture exploration
2. executable hardware modeling
3. fast compiled simulation
4. verification generation and execution
5. PPA analysis and recommendation

The agent is expected to orchestrate these capabilities. `rtlgen_x` provides
the engines.

One concrete worked example now lives in [../sfu/README.md](../sfu/README.md):
a fully pipelined FP16 SFU that uses LUT-backed second-order interpolation and
is regression-locked across the legacy DSL simulator, lowered executable model,
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
  dsl/       executable modeling surfaces and legacy DSL import/lowering
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
legacy DSL module or rtlgen_x native builder
  -> lowered executable SimModule
  -> PythonSimulator
  -> compiled C++ simulator
  -> verification / cosim / benchmark / PPA consumers
```

### Main architecture path

```text
ArchitectureModel + Workload
  -> BehaviorSimulator
  -> CycleSimulator
  -> sweep / bottleneck ranking / architecture-side PPA analysis
```

### Feedback path

`rtlgen_x` is designed to make feedback cheap:

1. architecture exploration can suggest bandwidth, queue-depth, capacity,
   latency, or II changes
2. detailed simulation can expose semantic bugs, reset bugs, and state-update
   problems early
3. verification can surface failing transactions and replayable traces
4. PPA analysis can point at structural hotspots and possible rewrite targets
5. the agent can then update the model or RTL and rerun the loop

This is the intended replacement for a document-heavy framework loop: faster,
more executable, less ceremony.

## Fully Pipelined RTL Pattern

When building a true throughput-1 pipeline in the legacy DSL, use a valid-bit
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

Inference and calibration helpers:

1. `infer_architecture_from_module(...)`
2. `infer_flow_from_module(...)`
3. `calibrate_architecture_model(...)`

Notes:

1. `bytes_per_token` is modeled and affects memory/interconnect/datapath service
   pressure
2. behavior-level mode is fast and good for throughput reasoning
3. cycle-level mode is better for backpressure, queue pressure, and contention

### 2. Executable design modeling: `rtlgen_x.dsl`

`dsl` provides two practical entry styles.

#### 2.1 Legacy DSL compatibility surface

`rtlgen_x.dsl` re-exports the existing legacy RTL DSL under the `rtlgen_x`
namespace so current module-authoring patterns can keep working.

Important entry points:

1. `VerilogEmitter`
2. `Simulator`
3. `DSLSimValidator`
4. `lower_legacy_module_to_sim(...)`
5. `build_compiled_simulator_from_legacy(...)`

Useful legacy constructs are also re-exported, including:

1. `Module`, `Input`, `Output`, `Reg`, `Wire`, `Array`
2. `If`, `Else`, `Elif`, `Switch`, `When`
3. `FSM`, `Pipeline`, `SyncFIFO`, `AsyncFIFO`
4. `Bundle`, `Interface`, `Handshake`, `HandshakeInterface`
5. `AXI4`, `AXI4Lite`, `AXI4Stream`, `APB`, `AHBLite`, `Wishbone`
6. `SinglePortRAM`, `SimpleDualPortRAM`

#### 2.2 Small native executable builder

`rtlgen_x.dsl.native` provides a small direct builder that lowers straight into
`SimModule`.

Important entry points:

1. `NativeModuleBuilder`
2. `NativeSignal`
3. `NativeMemory`
4. `NativeValue`
5. `const(...)`
6. `mux(...)`

This surface is intentionally small and useful when an agent wants a precise,
editable executable model without bringing in the full legacy DSL style.

#### 2.3 Lowering semantics

Legacy DSL modules can be lowered into `SimModule` for use by the new simulator
stack.

The lowering path currently supports:

1. combinational assignments
2. sequential state updates
3. memories and memory writes
4. init-block derived initial values
5. dynamic bit/slice/part-select updates
6. latch blocks

Recent latch closure is important here:

1. legacy DSL `with self.latch:` is preserved
2. latch assignments are represented with `phase="latch"`
3. Python runtime, compiled runtime, and generated reference models all support
   latch behavior
4. generated legacy DUT SystemVerilog now emits `always_latch` / `always_ff` /
   `always_comb` when exporting SV collateral
5. nested `Slice(Slice(...))` chains are flattened across multiple levels, and
   slices rooted at `BinOp` / `UnaryOp` / `Mux` / `Concat` expressions fall
   back to shift+mask emission when direct part-select syntax would break
   `iverilog`
6. `Memory(..., init_data=...)` now stays consistent across emitted RTL, legacy
   AST simulation, legacy JIT, and lowered `SimModule` execution
7. arithmetic right shift via `SRA(...)` lowers and emits consistently
8. combinational assignments are topologically ordered during lowering so
   dependent wire chains evaluate correctly in the executable model
9. lowered multiply expressions preserve full product width instead of truncating
   to the larger operand width

### 3. Detailed simulation: `rtlgen_x.sim`

`sim` is the detailed execution engine. It has two runtimes:

1. `PythonSimulator` for easy reference execution
2. `CompiledSimulator` for fast compiled execution via generated C++

Core executable model objects:

1. `SimModule`
2. `Signal`
3. `Memory`
4. `Assignment`
5. `MemoryWrite`

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

A unified `reset_simulator(...)` helper resets either the new
(`PythonSimulator` / `CompiledSimulator`) or the legacy simulator frontend, so
test harnesses need not branch on the concrete simulator class.

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

1. `run_legacy_rtl_cosim(...)`

This path compares compiled execution against emitted RTL using `iverilog` when
available. For valid-gated pipelines, use `valid_signal`, `flush_cycles`, and
`flush_inputs` so the helper only checks architecturally meaningful output
beats.

For hand-written or generated streaming RTL cosim, keep two practical rules in
mind:

1. size expected-value storage from the actual vector count, not from a fixed
   historical constant
2. use per-run artifact names when repeated or parallel cosim invocations may
   share the same build directory

### 4. Verification capability: `rtlgen_x.verify`

`verify` provides three layers of verification.

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
3. lowered legacy DSL modules

It supports:

1. explicit expected values
2. online `expected_fn`
3. local reference-model prediction
4. optional batch execution
5. coverage collection
6. triage JSON export

#### 4.3 Protocol-aware sequences and reference models

The verification layer already includes reusable protocol adapters:

1. `apb_sequence(...)`
2. `wishbone_sequence(...)`
3. `axilite_sequence(...)`
4. `axi4_sequence(...)`
5. `axistream_sequence(...)`
6. `csr_sequence(...)`
7. `interrupt_sequence(...)`

Reference models include:

1. `register_reference_model(...)`
2. `axi_memory_reference_model(...)`
3. `csr_reference_model(...)`
4. `interrupt_reference_model(...)`

Supported transaction types include:

1. `ApbTransfer`
2. `WishboneTransfer`
3. `AxiLiteTransfer`
4. `Axi4Transfer`
5. `AxiStreamTransfer`
6. `CsrTransfer`
7. `InterruptEvent`

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
4. legacy DSL latch modules can now be exported through the runtime-bundle path
5. runtime bundles no longer require the DUT itself to expose a real clock input;
   a synthetic verification clock can drive the UVM environment while the DUT
   only sees its actual ports

#### 4.5 Remote VCS/UVM execution

For real SV/UVM closure on a remote host with VCS:

1. `run_remote_uvm_probe(...)`
2. `run_remote_uvm_regression(...)`
3. `write_remote_uvm_regression_report(...)`
4. `default_remote_dir(...)`
5. `summarize_uvm_output(...)`
6. `load_module_instance(...)`

Helper scripts also exist:

1. [scripts/run_remote_uvm_probe.py](../scripts/run_remote_uvm_probe.py)
2. [scripts/run_remote_uvm_regression.py](../scripts/run_remote_uvm_regression.py)

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

Structural/runtime analysis:

1. `analyze_module_ppa(...)`
2. `analyze_architecture_ppa(...)`
3. `advise_ppa(...)`

Core report objects:

1. `PpaGoals`
2. `PpaReport`
3. `PpaRecommendation`
4. `PpaTransformCandidate`
5. `ModulePpaStats`
6. `ArchitecturePpaStats`

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
2. this makes it possible to point the agent at a concrete module/signal/site
   without giving rewrite authority to the tool itself

## Recommended design flow

This is the recommended way to use the current framework.

### Flow A: architecture-first exploration

1. build or infer an `ArchitectureModel`
2. construct a `Workload`
3. run `BehaviorSimulator().run(...)`
4. run `CycleSimulator().run(...)`
5. sweep likely bottlenecks
6. feed results into `analyze_architecture_ppa(...)` or `advise_ppa(...)`
7. push changes back into the architectural structure or detailed design

This is the preferred loop for early CPU/GPU/NPU/controller/datapath tradeoff
work.

### Flow B: executable detailed design

1. write a module in the legacy DSL, or use `NativeModuleBuilder`
2. obtain a `SimModule` directly or through `lower_legacy_module_to_sim(...)`
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
4. use protocol sequence builders when the interface matches one of the
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

1. run `analyze_module_ppa(...)` on the executable design
2. run `analyze_architecture_ppa(...)` on the architecture model if applicable
3. use `advise_ppa(...)` to obtain recommendations and transform candidates
4. if you have implementation reports, parse and calibrate them
5. let the agent rewrite the design, then rerun simulation and verification

This is the preferred loop for timing/area/power-driven iteration.

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

### Example 2: build a small executable module directly

```python
from rtlgen_x.dsl import NativeModuleBuilder, const
from rtlgen_x.sim import PythonSimulator

b = NativeModuleBuilder("accum_native")
inp = b.input("inp", width=8)
acc = b.state("acc", width=8, init=3)
out = b.output("out", width=8)

b.comb(out, acc + inp)
b.seq(acc, out)

module = b.build(outputs_post_state=False)
sim = PythonSimulator(module)

print(sim.step({"inp": 5}))  # {'out': 8}
print(sim.step({"inp": 2}))  # {'out': 10}
```

### Example 3: lower a legacy DSL module to compiled simulation

```python
from rtlgen_x.dsl import build_compiled_simulator_from_legacy

# module is a legacy DSL Module instance
with build_compiled_simulator_from_legacy(module, build_dir="build/my_module") as sim:
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
python -m pytest rtlgen_x/tests/test_dsl_legacy_import.py sfu/tests/test_functional.py -q -rA
python sfu/iverilog_cosim.py
```

And emit the DUT RTL with:

```python
from rtlgen_x.dsl import VerilogEmitter
from sfu.dsl import Fp16Sfu

rtl = VerilogEmitter().emit(Fp16Sfu())
print(rtl[:400])
```

This example also acted as a framework stress test: the latest fixes for
`init_data`, `SRA`, combinational dependency ordering, and multiply-width
inference were all validated through this design.

For emitted RTL closure, the current best practice is:

1. use the dedicated `sfu/iverilog_cosim.py` harness for valid-aware streaming
   parity when you want DUT-specific checks or larger stress runs
2. use `run_legacy_rtl_cosim(...)` for both cycle-aligned interfaces and
   straightforward valid-gated streaming parity

## Tutorials

For full step-by-step flows, use the standalone tutorials:

1. [TUTORIAL_UVM.md](./TUTORIAL_UVM.md): legacy DSL -> executable validation ->
   generated SV/UVM collateral -> remote VCS/UVM
2. [TUTORIAL_ARCH_PPA.md](./TUTORIAL_ARCH_PPA.md): architecture exploration ->
   stage sweeps -> PPA analysis -> design feedback loop

## Current validation status

`rtlgen_x/tests/` regression-locks the clean-core area.

The current stack has explicit test coverage across:

1. architecture simulation presets and sweeps
2. legacy DSL lowering into `SimModule`
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
4. legacy memory `init_data` propagation through AST sim, JIT, and lowered
   executable simulation
5. arithmetic right shift round-trip through lowering, simulation, and Verilog
   emission
6. a fully pipelined LUT-backed FP16 SFU across directed and random streaming
   verification
7. sequential multiply inside `seq` blocks across truncation, sliced-product,
   and full-width product-register forms (Python and compiled paths agree)
8. `LegacyLoweringError` diagnostics naming the offending port/kind and the
   recommended shadow-register pattern for Output targets in sequential blocks
9. generated reference models loading their runtime via an env override or the
   `runtime_path` kwarg when the model and runtime are separated
10. iverilog probe reports surfacing width-mismatch and other warning lines
11. a unified `reset_simulator(...)` adapter that resets both the legacy and the
    new simulator frontends

## Recent fixes (audit0621-kimi)

A closure pass against the GPU SM reference design surfaced several framework
friction points. The ones that translated into code changes are summarized here.

1. **Sequential multiply (`A * B` inside `seq` blocks)** is verified across the
   Python runtime, the compiled runtime, and a gpu_sm-style full-width
   product-register form. The product width is preserved during lowering and
   only truncated at the assignment target, so registered products no longer
   silently collapse to zero. Regression tests lock all three forms.

2. **`LegacyLoweringError` diagnostics** for unsupported assignment targets now
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
   resets either frontend: it calls the no-arg `reset()` on the new
   `PythonSimulator` / `CompiledSimulator`, and forwards `rst` / `cycles` to the
   legacy `Simulator.reset(rst=None, cycles=2)`. Test harnesses no longer need
   to branch on the concrete simulator class.

The remaining audit note is a modeling-discipline item rather than a framework
bug: the Python-UVM scoreboard compares outputs cycle-by-cycle, so a reference
model must emit any "preview" output in the same cycle the DUT asserts
`out_valid`, deferring only the architectural state commit. See the pipelined
DUT guidance in [TUTORIAL_UVM.md](./TUTORIAL_UVM.md).

## Practical boundaries today

The current framework is strong, but it still has clear boundaries.

1. `archsim` is lightweight by design; it is for exploration, not full
   microarchitectural golden modeling
2. the native executable DSL is intentionally small; the legacy DSL is still the
   richer modeling surface
3. `iverilog` can be used for local RTL/collateral smoke, but full UVM closure
   still depends on an external simulator environment
4. PPA is analysis-first; rewrite authority should remain with the agent or the
   human designer
5. there is no mandatory top-level SoC workflow engine here by design

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
