"""
rtlgen.mem_timing — Memory Timing Utilities

JEDEC-standard timing constants for DDR3/DDR4/LPDDR5/HBM.
Convert ns timing constraints to clock cycles at a given MHz.
"""
from __future__ import annotations

from typing import Dict


def ns_to_cycles(time_ns: float, mhz: int) -> int:
    """Convert nanoseconds to clock cycles at given MHz.

    Example: tRCD=15ns at 100MHz → 2 cycles
    """
    if mhz <= 0:
        return max(1, int(time_ns))
    cycle_time_ns = 1000.0 / mhz
    return max(1, int((time_ns + (cycle_time_ns - 0.001)) // cycle_time_ns))


# =====================================================================
# DDR3 Timing Database (JEDEC Standard)
# =====================================================================

_DDR3_TIMINGS: Dict[str, Dict[str, float]] = {
    "DDR3-800":  {"tRCD": 13.75, "tRP": 13.75, "tRFC": 260,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 35, "tRC": 48.75,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
    "DDR3-1066": {"tRCD": 13.125, "tRP": 13.125, "tRFC": 260,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 35, "tRC": 48.125,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
    "DDR3-1333": {"tRCD": 13.5, "tRP": 13.5, "tRFC": 260,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 35, "tRC": 48.5,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
    "DDR3-1600": {"tRCD": 13.75, "tRP": 13.75, "tRFC": 260,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 35, "tRC": 48.75,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
    "DDR3-1866": {"tRCD": 14.0, "tRP": 14.0, "tRFC": 350,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 34, "tRC": 48,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
    "DDR3-2133": {"tRCD": 14.0, "tRP": 14.0, "tRFC": 350,
                  "tWTR": 7.5, "tFAW": 37.5, "tRAS": 33, "tRC": 47,
                  "tRRD": 10.0, "tWR": 15.0, "tRTP": 7.5},
}


class DDR3Timing:
    """DDR3 timing constants from JEDEC standard.

    Usage:
        timing = DDR3Timing("DDR3-800")
        cycles = timing.to_cycles(mhz=100)
        # → {'tRCD': 2, 'tRP': 2, 'tRFC': 26, ...}
    """

    def __init__(self, speed_bin: str = "DDR3-800"):
        if speed_bin not in _DDR3_TIMINGS:
            raise ValueError(f"Unknown DDR3 speed bin: {speed_bin}. "
                             f"Available: {list(_DDR3_TIMINGS.keys())}")
        self.speed_bin = speed_bin
        self._timings_ns = _DDR3_TIMINGS[speed_bin]

    def to_cycles(self, mhz: int) -> Dict[str, int]:
        """Convert all timing params to cycles at given MHz."""
        return {k: ns_to_cycles(v, mhz) for k, v in self._timings_ns.items()}

    def get(self, name: str, mhz: int = 100) -> int:
        """Get a single timing parameter in cycles."""
        if name not in self._timings_ns:
            return 0
        return ns_to_cycles(self._timings_ns[name], mhz)

    @property
    def refresh_interval_us(self) -> float:
        """64ms / 8192 rows = 7.8125 µs average refresh interval."""
        return 7.8125

    @property
    def all_timings_ns(self) -> Dict[str, float]:
        """Return all timing parameters in nanoseconds."""
        return dict(self._timings_ns)
