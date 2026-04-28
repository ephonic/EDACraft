# verification — Debug, Testbench & Simulation

## Overview

Tools and reference testbenches for verifying rtlgen designs through cycle-accurate Python simulation, VCD dumping, and hierarchical signal probing.

## Sub-directories

### `debug/` — Debugging Utilities

| File | Description |
|------|-------------|
| `debug_montgomery.py` | Example of tracing `MontgomeryMult384` pipeline events with `DebugProbe` |

**Key Tool — `DebugProbe`:**

```python
from rtlgen.pipeline import DebugProbe

probe = DebugProbe(sim)
probe.get("o_valid")                          # top-level signal
probe.get("qm2", path="u_r0")                # submodule signal
probe.find_subsim("u_r0")                     # fuzzy submodule search
probe.print_all(["valid_in","out_valid"], path_prefix="u_r0")
```

## Simulation Checklist

1. **Reset**: `sim.reset('rst_n')` — holds rst_n low for a few cycles then releases
2. **Drive inputs**: `sim.set("X", value)` before `sim.step()`
3. **Check outputs**: `sim.get("Z")` after `sim.step()`
4. **Dump VCD**: `sim.to_vcd("wave.vcd")` for GTKWave visualization
5. **Hierarchical probe**: Use `DebugProbe` to peek inside submodules without flattening logic

## Testing Philosophy

- **Directed tests**: Small set of known vectors to catch obvious bugs
- **Random tests**: `random.randint()` with reference model comparison
- **Back-to-back tests**: Verify throughput = 1 result/cycle with consecutive inputs
- **Lint tests**: `VerilogEmitter.emit_with_lint()` to catch implicit wires

## See Also

- `../fundamentals/tutorials/` — `sim_*.py` demo files
- `rtlgen/pipeline.py` — `ShiftReg`, `ValidPipe`, `DebugProbe`
