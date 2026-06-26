"""
skills/thor — Blackwell-class GPGPU (NVIDIA Thor architecture modeled).

Architecture:
  - CTA Scheduler: workgroup dispatch to SMs
  - SM (Streaming Multiprocessor) × 4:
    - Warp Scheduler × 4 (each managing 4 warps)
    - SIMT Stack (branch divergence handling)
    - IBuffer × 4 (instruction buffers per scheduler)
    - Scoreboard (register dependency tracking)
    - Operand Collector (bypass network + register read)
    - Execution Units:
      - Vector ALU (INT32, 16-lane)
      - Vector FPU (FP32, 16-lane)
      - SFU (special function: sqrt, rcp, sin/cos)
      - Tensor Core (4×4×4 matrix multiply-accumulate)
    - LSU (load/store with coalescing)
    - L1 Data Cache + Shared Memory (unified, 64 KB/SM)
    - Register File (128 regs × 32-bit × 16 warps × 16 lanes)
  - L2 Cache (shared, 512 KB)
  - Memory Controller (HBM3-like, 4 channels)
"""
from __future__ import annotations

# =====================================================================
# Architecture Parameters
# =====================================================================
XLEN       = 32       # scalar width
FLEN       = 32       # FP width
NLANE      = 16       # SIMD lanes per warp
VLEN       = XLEN * NLANE  # 512-bit vector width
VREGS      = 128      # vector registers per warp
NWARP      = 16       # warps per SM
N_SCHED    = 4        # warp schedulers per SM
WARP_PER_SCHED = NWARP // N_SCHED  # 4 warps per scheduler
NSM        = 4        # SMs
NL2_BANK   = 8        # L2 cache banks
L2_SIZE    = 512 * 1024  # 512 KB
L1_SIZE    = 64 * 1024   # 64 KB per SM
SMEM_SIZE  = 32 * 1024   # 32 KB shared memory per SM
IMEM_DEPTH = 256      # instruction memory entries
N_CTA_MAX  = 16       # max concurrent CTAs per SM

# Execution unit counts
N_ALU      = 4        # vector ALU pipes
N_FPU      = 4        # vector FPU pipes
N_SFU      = 2        # special function units
N_TENSOR   = 2        # tensor cores
N_LSU      = 4        # load/store units

# Memory channels
N_MEM_CH   = 4        # HBM3 channels
MEM_CH_W   = 128      # bits per channel
MEM_BURST  = 8        # burst length

# Opcodes (25-bit instruction format)
OP_NOP     = 0x00
OP_SLOAD   = 0x01     # scalar load immediate
OP_VLOAD   = 0x02     # vector load from global
OP_VSTORE  = 0x03     # vector store to global
OP_VADD    = 0x04     # vector integer add
OP_VSUB    = 0x05     # vector integer sub
OP_VMUL    = 0x06     # vector integer multiply
OP_VMLA    = 0x07     # vector integer multiply-accumulate
OP_FADD    = 0x08     # vector FP add
OP_FMUL    = 0x09     # vector FP multiply
OP_FMLA    = 0x0A     # vector FP multiply-accumulate
OP_SFU     = 0x0B     # special function (sqrt, rcp, sin, cos)
OP_TENSOR  = 0x0C     # tensor core matrix MAC
OP_BARRIER = 0x0D     # warp barrier
OP_DONE    = 0x0F     # warp done
OP_BRA     = 0x10     # branch (for divergence)
OP_SYNC    = 0x11     # CTA sync

# SIMT stack states
SIMT_STACK_DEPTH = 16

# Instruction decode helpers
def decode_inst(inst: int):
    """Decode Thor GPU 24-bit instruction.
    Format: [31:28] opcode, [27:24] rd, [23:20] rs1, [19:16] rs2, [15:0] imm
    """
    opcode = (inst >> 28) & 0x1F
    rd     = (inst >> 23) & 0x1F
    rs1    = (inst >> 18) & 0x1F
    rs2    = (inst >> 13) & 0x1F
    imm    = inst & 0x1FFF
    return opcode, rd, rs1, rs2, imm
