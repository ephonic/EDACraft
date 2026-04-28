"""
GPGPU Assembler — Text ISA to 64-bit machine code.

Two-pass assembler:
  Pass 1: collect label addresses
  Pass 2: encode instructions

Syntax:
    label:
        ADD r1, r2, r3          ; register-register
        ADD r1, r2, #10         ; register-immediate
        LD  r1, [r2]            ; load
        LD  r1, [r2, #16]       ; load with offset
        ST  [r1], r2            ; store
        ST  [r1, #4], r2        ; store with offset
        BRA label               ; branch
        SYNC                    ; barrier
        EXIT                    ; thread exit
        MOV r1, r2
        SEL r1, r2, r3, p0      ; select based on predicate

Registers: r0-r31, p0-p7 (predicates)
Immediate: #decimal or 0xhex
"""

import re
from typing import List, Dict, Tuple

from skills.gpgpu.common import isa


# ---------------------------------------------------------------------------
# Instruction table: mnemonic -> (opcode, func, unit)
# ---------------------------------------------------------------------------
INSTR_TABLE = {
    # ALU integer
    "ADD":   (isa.OP_ALU, isa.ALU_ADD,   isa.UNIT_ALU),
    "SUB":   (isa.OP_ALU, isa.ALU_SUB,   isa.UNIT_ALU),
    "MUL":   (isa.OP_ALU, isa.ALU_MUL,   isa.UNIT_ALU),
    "MAD":   (isa.OP_ALU, isa.ALU_MAD,   isa.UNIT_ALU),
    "AND":   (isa.OP_ALU, isa.ALU_AND,   isa.UNIT_ALU),
    "OR":    (isa.OP_ALU, isa.ALU_OR,    isa.UNIT_ALU),
    "XOR":   (isa.OP_ALU, isa.ALU_XOR,   isa.UNIT_ALU),
    "NOT":   (isa.OP_ALU, isa.ALU_NOT,   isa.UNIT_ALU),
    "SHL":   (isa.OP_ALU, isa.ALU_SHL,   isa.UNIT_ALU),
    "SHR":   (isa.OP_ALU, isa.ALU_SHR,   isa.UNIT_ALU),
    "ASR":   (isa.OP_ALU, isa.ALU_ASR,   isa.UNIT_ALU),
    "MIN":   (isa.OP_ALU, isa.ALU_MIN,   isa.UNIT_ALU),
    "MAX":   (isa.OP_ALU, isa.ALU_MAX,   isa.UNIT_ALU),
    "ABS":   (isa.OP_ALU, isa.ALU_ABS,   isa.UNIT_ALU),
    "NEG":   (isa.OP_ALU, isa.ALU_NEG,   isa.UNIT_ALU),
    # ALU FP
    "FADD":  (isa.OP_ALU, isa.ALU_FADD,  isa.UNIT_ALU),
    "FSUB":  (isa.OP_ALU, isa.ALU_FSUB,  isa.UNIT_ALU),
    "FMUL":  (isa.OP_ALU, isa.ALU_FMUL,  isa.UNIT_ALU),
    "FMAD":  (isa.OP_ALU, isa.ALU_FMAD,  isa.UNIT_ALU),
    "FMIN":  (isa.OP_ALU, isa.ALU_FMIN,  isa.UNIT_ALU),
    "FMAX":  (isa.OP_ALU, isa.ALU_FMAX,  isa.UNIT_ALU),
    "FABS":  (isa.OP_ALU, isa.ALU_FABS,  isa.UNIT_ALU),
    "FNEG":  (isa.OP_ALU, isa.ALU_FNEG,  isa.UNIT_ALU),
    # Compare
    "SETP.EQ": (isa.OP_ALU, isa.ALU_SETP_EQ, isa.UNIT_ALU),
    "SETP.NE": (isa.OP_ALU, isa.ALU_SETP_NE, isa.UNIT_ALU),
    "SETP.LT": (isa.OP_ALU, isa.ALU_SETP_LT, isa.UNIT_ALU),
    "SETP.LE": (isa.OP_ALU, isa.ALU_SETP_LE, isa.UNIT_ALU),
    "SETP.GT": (isa.OP_ALU, isa.ALU_SETP_GT, isa.UNIT_ALU),
    "SETP.GE": (isa.OP_ALU, isa.ALU_SETP_GE, isa.UNIT_ALU),
    # SFU
    "SIN":   (isa.OP_SFU, isa.SFU_SIN,   isa.UNIT_SFU),
    "COS":   (isa.OP_SFU, isa.SFU_COS,   isa.UNIT_SFU),
    "LOG2":  (isa.OP_SFU, isa.SFU_LOG2,  isa.UNIT_SFU),
    "EXP2":  (isa.OP_SFU, isa.SFU_EXP2,  isa.UNIT_SFU),
    "RECIP": (isa.OP_SFU, isa.SFU_RECIP, isa.UNIT_SFU),
    "RSQRT": (isa.OP_SFU, isa.SFU_RSQRT, isa.UNIT_SFU),
    # Memory
    "LD":    (isa.OP_MEM, isa.MEM_LD,    isa.UNIT_MEM),
    "ST":    (isa.OP_MEM, isa.MEM_ST,    isa.UNIT_MEM),
    "LDS":   (isa.OP_MEM, isa.MEM_LDS,   isa.UNIT_MEM),
    "STS":   (isa.OP_MEM, isa.MEM_STS,   isa.UNIT_MEM),
    # Control
    "BRA":   (isa.OP_CTRL, isa.CTRL_BRA,  isa.UNIT_ALU),
    "BRK":   (isa.OP_CTRL, isa.CTRL_BRK,  isa.UNIT_ALU),
    "CONT":  (isa.OP_CTRL, isa.CTRL_CONT, isa.UNIT_ALU),
    "SYNC":  (isa.OP_CTRL, isa.CTRL_SYNC, isa.UNIT_ALU),
    "NOP":   (isa.OP_CTRL, isa.CTRL_NOP,  isa.UNIT_ALU),
    "EXIT":  (isa.OP_CTRL, isa.CTRL_EXIT, isa.UNIT_ALU),
    # Move
    "MOV":   (isa.OP_MOV, isa.MOV_MOV,   isa.UNIT_ALU),
    "SEL":   (isa.OP_MOV, isa.MOV_SEL,   isa.UNIT_ALU),
    # Predicate
    "PAND":  (isa.OP_PRED, isa.PRED_AND, isa.UNIT_ALU),
    "POR":   (isa.OP_PRED, isa.PRED_OR,  isa.UNIT_ALU),
    "PXOR":  (isa.OP_PRED, isa.PRED_XOR, isa.UNIT_ALU),
    "PNOT":  (isa.OP_PRED, isa.PRED_NOT, isa.UNIT_ALU),
    # Tensor
    "MMA":   (isa.OP_TENSOR, isa.TENSOR_MMA_FP16, isa.UNIT_TENSOR),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_reg(token: str) -> int:
    """Parse register token like 'r5' or 'p3'."""
    token = token.strip().lower()
    if token.startswith("r"):
        return int(token[1:])
    if token.startswith("p"):
        return int(token[1:])
    raise ValueError(f"Invalid register: {token}")


def _parse_imm(token: str) -> int:
    """Parse immediate like '#10', '#0x10', '0x10'."""
    token = token.strip()
    if token.startswith("#"):
        token = token[1:]
    if token.startswith("0x"):
        return int(token, 16)
    return int(token)


def _tokenize_line(line: str) -> Tuple[str, List[str]]:
    """Tokenize a single assembly line into (mnemonic, operands).
    Returns ('', []) for empty/comment lines.
    """
    # Remove comments
    line = line.split(";")[0].strip()
    if not line:
        return "", []

    # Check for label at start:  "label:  ADD r1, r2, r3"
    label_match = re.match(r"(\w+):\s*(.*)", line)
    if label_match:
        # Return label as mnemonic placeholder, rest as a single operand string
        # Caller will handle this in pass 1
        label = label_match.group(1)
        rest = label_match.group(2).strip()
        if rest:
            return "__LABEL__", [label, rest]
        return "__LABEL__", [label]

    # Split mnemonic and operands
    parts = line.split(None, 1)
    mnemonic = parts[0].upper()
    operands = []
    if len(parts) > 1:
        # Split by comma, respecting brackets
        raw = parts[1]
        operands = [p.strip() for p in raw.split(",")]
    return mnemonic, operands


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------
def assemble(code: str) -> List[int]:
    """Assemble GPGPU assembly text into a list of 64-bit machine code words."""
    lines = code.strip().splitlines()

    # Pass 1: collect labels and expand pseudo-instructions
    label_addrs: Dict[str, int] = {}
    expanded_lines: List[Tuple[int, str, List[str]]] = []  # (addr, mnemonic, operands)
    addr = 0

    for raw_line in lines:
        mnemonic, operands = _tokenize_line(raw_line)
        if mnemonic == "":
            continue
        if mnemonic == "__LABEL__":
            label = operands[0]
            label_addrs[label] = addr
            if len(operands) > 1:
                # Label followed by instruction on same line
                mnemonic, operands = _tokenize_line(operands[1])
            else:
                continue
        if mnemonic:
            expanded_lines.append((addr, mnemonic, operands))
            addr += 1

    # Pass 2: encode
    machine_code: List[int] = []
    for addr, mnemonic, operands in expanded_lines:
        word = _encode_instruction(addr, mnemonic, operands, label_addrs)
        machine_code.append(word)

    return machine_code


def _encode_instruction(addr: int, mnemonic: str, operands: List[str],
                        label_addrs: Dict[str, int]) -> int:
    """Encode a single instruction."""
    if mnemonic not in INSTR_TABLE:
        raise ValueError(f"Unknown instruction: {mnemonic} at address {addr}")

    opcode, func, unit = INSTR_TABLE[mnemonic]
    dst = 0
    src_a = 0
    src_b = 0
    src_c = 0
    pred_use = 0
    pred_reg = 0
    pred_neg = 0
    imm = 0

    # Special-case memory instructions with bracket syntax
    if mnemonic in ("LD", "LDS"):
        # LD dst, [addr]  or  LD dst, [addr, #offset]
        # operands may have been split by comma, so reconstruct mem expr from operands[1:]
        dst = _parse_reg(operands[0])
        mem_expr = ",".join(operands[1:]).strip()
        inner = mem_expr[1:-1].strip()  # strip [ and ]
        mem_parts = [p.strip() for p in inner.split(",")]
        src_a = _parse_reg(mem_parts[0])
        if len(mem_parts) > 1:
            imm = _parse_imm(mem_parts[1])
    elif mnemonic in ("ST", "STS"):
        # ST [addr], src  or  ST [addr, #offset], src
        # operands may have been split by comma; last operand is src, rest form mem expr
        src_b = _parse_reg(operands[-1])
        mem_expr = ",".join(operands[:-1]).strip()
        inner = mem_expr[1:-1].strip()
        mem_parts = [p.strip() for p in inner.split(",")]
        src_a = _parse_reg(mem_parts[0])
        if len(mem_parts) > 1:
            imm = _parse_imm(mem_parts[1])
    elif mnemonic == "BRA":
        # BRA label
        label = operands[0]
        if label not in label_addrs:
            raise ValueError(f"Undefined label: {label} at address {addr}")
        imm = label_addrs[label]
    elif mnemonic in ("SYNC", "NOP", "EXIT"):
        # No operands
        pass
    elif mnemonic == "SEL":
        # SEL dst, src_a, src_b, pred
        dst = _parse_reg(operands[0])
        src_a = _parse_reg(operands[1])
        src_b = _parse_reg(operands[2])
        pred = operands[3].strip().lower()
        if pred.startswith("p"):
            pred_use = 1
            pred_reg = int(pred[1:])
        else:
            raise ValueError(f"Invalid predicate: {pred}")
    elif mnemonic == "MOV":
        # MOV dst, src
        dst = _parse_reg(operands[0])
        src_a = _parse_reg(operands[1])
    else:
        # Generic 3-operand:  OP dst, src_a, src_b
        # Or 2-operand with immediate: OP dst, src_a, #imm
        if len(operands) >= 1:
            dst = _parse_reg(operands[0])
        if len(operands) >= 2:
            src_a = _parse_reg(operands[1])
        if len(operands) >= 3:
            op3 = operands[2].strip()
            if op3.startswith("r") or op3.startswith("p"):
                src_b = _parse_reg(op3)
            else:
                # Immediate
                imm = _parse_imm(op3)
        if len(operands) >= 4:
            src_c = _parse_reg(operands[3])

    return isa.encode_instr(
        opcode=opcode,
        func=func,
        dst=dst,
        src_a=src_a,
        src_b=src_b,
        src_c=src_c,
        pred_use=pred_use,
        pred_reg=pred_reg,
        pred_neg=pred_neg,
        unit=unit,
        imm=imm,
    )
