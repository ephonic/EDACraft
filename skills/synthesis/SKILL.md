# synthesis — Logic Synthesis & Technology Mapping

## Overview

This directory contains the **ABC-based synthesis flow** integrated into rtlgen. It converts RTL IR (via BLIF) into technology-mapped netlists using Berkeley ABC, providing area, delay, gate count, and logic depth metrics.

## Files

| File | Description |
|------|-------------|
| `synth.py` | Reference copy of `rtlgen/synth.py` (`ABCSynthesizer`, `SynthResult`, `WireLoadModel`) |

## Architecture

```
RTL IR ──► BLIF ──► ABC read_blif ──► strash (AIG)
                                          │
                                          ▼
                              resyn2 (balance/rewrite/refactor)
                                          │
                              read_liberty tech.lib
                                          │
                                    map (technology mapping)
                                          │
                              write_verilog mapped.v
```

## Quick Start

### Basic Synthesis

```python
from rtlgen import VerilogEmitter
from rtlgen.synth import ABCSynthesizer, SynthResult

text = VerilogEmitter().emit_design(top)
# Save to BLIF via rtlgen.blifgen
# ... (see test_abc_synthesis for full flow)

synth = ABCSynthesizer()
result = synth.run(
    input_blif="design.blif",
    liberty="gf65.lib",
    output_verilog="mapped.v",
    optimization="resyn2",
)

print(f"Area = {result.area} um^2")
print(f"Delay = {result.delay} ns")
print(f"Gates = {result.gates}")
print(f"Depth = {result.depth}")
```

### Wire Load Model

ABC's mapped delay does not include interconnect. Use `WireLoadModel` for post-mapping wire delay estimation:

```python
from rtlgen.synth import WireLoadModel

wlm = WireLoadModel(name="gf65_wlm", slope=0.05, intercept=0.01)
wire_delay = wlm.estimate_delay(fanout=4)
# total_delay = abc_delay + wire_delay
```

### Optimization Strategies

| Strategy | ABC Command | Use Case |
|----------|-------------|----------|
| `resyn2` | `balance; rewrite; refactor; balance; rewrite -z; refactor -z; rewrite -z; balance` | General-purpose, good area/delay trade-off |
| `resyn` | `balance; rewrite; refactor; balance; rewrite` | Faster, slightly less optimized |
| `compress2` | `balance; rewrite -l; refactor -l; balance; rewrite -l; rewrite -z -l; balance` | Aggressive area reduction |

Pass `optimization="resyn2"` (default) or any supported ABC alias to `ABCSynthesizer.run()`.

### Gate Sizing

After technology mapping, you can optionally run gate sizing:

```python
result = synth.run(
    input_blif="design.blif",
    liberty="gf65.lib",
    upsize=True,   # upsize gates on critical path
    dnsize=False,  # don't downsize non-critical gates
)
```

## ABC Installation

If ABC is not found in `PATH`, `ABCSynthesizer.run()` will generate a `run_abc.sh` script and raise a helpful error:

```bash
# macOS / Linux
git clone https://github.com/berkeley-abc/abc.git
cd abc
make -j$(nproc)
sudo cp abc /usr/local/bin/
```

## Reference: `SynthResult`

```python
@dataclass
class SynthResult:
    area: float           # um^2 (from liberty units)
    delay: float          # ns (critical path)
    gates: int            # number of gates (nd)
    depth: int            # logic levels (lev)
    stdout: str           # ABC full stdout
    stderr: str           # ABC stderr
    mapped_verilog: Optional[str] = None  # mapped netlist content
```

## Integration with Tests

The rtlgen test suite uses synthesis to verify that generated designs are synthesizable:

```python
def test_abc_synthesis():
    from rtlgen import VerilogEmitter, BLIFEmitter
    from rtlgen.synth import ABCSynthesizer

    top = MontgomeryMult384()
    blif_text = BLIFEmitter().emit_design(top)
    # ... write to file, run ABC ...
    assert result.area > 0
    assert result.delay > 0
```

## See Also

- `../physical-design/SKILL.md` — Placement, routing, and physical signoff
- `rtlgen/blifgen.py` — BLIF emission from rtlgen IR
- `rtlgen/ppa.py` — Power/Performance/Area analysis helpers
