"""L2 CycleIR model for the EarphoneRV32 core.

This layer provides a cycle-accurate reference model of the RV32IM pipeline.
It is kept aligned with the L1 BehaviorIR golden model and is used to validate
that the L5 DSL implementation matches the intended cycle-level behavior.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from earphone.modules.rv32.layer_L1_behavior.src.behavior import RV32IM_ISS, RV32IMState


class RV32CycleState:
    """Cycle-level state snapshot used by the L2 model."""

    def __init__(self):
        self.iss_state = RV32IMState()
        self.cycle: int = 0
        self.stall: bool = False
        self.flush: bool = False


class RV32IMCycleModel:
    """Cycle-accurate wrapper around the L1 ISS.

    For the current EarphoneRV32 implementation the core is single-cycle
    (apart from multi-cycle M-extension operations).  This model therefore
    tracks pipeline control signals while delegating functional execution to
    the L1 ISS.
    """

    def __init__(self):
        self.state = RV32CycleState()
        self._iss = RV32IM_ISS()
        self._mem_trace: List[Dict] = []

    def reset(self, pc: int = 0x1000) -> None:
        """Reset the cycle model."""
        self._iss.reset(pc)
        self.state.cycle = 0
        self.state.stall = False
        self.state.flush = False
        self._mem_trace.clear()

    def load_program_words(self, words: List[int], entry_point: int = 0x1000) -> None:
        """Load a program into the model memory."""
        self._iss.load_program_words(words, entry_point)

    def step(self) -> Optional[str]:
        """Advance one clock cycle.

        Returns the retired instruction mnemonic, or None if the model is
        stalled or halted.
        """
        if self.state.stall or self._iss.state.halted:
            self.state.cycle += 1
            return None
        mnemonic = self._iss.step()
        self.state.cycle += 1
        return mnemonic

    def run(self, max_cycles: int = 10000) -> int:
        """Run until halt or max_cycles.  Returns the number of cycles."""
        for _ in range(max_cycles):
            if self._iss.state.halted:
                break
            self.step()
        return self.state.cycle
