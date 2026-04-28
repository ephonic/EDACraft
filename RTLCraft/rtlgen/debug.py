"""rtlgen.debug — Debugging and tracing utilities for the rtlgen simulator.

Provides convenient helpers for inspecting signal values, tracing state
machine transitions, and dumping hierarchical state without fighting the
JIT/AST abstraction layers.

Examples:
    from rtlgen.debug import SignalTracer, probe_submodule

    tracer = SignalTracer(sim)
    tracer.track("npu.state", "adapter.state", "adapter.rd_ptr")
    tracer.run(100)
    tracer.report()

    probe_submodule(sim, npu.systolic_adapter)
"""

from typing import Any, Dict, List, Optional, Union
from collections import defaultdict


class SignalTracer:
    """Trace a set of signals across clock cycles."""

    def __init__(self, sim: Any):
        self.sim = sim
        self.tracked: List[str] = []
        self.history: Dict[str, List[int]] = defaultdict(list)
        self._cycle = 0

    def track(self, *names: str):
        """Add hierarchical signal names to the trace list."""
        self.tracked.extend(names)
        return self

    def track_signals(self, *signals: Any):
        """Add Signal objects to the trace list (auto-resolves hierarchy)."""
        for sig in signals:
            name = self.sim._hier_name(sig)
            self.tracked.append(name)
        return self

    def sample(self):
        """Record current values of all tracked signals."""
        for name in self.tracked:
            try:
                val = self.sim.peek(name)
            except Exception:
                val = "X"
            self.history[name].append(int(val) if val != "X" else val)
        self._cycle += 1

    def run(self, cycles: int):
        """Advance simulation for N cycles and record each step."""
        for _ in range(cycles):
            self.sample()
            self.sim.step()

    def report(self, max_rows: int = 50):
        """Print a formatted table of traced values."""
        if not self.tracked:
            print("No signals tracked.")
            return

        names = self.tracked
        n = min(self._cycle, max_rows)

        # Header
        header = f"{'cycle':>6} | " + " | ".join(f"{name:>20}" for name in names)
        print(header)
        print("-" * len(header))

        for cyc in range(n):
            row = f"{cyc:>6} | " + " | ".join(
                f"{self.history[name][cyc]:>20}" for name in names
            )
            print(row)

        if self._cycle > max_rows:
            print(f"... ({self._cycle - max_rows} more cycles)")


class FSMTracer:
    """Trace state-machine transitions for a single state signal."""

    def __init__(self, sim: Any, state_name: str):
        self.sim = sim
        self.state_name = state_name
        self.transitions: List[tuple] = []
        self._prev = None
        self._cycle = 0

    def sample(self):
        """Check for a transition and record it."""
        val = int(self.sim.peek(self.state_name))
        if self._prev is not None and val != self._prev:
            self.transitions.append((self._cycle, self._prev, val))
        self._prev = val
        self._cycle += 1

    def run(self, cycles: int):
        """Advance simulation and watch for transitions."""
        for _ in range(cycles):
            self.sample()
            self.sim.step()

    def report(self):
        """Print all recorded transitions."""
        print(f"FSM transitions for '{self.state_name}':")
        if not self.transitions:
            print("  (no transitions observed)")
            return
        for cyc, fr, to in self.transitions:
            print(f"  cycle {cyc:>4}: {fr} -> {to}")


def probe_submodule(sim: Any, submodule: Any, prefix: str = ""):
    """Print every signal inside a submodule instance.

    Args:
        sim: Simulator instance
        submodule: the Module instance (e.g. npu.systolic_adapter)
        prefix: optional prefix printed before each line
    """
    inst_name = prefix or submodule.name
    print(f"\n--- probe: {inst_name} ---")

    for attr in ("_inputs", "_outputs", "_wires", "_regs"):
        d = getattr(submodule, attr, {})
        if not d:
            continue
        print(f"  [{attr}]")
        for name, sig in sorted(d.items()):
            hier = sim._hier_name(sig)
            try:
                val = sim.peek(hier)
            except Exception:
                val = "?"
            print(f"    {name:>20} = {val}")


def dump_memory(sim: Any, mem_name: str, start: int = 0, count: int = 16):
    """Print a slice of a JIT memory by hierarchical name."""
    if sim._jit is None:
        print("JIT not available; cannot dump memory directly.")
        return

    idx = sim._jit.mem_idx.get(mem_name)
    if idx is None:
        print(f"Memory '{mem_name}' not found in JIT.")
        return

    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    print(f"Memory '{mem_name}' (width={width}):")
    for addr in range(start, min(start + count, len(mem))):
        print(f"  [{addr:>4}] = {mem[addr] & mask}")


def compare_ast_vs_jit(sim: Any, signal: Any) -> Optional[tuple]:
    """Return (jit_val, ast_val) for a signal, useful when debugging
    JIT/AST divergence.  Requires JIT to be enabled."""
    if sim._jit is None:
        print("JIT not enabled.")
        return None

    name = sim._hier_name(signal)
    jit_val = sim._jit.get(name)

    # AST fallback: read from self.state dict
    ast_val = sim.state.get(name, 0)
    return int(jit_val), int(ast_val)
