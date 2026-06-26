"""Thor GPU — Vector ALU L3 DSL. Configurable-latency 16-lane INT32 SIMD.
Pipeline with valid/ready handshake and automatic drain."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif, Switch

from skills.thor import XLEN, NLANE, VLEN, OP_VADD, OP_VMUL


class VectorALU(Module):
    def __init__(self, name="vector_alu", latency=3):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.opcode = Input(5, "opcode")
        self.op1 = Input(VLEN, "op1"); self.op2 = Input(VLEN, "op2")
        self.pred_mask = Input(NLANE, "pred_mask")
        self.in_valid = Input(1, "in_valid")
        self.out_ready = Input(1, "out_ready")
        self.result = Output(VLEN, "result"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")

        M32 = (1 << XLEN) - 1
        self._pv = [Reg(1, f"apv_{i}") for i in range(latency)]
        for l in range(NLANE):
            setattr(self, f"lr_{l}", Array(XLEN, latency, f"lr_{l}"))
        lr = [getattr(self, f"lr_{l}") for l in range(NLANE)]

        with self.comb:
            self.in_ready <<= (self._pv[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(latency): self._pv[i] <<= 0
                for l in range(NLANE):
                    for s in range(latency): lr[l][s] <<= 0
            with Else():
                # Each stage: if next stage accepts, shift data forward
                # Last stage: if output consumed, clear
                out_fire = self._pv[latency - 1] & self.out_ready
                with If(out_fire):
                    self._pv[latency - 1] <<= 0

                for s in range(latency - 2, -1, -1):
                    nxt_free = (self._pv[s + 1] == 0)
                    with If(self._pv[s] & (nxt_free | self.out_ready)):
                        for l in range(NLANE): lr[l][s + 1] <<= lr[l][s]
                        self._pv[s + 1] <<= 1
                        self._pv[s] <<= 0

                # Stage 0: new input
                with If(self.in_valid & self.in_ready):
                    for lane in range(NLANE):
                        a = (self.op1 >> (lane * XLEN)) & M32
                        b = (self.op2 >> (lane * XLEN)) & M32
                        with If((self.pred_mask >> lane) & 1):
                            with Switch(self.opcode) as sw:
                                with sw.case(OP_VADD): lr[lane][0] <<= a + b
                                with sw.case(OP_VMUL): lr[lane][0] <<= a * b
                                with sw.default(): lr[lane][0] <<= 0
                        with Else(): lr[lane][0] <<= 0
                    self._pv[0] <<= 1

        with self.comb:
            packed = 0
            for lane in range(NLANE):
                packed |= lr[lane][latency - 1] << (lane * XLEN)
            self.result <<= packed
            self.out_valid <<= self._pv[latency - 1]
