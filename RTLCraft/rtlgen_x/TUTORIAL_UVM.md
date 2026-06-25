# DSL to Remote VCS/UVM Tutorial

This tutorial shows the recommended path from a DSL module to:

1. executable local validation
2. generated SV/UVM collateral
3. remote VCS/UVM execution
4. feedback-driven iteration

It is the most practical path when you already have a module written in the
DSL and want to move from design intent to runnable verification quickly.

## When to use this tutorial

Use this flow when:

1. the DUT already exists as a DSL `Module`
2. you want semantic checks before exporting RTL/UVM
3. you want generated Python reference models and SV/UVM collateral
4. you want to run full UVM closure on a remote VCS host

## Prerequisites

Local prerequisites:

1. the repository is available locally
2. the DUT can be imported from Python
3. the local Python environment can import `rtlgen_x`
4. `iverilog` is optional but helpful for local SV smoke checks

Remote prerequisites:

1. passwordless SSH access to the remote host
2. the remote host has a working VCS installation
3. the remote host can `source /apps/EDAs/syn.bash` or an equivalent setup script
4. the remote host has `python3`, `python3-config`, and `gcc`

## End-to-end path

```text
DSL module
  -> lower for inspection and low-level executable use
  -> Python/local compiled validation
  -> Python-UVM or directed regression
  -> generate SV/UVM runtime bundle
  -> smoke-check generated reference model
  -> local iverilog packaging probe
  -> remote VCS/UVM probe or regression
  -> feed failures back into design/lowering/export
```

## Step 1: instantiate the DUT

Start from the DSL class.

```python
from my_design.dsl import MyDslModule

module = MyDslModule()
```

If your module already lives in a dedicated file and class, keep that pair handy.
The helper scripts use exactly that interface.

## Step 2: lower into the executable model

Lowering converts the DSL module into the internal executable model used by the
new simulator stack.

```python
from rtlgen_x.dsl import lower_dsl_module_to_sim

lowered = lower_dsl_module_to_sim(module)
sim_module = lowered.module

print(sim_module.name)
print(lowered.report.assignment_count)
```

What to check here:

1. lowering succeeds without `DslLoweringError`
2. the output names and input names look sane
3. state and memory objects were captured as expected
4. reset behavior is represented correctly
5. latch-heavy modules lower cleanly if they use `with self.latch:`

Important boundary:

1. single-clock DUTs are the smoothest path for generated reference models,
   Python-UVM, and exported SV/UVM collateral
2. multi-clock DSL modules can lower into the new executable model, and the
   lowered runtime can execute them with `step_clocks(...)`
3. local Python-UVM can also run multi-clock DUTs when every sequence item
   carries explicit `active_domains`
4. generated Python reference models can also run explicit multi-clock
   `predict_clocks(...)` / smoke checks
5. generated UVM collateral can now run an explicit directed multi-clock path
   when every `UvmSequenceStep` names `active_domains`
6. randomized / generic multi-clock generated UVM is still out of scope, so
   broader multi-clock closure still prefers emitted RTL plus an external
   simulator flow
7. generated DSL DUT export preserves the module's authored reset semantics,
   so sync reset stays sync and explicit async-low reset stays async-low in the
   emitted SV/UVM bundle
8. `sim_module` is for low-level runtimes such as `PythonSimulator`,
   `CompiledSimulator`, or architecture inference helpers; public verify and
   UVM helpers should receive the original DSL `Module` or the full
   `LoweredDslModule`, not `lowered.module`

## Step 2.5: run CDC preflight for clock/reset-domain hazards

If the DUT has more than one clock domain, run the static CDC check before
local simulation or collateral export. Also run it on single-clock DUTs that
use async reset, because reset-release hazards are checked too.

```python
from rtlgen_x.verify import analyze_cdc, emit_cdc_report_markdown

cdc_report = analyze_cdc(module)
print(cdc_report.error_count, cdc_report.warning_count)
print(emit_cdc_report_markdown(cdc_report, title="My DUT CDC Preflight"))
```

What this catches today:

1. single-bit level crossings that should use `SyncCell`
2. pulse/event crossings that should use `PulseSynchronizer`
3. multi-bit payload crossings that should use `AsyncFIFO` or an explicit
   synchronized protocol
