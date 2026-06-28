# Smart Earphone SoC — RTLCraft Spec2RTL Design

This directory contains a complete, end-to-end Spec2RTL design for a low-power
smart earphone chip. It uses RTLCraft's layered IR framework and produces
synthesizable Verilog together with cross-layer verification evidence. The
framework supports a full 6-layer vocabulary, but not every module must always
materialize every intermediate layer as a separately-authored artifact.

**Key reference**: [`design_spec.md`](design_spec.md) has the full requirements,
architecture, PPA targets, and roadmap.

---

## Directory Layout

```
earphone/
├── design_spec.md              # Full design specification
├── README.md                   # This file
├── Tutorial.md                 # Step-by-step getting-started guide
├── design_earphone.py          # Single-entry Spec2RTL flow
├── specs/                      # Generated review bundle (01-11)
│   ├── 01_spec_review.md
│   ├── 02_behavior_review.md
│   ├── ...
│   ├── 11_decision_log.md
│   └── flow_feedback.json      # Structured flow / approval feedback
├── modules/                    # Per-module layered decomposition (full 6-layer on complex IPs)
│   ├── rv32/
│   ├── simd16/
│   ├── fft256/
│   ├── qspi/
│   ├── i2c/
│   ├── sram256k/
│   ├── apb_bridge/
│   └── common/
├── twiddle/                    # FFT256 twiddle tables (.hex)
├── verilog/                    # Generated Verilog output
│   ├── earphone_rv32.v
│   ├── earphone_simd16.v
│   ├── earphone_fft256.v
│   ├── fft_controller_256.v
│   ├── earphone_qspi.v
│   ├── earphone_i2c.v
│   ├── earphone_sram256k.v
│   ├── earphone_apb_bridge.v
│   └── earphone_top.v
└── tb/                         # Testbench harnesses
    ├── iverilog/               # Working iverilog-based harness (6 targets)
    ├── verilog/                # Additional standalone Verilog testbenches
    ├── cocotb/                 # Auto-generated cocotb intent tests
    └── constraints/            # Generated SVA constraints / reports
```

---

## How to Run

**Prerequisites**

- Python 3.12+
- `numpy`
- `pytest` 7.4+
- `iverilog` 13.0 + `vvp`

**1. Full Spec2RTL flow**

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft
python earphone/design_earphone.py
```

This single command:

1. Propagates design constraints through the scaffold (compliance checklist).
2. Generates FFT256 twiddle tables.
3. Writes the review bundle (`specs/01_*.md .. 11_*.md`).
4. Runs Layer 1 functional tests.
5. Runs Layer 3 DSL simulation tests.
6. Runs cross-layer verification (`L1 == L2 == L3`).
7. Generates 9 Verilog modules and runs the Verilog linter.
8. Runs intent-driven tests and emits cocotb test skeletons.

**2. Refresh approval evidence without sign-off**

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft
python -m earphone.flow --module all --check --top-level
```

This check-mode flow regenerates per-module layered docs, emits structured
`*.json` sidecars for layer/module test plans and reports, refreshes top-level
review/scaffold evidence for `CP1_SOC`, and writes
`earphone/specs/flow_feedback.json` for upward feedback review.

**3. Module-level pytest suite**

`earphone` is not installed as a package, so pytest needs the project root on
`PYTHONPATH`:

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft pytest earphone/modules -q
```

The `EarphoneFFT256` L5 DSL wrapper imports the external FFT generator
`design_scripts.design_fft`. Local generated-UVM runtime checks skip only that
FFT256 case when the generator is not installed; when it is present, the real
wrapper is imported and exercised.

**4. iverilog cycle-accurate harness**

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft/earphone/tb/iverilog
make all
```

> Note: `fft_controller_256.v` uses `$readmemh("generated/...")`.  A symlink
> `earphone/tb/iverilog/generated -> ../../../generated` is provided so the
> top-level simulation finds the twiddle hex files.

---

## Design Highlights

| Module | Description | Source |
|--------|-------------|--------|
| `EarphoneRV32` | RV32IM 3-stage in-order core, iterative 32-cycle restoring divider | `modules/rv32/layer_L5_dsl/src/dsl.py` |
| `EarphoneSIMD16` | 16-lane INT16 ALU + 3-stage FP16 MAC, independent `int_ce`/`fp_ce` | `modules/simd16/layer_L5_dsl/src/dsl.py` |
| `EarphoneFFT256` | 256-point streaming radix-2² SDF FFT wrapper around `FFTController` | `modules/fft256/layer_L5_dsl/src/dsl.py` |
| `EarphoneQSPI` | QSPI XIP flash controller with idle clock gating | `modules/qspi/layer_L5_dsl/src/dsl.py` |
| `EarphoneI2C` | APB I2C master byte controller with idle clock gating | `modules/i2c/layer_L5_dsl/src/dsl.py` |
| `EarphoneSRAM256K` | 256 KB single-port SRAM with byte-write mask, APB slave | `modules/sram256k/layer_L5_dsl/src/dsl.py` |
| `EarphoneAPBBridge` | APB4 address decoder, 8 slave slots (4 MB each) | `modules/apb_bridge/layer_L5_dsl/src/dsl.py` |
| `EarphoneTop` | SoC integration: CPU, SIMD, FFT, QSPI, APB bridge → SRAM/I2C | `design_earphone.py` |

