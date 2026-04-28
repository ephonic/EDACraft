"""
NeuralAccel NPU Intermediate Representation (IR)

A simple dataflow IR for representing neural network computations
targeting the NeuralAccel NPU.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum, auto


class DataType(Enum):
    INT16 = auto()
    INT32 = auto()
    FP16 = auto()


class OpType(Enum):
    LOAD = auto()      # External DRAM -> SRAM
    STORE = auto()     # SRAM -> External DRAM
    GEMM = auto()      # Systolic array matrix multiply
    VEC_ALU = auto()   # Vector element-wise ALU
    SFU = auto()       # Special function unit
    CROSSBAR = auto()  # On-chip data movement
    SYNC = auto()      # Synchronization barrier
    IM2COL = auto()    # Image-to-column transformation
    POOL = auto()      # 2D pooling (MAX/AVG)


class VecALUFunc(Enum):
    ADD = 0b0000
    SUB = 0b0001
    MUL = 0b0010
    MAX = 0b0011
    MIN = 0b0100
    AND = 0b0101
    OR = 0b0110
    XOR = 0b0111
    RELU = 0b1000
    NOT = 0b1001
    LSHIFT = 0b1010
    RSHIFT = 0b1011


class SFUFunc(Enum):
    SIGMOID = 0b000
    TANH = 0b001
    EXP = 0b010
    SQRT = 0b011
    RECIP = 0b100


@dataclass
class NPUTensor:
    """Metadata for a tensor in NPU memory."""
    name: str
    shape: Tuple[int, ...]
    dtype: DataType = DataType.INT16
    addr: Optional[int] = None  # SRAM address (if allocated)
    buffer_id: Optional[int] = None  # 0=A, 1=B, 2=C, 3=Scratch
    external_addr: Optional[int] = None  # DRAM address (if off-chip)

    def numel(self) -> int:
        n = 1
        for dim in self.shape:
            n *= dim
        return n

    def size_bytes(self) -> int:
        bytes_per_elem = {
            DataType.INT16: 2,
            DataType.INT32: 4,
            DataType.FP16: 2,
        }[self.dtype]
        return self.numel() * bytes_per_elem


@dataclass
class NPUOp:
    """Base class for NPU operations."""
    op_type: OpType
    name: str
    inputs: List[NPUTensor] = field(default_factory=list)
    outputs: List[NPUTensor] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GemmOp(NPUOp):
    """Matrix multiplication: output = input_a @ input_b + input_c (optional)."""
    k_dim: int = 0

    def __init__(self, name: str, input_a: NPUTensor, input_b: NPUTensor,
                 output: NPUTensor, k_dim: int = 0, input_c: Optional[NPUTensor] = None):
        inputs = [input_a, input_b]
        if input_c is not None:
            inputs.append(input_c)
        super().__init__(OpType.GEMM, name, inputs, [output], {"k_dim": k_dim})
        self.k_dim = k_dim


@dataclass
class VecALUOp(NPUOp):
    """Vector element-wise operation."""
    func: VecALUFunc = VecALUFunc.ADD
    shift_amt: int = 0

    def __init__(self, name: str, func: VecALUFunc,
                 inputs: List[NPUTensor], output: NPUTensor, shift_amt: int = 0):
        super().__init__(OpType.VEC_ALU, name, inputs, [output],
                         {"func": func, "shift_amt": shift_amt})
        self.func = func
        self.shift_amt = shift_amt


@dataclass
class SFUOp(NPUOp):
    """Special function unit operation."""
    func: SFUFunc = SFUFunc.SIGMOID

    def __init__(self, name: str, func: SFUFunc,
                 input_t: NPUTensor, output: NPUTensor):
        super().__init__(OpType.SFU, name, [input_t], [output], {"func": func})
        self.func = func


@dataclass
class LoadOp(NPUOp):
    """Load tensor from external DRAM to SRAM."""
    def __init__(self, name: str, src: NPUTensor, dst: NPUTensor):
        super().__init__(OpType.LOAD, name, [src], [dst])


@dataclass
class StoreOp(NPUOp):
    """Store tensor from SRAM to external DRAM."""
    def __init__(self, name: str, src: NPUTensor, dst: NPUTensor):
        super().__init__(OpType.STORE, name, [src], [dst])


@dataclass
class CrossbarOp(NPUOp):
    """On-chip data movement via crossbar."""
    mode: int = 0  # 0=BLOCK, 1=STRIDE, 2=BROADCAST, 3=GATHER
    length: int = 0
    src_addr: int = 0
    dst_addr: int = 0
    stride: int = 1

    def __init__(self, name: str, src: NPUTensor, dst: NPUTensor,
                 mode: int = 0, length: int = 0,
                 src_addr: int = 0, dst_addr: int = 0, stride: int = 1):
        super().__init__(OpType.CROSSBAR, name, [src], [dst],
                         {"mode": mode, "length": length,
                          "src_addr": src_addr, "dst_addr": dst_addr,
                          "stride": stride})
        self.mode = mode
        self.length = length
        self.src_addr = src_addr
        self.dst_addr = dst_addr
        self.stride = stride


@dataclass
class SyncOp(NPUOp):
    """Synchronization barrier."""
    def __init__(self, name: str = "sync"):
        super().__init__(OpType.SYNC, name, [], [])


@dataclass
class Im2ColOp(NPUOp):
    """Hardware im2col transformation."""
    kernel_h: int = 1
    kernel_w: int = 1
    stride_h: int = 1
    stride_w: int = 1
    pad_h: int = 0
    pad_w: int = 0
    in_h: int = 1
    in_w: int = 1
    in_c: int = 1
    out_h: int = 1
    out_w: int = 1
    src_addr: int = 0
    dst_addr: int = 0

    def __init__(self, name: str, input_t: NPUTensor, output: NPUTensor,
                 kernel_h: int = 1, kernel_w: int = 1,
                 stride_h: int = 1, stride_w: int = 1,
                 pad_h: int = 0, pad_w: int = 0,
                 in_h: int = 1, in_w: int = 1, in_c: int = 1,
                 out_h: int = 1, out_w: int = 1,
                 src_addr: int = 0, dst_addr: int = 0):
        super().__init__(OpType.IM2COL, name, [input_t], [output],
                         {"kernel_h": kernel_h, "kernel_w": kernel_w,
                          "stride_h": stride_h, "stride_w": stride_w,
                          "pad_h": pad_h, "pad_w": pad_w,
                          "in_h": in_h, "in_w": in_w, "in_c": in_c,
                          "out_h": out_h, "out_w": out_w,
                          "src_addr": src_addr, "dst_addr": dst_addr})
        self.kernel_h = kernel_h
        self.kernel_w = kernel_w
        self.stride_h = stride_h
        self.stride_w = stride_w
        self.pad_h = pad_h
        self.pad_w = pad_w
        self.in_h = in_h
        self.in_w = in_w
        self.in_c = in_c
        self.out_h = out_h
        self.out_w = out_w
        self.src_addr = src_addr
        self.dst_addr = dst_addr


@dataclass
class PoolOp(NPUOp):
    """2D pooling operation."""
    pool_type: str = "MAX"  # "MAX" or "AVG"
    kernel_h: int = 1
    kernel_w: int = 1
    stride_h: int = 1
    stride_w: int = 1
    pad_h: int = 0
    pad_w: int = 0
    in_h: int = 1
    in_w: int = 1
    in_c: int = 1
    out_h: int = 1
    out_w: int = 1
    div_shift: int = 0  # for AVG: right shift amount
    src_addr: int = 0
    dst_addr: int = 0

    def __init__(self, name: str, input_t: NPUTensor, output: NPUTensor,
                 pool_type: str = "MAX",
                 kernel_h: int = 1, kernel_w: int = 1,
                 stride_h: int = 1, stride_w: int = 1,
                 pad_h: int = 0, pad_w: int = 0,
                 in_h: int = 1, in_w: int = 1, in_c: int = 1,
                 out_h: int = 1, out_w: int = 1,
                 div_shift: int = 0,
                 src_addr: int = 0, dst_addr: int = 0):
        super().__init__(OpType.POOL, name, [input_t], [output],
                         {"pool_type": pool_type,
                          "kernel_h": kernel_h, "kernel_w": kernel_w,
                          "stride_h": stride_h, "stride_w": stride_w,
                          "pad_h": pad_h, "pad_w": pad_w,
                          "in_h": in_h, "in_w": in_w, "in_c": in_c,
                          "out_h": out_h, "out_w": out_w,
                          "div_shift": div_shift,
                          "src_addr": src_addr, "dst_addr": dst_addr})
        self.pool_type = pool_type
        self.kernel_h = kernel_h
        self.kernel_w = kernel_w
        self.stride_h = stride_h
        self.stride_w = stride_w
        self.pad_h = pad_h
        self.pad_w = pad_w
        self.in_h = in_h
        self.in_w = in_w
        self.in_c = in_c
        self.out_h = out_h
        self.out_w = out_w
        self.div_shift = div_shift
        self.src_addr = src_addr
        self.dst_addr = dst_addr


@dataclass
class NPUGraph:
    """A complete NPU computation graph."""
    name: str
    ops: List[NPUOp] = field(default_factory=list)
    tensors: Dict[str, NPUTensor] = field(default_factory=dict)

    def add_op(self, op: NPUOp):
        self.ops.append(op)
        for t in op.inputs + op.outputs:
            self.tensors[t.name] = t

    def iter_ops(self):
        return iter(self.ops)