4. cross-domain memory reads/writes that need CDC-safe ownership or buffering
5. multi-writer shared state or memory hazards
6. async reset release paths that bypass a recognized sync-release stage

What to run it on:

1. prefer the original DSL `Module` when available, because safe helper
   instances like `SyncCell`, `PulseSynchronizer`, `AsyncFIFO`, and
   `AsyncResetRel` are recognized there
2. the lowered executable model carries the same clock/reset metadata into the
   simulator and verification stack
3. the DSL path also recognizes common hand-written two-flop level
   synchronizers and hand-written async-assert / sync-release reset chains
4. same-clock DSL designs are allowed to build `rst_sync` in one raw-reset
   block and consume that synchronized reset from separate functional blocks

How to use the result:

1. treat `error` findings as redesign-required before UVM closure
2. treat `warning` findings as synchronizer/protocol-review-required
3. `reset_release_crossing` means the functional domain still sees a raw async
   reset, so add `AsyncResetRel` or a hand-written sync-release chain and feed
   the resulting `rst_sync` into the functional block
4. if source metadata is present, use the reported producer/consumer file+line
   sites to patch the DUT directly; for reset-release findings, also use the
   affected sequential target sites to identify the functional state that still
   depends on the raw async reset
5. current reset-release findings also carry a recommended `AsyncResetRel`
   instance name and synchronized-reset signal name, so an agent can patch the
   wrapper with less naming guesswork

Practical control-plane stdlib guidance:

1. `APBRegisterBank` is still a strong control-plane closure path for lowering,
   executable simulation, Python-UVM, and generated SV/UVM collateral
2. however, if you drive it from a raw asynchronous `presetn`, the CDC preflight
   will intentionally report a `reset_release_crossing` warning until you add a
   per-domain reset-release synchronizer
3. `AXI4LiteRegisterBank` and `WishboneRegisterBank` do not currently trigger
   that specific warning in the stdlib implementation, because their reset path
   is synchronous today
4. so if an agent is choosing between the built-in control-plane helpers for a
   quick single-clock closure, `AXI4LiteRegisterBank` or `WishboneRegisterBank`
   are the lower-friction path when you do not want to author a reset-release
   wrapper first
5. if APB is the required architectural interface, keep using
   `APBRegisterBank`, but treat the reset wrapper as part of the intended DUT
   authoring rather than as a post-hoc cleanup

This step is intentionally report-oriented: `rtlgen_x` tells you what is unsafe
and what primitive pattern fits, while the agent or designer edits the module.

## Step 3: run quick semantic checks in Python

Use `PythonSimulator` first because it is simple and fast to inspect.

```python
from rtlgen_x.sim import PythonSimulator

py_sim = PythonSimulator(sim_module)
py_sim.reset()

print(py_sim.step({"clk": 0, "rst": 1, "inp": 0}))
print(py_sim.step({"clk": 0, "rst": 0, "inp": 5}))
print(py_sim.step({"clk": 0, "rst": 0, "inp": 2}))
```

Recommended checks:

1. reset and deassertion sequence
2. representative stimulus
3. state-hold behavior
4. memory write/read sequencing
5. latch hold/update behavior

If this stage fails, the bug is usually in:

1. the original DSL module
2. the intended semantics
3. the lowering assumptions

### Important note for fully-pipelined DUTs

If the DUT accepts one transaction per cycle, model it with:

1. an unconditional valid-bit shift chain
2. payload registers that only update when the matching valid bit is high

Example:

```python
@self.seq(self.clk, self.rst)
def _seq():
    with If(self.rst == 1):
        self.v0 <<= 0
        self.v1 <<= 0
        self.stage0_q <<= 0
        self.stage1_q <<= 0
    with Else():
        self.v0 <<= self.in_valid
        self.v1 <<= self.v0

        with If(self.in_valid == 1):
            self.stage0_q <<= stage0_expr
        with If(self.v0 == 1):
            self.stage1_q <<= stage1_expr
```

If payload writes are not valid-gated, bubble cycles can overwrite in-flight
data even though one-shot tests still pass.

## Step 4: run compiled simulation

Once Python behavior looks right, validate on the compiled path.

```python
from rtlgen_x.dsl import build_compiled_simulator_from_dsl

with build_compiled_simulator_from_dsl(module, build_dir="build/my_dsl_compiled") as cpp_sim:
    cpp_sim.reset()
    print(cpp_sim.step({"clk": 0, "rst": 1, "inp": 0}))
    print(cpp_sim.step({"clk": 0, "rst": 0, "inp": 5}))
    print(cpp_sim.step({"clk": 0, "rst": 0, "inp": 2}))
```