`EarphoneTop` exposes an external APB4 master port so the on-chip peripherals
(SRAM at slot 1, I2C at slot 4) can be exercised from a testbench without a
booted CPU.

---

## Verification Status

| Check | Result |
|-------|--------|
| Design scaffold compliance | 6/6 OK |
| Layer 1 functional tests | 4/4 PASS |
| Layer 3 DSL simulation tests | 4/4 PASS |
| Cross-layer verification | 8/8 PASS |
| Intent-driven tests | 4/4 PASS |
| Verilog module generation | 9/9 generated |
| Module pytest suite | 60/60 PASS |
| iverilog harness | 6/6 PASS |
| **Overall** | **PASS** |

**Generated Verilog**

| File | Lines | Lint issues |
|------|------:|------------:|
| `earphone_rv32.v` | 391 | 14 |
| `earphone_simd16.v` | 112 | 2 |
| `earphone_fft256.v` | 47 | 1 |
| `fft_controller_256.v` | 1,188 | 8 |
| `earphone_qspi.v` | 114 | 1 |
| `earphone_i2c.v` | 178 | 4 |
| `earphone_sram256k.v` | 77 | 3 |
| `earphone_apb_bridge.v` | 96 | 1 |
| `earphone_top.v` | 242 | 1 |
| **Total** | **2,445** | **35** |

Lint issues are non-blocking style/simulation warnings (e.g. `iverilog` time-unit
warnings, register-array sensitivity notes); all modules compile and simulate
cleanly.

---

## iverilog Test Harness

Because `cocotb` cannot currently be installed in this environment (SSL/TLS EOF
errors), module-level cycle-accurate verification is performed with `iverilog`:

| Target | Testbench | Coverage |
|--------|-----------|----------|
| `simd16` | `tb_earphone_simd16.v` | INT16 vadd, vsub |
| `sram` | `tb_earphone_sram256k.v` | APB write/read |
| `apb_bridge` | `tb_earphone_apb_bridge.v` | Slave decode, invalid address |
| `qspi` | `tb_earphone_qspi.v` | XIP 32-bit read |
| `i2c` | `tb_earphone_i2c.v` | Master write sequence |
| `top` | `tb_earphone_top.v` | Reset, APB SRAM, APB I2C, invalid region |

Run a single target with `make <target>` (e.g. `make qspi`) or `make all`.

---

## PPA Improvements

Following the 6-layer IR methodology, the following low-power / area decisions
are modeled in the DSL and preserved in Verilog:

1. **RV32IM divider area**: 32-cycle iterative restoring divider for
   `DIV`/`DIVU`/`REM`/`REMU` instead of a combinational divider.
2. **CPU dynamic power**: Pipeline registers are clock-gated by `core_clk_en`
   during memory/divide stalls.
3. **Multiplier operand isolation**: RV32M product terms are forced to zero when
   no M-extension instruction is in flight.
4. **SIMD clock gating**: Independent `int_ce` and `fp_ce` enables; the FP16 MAC
   pipeline advances only when occupied.
5. **SRAM clock gating**: Memory array and read-data register update only on
   active APB transfers (`sram_ce = psel & penable`).
6. **Peripheral idle gating**: QSPI and I2C state-machine registers are gated
   when the bus is idle.

---

## Known Limitations

- **FP16 MAC**: Approximated as integer multiply-add; a full IEEE-754 FP16
  add/mul implementation is deferred to a future revision.
- **BTLE PHY / UART / SPI / I2S**: Not yet instantiated in `EarphoneTop`.  The
  APB bridge infrastructure is in place; existing skills (`skills.interfaces.*`,
  `skills.dsp.*`) can be wrapped as APB slaves.
- **Power domains / retention**: Clock gating is modeled; power-domain
  controllers and retention flops are not.
- **cocotb**: Not available in this environment; verification uses iverilog.

---

## Next Steps

1. Run the RISC-V compliance suite (`rv32ui-p`, `rv32um-p`) on the generated
   `earphone_rv32.v`.
2. Wrap and integrate `BTLE_PHY`, UART, SPI, and I2S as APB peripherals.
3. Add clock/reset/POR and power-domain controller with retention cells.
4. Close remaining linter warnings and run synthesis feedback (Yosys/ABC) to
   quantify area and power savings.

---

## See Also

- [`Tutorial.md`](Tutorial.md) — step-by-step walkthrough and module anatomy.
- [`design_spec.md`](design_spec.md) — requirements, architecture, and roadmap.
