"""
skills.riscv64_soc.models — SoC Behavioral Models

64-core RISC-V SoC behavioral models:
  - CoreModel: Single RV64 core instruction throughput model
  - L1CacheModel: L1 I/D cache hit/miss model
  - CoherenceDirModel: MSI directory tracking
  - L2CacheModel: L2 cache bank model
  - ClusterModel: Full cluster behavioral model
  - SoCModel: 8x8 mesh SoC behavioral model
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Coherence states
STATE_I = 0  # Invalid
STATE_S = 1  # Shared
STATE_M = 2  # Modified

# Cache states
CACHE_IDLE = 0
CACHE_TAG_CHECK = 1
CACHE_HIT = 2
CACHE_MISS = 3
CACHE_FILL = 4


@dataclass
class CacheLine:
    """Single cache line state."""
    tag: int = 0
    state: int = STATE_I
    valid: bool = False
    lru_counter: int = 0
    data_addr: int = 0


@dataclass
class DirectoryEntry:
    """Directory entry for a cache line."""
    tag: int = 0
    state: int = STATE_I
    sharers: int = 0  # 64-bit bitmask
    owner: int = -1   # core ID or -1
    valid: bool = False


@dataclass
class CoreModel:
    """Single RV64 core behavioral model."""
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
        """Simulate one cycle."""
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
    ways: int = 8
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
            self.lines[key].lru_counter = 0
            return True
        self.misses += 1
        return False

    def fill(self, addr: int):
        tag = addr >> 12
        set_idx = (addr >> 6) & 0x3F
        key = (set_idx, tag)
        self.lines[key] = CacheLine(tag=tag, state=STATE_S, valid=True, data_addr=addr)


@dataclass
class CoherenceDirModel:
    """Directory-based MSI coherence tracker."""
    entries: Dict[int, DirectoryEntry] = field(default_factory=dict)
    snoop_reqs: int = 0
    snoop_resps: int = 0
    invalidations: int = 0

    def lookup(self, addr: int) -> Tuple[int, int, int]:
        """Return (state, sharers, owner)."""
        tag = addr >> 12
        entry = self.entries.get(tag)
        if entry and entry.valid:
            return entry.state, entry.sharers, entry.owner
        return STATE_I, 0, -1

    def request(self, core_id: int, addr: int, req_state: int) -> int:
        """Core requests cache line. Returns granted state."""
        tag = addr >> 12
        entry = self.entries.get(tag)
        if entry is None or not entry.valid:
            # Cold miss — grant Shared
            self.entries[tag] = DirectoryEntry(
                tag=tag, state=STATE_S, sharers=(1 << core_id), owner=core_id, valid=True,
            )
            return STATE_S

        if req_state == STATE_M:
            if entry.state == STATE_M and entry.owner != core_id:
                # Must invalidate current owner
                self.invalidations += 1
                entry.owner = core_id
                entry.state = STATE_M
                entry.sharers = 1 << core_id
            else:
                entry.owner = core_id
                entry.state = STATE_M
                entry.sharers = 1 << core_id
            return STATE_M
        else:
            # Shared request
            entry.sharers |= 1 << core_id
            if entry.state == STATE_M and entry.owner != core_id:
                self.invalidations += 1
                entry.state = STATE_S
            return STATE_S

    def release(self, core_id: int, addr: int):
        """Core releases/evicts cache line."""
        tag = addr >> 12
        entry = self.entries.get(tag)
        if entry and entry.valid:
            entry.sharers &= ~(1 << core_id)
            if entry.sharers == 0:
                entry.valid = False


@dataclass
class L2CacheModel:
    """L2 cache bank behavioral model."""
    bank_id: int = 0
    ways: int = 8
    sets: int = 128
    hits: int = 0
    misses: int = 0
    dram_accesses: int = 0

    def lookup(self, addr: int) -> bool:
        # Simplified: 50% hit rate model
        tag = addr >> 12
        if tag % 3 == 0:
            self.hits += 1
            return True
        self.misses += 1
        self.dram_accesses += 1
        return False


@dataclass
class ClusterModel:
    """Full cluster behavioral model."""
    cluster_id: int = 0
    core: CoreModel = field(default_factory=CoreModel)
    l1i: L1CacheModel = field(default_factory=L1CacheModel)
    l1d: L1CacheModel = field(default_factory=L1CacheModel)
    coherence: CoherenceDirModel = field(default_factory=CoherenceDirModel)
    l2: L2CacheModel = field(default_factory=L2CacheModel)
    noc_flits_sent: int = 0
    noc_flits_received: int = 0

    def step(self):
        """Simulate one cycle for the cluster."""
        # Simplified: core issues requests, L1 responds, misses go to coherence/L2
        l1i_hit = self.l1i.lookup(self.core.pc)
        l1d_hit = self.l1d.lookup(self.core.pc + 8)
        result = self.core.step(l1i_hit=l1i_hit, l1d_hit=l1d_hit)
        if not l1i_hit or not l1d_hit:
            # Coherence request
            self.coherence.request(self.cluster_id, self.core.pc, STATE_S)
            self.noc_flits_sent += 1
        return result


@dataclass
class SoCModel:
    """Full 64-core SoC behavioral model."""
    mesh_x: int = 8
    mesh_y: int = 8
    clusters: List[ClusterModel] = field(default_factory=list)
    global_coherence: CoherenceDirModel = field(default_factory=CoherenceDirModel)
    total_cycles: int = 0
    total_retired: int = 0
    total_l1i_hits: int = 0
    total_l1d_hits: int = 0
    total_l1i_misses: int = 0
    total_l1d_misses: int = 0
    total_l2_hits: int = 0
    total_l2_misses: int = 0
    total_dram_accesses: int = 0
    total_noc_flits: int = 0
    total_invalidations: int = 0

    def __post_init__(self):
        if not self.clusters:
            self.clusters = [ClusterModel(cluster_id=i) for i in range(self.mesh_x * self.mesh_y)]

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        """Run behavioral simulation."""
        for _ in range(num_cycles):
            self.total_cycles += 1
            cluster_retired = 0
            for cluster in self.clusters:
                result = cluster.step()
                if result.get("retired"):
                    cluster_retired += 1
                # Aggregate L1 stats
                self.total_l1i_hits += cluster.l1i.hits
                self.total_l1d_hits += cluster.l1d.hits
                self.total_l1i_misses += cluster.l1i.misses
                self.total_l1d_misses += cluster.l1d.misses
                self.total_noc_flits += cluster.noc_flits_sent
            # Reset per-cluster accumulators for next cycle
            for cluster in self.clusters:
                cluster.l1i.hits = 0
                cluster.l1d.hits = 0
                cluster.l1i.misses = 0
                cluster.l1d.misses = 0
                cluster.noc_flits_sent = 0
            self.total_retired += cluster_retired

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_cycles": self.total_cycles,
            "total_retired": self.total_retired,
            "ipc": self.total_retired / max(self.total_cycles, 1),
            "l1i_hit_rate": self.total_l1i_hits / max(self.total_l1i_hits + self.total_l1i_misses, 1),
            "l1d_hit_rate": self.total_l1d_hits / max(self.total_l1d_hits + self.total_l1d_misses, 1),
            "total_noc_flits": self.total_noc_flits,
            "l1i_hits": self.total_l1i_hits,
            "l1d_hits": self.total_l1d_hits,
            "l1i_misses": self.total_l1i_misses,
            "l1d_misses": self.total_l1d_misses,
        }
