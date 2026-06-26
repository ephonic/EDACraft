# Smart Earphone SoC — Hands-On Tutorial

This tutorial walks through the Smart Earphone SoC Spec2RTL flow from a clean
checkout to generated Verilog and cycle-accurate simulation.

---

## What You Will Do

1. Run the single-entry `design_earphone.py` flow.
2. Refresh module/top-level approval evidence without sign-off.
3. Run the module-level pytest suite.
4. Simulate generated Verilog with the iverilog harness.
5. Understand how a module is organized across the layered IR flow, and when a full 6-layer split is actually justified.
6. See how to add a simple APB peripheral.

---

## Before You Start

You need:

- Python 3.12+
- `numpy` and `pytest`
- `iverilog` 13.0 + `vvp`

Set the project root in your shell for the commands below:

```bash
export RTLCRAFT_ROOT=/Users/yangfan/release/EDACraft-main/RTLCraft
cd $RTLCRAFT_ROOT
```

`earphone` is not installed as a Python package, so the examples use
`PYTHONPATH=$RTLCRAFT_ROOT` when invoking pytest.

---

## Step 1 — Run the Full Spec2RTL Flow

```bash
cd $RTLCRAFT_ROOT
python earphone/design_earphone.py
```

Expected final summary (exact numbers may shift slightly as the design evolves):

```
SMART EARPHONE SoC — DESIGN SUMMARY
======================================================================
  Scaffold compliance   : 6/6 OK
  L1 functional tests   : 4/4 PASS
  L3 DSL sim tests      : 4/4 PASS
  Cross-layer checks    : 8/8 PASS
  Intent-driven tests   : 4/4 PASS
  Verilog modules       : 9/9 generated
  Total Verilog lines   : 2445
  Total lint issues     : 35
======================================================================

  Overall: PASS
```

Artifacts produced:

- `earphone/specs/01_spec_review.md` .. `11_decision_log.md` — review bundle
- `earphone/specs/flow_feedback.json` — structured upward feedback / approval status
- `earphone/modules/<module>/specs/07_module_test_plan.json` — module handoff plan sidecar
- `earphone/modules/<module>/specs/08_module_test_report.json` — module handoff report sidecar
- `earphone/twiddle/twiddle_256_*.hex` — FFT twiddle tables
- `earphone/verilog/*.v` — 9 generated Verilog modules
- `earphone/tb/constraints/*` — generated SVA constraints and reports
- `earphone/tb/cocotb/*.py` — auto-generated cocotb test skeletons

---

## Optional Step 2 — Refresh Approval Evidence

```bash
cd $RTLCRAFT_ROOT
python -m earphone.flow --module all --check --top-level
```

Use this when you want to regenerate the module-level handoff packet and the
top-level `CP1_SOC` review artifacts before writing or refreshing human approval
files. The command refreshes:

- module specs plus aggregated `07/08` test-plan/report markdown
- structured `07/08` JSON sidecars for machine-consumable plan/report data
- top-level scaffold evidence and review bundle metadata
- `earphone/specs/flow_feedback.json` for upward feedback and blocker review

---

## Step 3 — Run the Module pytest Suite

```bash
cd $RTLCRAFT_ROOT
PYTHONPATH=$RTLCRAFT_ROOT pytest earphone/modules -q
```

Expected:

```
60 passed in ...
```

Each module contributes executable tests at the layers required by its profile. In the current Earphone pilot, the common executable checkpoints are:

- `layer_L1_behavior/tests/` — pure-Python functional model tests
- `layer_L2_cycle/tests/` — cycle-accurate Python model tests
- `layer_L5_dsl/tests/` — DSL (rtlgen `Module`) tests

Run a single module, for example the I2C master:

```bash
PYTHONPATH=$RTLCRAFT_ROOT pytest earphone/modules/i2c -q
```

---

## Step 4 — Simulate the Generated Verilog

The working harness is in `earphone/tb/iverilog/`.

```bash
cd $RTLCRAFT_ROOT/earphone/tb/iverilog
make all
```

You should see six `ALL PASS` messages, one per target:

```
[SIMD16 TB] ALL PASS
[SRAM TB] ALL PASS
[APB_BRIDGE TB] ALL PASS
[QSPI TB] ALL PASS
[I2C TB] ALL PASS
[TOP TB] ALL PASS
```

Run a single target, e.g. QSPI:

```bash
make qspi
```

> The top-level simulation needs the FFT twiddle hex files.  The directory
> already contains a symlink `generated -> ../../../generated`; if it is missing,
> recreate it with `ln -s ../../../generated generated`.

---

## Step 5 — Anatomy of a Module

Let's look at `EarphoneQSPI` as a representative module.

```
earphone/modules/qspi/
├── specs/
│   └── 00_module_spec.md            # Module-level specification
├── layer_L1_behavior/
│   ├── specs/                       # Behavior spec / test plan / report
│   └── src/behavior.py              # Functional flash + XIP model
├── layer_L2_cycle/
│   ├── specs/
│   └── src/cycle.py                 # Cycle-accurate FSM model
├── layer_L3_architecture/
│   ├── specs/
│   └── src/arch.py                  # Architecture plan placeholder
├── layer_L4_structure/
│   ├── specs/
│   └── src/structure.py             # Structural decomposition placeholder
├── layer_L5_dsl/
│   ├── specs/
│   └── src/dsl.py                   # Synthesizable rtlgen Module
└── layer_L6_verilog/
    ├── specs/
    └── src/emitter.py               # Verilog emission helper
```

**How the layers relate**