If Python and compiled behavior differ, stop here and debug before generating
verification collateral.

## Step 4.5: decide storage initialization semantics early

Before leaning on RTL cosim or remote UVM, decide whether storage contents are
architecturally meaningful before the first write.

Use these rules:

1. `Memory(..., init_zero=True)` and `Memory(..., init_data=...)` export
   explicit RTL initialization and stay aligned with lowered execution
2. `Array(...)` does not inject implicit RTL initialization, even though the
   lowered Python and compiled simulators still begin from concrete values
3. if the design reads an `Array(...)` before reset logic or write traffic has
   initialized it, local RTL cosim may surface `x` even when the executable
   model produces a number

If `run_dsl_multiclock_rtl_cosim(...)` raises `CosimUnknownValueError`,
treat that as a real design/export boundary:

1. switch the storage to `Memory(..., init_zero=True)` if zero-init is part of
   the intended hardware contract
2. add explicit init-block or reset writes if the storage should be initialized
   structurally
3. delay scoreboarding until after the first architecturally meaningful write if
   the pre-init read truly does not matter

Useful helpers at this stage:

1. `compare_python_and_compiled(...)`
2. `capture_execution_trace(...)`
3. `run_random_parity_fuzz(...)`
4. `run_dsl_rtl_cosim(...)` if emitted RTL parity matters early for
   cycle-aligned interfaces or simple valid-gated streaming interfaces

For valid-driven streaming DUTs, the generic helper now supports
`valid_signal`, `flush_cycles`, and `flush_inputs`, so it can check results on
`out_valid` rather than one trace row per input row. The SFU example in
`sfu/iverilog_cosim.py` is still the reference pattern when you want richer
DUT-specific scoreboarding or protocol checks.

## Step 5: run structured local verification

Before exporting to VCS/UVM, it is usually worth running at least one structured
local regression.

### Option A: directed or streaming checks

```python
from rtlgen_x.verify import StepVector, run_directed_test

vectors = (
    StepVector(inputs={"clk": 0, "rst": 1, "inp": 0}, expected={"out": 0}),
    StepVector(inputs={"clk": 0, "rst": 0, "inp": 5}, expected={"out": 5}),
)

report = run_directed_test(module, vectors, name="dsl_directed")
print(report.passed)
```

### Option B: Python-UVM style local verification

```python
from rtlgen_x.verify import PythonUvmSequenceItem, run_python_uvm_test

sequence = (
    PythonUvmSequenceItem(inputs={"clk": 0, "rst": 1, "inp": 0}, label="reset"),
    PythonUvmSequenceItem(inputs={"clk": 0, "rst": 0, "inp": 5}, label="op0"),
    PythonUvmSequenceItem(inputs={"clk": 0, "rst": 0, "inp": 2}, label="op1"),
)

report = run_python_uvm_test(module, sequence, name="dsl_local_uvm")
print(report.passed, report.total_cycles)
```

Use Python-UVM when you want:

1. sequences
2. scoreboarding
3. coverage bins
4. failure triage bundles
5. explicit multi-clock local event verification via `active_domains`

For a multi-clock local run, make each transaction an explicit clock-domain
event:

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

report = run_python_uvm_test(module, sequence, name="dsl_multiclk_local_uvm")
print(report.passed, report.traces[-1].active_domains)
```

For DSL modules that declare semantic clock domains, prefer those semantic
names in `active_domains`. Raw signal names such as `wr_clk` / `rd_clk` remain
accepted as compatibility aliases.

Today this local path is scalar-step only. If you pass `batch_cycles`, any
chunk containing `active_domains` items automatically falls back to per-item
stepping so the event order stays explicit.

For streaming or pipelined DUTs, include:

1. one-shot tests
2. back-to-back tests
3. drain-bubble tests
4. reset-near-traffic tests when the DUT has explicit reset
5. at least one longer-stream smoke where scoreboard or expected-value storage
   scales from the actual vector count

If you keep a hand-written `iverilog` cosim beside the generated UVM collateral,
also keep build artifacts unique per run when multiple probes may reuse the
same output directory.

For pipelined streaming DUTs, also keep one more discipline:

1. collect expected values by output transaction, not by raw cycle count
2. drain the pipe until the expected number of `out_valid` results arrive
3. keep the local smoke vector count modest when using `iverilog` on larger
   LUT-heavy DUTs, then scale up with explicit scripts as needed

## Step 6: generate UVM collateral

At this point the DUT should already be semantically healthy. Now generate SV/UVM
collateral.

### Static collateral only

```python
from rtlgen_x.verify import generate_uvm_collateral, write_uvm_collateral

