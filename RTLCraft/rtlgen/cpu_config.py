"""
rtlgen.cpu_config — CPU configuration system (inspired by C910's cpu_cfig.h).

Provides typed parameters for CPU microarchitecture configuration.
Config is passed through the generation pipeline to produce
appropriately-sized RTL.

Usage:
    cfg = CPUConfig(
        pipeline_stages=12,
        fetch_width=4,
        issue_width=8,
        rob_depth=128,
        iq_entries=32,
        phys_regs=256,
        btb_entries=1024,
        l1_icache_size=65536,
        l1_dcache_size=65536,
        l2_cache_size=1048576,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CPUConfig:
    """CPU microarchitecture configuration parameters.

    Mirrors the key defines from C910's cpu_cfig.h:
      BTB_1024, IBP_PRO, ICACHE_64K, DCACHE_64K,
      L2_CACHE_16WAY, L2_CACHE_1M, MULTI_PROCESSING,
      JTLB_ENTRY_1024, PA_WIDTH=40, VA_WIDTH=39
    """

    # ── Pipeline width ──
    fetch_width: int = 2          # instructions per cycle fetch
    decode_width: int = 2         # instructions per cycle decode
    issue_width: int = 2          # instructions per cycle issue
    commit_width: int = 2         # instructions per cycle commit

    # ── Pipeline stages ──
    pipeline_stages: int = 6      # total pipeline depth
    fetch_stages: int = 1         # IF stages
    decode_stages: int = 1        # ID stages
    execute_stages: int = 2       # EX stages (including bypass)

    # ── Buffers ──
    rob_depth: int = 64           # reorder buffer entries
    iq_entries: int = 32          # issue queue entries per queue type
    load_queue_depth: int = 16    # load queue entries
    store_queue_depth: int = 16   # store queue entries
    phys_int_regs: int = 128      # physical integer registers
    phys_fp_regs: int = 128       # physical floating-point registers

    # ── Branch predictor ──
    btb_entries: int = 64         # BTB entries
    btb_ways: int = 4             # BTB associativity
    bht_entries: int = 4096       # branch history table entries
    ras_depth: int = 8            # return address stack depth
    l0_btb_entries: int = 4       # L0 BTB entries (fast path)
    use_loop_buffer: bool = False # SFP loop buffer

    # ── Caches ──
    l1_icache_size: int = 32768   # L1 I-cache size in bytes
    l1_icache_ways: int = 8       # L1 I-cache associativity
    l1_icache_line: int = 64      # L1 I-cache line size
    l1_dcache_size: int = 32768   # L1 D-cache size
    l1_dcache_ways: int = 8       # L1 D-cache associativity
    l1_dcache_line: int = 64      # L1 D-cache line size
    l2_cache_size: int = 0        # L2 cache size (0 = no L2)
    l2_cache_ways: int = 16       # L2 associativity

    # ── TLB / MMU ──
    itlb_entries: int = 32        # instruction TLB entries
    dtlb_entries: int = 32        # data TLB entries
    jtlb_entries: int = 1024     # joint TLB entries (shared L2 TLB)
    pa_width: int = 40            # physical address width
    va_width: int = 39            # virtual address width

    # ── Features ──
    multi_processing: bool = False  # SMP support (snoop coherence)
    vector_enable: bool = False     # Vector extension
    fp_enable: bool = False         # Floating point
    debug_enable: bool = False      # Hardware debug (HAD)
    perf_counters: bool = False     # Performance counters (HPCP)

    # ── Derived properties ──
    @property
    def l1_icache_sets(self) -> int:
        return self.l1_icache_size // (self.l1_icache_ways * self.l1_icache_line)

    @property
    def l1_dcache_sets(self) -> int:
        return self.l1_dcache_size // (self.l1_dcache_ways * self.l1_dcache_line)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ── Preset configurations ──

C910_CONFIG = CPUConfig(
    fetch_width=4, decode_width=4, issue_width=8, commit_width=4,
    pipeline_stages=12, fetch_stages=3, decode_stages=3, execute_stages=3,
    rob_depth=128, iq_entries=32,
    load_queue_depth=24, store_queue_depth=24,
    phys_int_regs=256, phys_fp_regs=256,
    btb_entries=1024, btb_ways=4, bht_entries=4096, ras_depth=8,
    l0_btb_entries=4,
    l1_icache_size=65536, l1_icache_ways=2, l1_icache_line=64,
    l1_dcache_size=65536, l1_dcache_ways=4, l1_dcache_line=64,
    l2_cache_size=1048576, l2_cache_ways=16,
    itlb_entries=32, dtlb_entries=32, jtlb_entries=1024,
    pa_width=40, va_width=39,
    multi_processing=True, vector_enable=True, fp_enable=True,
    debug_enable=True, perf_counters=True,
)

OFO_CONFIG = CPUConfig(
    fetch_width=2, decode_width=2, issue_width=2, commit_width=2,
    pipeline_stages=6, fetch_stages=1, decode_stages=1, execute_stages=2,
    rob_depth=64, iq_entries=32,
    load_queue_depth=16, store_queue_depth=16,
    phys_int_regs=128, phys_fp_regs=0,
    btb_entries=64, btb_ways=4, bht_entries=4096, ras_depth=8,
    l0_btb_entries=4,
    l1_icache_size=32768, l1_icache_ways=8, l1_icache_line=64,
    l1_dcache_size=32768, l1_dcache_ways=8, l1_dcache_line=64,
    l2_cache_size=0,
    itlb_entries=32, dtlb_entries=32, jtlb_entries=1024,
    pa_width=40, va_width=39,
)

HIGH_PERF_RV64_4CORE_CONFIG = CPUConfig(
    fetch_width=4, decode_width=4, issue_width=6, commit_width=4,
    pipeline_stages=12, fetch_stages=3, decode_stages=2, execute_stages=4,
    rob_depth=192, iq_entries=48,
    load_queue_depth=32, store_queue_depth=32,
    phys_int_regs=192, phys_fp_regs=128,
    btb_entries=1024, btb_ways=4, bht_entries=8192, ras_depth=16,
    l0_btb_entries=8, use_loop_buffer=True,
    l1_icache_size=65536, l1_icache_ways=4, l1_icache_line=64,
    l1_dcache_size=65536, l1_dcache_ways=4, l1_dcache_line=64,
    l2_cache_size=2097152, l2_cache_ways=16,
    itlb_entries=64, dtlb_entries=64, jtlb_entries=2048,
    pa_width=48, va_width=39,
    multi_processing=True, vector_enable=False, fp_enable=True,
    debug_enable=True, perf_counters=True,
)
