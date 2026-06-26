# DSL To Local UVM Tutorial

This tutorial describes the release-supported path from a `rtlgen` DSL module
to local verification collateral.

The release flow is local-first:

1. lower the DSL module
2. run Python simulation
3. run compiled C++ simulation
4. run directed or Python-UVM checks
5. generate SV/UVM collateral
6. smoke-check the generated reference model
7. run local RTL/UVM tools when available

The release tutorial assumes local simulator execution. If your environment
provides VCS, run it through the local VCS setup.

## When To Use This Tutorial

Use this flow when:

1. the DUT already exists as a `rtlgen.dsl.Module`
2. you want semantic checks before exporting RTL/UVM
3. you want generated Python reference models and SV/UVM collateral
4. you want a local path that works with Python, compiled C++, `iverilog`,
   `verilator`, or local `vcs`

## Prerequisites

Required:

1. the repository is available locally
2. the DUT can be imported from Python
3. the local Python environment can import `rtlgen`
4. `pytest` is available for regression runs

Optional:

1. `iverilog` for generated SV collateral smoke checks
2. `verilator` for stronger local emitted-RTL closure
3. local `vcs` for project-style UVM simulation if your site provides it

## End-To-End Path

```text
DSL module
  -> lower for inspection
  -> Python simulation
  -> compiled C++ simulation
  -> directed / Python-UVM verification
  -> generate SV/UVM runtime bundle
  -> smoke-check generated Python reference model
  -> local RTL/UVM backend
  -> feed failures back into DSL or export code
```

## Step 1: Instantiate The DUT

```python
from my_design.dsl import MyDslModule

module = MyDslModule()
```

Keep the module file and class name stable. Generated collateral and helper
scripts work best when the DUT is importable without side effects.

## Step 2: Lower Into The Executable Model

```python
from rtlgen.dsl import lower_dsl_module_to_sim

lowered = lower_dsl_module_to_sim(module)
sim_module = lowered.module

print(sim_module.name)
print(lowered.report.assignment_count)
```

Check:

1. lowering succeeds without `DslLoweringError`
2. inputs, outputs, state, arrays, and memories are present
3. reset behavior is represented correctly
4. domain declarations match the sequential blocks
5. unsupported storage or hierarchy contracts fail fast with useful diagnostics

Important boundary:

1. public verification helpers should receive the original DSL `Module` or the
   full `LoweredDslModule`
2. raw `SimModule` is a lower-level executable object, not the main authoring
   surface

## Step 3: Run CDC / Reset Preflight When Needed

If the DUT has more than one clock domain, run static CDC checks before
collateral export. Also run it on async-reset designs when reset-release
hazards matter.

```python
from rtlgen.verify import analyze_cdc, emit_cdc_report_markdown

cdc_report = analyze_cdc(module)
print(emit_cdc_report_markdown(cdc_report))
```

The CDC checker is report-oriented. It recognizes common safe patterns and
points at likely hazards, but it does not prove arbitrary CDC protocols.

## Step 4: Run Python Simulation

```python
from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

sim = PythonSimulator(lower_dsl_module_to_sim(module).module)

outputs = []
outputs.append(sim.step({"clk": 0, "rst": 1}))
outputs.append(sim.step({"clk": 0, "rst": 0}))
print(outputs)
```

Use Python simulation to debug:

1. reset behavior
2. state updates
3. ready/valid handshakes
4. signed arithmetic
5. ROM/LUT initialization

## Step 5: Run Compiled Simulation

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl

sim = build_compiled_simulator_from_dsl(module)
print(sim.step({"clk": 0, "rst": 1}))
print(sim.step({"clk": 0, "rst": 0}))
```

Best practice:

1. reuse the same vectors as Python simulation
2. check Python-vs-C++ parity before generating external collateral
3. use compiled simulation for longer regressions once the failure mode is
   localized

## Step 6: Run Directed Verification

Use directed steps for deterministic checks.

```python
from rtlgen.verify import StepVector, run_directed_test