collateral = generate_uvm_collateral(module, clock_name="clk")
write_uvm_collateral(collateral, "build/my_dsl_uvm_collateral")
```

### Runnable bundle

```python
from rtlgen_x.verify import generate_uvm_runtime_bundle, write_uvm_runtime_bundle

bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
write_uvm_runtime_bundle(bundle, "build/my_dsl_uvm", include_runtime_package=False)
```

The runtime bundle adds:

1. generated DUT SystemVerilog
2. generated top module
3. file list
4. `run_vcs.sh`

If the DUT does not expose a real clock input, you can still choose a synthetic
verification clock name, for example:

```python
bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
```

In that case the UVM environment is clocked, but only the DUT's real ports are
connected into the DUT instance.

## Step 7: inspect the generated artifacts

The most useful files to inspect first are:

1. `*_dut.sv`
2. `*_top.sv`
3. `*_scoreboard.sv`
4. `*_ref_model.py`
5. `rtlgen_x_ref_runtime.py`
6. `run_vcs.sh`

What to check:

1. the DUT module name matches expectations
2. reset polarity looks right in the smoke sequence
3. scoreboard inputs line up with the intended transaction fields
4. generated reference-model outputs match the DUT outputs
5. latch-based DUTs emit `always_latch` when exported as SV

For control-plane stdlib blocks, also check:

1. `APBRegisterBank` smoke sequences assert `presetn == 1'b0` during reset and
   `presetn == 1'b1` during normal traffic
2. `AXI4LiteRegisterBank` / `WishboneRegisterBank` smoke sequences match the
   DUT reset polarity (`rst` / `rst_i`)
3. generated reference models preserve byte-enable metadata so partial writes
   (`pstrb` / `wstrb` / `sel_i`) are not silently flattened into full-word
   overwrites

For pipelined DUTs also check:

1. valid bits and payload registers move stage-by-stage as intended
2. payload registers are not rewritten on bubble cycles
3. `out_valid` timing matches the intended scoreboard collection point

## Step 8: smoke-test the generated reference model

Before involving remote tools, prove that the generated reference model is alive.

```python
from rtlgen_x.verify import smoke_test_generated_reference_model

report = smoke_test_generated_reference_model(
    "build/my_dsl_uvm/my_dsl_module_ref_model.py",
    inputs={"clk": 0, "rst": 0, "inp": 5},
)
print(report.class_name)
print(report.predicted)
```

For a multi-clock generated reference model, pass an explicit domain-event
schedule:

```python
report = smoke_test_generated_reference_model(
    "build/my_dsl_uvm/my_dsl_module_ref_model.py",
    inputs={"wr_en": 1, "din": 11},
    active_domains=("write",),
)
print(report.predicted)
print(report.active_domains)
```

For a multi-clock generated UVM bundle, use directed steps with explicit active
domains:

```python
from rtlgen_x.verify import UvmSequenceStep, generate_uvm_runtime_bundle

bundle = generate_uvm_runtime_bundle(
    module,
    clock_name="wr_clk",
    directed_sequence=(
        UvmSequenceStep(
            inputs={"wr_rst": 1, "rd_rst": 1},
            active_domains=("write", "read"),
            label="reset",
        ),
        UvmSequenceStep(
            inputs={"wr_en": 1, "din": 0x11},
            active_domains=("write",),
            label="write0",
        ),
        UvmSequenceStep(
            inputs={"rd_en": 1},
            active_domains=("read",),
            label="read0",
        ),
    ),
)
```

For single-clock control-plane stdlib DUTs, you can also reuse protocol-transfer
helpers directly instead of hand-writing `UvmSequenceStep(...)` items:

