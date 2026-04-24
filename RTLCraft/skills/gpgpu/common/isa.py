"""
GPGPU ISA Instruction Encodings

A simplified SIMT ISA inspired by NVIDIA PTX/SASS.
Instructions are 64-bit:
  [63:58] opcode   (6-bit major opcode)
  [57:52] func     (6-bit sub-function / ALU op)
  [51:46] dst      (6-bit destination register)
  [45:40] src_a    (6-bit source A register)
  [39:34] src_b    (6-bit source B register)
  [33:28] src_c    (6-bit source C register)
  [27]    pred_use (use predicate?)
  [26:22] pred_reg (5-bit predicate register number)
  [21]    pred_neg (negate predicate?)
  [20:18] unit     (execution unit: ALU=0, SFU=1, TENSOR=2, MEM=3)
  [17:10] imm_hi   (8-bit immediate high)
  [9:0]   imm_lo   (10-bit immediate low)

Total immediate: 18-bit signed/unsigned depending on op.
"""

# -----------------------------------------------------------------------
# Major opcodes [63:58]
# -----------------------------------------------------------------------
OP_ALU     = 0b000000   # Integer / FP arithmetic
OP_SFU     = 0b000001   # Special function
OP_TENSOR  = 0b000010   # Tensor core MMA
OP_MEM     = 0b000011   # Load / Store
OP_CTRL    = 0b000100   # Branch, sync, nop, etc.
OP_MOV     = 0b000101   # Register move / select
OP_PRED    = 0b000110   # Predicate operations

# -----------------------------------------------------------------------
# Execution units [20:18]
# -----------------------------------------------------------------------
UNIT_ALU    = 0b000
UNIT_SFU    = 0b001
UNIT_TENSOR = 0b010
UNIT_MEM    = 0b011

# -----------------------------------------------------------------------
# ALU sub-functions [57:52] — OP_ALU
# -----------------------------------------------------------------------
# Integer
ALU_ADD   = 0b000000
ALU_SUB   = 0b000001
ALU_MUL   = 0b000010
ALU_MAD   = 0b000011
ALU_AND   = 0b000100
ALU_OR    = 0b000101
ALU_XOR   = 0b000110
ALU_NOT   = 0b000111
ALU_SHL   = 0b001000
ALU_SHR   = 0b001001
ALU_ASR   = 0b001010
ALU_MIN   = 0b001011
ALU_MAX   = 0b001100
ALU_ABS   = 0b001101
ALU_NEG   = 0b001110

# Floating-point
ALU_FADD  = 0b010000
ALU_FSUB  = 0b010001
ALU_FMUL  = 0b010010
ALU_FMAD  = 0b010011
ALU_FMIN  = 0b010100
ALU_FMAX  = 0b010101
ALU_FABS  = 0b010110
ALU_FNEG  = 0b010111

# Comparison (set predicate)
ALU_SETP_EQ = 0b100000
ALU_SETP_NE = 0b100001
ALU_SETP_LT = 0b100010
ALU_SETP_LE = 0b100011
ALU_SETP_GT = 0b100100
ALU_SETP_GE = 0b100101

# -----------------------------------------------------------------------
# SFU sub-functions [57:52] — OP_SFU
# -----------------------------------------------------------------------
SFU_SIN    = 0b000000
SFU_COS    = 0b000001
SFU_LOG2   = 0b000010
SFU_EXP2   = 0b000011
SFU_RECIP  = 0b000100
SFU_RSQRT  = 0b000101

# -----------------------------------------------------------------------
# Tensor core sub-functions [57:52] — OP_TENSOR
# -----------------------------------------------------------------------
TENSOR_MMA_FP16 = 0b000000
TENSOR_MMA_BF16 = 0b000001
TENSOR_MMA_INT8 = 0b000010

# -----------------------------------------------------------------------
# Memory sub-functions [57:52] — OP_MEM
# -----------------------------------------------------------------------
MEM_LD   = 0b000000   # Load
MEM_ST   = 0b000001   # Store
MEM_LDS  = 0b000010   # Load shared
MEM_STS  = 0b000011   # Store shared

# -----------------------------------------------------------------------
# Control sub-functions [57:52] — OP_CTRL
# -----------------------------------------------------------------------
CTRL_BRA   = 0b000000   # Branch
CTRL_BRK   = 0b000001   # Break
CTRL_CONT  = 0b000010   # Continue
CTRL_SYNC  = 0b000011   # Barrier sync (__syncthreads)
CTRL_NOP   = 0b000100   # No-op
CTRL_EXIT  = 0b000101   # Thread exit

# -----------------------------------------------------------------------
# Move / Select sub-functions [57:52] — OP_MOV
# -----------------------------------------------------------------------
MOV_MOV  = 0b000000
MOV_SEL  = 0b000001   # Select based on predicate

# -----------------------------------------------------------------------
# Predicate sub-functions [57:52] — OP_PRED
# -----------------------------------------------------------------------
PRED_AND  = 0b000000
PRED_OR   = 0b000001
PRED_XOR  = 0b000010
PRED_NOT  = 0b000011


# -----------------------------------------------------------------------
# Instruction assembly helper
# -----------------------------------------------------------------------
def encode_instr(
    opcode: int,
    func: int,
    dst: int = 0,
    src_a: int = 0,
    src_b: int = 0,
    src_c: int = 0,
    pred_use: int = 0,
    pred_reg: int = 0,
    pred_neg: int = 0,
    unit: int = 0,
    imm: int = 0,
) -> int:
    """Encode a 64-bit GPGPU instruction."""
    imm_hi = (imm >> 10) & 0xFF
    imm_lo = imm & 0x3FF
    return (
        ((opcode & 0x3F) << 58)
        | ((func & 0x3F) << 52)
        | ((dst & 0x3F) << 46)
        | ((src_a & 0x3F) << 40)
        | ((src_b & 0x3F) << 34)
        | ((src_c & 0x3F) << 28)
        | ((pred_use & 0x1) << 27)
        | ((pred_reg & 0x1F) << 22)
        | ((pred_neg & 0x1) << 21)
        | ((unit & 0x7) << 18)
        | ((imm_hi & 0xFF) << 10)
        | (imm_lo & 0x3FF)
    )


def decode_instr(instr: int) -> dict:
    """Decode a 64-bit GPGPU instruction into fields."""
    return {
        "opcode": (instr >> 58) & 0x3F,
        "func": (instr >> 52) & 0x3F,
        "dst": (instr >> 46) & 0x3F,
        "src_a": (instr >> 40) & 0x3F,
        "src_b": (instr >> 34) & 0x3F,
        "src_c": (instr >> 28) & 0x3F,
        "pred_use": (instr >> 27) & 0x1,
        "pred_reg": (instr >> 22) & 0x1F,
        "pred_neg": (instr >> 21) & 0x1,
        "unit": (instr >> 18) & 0x7,
        "imm": ((instr >> 10) & 0xFF) << 10 | (instr & 0x3FF),
    }
