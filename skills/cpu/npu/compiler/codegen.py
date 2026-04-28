"""
NeuralAccel NPU Instruction Code Generator

Converts NPU IR (NPUGraph) into a sequence of 32-bit NPU instructions.

Instruction Format:
  [31:28] opcode  (4-bit)
  [27:24] func    (4-bit sub-opcode)
  [23:16] rd      (8-bit destination)
  [15:8]  rs1     (8-bit source 1)
  [7:0]   rs2_imm (8-bit source 2 / immediate)

Opcodes:
  0x0 NOP
  0x1 LOAD       : external memory -> SRAM via DMA
  0x2 STORE      : SRAM -> external memory via DMA
  0x3 GEMM       : launch systolic array
  0x4 VEC_ALU    : vector element-wise operation
  0x5 SFU        : special function unit
  0x6 CROSSBAR   : crossbar data movement
  0x7 SYNC       : synchronization barrier
  0x8 CONFIG     : configuration write
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from typing import List, Tuple, Dict, Any
import struct

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.compiler.ir import (
    NPUGraph, NPUOp, OpType,
    GemmOp, VecALUOp, SFUOp, LoadOp, StoreOp, CrossbarOp, SyncOp, Im2ColOp, PoolOp,
    VecALUFunc, SFUFunc, NPUTensor,
)


# Hardware opcodes (must match instruction_decode.py)
OP_NOP = 0x0
OP_LOAD = 0x1
OP_STORE = 0x2
OP_GEMM = 0x3
OP_VEC_ALU = 0x4
OP_SFU = 0x5
OP_CROSSBAR = 0x6
OP_SYNC = 0x7
OP_CONFIG = 0x8
OP_IM2COL = 0x9
OP_POOL = 0xA

# VecALU func encoding (must match vector_alu.py)
_VEC_ALU_ENC = {
    VecALUFunc.ADD: 0b0000,
    VecALUFunc.SUB: 0b0001,
    VecALUFunc.MUL: 0b0010,
    VecALUFunc.MAX: 0b0011,
    VecALUFunc.MIN: 0b0100,
    VecALUFunc.AND: 0b0101,
    VecALUFunc.OR: 0b0110,
    VecALUFunc.XOR: 0b0111,
    VecALUFunc.RELU: 0b1000,
    VecALUFunc.NOT: 0b1001,
    VecALUFunc.LSHIFT: 0b1010,
    VecALUFunc.RSHIFT: 0b1011,
}

# SFU func encoding (must match sfu.py)
_SFU_ENC = {
    SFUFunc.SIGMOID: 0b000,
    SFUFunc.TANH: 0b001,
    SFUFunc.EXP: 0b010,
    SFUFunc.SQRT: 0b011,
    SFUFunc.RECIP: 0b100,
}


def _encode_instr(opcode: int, func: int, rd: int, rs1: int, rs2_imm: int,
                     set_fence: int = 0, wait_fence: int = 0) -> int:
    """Encode a 32-bit NPU instruction.

    Bit layout:
      [31:28] opcode     (4 bits)
      [27:24] func       (4 bits)
      [23:18] rd         (6 bits)
      [17:12] rs1        (6 bits)
      [11:6]  rs2_imm    (6 bits)
      [5:3]   set_fence  (3 bits)
      [2:0]   wait_fence (3 bits)
    """
    return (
        ((opcode & 0xF) << 28) |
        ((func & 0xF) << 24) |
        ((rd & 0x3F) << 18) |
        ((rs1 & 0x3F) << 12) |
        ((rs2_imm & 0x3F) << 6) |
        ((set_fence & 0x7) << 3) |
        (wait_fence & 0x7)
    )


def _instr_to_bytes(instr: int) -> bytes:
    """Convert 32-bit instruction to 4 big-endian bytes."""
    return struct.pack(">I", instr)


class MemoryPlanner:
    """Liveness-aware memory allocator for NPU SRAM buffers.

    Allocates tensors into one of four on-chip buffers:
      0 = SRAM_A, 1 = SRAM_B, 2 = SRAM_C, 3 = Scratchpad

    Uses liveness analysis to reuse SRAM addresses when tensors are no
    longer needed. This allows much larger models to fit in limited SRAM.
    """

    def __init__(self, params: NeuralAccelParams = None):
        if params is None:
            params = NeuralAccelParams()
        self.params = params
        self.sram_depth = params.SRAM_DEPTH
        self.data_width = params.DATA_WIDTH
        self.bytes_per_word = params.DATA_WIDTH // 8

    def allocate(self, graph: NPUGraph):
        """Assign buffer IDs and SRAM addresses using liveness analysis."""
        # Step 1: Compute tensor birth/death op indices
        tensor_birth: Dict[str, int] = {}
        tensor_death: Dict[str, int] = {}
        for idx, op in enumerate(graph.ops):
            for out in op.outputs:
                if out.name not in tensor_birth:
                    tensor_birth[out.name] = idx
            for inp in op.inputs:
                tensor_death[inp.name] = max(tensor_death.get(inp.name, -1), idx)

        # Step 2: Heuristic buffer assignment
        for name, tensor in graph.tensors.items():
            if tensor.buffer_id is not None:
                continue
            if "weight" in name.lower() or "bias" in name.lower():
                tensor.buffer_id = 0  # SRAM_A: hardware reads weights from SRAM_A
            elif "input" in name.lower() or name == "x":
                tensor.buffer_id = 1  # SRAM_B: hardware reads activations from SRAM_B
            else:
                tensor.buffer_id = 2  # SRAM_C: hardware writes results to SRAM_C

        # Step 3: Per-buffer liveness allocation
        for buf_id in range(4):
            self._allocate_buffer_liveness(graph, buf_id, tensor_birth, tensor_death)

    def _allocate_buffer_liveness(self, graph: NPUGraph, buf_id: int,
                                  tensor_birth: Dict[str, int],
                                  tensor_death: Dict[str, int]):
        buf_tensors = {name: t for name, t in graph.tensors.items()
                       if t.buffer_id == buf_id}
        if not buf_tensors:
            return

        allocated = []  # (addr, size, name, death_op)
        free_blocks = []  # (addr, size)
        next_addr = 0

        # Sort tensors by birth op index
        sorted_tensors = sorted(buf_tensors.items(),
                                key=lambda x: tensor_birth.get(x[0], 0))

        for name, tensor in sorted_tensors:
            size = max(1, (tensor.size_bytes() + self.bytes_per_word - 1) // self.bytes_per_word)
            birth = tensor_birth.get(name, 0)
            death = tensor_death.get(name, birth)

            # Free tensors that died before this tensor is born
            newly_alive = []
            for a_addr, a_size, a_name, a_death in allocated:
                if a_death < birth:
                    free_blocks.append((a_addr, a_size))
                else:
                    newly_alive.append((a_addr, a_size, a_name, a_death))
            allocated = newly_alive

            # Coalesce free blocks
            free_blocks.sort()
            coalesced = []
            for f_addr, f_size in free_blocks:
                if coalesced and f_addr == coalesced[-1][0] + coalesced[-1][1]:
                    coalesced[-1] = (coalesced[-1][0], coalesced[-1][1] + f_size)
                else:
                    coalesced.append((f_addr, f_size))
            free_blocks = coalesced

            # Best-fit allocation
            best_idx = -1
            best_size = float('inf')
            for i, (f_addr, f_size) in enumerate(free_blocks):
                if f_size >= size and f_size < best_size:
                    best_idx = i
                    best_size = f_size

            if best_idx >= 0:
                f_addr, f_size = free_blocks[best_idx]
                tensor.addr = f_addr
                remaining = f_size - size
                if remaining > 0:
                    free_blocks[best_idx] = (f_addr + size, remaining)
                else:
                    free_blocks.pop(best_idx)
                allocated.append((f_addr, size, name, death))
            else:
                if next_addr + size > self.sram_depth:
                    raise RuntimeError(
                        f"Buffer {buf_id} overflow: tensor {name} needs {size} words, "
                        f"but only {self.sram_depth - next_addr} available"
                    )
                tensor.addr = next_addr
                allocated.append((next_addr, size, name, death))
                next_addr += size


class NPUCodeGen:
    """Generate NPU instruction sequences from NPU IR."""

    def __init__(self, params: NeuralAccelParams = None):
        self.params = params if params is not None else NeuralAccelParams()
        self.planner = MemoryPlanner(self.params)
        self.instructions: List[int] = []
        self.weight_data: Dict[str, Any] = {}  # name -> numpy array or list
        # Fence tracking for sequential execution (simplified)
        self._last_fence = 0
        self._next_fence_id = 1

    def _emit_seq_instr(self, opcode: int, func: int, rd: int, rs1: int, rs2_imm: int):
        """Emit an instruction that writes SRAM, with automatic fence sync.

        Each sequential writer sets a fence ID and waits for the previous
        writer's fence, ensuring in-order completion for data-dependent ops.
        """
        wait_fence = self._last_fence
        set_fence = self._next_fence_id
        self.instructions.append(_encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence, wait_fence))
        self._last_fence = set_fence
        self._next_fence_id = (set_fence % 7) + 1

    def compile(self, graph: NPUGraph) -> Tuple[List[int], Dict[str, Any]]:
        """Compile NPU IR graph to instruction binary and weight data.

        Implements layer-by-layer execution with automatic LOAD/STORE:
        - Tensors are loaded from external DRAM before use
        - Tensors are stored back to DRAM after their last consumer
        - Liveness-based SRAM reuse minimizes on-chip memory pressure
        """
        # Plan SRAM memory layout with liveness reuse
        self.planner.allocate(graph)

        # Assign external DRAM addresses for all tensors
        self._assign_dram_addrs(graph)

        # Identify explicitly loaded/stored tensors (from IR LoadOp/StoreOp)
        explicit_loads = set()
        explicit_stores = set()
        for op in graph.iter_ops():
            if op.op_type == OpType.LOAD:
                explicit_loads.add(op.outputs[0].name)
            elif op.op_type == OpType.STORE:
                explicit_stores.add(op.inputs[0].name)

        # Build tensor consumer map: name -> list of op indices
        from collections import defaultdict
        tensor_consumers = defaultdict(list)
        for idx, op in enumerate(graph.ops):
            for inp in op.inputs:
                tensor_consumers[inp.name].append(idx)

        # Track which tensors currently reside in SRAM
        sram_resident = set()

        for idx, op in enumerate(graph.ops):
            # Pass through explicit LOAD/STORE ops
            if op.op_type == OpType.LOAD:
                self._emit_op(op)
                sram_resident.add(op.outputs[0].name)
                continue
            elif op.op_type == OpType.STORE:
                self._emit_op(op)
                sram_resident.discard(op.inputs[0].name)
                continue

            # Auto-load inputs that are not yet in SRAM
            for inp in op.inputs:
                if inp.name not in sram_resident:
                    self._emit_load_tensor(inp)
                    sram_resident.add(inp.name)

            # Emit the compute op
            self._emit_op(op)

            # Track outputs now in SRAM
            for out in op.outputs:
                sram_resident.add(out.name)

            # Auto-store outputs with no future consumers
            for out in op.outputs:
                if out.name in explicit_stores:
                    continue
                consumers = tensor_consumers.get(out.name, [])
                future = [c for c in consumers if c > idx]
                if not future:
                    self._emit_store_tensor(out)
                    sram_resident.discard(out.name)

        return self.instructions, self.weight_data

    def _assign_dram_addrs(self, graph: NPUGraph):
        """Assign sequential DRAM addresses to all tensors."""
        next_addr = 0
        for name in sorted(graph.tensors.keys()):
            tensor = graph.tensors[name]
            if tensor.external_addr is None:
                tensor.external_addr = next_addr
                next_addr += tensor.size_bytes()
                # Align to 64-bit boundary for AXI burst efficiency
                align = 8
                if next_addr % align != 0:
                    next_addr += align - (next_addr % align)

    def _emit_load_tensor(self, tensor: NPUTensor):
        """Emit LOAD instruction sequence for a single tensor."""
        length = tensor.numel()
        buf_id = tensor.buffer_id or 0
        sram_addr = tensor.addr or 0
        self._emit_config_addr(tensor)
        self._emit_config_len(length)
        self._emit_config_sram_addr(sram_addr)
        self.instructions.append(_encode_instr(OP_LOAD, 0, buf_id, 0, 0))

    def _emit_store_tensor(self, tensor: NPUTensor):
        """Emit STORE instruction sequence for a single tensor."""
        length = tensor.numel()
        buf_id = tensor.buffer_id or 0
        sram_addr = tensor.addr or 0
        self._emit_config_addr(tensor)
        self._emit_config_len(length)
        self._emit_config_sram_addr(sram_addr)
        self.instructions.append(_encode_instr(OP_STORE, 0, 0, buf_id, 0))

    def _emit_op(self, op: NPUOp):
        """Emit instructions for a single NPU operation."""
        if op.op_type == OpType.LOAD:
            self._emit_load(op)
        elif op.op_type == OpType.STORE:
            self._emit_store(op)
        elif op.op_type == OpType.GEMM:
            self._emit_gemm(op)
        elif op.op_type == OpType.VEC_ALU:
            self._emit_vec_alu(op)
        elif op.op_type == OpType.SFU:
            self._emit_sfu(op)
        elif op.op_type == OpType.CROSSBAR:
            self._emit_crossbar(op)
        elif op.op_type == OpType.IM2COL:
            self._emit_im2col(op)
        elif op.op_type == OpType.POOL:
            self._emit_pool(op)
        elif op.op_type == OpType.SYNC:
            self._emit_sync(op)

    def _emit_config_addr(self, tensor: NPUTensor):
        """Emit CONFIG instructions to set DMA external address."""
        addr = tensor.external_addr or 0
        # CONFIG func=0: addr[15:0]
        low = addr & 0xFFFF
        rd_low = (low >> 8) & 0xFF
        rs2_low = low & 0xFF
        self.instructions.append(_encode_instr(OP_CONFIG, 0, rd_low, 0, rs2_low))

        # CONFIG func=1: addr[31:16]
        high = (addr >> 16) & 0xFFFF
        rd_high = (high >> 8) & 0xFF
        rs2_high = high & 0xFF
        self.instructions.append(_encode_instr(OP_CONFIG, 1, rd_high, 0, rs2_high))

    def _emit_config_len(self, length: int):
        """Emit CONFIG instruction to set DMA transfer length."""
        rd = (length >> 8) & 0xFF
        rs2 = length & 0xFF
        self.instructions.append(_encode_instr(OP_CONFIG, 2, rd, 0, rs2))

    def _emit_config_sram_addr(self, addr: int):
        """Emit CONFIG instruction to set DMA SRAM address."""
        self.instructions.append(_encode_instr(OP_CONFIG, 3, 0, 0, addr & 0xFF))

    def _emit_load(self, op: LoadOp):
        """Emit LOAD instruction sequence via DMA."""
        dst = op.outputs[0]
        length = dst.numel()
        buf_id = dst.buffer_id or 0
        sram_addr = dst.addr or 0

        self._emit_config_addr(dst)
        self._emit_config_len(length)
        self._emit_config_sram_addr(sram_addr)

        # LOAD rd=buffer_id, rs2_imm=length (or 0 to use CONFIG length)
        self._emit_seq_instr(OP_LOAD, 0, buf_id, 0, 0)

    def _emit_store(self, op: StoreOp):
        """Emit STORE instruction sequence via DMA."""
        src = op.inputs[0]
        length = src.numel()
        buf_id = src.buffer_id or 0
        sram_addr = src.addr or 0

        self._emit_config_addr(src)
        self._emit_config_len(length)
        self._emit_config_sram_addr(sram_addr)

        # STORE rs1=buffer_id, rs2_imm=length (or 0 to use CONFIG length)
        self._emit_seq_instr(OP_STORE, 0, 0, buf_id, 0)

    def _emit_config_base_addr(self, base_addr: int, rs1_val: int):
        """Emit CONFIG instruction to set a 16-bit base address register.

        Uses CONFIG func=0 with rs1 selecting the target register:
          rs1=1: gemm_weight_base_addr
          rs1=2: gemm_act_base_addr
          rs1=3: gemm_result_base_addr
          rs1=4: im2col_full_src_addr
          rs1=5: im2col_full_dst_addr
        """
        cfg_data = base_addr & 0xFFFF
        rd = (cfg_data >> 8) & 0xFF
        rs2 = cfg_data & 0xFF
        self.instructions.append(_encode_instr(OP_CONFIG, 0, rd, rs1_val, rs2))

    def _emit_gemm(self, op: GemmOp):
        """Emit GEMM instruction with base address configuration."""
        output = op.outputs[0]
        input_a = op.inputs[0]
        input_b = op.inputs[1]
        k_dim = op.attrs.get("k_dim", 0)

        rd = output.buffer_id or 2
        rs1 = input_a.buffer_id or 0
        rs2_imm = k_dim & 0x3F

        # Set base addresses via CONFIG before GEMM
        weight_addr = (input_a.addr or 0) & 0xFFFF
        act_addr = (input_b.addr or 0) & 0xFFFF
        result_addr = (output.addr or 0) & 0xFFFF

        self._emit_config_base_addr(weight_addr, 1)
        self._emit_config_base_addr(act_addr, 2)
        self._emit_config_base_addr(result_addr, 3)

        self._emit_seq_instr(OP_GEMM, 0, rd, rs1, rs2_imm)

    def _emit_vec_alu(self, op: VecALUOp):
        """Emit VEC_ALU instruction."""
        func = op.attrs.get("func", VecALUFunc.ADD)
        func_enc = _VEC_ALU_ENC.get(func, 0)

        output = op.outputs[0]
        rd = output.buffer_id or 2

        # Source buffer from first input
        if len(op.inputs) >= 1:
            rs1 = op.inputs[0].buffer_id or 0
        else:
            rs1 = 0

        # Second source or immediate (for shift)
        if len(op.inputs) >= 2:
            rs2_imm = op.inputs[1].buffer_id or 1
        elif func in (VecALUFunc.LSHIFT, VecALUFunc.RSHIFT):
            rs2_imm = op.attrs.get("shift_amt", 0)
        else:
            # Single-operand ops (ReLU, NOT): encode element count in rs2_imm
            # so the hardware knows how many elements to process.
            rs2_imm = min(output.numel(), 63)

        self._emit_seq_instr(OP_VEC_ALU, func_enc, rd, rs1, rs2_imm)

    def _emit_sfu(self, op: SFUOp):
        """Emit SFU instruction."""
        func = op.attrs.get("func", SFUFunc.SIGMOID)
        func_enc = _SFU_ENC.get(func, 0)

        output = op.outputs[0]
        input_t = op.inputs[0]

        rd = output.buffer_id or 2
        rs1 = input_t.buffer_id or 0

        self._emit_seq_instr(OP_SFU, func_enc & 0xF, rd, rs1, 0)

    def _emit_crossbar(self, op: CrossbarOp):
        """Emit CROSSBAR instruction."""
        src = op.inputs[0]
        dst = op.outputs[0]

        mode = op.attrs.get("mode", 0)
        length = op.attrs.get("length", 0)

        rd = dst.buffer_id or 2
        rs1 = src.buffer_id or 0
        rs2_imm = length & 0x3F

        self._emit_seq_instr(OP_CROSSBAR, mode & 0xF, rd, rs1, rs2_imm)

    def _emit_config_im2col(self, func_low: int, rd: int, rs2: int):
        """Emit CONFIG instruction for Im2Col (func = 0x8 | func_low)."""
        self.instructions.append(_encode_instr(OP_CONFIG, 0x8 | (func_low & 0x7), rd, 0, rs2))

    def _emit_pool(self, op: PoolOp):
        """Emit Pool CONFIG + POOL instruction sequence.

        Pool reuses Im2Col spatial config registers, so we only need to
        emit the Im2Col spatial configs + one Pool-specific config + POOL.
        """
        pool_type = 0 if op.attrs.get("pool_type", "MAX") == "MAX" else 1
        kh = op.attrs.get("kernel_h", 1)
        kw = op.attrs.get("kernel_w", 1)
        stride_h = op.attrs.get("stride_h", 1)
        stride_w = op.attrs.get("stride_w", 1)
        pad_h = op.attrs.get("pad_h", 0)
        pad_w = op.attrs.get("pad_w", 0)
        in_h = op.attrs.get("in_h", 1)
        in_w = op.attrs.get("in_w", 1)
        in_c = op.attrs.get("in_c", 1)
        out_h = op.attrs.get("out_h", 1)
        out_w = op.attrs.get("out_w", 1)
        div_shift = op.attrs.get("div_shift", 0)

        input_t = op.inputs[0]
        output = op.outputs[0]
        src_addr = input_t.addr or 0
        dst_addr = output.addr or 0

        # Reuse Im2Col config instructions for spatial parameters
        self._emit_config_im2col(0, kw & 0xF, kh & 0xF)
        self._emit_config_im2col(1, stride_w & 0xF, stride_h & 0xF)
        self._emit_config_im2col(2, pad_w & 0xF, pad_h & 0xF)
        self._emit_config_im2col(3, (in_h >> 8) & 0xFF, in_h & 0xFF)
        self._emit_config_im2col(4, (in_w >> 8) & 0xFF, in_w & 0xFF)
        self._emit_config_im2col(5, (in_c >> 8) & 0xFF, in_c & 0xFF)
        self._emit_config_im2col(6, (out_h >> 8) & 0xFF, out_h & 0xFF)
        self._emit_config_im2col(7, (out_w >> 8) & 0xFF, out_w & 0xFF)

        # Pool-specific config: pool_type and div_shift (CONFIG func=0x4)
        rd = ((div_shift & 0xF) << 1) | (pool_type & 0x1)
        self.instructions.append(_encode_instr(OP_CONFIG, 0x4, rd, 0, 0))

        # POOL instruction
        src_buf = input_t.buffer_id or 0
        dst_buf = output.buffer_id or 2
        func = ((dst_buf & 0x3) << 2) | (src_buf & 0x3)
        self._emit_seq_instr(OP_POOL, func, dst_addr & 0xFF, src_addr & 0xFF, 0)

    def _emit_im2col(self, op: Im2ColOp):
        """Emit Im2Col CONFIG + IM2COL instruction sequence."""
        # Config registers
        kh = op.attrs.get("kernel_h", 1)
        kw = op.attrs.get("kernel_w", 1)
        stride_h = op.attrs.get("stride_h", 1)
        stride_w = op.attrs.get("stride_w", 1)
        pad_h = op.attrs.get("pad_h", 0)
        pad_w = op.attrs.get("pad_w", 0)
        in_h = op.attrs.get("in_h", 1)
        in_w = op.attrs.get("in_w", 1)
        in_c = op.attrs.get("in_c", 1)
        out_h = op.attrs.get("out_h", 1)
        out_w = op.attrs.get("out_w", 1)

        # Use tensor addresses allocated by MemoryPlanner
        input_t = op.inputs[0]
        output = op.outputs[0]
        src_addr = input_t.addr or 0
        dst_addr = output.addr or 0

        # CONFIG func=0x8: kh/kw
        self._emit_config_im2col(0, kw & 0xF, kh & 0xF)
        # CONFIG func=0x9: stride_h/stride_w
        self._emit_config_im2col(1, stride_w & 0xF, stride_h & 0xF)
        # CONFIG func=0xA: pad_h/pad_w
        self._emit_config_im2col(2, pad_w & 0xF, pad_h & 0xF)
        # CONFIG func=0xB: in_h
        self._emit_config_im2col(3, (in_h >> 8) & 0xFF, in_h & 0xFF)
        # CONFIG func=0xC: in_w
        self._emit_config_im2col(4, (in_w >> 8) & 0xFF, in_w & 0xFF)
        # CONFIG func=0xD: in_c
        self._emit_config_im2col(5, (in_c >> 8) & 0xFF, in_c & 0xFF)
        # CONFIG func=0xE: out_h
        self._emit_config_im2col(6, (out_h >> 8) & 0xFF, out_h & 0xFF)
        # CONFIG func=0xF: out_w
        self._emit_config_im2col(7, (out_w >> 8) & 0xFF, out_w & 0xFF)

        # Set full 16-bit addresses via CONFIG
        self._emit_config_base_addr(src_addr & 0xFFFF, 4)
        self._emit_config_base_addr(dst_addr & 0xFFFF, 5)

        # IM2COL instruction
        src_buf = input_t.buffer_id or 0
        dst_buf = output.buffer_id or 2
        func = ((dst_buf & 0x3) << 2) | (src_buf & 0x3)
        self._emit_seq_instr(OP_IM2COL, func, 0, 0, 0)

    def _emit_sync(self, op: SyncOp):
        """Emit SYNC instruction."""
        self.instructions.append(_encode_instr(OP_SYNC, 0, 0, 0, 0))

    def to_binary(self) -> bytes:
        """Convert instruction list to binary blob."""
        data = b"".join(_instr_to_bytes(i) for i in self.instructions)
        return data

    def to_asm(self) -> str:
        """Convert instruction list to human-readable assembly."""
        lines = []
        opcode_names = {
            OP_NOP: "NOP", OP_LOAD: "LOAD", OP_STORE: "STORE",
            OP_GEMM: "GEMM", OP_VEC_ALU: "VEC_ALU", OP_SFU: "SFU",
            OP_CROSSBAR: "CROSSBAR", OP_SYNC: "SYNC", OP_CONFIG: "CONFIG",
        }
        for idx, instr in enumerate(self.instructions):
            opcode = (instr >> 28) & 0xF
            func = (instr >> 24) & 0xF
            rd = (instr >> 18) & 0x3F
            rs1 = (instr >> 12) & 0x3F
            rs2 = (instr >> 6) & 0x3F
            set_fence = (instr >> 3) & 0x7
            wait_fence = instr & 0x7
            name = opcode_names.get(opcode, f"OP{opcode}")
            lines.append(f"{idx:04d}: {name:8s} func={func:#x} rd={rd:#04x} rs1={rs1:#04x} rs2={rs2:#04x} sf={set_fence} wf={wait_fence}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_graph(graph: NPUGraph, params_or_depth=None, data_width: int = None, *, sram_depth: int = None) -> Tuple[List[int], Dict[str, Any]]:
    """Compile an NPU IR graph to instructions and weight data.

    Args:
        graph: NPU IR computation graph.
        params_or_depth: Either NeuralAccelParams or legacy sram_depth int.
        data_width: Legacy data_width (only used when params_or_depth is int).
        sram_depth: Legacy keyword argument for backward compatibility.

    Returns:
        (instructions, weight_data)
    """
    if isinstance(params_or_depth, NeuralAccelParams):
        params = params_or_depth
    elif isinstance(params_or_depth, int):
        # Legacy positional call: compile_graph(graph, sram_depth, data_width)
        params = NeuralAccelParams(
            sram_depth=params_or_depth,
            data_width=data_width or 16,
        )
    elif sram_depth is not None:
        # Legacy keyword call: compile_graph(graph, sram_depth=256)
        params = NeuralAccelParams(
            sram_depth=sram_depth,
            data_width=data_width or 16,
        )
    else:
        params = NeuralAccelParams()
    codegen = NPUCodeGen(params)
    return codegen.compile(graph)