```python
from rtlgen_x.dsl import APBRegisterBank
from rtlgen_x.verify import (
    ApbTransfer,
    generate_uvm_runtime_bundle,
    protocol_transfers_to_uvm_sequence_steps,
)

bundle = generate_uvm_runtime_bundle(
    APBRegisterBank(depth=8),
    clock_name="pclk",
    directed_sequence=protocol_transfers_to_uvm_sequence_steps(
        "apb",
        (
            ApbTransfer(addr=0x10, write=True, wdata=0x55AA, label="wr0"),
            ApbTransfer(addr=0x10, write=False, expected_rdata=0x55AA, label="rd0"),
        ),
    ),
)
```

The bridge only reuses protocol stimulus shaping. Generated UVM still checks
behavior through the emitted DUT wrapper, generated reference model, and
scoreboard rather than copying Python-UVM `expected` dictionaries into the
sequence step object.

Generated runtime bundles preserve the DSL module's reset semantics. In
practice that means:

1. `@self.seq(clk, rst)` exports as a synchronous `always_ff @(posedge clk)`
   reset style
2. `@self.seq(clk, ~rst_n)` exports as `always_ff @(posedge clk or negedge rst_n)`

That detail matters for multi-clock directed sequences, because reset release
must not silently introduce an extra event on the wrong domain.

If this fails, feed the issue back into:

1. interface description
2. lowering
3. exported runtime/reference-model generation

## Operand timing for clocked DUTs

For a clocked DUT, the safest canonical driver pattern is:

```text
@(negedge clk);   drive operands and in_valid
@(negedge clk);   keep them stable across the sampling posedge
deassert or move to the next transaction
```

That rule matters most for:

1. the first transaction after reset release
2. back-to-back streaming sequences
3. any self-checking scoreboard that assumes fixed op-to-result alignment

If operands and `in_valid` are driven too late, the DUT can sample the next
transaction or a bubble instead of the intended one, which looks like a design
bug but is really a TB-edge issue.

For long streaming regressions, the most common TB hygiene bugs are:

1. fixed-size expected arrays that silently truncate longer runs
2. shared `tb.v` / `tb.vvp` artifact names that make repeated probes race each
   other

Those are verification-collateral bugs, not DUT bugs, but they are easy to
misdiagnose if the local smoke discipline is weak.

## Step 9: run a local collateral compile smoke

Use `iverilog` as a local packaging sanity check.

```python
from rtlgen_x.verify import generate_uvm_collateral, probe_iverilog_uvm_collateral

collateral = generate_uvm_collateral(module, clock_name="clk")
probe = probe_iverilog_uvm_collateral(collateral, output_dir="build/my_dsl_iverilog_probe")

print(probe.interface_compile_ok)
print(probe.package_compile_ok)
print(probe.skipped_reason)
```

This is not full UVM closure. It helps catch:

1. broken emitted file structure
2. obvious syntax problems
3. include/package arrangement mistakes

It does not replace a DUT-aware streaming cosim. For a module with a real
`in_valid/out_valid` contract, do that closure before or alongside collateral
export.

## Step 10: run one remote VCS/UVM probe

Once local smoke passes, generate and run the bundle remotely.

### Optional preflight

Before generating any bundle, confirm the remote host can source the simulator
environment and find `vcs`:

```python
from rtlgen_x.verify import probe_remote_uvm_environment

env_report = probe_remote_uvm_environment(
    host="10.134.143.28",
    source_script="/apps/EDAs/syn.bash",
)

print(env_report.environment_ok)
print(env_report.vcs_path)
print(env_report.stderr)
```

### Python API

```python
from rtlgen_x.verify import default_remote_dir, run_remote_uvm_probe

result = run_remote_uvm_probe(
    module,
    clock_name="clk",
    host="10.134.143.28",
    remote_dir=default_remote_dir(getattr(module, "name", "my_dsl_module")),
    source_script="/apps/EDAs/syn.bash",
    local_bundle_dir="build/my_dsl_remote_probe",
)

print(result.returncode)
print(result.summary.passed)
print(result.summary.severity_counts)
for line in result.summary.scoreboard_lines:
    print(line)
```

### Helper script

```bash
python scripts/run_remote_uvm_probe.py \
  --module-file path/to/dsl.py \
  --module-class MyDslModule \
  --clock clk \
  --host 10.134.143.28 \
  --local-bundle-dir build/my_dsl_remote_probe
```

For multi-clock directed closure, add a step file and pass
`--directed-sequence-json`:

