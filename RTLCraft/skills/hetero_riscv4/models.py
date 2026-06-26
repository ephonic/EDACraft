"""
skills.hetero_riscv4.models — Heterogeneous 4-Core SoC Behavioral Models

Models for heterogeneous 4-core RISC-V SoC:
  - PerfCoreModel: Performance core (5-stage) IPC model
  - EffCoreModel: Efficiency core (3-stage) IPC model
  - L1CacheModel: L1 cache hit/miss model
  - CoherenceDirModel: MSI directory tracking for 4 cores
  - ClusterModel: Per-cluster behavioral model
  - HeteroSoCModel: Full 2x2 mesh SoC model
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Coherence states
STATE_I = 0  # Invalid
STATE_S = 1  # Shared
STATE_M = 2  # Modified


@dataclass
class CacheLine:
    """Single cache line state."""
    tag: int = 0
    state: int = STATE_I
    valid: bool = False
    lru_counter: int = 0


@dataclass
class DirectoryEntry:
    """Directory entry for a cache line."""
    tag: int = 0
    state: int = STATE_I
    sharers: int = 0  # 4-bit bitmask for 4 cores
    owner: int = -1
    valid: bool = False


@dataclass
class PerfCoreModel:
    """Performance core (5-stage) behavioral model."""
    core_id: int = 0
    pc: int = 0x1000
    retire_count: int = 0
    stall_cycles: int = 0
    l1i_hits: int = 0
    l1i_misses: int = 0
    l1d_hits: int = 0
    l1d_misses: int = 0
    instructions: int = 0

    def step(self, l1i_hit: bool = True, l1d_hit: bool = True) -> Dict[str, Any]:
        if l1i_hit:
            self.l1i_hits += 1
            self.instructions += 1
            self.pc += 4
            self.retire_count += 1
        else:
            self.l1i_misses += 1
            self.stall_cycles += 1
        if not l1d_hit:
            self.l1d_misses += 1
        else:
            self.l1d_hits += 1
        return {
            "pc": self.pc,
            "retired": l1i_hit,
            "stalled": not l1i_hit,
        }


@dataclass
class EffCoreModel:
    """Efficiency core (3-stage) behavioral model."""
    core_id: int = 0
    pc: int = 0x2000
    retire_count: int = 0
    stall_cycles: int = 0
    l1i_hits: int = 0
    l1i_misses: int = 0
    l1d_hits: int = 0
    l1d_misses: int = 0
    instructions: int = 0

    def step(self, l1i_hit: bool = True, l1d_hit: bool = True) -> Dict[str, Any]:
        if l1i_hit:
            self.l1i_hits += 1
            self.instructions += 1
            self.pc += 4
            self.retire_count += 1
        else:
            self.l1i_misses += 1
            self.stall_cycles += 1
        if not l1d_hit:
            self.l1d_misses += 1
        else:
            self.l1d_hits += 1
        return {
            "pc": self.pc,
            "retired": l1i_hit,
            "stalled": not l1i_hit,
        }


@dataclass
class L1CacheModel:
    """L1 cache behavioral model."""
    cache_id: str = ""
    ways: int = 4
    sets: int = 64
    line_size: int = 64
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    lines: Dict[int, CacheLine] = field(default_factory=dict)

    def lookup(self, addr: int) -> bool:
        tag = addr >> 12
        set_idx = (addr >> 6) & 0x3F
        key = (set_idx, tag)
        if key in self.lines and self.lines[key].valid:
            self.hits += 1
            return True
        self.misses += 1
        return False

    def fill(self, addr: int):
        tag = addr >> 12
        set_idx = (addr >> 6) & 0x3F
        key = (set_idx, tag)
        self.lines[key] = CacheLine(tag=tag, state=STATE_S, valid=True)


@dataclass
class CoherenceDirModel:
    """Directory-based MSI coherence tracker for 4 cores."""
    entries: Dict[int, DirectoryEntry] = field(default_factory=dict)
    invalidations: int = 0

    def lookup(self, addr: int):
        tag = addr >> 12
        entry = self.entries.get(tag)
        if entry and entry.valid:
            return entry.state, entry.sharers, entry.owner
        return STATE_I, 0, -1

    def request(self, core_id: int, addr: int, req_state: int) -> int:
        tag = addr >> 12
        entry = self.entries.get(tag)
        if entry is None or not entry.valid:
            self.entries[tag] = DirectoryEntry(
                tag=tag, state=STATE_S, sharers=(1 << core_id), owner=core_id, valid=True,
            )
            return STATE_S

        if req_state == STATE_M:
            if entry.state == STATE_M and entry.owner != core_id:
                self.invalidations += 1
                entry.owner = core_id
                entry.sharers = 1 << core_id
            else:
                entry.owner = core_id
                entry.state = STATE_M
                entry.sharers = 1 << core_id
            return STATE_M
        else:
            entry.sharers |= 1 << core_id
            if entry.state == STATE_M and entry.owner != core_id:
                self.invalidations += 1
                entry.state = STATE_S
            return STATE_S


@dataclass
class ClusterModel:
    """Per-cluster behavioral model."""
    cluster_id: int = 0
    is_big: bool = True
    pc: int = 0x1000
    retire_count: int = 0
    l1_hits: int = 0
    l1_misses: int = 0

    def step(self, l1_hit: bool = True) -> Dict[str, Any]:
        if l1_hit:
            self.l1_hits += 1
            self.retire_count += 1
            self.pc += 4
        else:
            self.l1_misses += 1
        return {
            "pc": self.pc,
            "retired": l1_hit,
        }


@dataclass
class HeteroSoCModel:
    """Full heterogeneous 4-core SoC behavioral model.

    2 big cores (5-stage) + 2 little cores (3-stage) in 2x2 mesh.
    """
    total_cycles: int = 0
    total_retired: int = 0
    perf_retired: int = 0
    eff_retired: int = 0
    total_l1_hits: int = 0
    total_l1_misses: int = 0
    total_invalidations: int = 0
    clusters: List[ClusterModel] = field(default_factory=list)
    coherence: CoherenceDirModel = field(default_factory=CoherenceDirModel)

    def __post_init__(self):
        if not self.clusters:
            self.clusters = [
                ClusterModel(cluster_id=0, is_big=True, pc=0x1000),
                ClusterModel(cluster_id=1, is_big=True, pc=0x1100),
                ClusterModel(cluster_id=2, is_big=False, pc=0x2000),
                ClusterModel(cluster_id=3, is_big=False, pc=0x2100),
            ]

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        for _ in range(num_cycles):
            self.total_cycles += 1
            cycle_retired = 0
            for cluster in self.clusters:
                # Simplified: 80% L1 hit rate model
                l1_hit = (self.total_cycles % 5 != 0)
                result = cluster.step(l1_hit=l1_hit)
                if result.get("retired"):
                    cycle_retired += 1
                    if cluster.is_big:
                        self.perf_retired += 1
                    else:
                        self.eff_retired += 1
                if l1_hit:
                    self.total_l1_hits += 1
                else:
                    self.total_l1_misses += 1
            self.total_retired += cycle_retired

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        total_accesses = max(self.total_l1_hits + self.total_l1_misses, 1)
        return {
            "total_cycles": self.total_cycles,
            "total_retired": self.total_retired,
            "perf_retired": self.perf_retired,
            "eff_retired": self.eff_retired,
            "ipc": self.total_retired / max(self.total_cycles, 1),
            "l1_hit_rate": self.total_l1_hits / total_accesses,
            "l1_misses": self.total_l1_misses,
            "invalidations": self.total_invalidations,
        }
