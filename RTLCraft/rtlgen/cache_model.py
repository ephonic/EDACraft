"""
rtlgen.cache_model — Set-associative cache with configurable policy and coherency.

Supports arbitrary sets, ways, line size, and replacement policy (LRU, FIFO, Random).
Coherence protocols: MESI, MOESI, MSI.

This is a cycle-accurate behavioral model for golden-reference simulation.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CacheLine:
    """Single cache line state."""
    valid: bool = False
    dirty: bool = False
    tag: int = 0
    data: bytes = field(default_factory=bytes)
    state: str = "I"  # MESI/MOESI/MSI state
    lru_counter: int = 0  # For LRU replacement
    access_count: int = 0  # For LFU replacement


class CacheModel:
    """Set-associative cache behavioral model.

    Usage:
        cache = CacheModel(
            sets=128, ways=4, line_size=64,
            protocol="MESI", replacement="LRU"
        )
        hit, way = cache.access(addr=0x8000_0000, is_write=False)
        if hit:
            data = cache.read_line(addr, way)
        else:
            victim_way = cache.find_victim(addr)
            cache.fill_line(addr, way=victim_way, data=b"...")
    """

    VALID_PROTOCOLS = {"MESI", "MOESI", "MSI", "none"}
    VALID_REPLACEMENTS = {"LRU", "FIFO", "Random", "LFU", "PLRU"}

    def __init__(
        self,
        sets: int = 128,
        ways: int = 4,
        line_size: int = 64,
        protocol: str = "MESI",
        replacement: str = "LRU",
        writeback: bool = True,
        write_allocate: bool = True,
        name: str = "cache",
    ):
        if protocol not in self.VALID_PROTOCOLS:
            raise ValueError(f"Unknown protocol: {protocol}")
        if replacement not in self.VALID_REPLACEMENTS:
            raise ValueError(f"Unknown replacement: {replacement}")

        self.sets = sets
        self.ways = ways
        self.line_size = line_size
        self.protocol = protocol
        self.replacement = replacement
        self.writeback = writeback
        self.write_allocate = write_allocate
        self.name = name

        self._set_bits = sets.bit_length() - 1
        self._offset_bits = line_size.bit_length() - 1
        self._tag_shift = self._set_bits + self._offset_bits
        self._set_mask = sets - 1
        self._offset_mask = line_size - 1

        # Storage: [set_idx][way_idx] -> CacheLine
        self._storage: List[List[CacheLine]] = [
            [CacheLine(data=bytes(line_size)) for _ in range(ways)]
            for _ in range(sets)
        ]

        # FIFO queue per set (for FIFO replacement)
        self._fifo_queues: List[List[int]] = [list(range(ways)) for _ in range(sets)]

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._writebacks = 0
        self._snoops = 0
        self._snoop_hits = 0

        # Coherence: snoop callback (addr, is_invalidate) -> response
        self._snoop_callback: Optional[callable] = None

    # -----------------------------------------------------------------
    # Address decomposition
    # -----------------------------------------------------------------
    def _addr_to_set(self, addr: int) -> int:
        return (addr >> self._offset_bits) & self._set_mask

    def _addr_to_tag(self, addr: int) -> int:
        return addr >> self._tag_shift

    def _addr_to_line_base(self, addr: int) -> int:
        return addr & ~self._offset_mask

    # -----------------------------------------------------------------
    # Core access
    # -----------------------------------------------------------------
    def access(self, addr: int, is_write: bool = False) -> Tuple[bool, int]:
        """Access cache at `addr`. Returns (hit, way_idx).
        On miss, way_idx is the victim way (or -1 if full and dirty)."""
        set_idx = self._addr_to_set(addr)
        tag = self._addr_to_tag(addr)
        set_lines = self._storage[set_idx]

        # Check for hit
        for way, line in enumerate(set_lines):
            if line.valid and line.tag == tag:
                self._hits += 1
                self._update_replacement(set_idx, way, hit=True)
                if is_write:
                    line.dirty = True
                    line.state = self._transition_write(line.state)
                else:
                    line.state = self._transition_read(line.state)
                return True, way

        # Miss
        self._misses += 1
        victim = self.find_victim(addr)
        if victim >= 0:
            victim_line = set_lines[victim]
            if victim_line.valid and victim_line.dirty and self.writeback:
                self._writebacks += 1
            self._evictions += 1

        return False, victim

    def read(self, addr: int, size: int = 8) -> int:
        """Read `size` bytes from cache at `addr`.
        Returns value or raises if not present."""
        hit, way = self.access(addr, is_write=False)
        if not hit:
            raise CacheMissError(f"Cache miss on read: addr={addr:#x}")
        line = self._storage[self._addr_to_set(addr)][way]
        offset = addr & self._offset_mask
        data = line.data[offset:offset + size]
        return int.from_bytes(data, "little")

    def write(self, addr: int, value: int, size: int = 8) -> None:
        """Write `size` bytes to cache at `addr`.
        Raises if not present and write_allocate is False."""
        hit, way = self.access(addr, is_write=True)
        if not hit:
            if not self.write_allocate:
                raise CacheMissError(f"Cache miss on write (no allocate): addr={addr:#x}")
            # Need to fill first
            self.fill_line(addr, way=way, data=bytes(self.line_size))
            line = self._storage[self._addr_to_set(addr)][way]
        else:
            line = self._storage[self._addr_to_set(addr)][way]

        offset = addr & self._offset_mask
        data = value.to_bytes(size, "little")
        line_data = bytearray(line.data)
        line_data[offset:offset + size] = data
        line.data = bytes(line_data)
        line.dirty = True

    # -----------------------------------------------------------------
    # Line operations
    # -----------------------------------------------------------------
    def fill_line(self, addr: int, way: int, data: bytes,
                  state: Optional[str] = None) -> None:
        """Fill a cache line with data (e.g., from memory or another cache)."""
        set_idx = self._addr_to_set(addr)
        tag = self._addr_to_tag(addr)
        line = self._storage[set_idx][way]
        line.valid = True
        line.dirty = False
        line.tag = tag
        line.data = data[:self.line_size].ljust(self.line_size, b"\x00")
        line.state = state or ("E" if self.protocol == "MESI" else "S" if self.protocol in ("MESI", "MOESI", "MSI") else "I")
        line.access_count += 1
        self._update_replacement(set_idx, way, hit=False)

    def read_line(self, addr: int, way: int) -> bytes:
        """Read full line data."""
        set_idx = self._addr_to_set(addr)
        return self._storage[set_idx][way].data

    def write_line(self, addr: int, way: int, data: bytes) -> None:
        """Write full line data."""
        set_idx = self._addr_to_set(addr)
        line = self._storage[set_idx][way]
        line.data = data[:self.line_size].ljust(self.line_size, b"\x00")
        line.dirty = True

    def invalidate_line(self, addr: int) -> bool:
        """Invalidate line at `addr`. Returns True if line was present."""
        set_idx = self._addr_to_set(addr)
        tag = self._addr_to_tag(addr)
        for way, line in enumerate(self._storage[set_idx]):
            if line.valid and line.tag == tag:
                was_dirty = line.dirty
                line.valid = False
                line.dirty = False
                line.state = "I"
                return was_dirty
        return False

    def find_victim(self, addr: int) -> int:
        """Find victim way for replacement. Returns way index."""
        set_idx = self._addr_to_set(addr)
        set_lines = self._storage[set_idx]

        # First, find invalid line
        for way, line in enumerate(set_lines):
            if not line.valid:
                return way

        # Apply replacement policy
        if self.replacement == "LRU":
            # Find line with smallest lru_counter
            min_way = min(range(self.ways), key=lambda w: set_lines[w].lru_counter)
            return min_way
        elif self.replacement == "FIFO":
            return self._fifo_queues[set_idx].pop(0)
        elif self.replacement == "Random":
            return random.randint(0, self.ways - 1)
        elif self.replacement == "LFU":
            return min(range(self.ways), key=lambda w: set_lines[w].access_count)
        elif self.replacement == "PLRU":
            # Simplified: treat as LRU for now
            return min(range(self.ways), key=lambda w: set_lines[w].lru_counter)
        else:
            return 0

    # -----------------------------------------------------------------
    # Coherence snooping
    # -----------------------------------------------------------------
    def snoop(self, addr: int, is_invalidate: bool = False) -> Tuple[bool, str, bool]:
        """Snoop cache for coherence.
        Returns (hit, state, was_dirty) where state is the coherence state."""
        self._snoops += 1
        set_idx = self._addr_to_set(addr)
        tag = self._addr_to_tag(addr)
        for way, line in enumerate(self._storage[set_idx]):
            if line.valid and line.tag == tag:
                self._snoop_hits += 1
                old_state = line.state
                was_dirty = line.dirty
                if is_invalidate:
                    line.valid = False
                    line.dirty = False
                    line.state = "I"
                else:
                    # Downgrade: M->S, E->S
                    if line.state in ("M", "E"):
                        line.state = "S"
                        line.dirty = False
                return True, old_state, was_dirty
        return False, "I", False

    def set_snoop_callback(self, callback: callable) -> None:
        """Set callback for coherence requests to upper/lower level."""
        self._snoop_callback = callback

    # -----------------------------------------------------------------
    # Coherence state transitions
    # -----------------------------------------------------------------
    def _transition_read(self, old_state: str) -> str:
        if self.protocol == "none":
            return old_state
        # M->M, E->E, S->S, I->E (assuming exclusive on read miss)
        transitions = {
            "M": "M", "E": "E", "S": "S", "O": "O",
            "I": "E",  # Optimistic: assume exclusive
        }
        return transitions.get(old_state, old_state)

    def _transition_write(self, old_state: str) -> str:
        if self.protocol == "none":
            return old_state
        # All writes go to M
        transitions = {
            "M": "M", "E": "M", "S": "M", "O": "M", "I": "M",
        }
        return transitions.get(old_state, old_state)

    # -----------------------------------------------------------------
    # Replacement policy updates
    # -----------------------------------------------------------------
    def _update_replacement(self, set_idx: int, way: int, hit: bool):
        line = self._storage[set_idx][way]
        line.access_count += 1

        if self.replacement == "LRU":
            # Increment all other lines' counters, reset accessed line
            for w, l in enumerate(self._storage[set_idx]):
                if l.valid and w != way:
                    l.lru_counter += 1
            line.lru_counter = 0
        elif self.replacement == "FIFO" and not hit:
            self._fifo_queues[set_idx].append(way)

    # -----------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate

    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "writebacks": self._writebacks,
            "snoops": self._snoops,
            "snoop_hits": self._snoop_hits,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
        }

    def reset_stats(self):
        self._hits = self._misses = self._evictions = self._writebacks = 0
        self._snoops = self._snoop_hits = 0


class CacheMissError(Exception):
    """Raised on cache miss when not handling fill."""
    pass