```json
[
  {
    "inputs": {"wr_rst": 1, "rd_rst": 1},
    "label": "reset",
    "active_domains": ["write", "read"]
  },
  {
    "inputs": {"wr_en": 1, "din": 17},
    "label": "write0",
    "active_domains": ["write"]
  },
  {
    "inputs": {"rd_en": 1},
    "label": "read0",
    "active_domains": ["read"]
  }
]
```

```bash
python scripts/run_remote_uvm_probe.py \
  --module-file path/to/dsl.py \
  --module-class MyDslMultiClockModule \
  --clock wr_clk \
  --host 10.134.143.28 \
  --directed-sequence-json path/to/multiclk_steps.json \
  --local-bundle-dir build/my_multiclk_remote_probe
```

This path is usually the first full-system proof that:

1. SV export works
2. DPI bridge works
3. generated reference model agrees with the DUT in a real UVM simulator

## Step 11: scale to remote regression

When one probe passes, batch multiple modules.

### Python API

```python
from pathlib import Path
from rtlgen_x.verify import RemoteUvmTarget, run_remote_uvm_regression, write_remote_uvm_regression_report

targets = (
    RemoteUvmTarget(
        name="mod_a",
        module_file=Path("path/to/mod_a.py"),
        module_class="ModuleA",
        clock_name="clk",
    ),
    RemoteUvmTarget(
        name="mod_b",
        module_file=Path("path/to/mod_b.py"),
        module_class="ModuleB",
        clock_name="clk",
    ),
)

report = run_remote_uvm_regression(
    targets,
    host="10.134.143.28",
    source_script="/apps/EDAs/syn.bash",
    local_root="build/remote_uvm_regression",
)
write_remote_uvm_regression_report(report, "build/remote_uvm_regression/report.json")
```

### Helper script

```bash
python scripts/run_remote_uvm_regression.py \
  --host 10.134.143.28 \
  --target path/to/mod_a.py:ModuleA:clk \
  --target path/to/mod_b.py:ModuleB:clk \
  --local-root build/remote_uvm_regression \
  --json-out build/remote_uvm_regression/report.json
```

You can also load targets from JSON or overlay one explicit directed sequence
across every target:

```bash
python scripts/run_remote_uvm_regression.py \
  --host 10.134.143.28 \
  --targets-json build/remote_uvm_targets.json \
  --directed-sequence-json path/to/shared_steps.json \
  --local-root build/remote_uvm_regression \
  --json-out build/remote_uvm_regression/report.json
```

## Failure map and feedback path

Use failures to decide where to modify the system.

### Local Python sim fails

Likely fix points:

1. the DSL design itself
2. reset sequencing assumptions
3. latch, memory, or state semantics

### Python sim passes but compiled sim fails

Likely fix points:

1. lowering
2. C++ backend semantics
3. batch/scalar runtime discrepancies

### Local verification fails but scalar sim looks fine

Likely fix points:

1. expected-value generation
2. protocol sequence shape
3. scoreboard assumptions

### Generated reference model fails

Likely fix points:

1. interface ordering
2. generated runtime support
3. exported executable-model semantics

### Remote VCS/UVM fails

Likely fix points:

1. DUT export
2. SV/UVM packaging
3. DPI bridge environment
4. simulator-specific behavior
5. reset-style mismatches between the authored DSL module and the emitted
   DUT, especially if failure shows up exactly on reset release

The key design principle is:

```text
debug as locally and as executably as possible,
then re-export and rerun remotely
```

## Recommended completion checklist

Before calling the flow healthy, check off:

1. lowering succeeds
2. Python simulation matches intent
3. compiled simulation matches Python
4. at least one local directed or Python-UVM regression passes
5. generated reference model smoke passes
6. local collateral probe is clean enough for handoff
7. remote VCS/UVM probe passes
8. remote regression report is archived if running batch mode

## Related docs

1. [README.md](./README.md)
2. [TUTORIAL_ARCH_PPA.md](./TUTORIAL_ARCH_PPA.md)
3. [scripts/probe_remote_uvm_environment.py](../scripts/probe_remote_uvm_environment.py)
4. [scripts/run_remote_uvm_probe.py](../scripts/run_remote_uvm_probe.py)
5. [scripts/run_remote_uvm_regression.py](../scripts/run_remote_uvm_regression.py)
