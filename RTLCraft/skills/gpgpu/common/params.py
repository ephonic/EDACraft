"""
GPGPU Configuration Parameters

Defines the microarchitectural parameters for the SIMT streaming processor.
All dimensions are configurable at elaboration time.
"""

from dataclasses import dataclass


@dataclass
class GPGPUParams:
    """Micro-architecture parameters for the GPGPU core."""

    # ------------------------------------------------------------------
    # Thread / Warp / CTA hierarchy
    # ------------------------------------------------------------------
    warp_size: int = 32          # threads per warp (NVIDIA-style)
    num_warps: int = 4           # warps per SM / core
    num_threads: int = 128       # warp_size * num_warps

    # ------------------------------------------------------------------
    # Register file
    # ------------------------------------------------------------------
    num_regs: int = 32           # architectural registers per thread
    reg_width: int = 32          # 32-bit registers
    reg_banks: int = 4           # multi-bank RF to avoid port contention

    # ------------------------------------------------------------------
    # ALU array
    # ------------------------------------------------------------------
    data_width: int = 32         # ALU data width (int / fp32)
    alu_lanes: int = 32          # must equal warp_size for SIMT

    # ------------------------------------------------------------------
    # SFU
    # ------------------------------------------------------------------
    num_sfu: int = 4             # SFU units shared across warps
    sfu_latency: int = 4         # pipeline stages for SFU

    # ------------------------------------------------------------------
    # Tensor core
    # ------------------------------------------------------------------
    tensor_dim: int = 4          # 4×4×4 MMA
    tensor_acc_width: int = 32   # accumulator width

    # ------------------------------------------------------------------
    # Memory subsystem
    # ------------------------------------------------------------------
    l1_line_size: int = 128      # bytes per L1 cache line
    l1_sets: int = 16            # L1 cache sets
    l1_ways: int = 4             # L1 cache ways
    shared_mem_size: int = 16384 # 16 KB shared memory
    coalescer_width: int = 128   # bit-width of coalesced memory request

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------
    icache_sets: int = 16        # instruction cache sets
    icache_ways: int = 2         # instruction cache ways
    icache_line_size: int = 32   # bytes per instruction cache line
    max_instr_len: int = 64      # bits per instruction

    # ------------------------------------------------------------------
    # Scoreboard / scheduling
    # ------------------------------------------------------------------
    scoreboard_entries: int = 32 # in-flight instructions tracked
    max_divergence_depth: int = 8  # reconvergence stack depth