```
SpecIR (00_module_spec.md)
    │
    ▼
BehaviorIR (behavior.py)  ── pytest L1 tests
    │
    ▼
CycleIR    (cycle.py)     ── pytest L2 tests
    │
    ▼
ArchitectureIR / StructuralIR (arch.py, structure.py)
    │
    ▼
DSL AST    (dsl.py)       ── pytest L5 tests + design_earphone.py L3 sim
    │
    ▼
Verilog    (earphone_qspi.v) ── iverilog tb_earphone_qspi.v
```

The same pattern is repeated for every module under `earphone/modules/`, but in the general framework not every leaf module must author all middle layers. L3/L4 are most useful for architecturally rich or hierarchical blocks.

---

## Step 6 — Inspecting the Generated Verilog

After running `design_earphone.py`, open `earphone/verilog/earphone_qspi.v`.  You
will see:

- A single module `EarphoneQSPI`.
- An FSM with states idle→cmd→addr→dummy→data.
- A `counter` that loads `8` in the data phase for 8 nibbles = 32 bits.
- Clock-gating logic (`qspi_ce`) that stalls state-register updates when idle.

Compare it with the DSL source in `modules/qspi/layer_L5_dsl/src/dsl.py`.  The
DSL uses RTLCraft primitives such as `Reg`, `Wire`, `If`/`Elif`/`Else`, and
`Switch`/`Case`; the Verilog emitter translates these into plain
SystemVerilog-2012.

---

## Step 7 — Add a New APB Peripheral (Walkthrough)

Suppose you want to add a simple APB timer.

1. **Create the module directory**

   ```bash
   mkdir -p earphone/modules/timer/layer_L{1,2,3,4,5,6}_dsl/src
   touch earphone/modules/timer/__init__.py
   ```

2. **Write the L1 behavior model**

   `earphone/modules/timer/layer_L1_behavior/src/behavior.py`:

   ```python
   class TimerFunctional:
       def __init__(self):
           self.value = 0
           self.limit = 0
           self.irq = 0

       def write(self, addr, data):
           if addr == 0:
               self.value = data
           elif addr == 4:
               self.limit = data

       def read(self, addr):
           if addr == 0:
               return self.value
           elif addr == 4:
               return self.limit
           return 0

       def tick(self):
           self.value = (self.value + 1) & 0xFFFFFFFF
           self.irq = 1 if self.value >= self.limit and self.limit else 0
   ```

3. **Write L2 cycle model and L5 DSL**

   Follow the existing `i2c` or `qspi` modules.  The DSL should inherit from
   `rtlgen.core.Module`, define APB4 slave ports (`paddr`, `pwdata`, `prdata`,
   `pwrite`, `psel`, `penable`, `pready`), and implement the counter logic with
   `Reg` updates guarded by `psel & penable`.

4. **Add pytest tests**

   Create `layer_L1_behavior/tests/test_behavior.py` and
   `layer_L5_dsl/tests/test_dsl.py` analogous to the QSPI/I2C tests.

5. **Wire into `EarphoneTop`**

   In `earphone/design_earphone.py`, instantiate the timer and connect it to an
   unused APB bridge slot (e.g. slot 2).  Update the slave response mux so
   `s_prdata` and `s_pready` include the timer.

6. **Regenerate and verify**

   ```bash
   python earphone/design_earphone.py
   PYTHONPATH=$RTLCRAFT_ROOT pytest earphone/modules/timer -q
   ```

---

## Cross-Layer Verification at a Glance

`design_earphone.py` runs these consistency checks:

| Module | Layers Compared | What is checked |
|--------|-----------------|-----------------|
| SIMD16 | L1 ↔ L2 ↔ L3 | INT16 vadd/vsub bit-exact match |
| SRAM256K | L1 ↔ L3 | APB write/read returns expected data |
| APB Bridge | L1 ↔ L3 | Address decode produces correct one-hot `s_psel` |
| RV32IM | L1 ↔ L3 | MUL/DIV/DIVU/REM/REMU retire values |
| QSPI | L1 ↔ L2 | XIP read returns flash data in correct order |
| I2C | L1 ↔ L2 | Master write transaction completes correctly |
| FFT256 | L1 ↔ L3 | Fixed-point FFT output matches NumPy reference |

The FFT256 check is a good example of how numerical tolerance is handled:
inputs are 16-bit Q1.15 fixed-point, the hardware output is bit-reversed, and
the test unshuffles it before comparing against a NumPy reference.  Current
`max_diff = 0`.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `ModuleNotFoundError: No module named 'earphone'` when running pytest | Export `PYTHONPATH=$RTLCRAFT_ROOT` (see Step 2). |
| `iverilog` cannot find `generated/fft/twiddle_256_*.hex` | Ensure `earphone/tb/iverilog/generated` symlink points to `../../../generated`. |
| cocotb tests fail to import / cannot install cocotb | cocotb is not available in this environment; use the iverilog harness instead. |
| `design_earphone.py` fails with import errors | Run from the project root so the script can add it to `sys.path`. |
| iverilog warnings about time units | The design has no `timescale` directives; the warnings are cosmetic and simulation results are correct. |

---

## Where to Go Next

- Read [`design_spec.md`](design_spec.md) for requirements, architecture, and PPA targets.
- Read the generated review bundle in `earphone/specs/`.
- Pick a module under `earphone/modules/` and trace it from
  `layer_L1_behavior/src/behavior.py` → `layer_L5_dsl/src/dsl.py` →
  `earphone/verilog/earphone_*.v`.
- Try integrating an existing RTLCraft skill (e.g. UART from
  `skills/interfaces/uart`) as a new APB slave.
