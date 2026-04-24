# control — Control Logic, FSM & Scheduling

## Overview

Control-centric designs: state machines, counters, schedulers, and pipeline control logic. These modules typically manage datapath flow rather than perform arithmetic themselves.

## Sub-directories

### `fsm/` — Finite State Machines

| File | Description |
|------|-------------|
| `fsm_traffic.py` | Traffic-light FSM using `rtlgen.lib.FSM` |
| `fsmm.py` | Finite-State-Machine Matrix Multiplication |
| `fsmm_benchmark.py` | FSMM performance benchmark |
| `fsmm_ppa_feedback.py` | FSMM PPA (Power/Performance/Area) feedback analysis |

**Key Patterns:**
- `FSM` class with `@fsm.state` decorator for declarative state behavior
- `FSMStateContext` for per-state outputs and conditional transitions (`ctx.goto`)
- `fsm.build(clk, rst, parent=self)` to embed into a parent module

## Design Patterns

### Declarative FSM

```python
from rtlgen import FSM

fsm = FSM("IDLE", name="traffic")
fsm.add_output("red", width=1, default=0)
fsm.add_output("green", width=1, default=0)

@fsm.state("IDLE")
def idle(ctx):
    ctx.red = 1
    ctx.goto("RUN", when=start)

fsm.build(clk=self.clk, reset=self.rst, parent=self)
```

### Counter with Load/Enable

See `fundamentals/tutorials/counter.py` for a basic implementation.

## See Also

- `../fundamentals/SKILL.md` — Standard library (`FSM`, `RoundRobinArbiter`)
- `../arithmetic/SKILL.md` — Datapath designs that these FSMs control
