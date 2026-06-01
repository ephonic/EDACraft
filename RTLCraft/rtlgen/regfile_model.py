"""
rtlgen.regfile_model — Parameterized register file with bypass/forwarding support.

Supports arbitrary register count, width, read/write ports, and physical
register file modeling (for out-of-order cores).

This is a cycle-accurate behavioral model for golden-reference simulation.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class RegisterFileModel:
    """Parameterized register file.

    Usage:
        rf = RegisterFileModel(num_regs=32, width=64, x0_is_zero=True)
        rf.write(1, 0x1234)
        val = rf.read(1)  # -> 0x1234

    For physical register files (out-of-order):
        rf = RegisterFileModel(num_regs=128, width=64, x0_is_zero=False)
    """

    def __init__(
        self,
        num_regs: int = 32,
        width: int = 64,
        x0_is_zero: bool = True,
        init_zero: bool = True,
        read_ports: int = 2,
        write_ports: int = 1,
    ):
        self.num_regs = num_regs
        self.width = width
        self.x0_is_zero = x0_is_zero
        self.read_ports = read_ports
        self.write_ports = write_ports
        self._mask = (1 << width) - 1

        if init_zero:
            self._regs = [0] * num_regs
        else:
            import random
            self._regs = [random.randint(0, self._mask) for _ in range(num_regs)]
            if x0_is_zero:
                self._regs[0] = 0

        # Forwarding/bypass tracking for multi-port read-after-write
        self._pending_writes: Dict[int, int] = {}  # reg_idx -> value (committed next cycle)
        self._forward_map: Dict[int, int] = {}     # reg_idx -> value (this cycle bypass)

        # For physical register files: free list and allocation tracking
        self._free_list: Set[int] = set()
        self._allocated: Set[int] = set()
        if num_regs > 32:
            # Assume first 32 are architectural, rest are physical
            for i in range(32, num_regs):
                self._free_list.add(i)

    # -----------------------------------------------------------------
    # Basic access
    # -----------------------------------------------------------------
    def read(self, idx: int, bypass: bool = True) -> int:
        """Read register `idx`. If bypass=True, check forwarding map first."""
        if idx == 0 and self.x0_is_zero:
            return 0
        if idx < 0 or idx >= self.num_regs:
            raise IndexError(f"Register index out of range: {idx} (num_regs={self.num_regs})")
        if bypass and idx in self._forward_map:
            return self._forward_map[idx] & self._mask
        return self._regs[idx] & self._mask

    def write(self, idx: int, value: int) -> None:
        """Write register `idx` immediately (combinational)."""
        if idx == 0 and self.x0_is_zero:
            return
        if idx < 0 or idx >= self.num_regs:
            raise IndexError(f"Register index out of range: {idx} (num_regs={self.num_regs})")
        self._regs[idx] = int(value) & self._mask

    def write_pending(self, idx: int, value: int) -> None:
        """Queue a write to be committed on next cycle boundary."""
        if idx == 0 and self.x0_is_zero:
            return
        self._pending_writes[idx] = int(value) & self._mask

    def set_forward(self, idx: int, value: int) -> None:
        """Set a bypass value for this cycle (for read-after-write forwarding)."""
        if idx == 0 and self.x0_is_zero:
            return
        self._forward_map[idx] = int(value) & self._mask

    def commit(self) -> None:
        """Commit all pending writes and clear forwarding map."""
        for idx, val in self._pending_writes.items():
            self._regs[idx] = val
        self._pending_writes.clear()
        self._forward_map.clear()

    # -----------------------------------------------------------------
    # Physical register file (for OoO)
    # -----------------------------------------------------------------
    def alloc_preg(self) -> int:
        """Allocate a free physical register. Returns reg index or -1 if none."""
        if not self._free_list:
            return -1
        idx = min(self._free_list)
        self._free_list.remove(idx)
        self._allocated.add(idx)
        return idx

    def free_preg(self, idx: int) -> None:
        """Free a physical register back to the free list."""
        if idx in self._allocated:
            self._allocated.remove(idx)
            self._free_list.add(idx)

    def rename(self, arch_idx: int, preg_idx: int) -> None:
        """Record a rename mapping (architectural -> physical)."""
        # Rename table is maintained externally; this just validates
        if preg_idx not in self._allocated:
            raise ValueError(f"Physical register {preg_idx} not allocated")

    # -----------------------------------------------------------------
    # Multi-port access
    # -----------------------------------------------------------------
    def read_multi(self, indices: List[int], bypass: bool = True) -> List[int]:
        """Read multiple registers at once."""
        return [self.read(i, bypass) for i in indices]

    def write_multi(self, writes: List[Tuple[int, int]]) -> None:
        """Write multiple registers at once."""
        for idx, val in writes:
            self.write(idx, val)

    # -----------------------------------------------------------------
    # Bulk operations
    # -----------------------------------------------------------------
    def get_state(self) -> List[int]:
        """Return full register file state."""
        return list(self._regs)

    def set_state(self, state: List[int]) -> None:
        """Set full register file state."""
        if len(state) != self.num_regs:
            raise ValueError(f"State size mismatch: {len(state)} vs {self.num_regs}")
        self._regs = [int(v) & self._mask for v in state]
        if self.x0_is_zero:
            self._regs[0] = 0

    def dump(self, highlight: Optional[Set[int]] = None) -> str:
        """Pretty-print register file state."""
        lines = [f"RegisterFile ({self.num_regs}x{self.width}bit):"]
        for i in range(self.num_regs):
            val = self._regs[i]
            marker = " *" if highlight and i in highlight else ""
            lines.append(f"  x{i:02d} = {val:#018x}{marker}")
        return "\n".join(lines)