steps = [
    StepVector(inputs={"rst": 1, "in_valid": 0}, expected={"out_valid": 0}, label="reset"),
    StepVector(inputs={"rst": 0, "in_valid": 1, "in_data": 7}, label="sample0"),
]

report = run_directed_test(module, steps)
print(report.passed)
print(report.failures)
```

A good minimal directed set includes:

1. reset
2. one normal transaction
3. one boundary transaction
4. one backpressure or stall case for ready/valid designs
5. one signed or overflow case for numeric datapaths

## Step 7: Run Python-UVM Style Checks

Python-UVM checks are useful when a design is transaction-oriented but you still
want a local, fast, Python-driven loop.

```python
from rtlgen.verify import PythonUvmSequenceItem, run_python_uvm_test

items = [
    PythonUvmSequenceItem(inputs={"rst": 1}, label="reset"),
    PythonUvmSequenceItem(inputs={"rst": 0, "in_valid": 1, "in_data": 3}, label="drive0"),
]

report = run_python_uvm_test(module, items)
print(report.passed)
```

For multi-clock designs, sequence items should explicitly name active domains
where the API requires it.

## Step 8: Generate SV/UVM Collateral

```python
from rtlgen.verify import generate_uvm_runtime_bundle, write_uvm_runtime_bundle

bundle = generate_uvm_runtime_bundle(module)
write_uvm_runtime_bundle(bundle, "build/my_dut_uvm")
```

Typical generated content includes:

1. emitted DUT RTL
2. generated interface/package/sequence collateral
3. generated Python reference runtime
4. local run scripts where supported
5. metadata and summary files

Inspect the generated files before treating them as signoff collateral.

## Step 9: Smoke-Check The Generated Reference Model

Before involving an RTL simulator, prove that the generated reference model is
alive.

```python
from rtlgen.verify import smoke_test_generated_reference_model

report = smoke_test_generated_reference_model("build/my_dut_uvm")
print(report.passed)
print(report.details)
```

If this fails, debug the generated reference model or the DSL/lowering path
before moving to SystemVerilog simulation.

## Step 10: Run Local RTL/UVM Backends

Use local backends in this order:

1. `iverilog` for lightweight syntax/package smoke when supported
2. `verilator` for stronger local emitted-RTL closure
3. local `vcs` when your environment provides it and you need project-style
   UVM simulation behavior

Example local collateral probe:

```python
from rtlgen.verify import generate_uvm_collateral, probe_iverilog_uvm_collateral

collateral = generate_uvm_collateral(module)
report = probe_iverilog_uvm_collateral(collateral)
print(report.passed)
print(report.stderr)
```

If local VCS is available, run the generated VCS script from the bundle
directory according to your site's normal simulator setup.

## Failure Map

Use the first failing layer to pick the right fix:

| Failure | Likely Starting Point |
|---------|-----------------------|
| lowering fails | DSL authoring contract, storage/hierarchy intent, unsupported construct |
| Python simulation fails | design semantics, reset behavior, state update, handshake |
| Python passes but compiled C++ fails | backend signedness, width interpretation, runtime bug |
| generated reference model fails | lowering/export contract or unsupported construct |
| `iverilog` smoke fails | emitted RTL subset, package/include arrangement, reserved names |
| `verilator` or local `vcs` fails | backend-specific SystemVerilog assumptions, testbench/package behavior |
| CDC report flags hazard | add explicit synchronizer/bridge primitive or document the crossing |

## Best Practices

1. Keep all design-visible wires, arrays, and memories on `self`.
2. Keep directed transactions small and reusable.
3. Run Python and compiled simulation before generated UVM.
4. Treat generated collateral as reviewable source.
5. Prefer deterministic local reruns over environment-specific flows.
6. Document the exact rerun commands next to the DUT or test.

## Release Checklist

A DUT is ready for release-level local verification when:

1. lowering succeeds
2. Python simulator tests pass
3. compiled simulator parity passes
4. directed or Python-UVM checks pass
5. generated reference model smoke passes
6. local RTL smoke/closure passes for the supported backend subset
7. failure triage and rerun commands are documented
