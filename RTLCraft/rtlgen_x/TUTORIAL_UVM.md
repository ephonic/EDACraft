# Legacy DSL to Remote VCS/UVM Tutorial

This tutorial shows the recommended path from a legacy DSL module to:

1. executable local validation
2. generated SV/UVM collateral
3. remote VCS/UVM execution
4. feedback-driven iteration

It is the most practical path when you already have a module written in the
legacy DSL and want to move from design intent to runnable verification quickly.

## When to use this tutorial

Use this flow when:

1. the DUT already exists as a legacy DSL `Module`
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
legacy DSL module
  -> lower to SimModule
  -> Python/local compiled validation
  -> Python-UVM or directed regression
  -> generate SV/UVM runtime bundle
  -> smoke-check generated reference model
  -> local iverilog packaging probe
  -> remote VCS/UVM probe or regression
  -> feed failures back into design/lowering/export
```

## Step 1: instantiate the DUT

Start from the legacy DSL class.

```python
from my_design.dsl import MyLegacyModule

module = MyLegacyModule()
```

If your module already lives in a dedicated file and class, keep that pair handy.
The helper scripts use exactly that interface.

## Step 2: lower into the executable model

Lowering converts the legacy DSL module into `SimModule`, the execution model used
by the new simulator stack.

```python
from rtlgen_x.dsl import lower_legacy_module_to_sim

lowered = lower_legacy_module_to_sim(module)
sim_module = lowered.module

print(sim_module.name)
print(lowered.report.assignment_count)
```

What to check here:

1. lowering succeeds without `LegacyLoweringError`
2. the output names and input names look sane
3. state and memory objects were captured as expected
4. reset behavior is represented correctly
5. latch-heavy modules lower cleanly if they use `with self.latch:`

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
from rtlgen_x.dsl import build_compiled_simulator_from_legacy

with build_compiled_simulator_from_legacy(module, build_dir="build/my_legacy_compiled") as cpp_sim:
    cpp_sim.reset()
    print(cpp_sim.step({"clk": 0, "rst": 1, "inp": 0}))
    print(cpp_sim.step({"clk": 0, "rst": 0, "inp": 5}))
    print(cpp_sim.step({"clk": 0, "rst": 0, "inp": 2}))
```

If Python and compiled behavior differ, stop here and debug before generating
verification collateral.

Useful helpers at this stage:

1. `compare_python_and_compiled(...)`
2. `capture_execution_trace(...)`
3. `run_random_parity_fuzz(...)`
4. `run_legacy_rtl_cosim(...)` if emitted RTL parity matters early

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

report = run_directed_test(module, vectors, name="legacy_directed")
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

report = run_python_uvm_test(module, sequence, name="legacy_local_uvm")
print(report.passed, report.total_cycles)
```

Use Python-UVM when you want:

1. sequences
2. scoreboarding
3. coverage bins
4. failure triage bundles

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

## Step 6: generate UVM collateral

At this point the DUT should already be semantically healthy. Now generate SV/UVM
collateral.

### Static collateral only

```python
from rtlgen_x.verify import generate_uvm_collateral, write_uvm_collateral

collateral = generate_uvm_collateral(module, clock_name="clk")
write_uvm_collateral(collateral, "build/my_legacy_uvm_collateral")
```

### Runnable bundle

```python
from rtlgen_x.verify import generate_uvm_runtime_bundle, write_uvm_runtime_bundle

bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
write_uvm_runtime_bundle(bundle, "build/my_legacy_uvm", include_runtime_package=False)
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

For pipelined DUTs also check:

1. valid bits and payload registers move stage-by-stage as intended
2. payload registers are not rewritten on bubble cycles
3. `out_valid` timing matches the intended scoreboard collection point

## Step 8: smoke-test the generated reference model

Before involving remote tools, prove that the generated reference model is alive.

```python
from rtlgen_x.verify import smoke_test_generated_reference_model

report = smoke_test_generated_reference_model(
    "build/my_legacy_uvm/my_legacy_module_ref_model.py",
    inputs={"clk": 0, "rst": 0, "inp": 5},
)
print(report.class_name)
print(report.predicted)
```

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
probe = probe_iverilog_uvm_collateral(collateral, output_dir="build/my_legacy_iverilog_probe")

print(probe.interface_compile_ok)
print(probe.package_compile_ok)
print(probe.skipped_reason)
```

This is not full UVM closure. It helps catch:

1. broken emitted file structure
2. obvious syntax problems
3. include/package arrangement mistakes

## Step 10: run one remote VCS/UVM probe

Once local smoke passes, generate and run the bundle remotely.

### Python API

```python
from rtlgen_x.verify import default_remote_dir, run_remote_uvm_probe

result = run_remote_uvm_probe(
    module,
    clock_name="clk",
    host="10.134.143.28",
    remote_dir=default_remote_dir(getattr(module, "name", "my_legacy_module")),
    source_script="/apps/EDAs/syn.bash",
    local_bundle_dir="build/my_legacy_remote_probe",
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
  --module-class MyLegacyModule \
  --clock clk \
  --host 10.134.143.28 \
  --local-bundle-dir build/my_legacy_remote_probe
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

## Failure map and feedback path

Use failures to decide where to modify the system.

### Local Python sim fails

Likely fix points:

1. the legacy DSL design itself
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
3. [scripts/run_remote_uvm_probe.py](../scripts/run_remote_uvm_probe.py)
4. [scripts/run_remote_uvm_regression.py](../scripts/run_remote_uvm_regression.py)
