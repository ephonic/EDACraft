"""L1 behavior model tests for EarphoneRV32."""

import pytest

from earphone.modules.rv32 import RV32IM_ISS


class TestRV32IMISS:
    def _run_program(self, prog, max_cycles=100):
        iss = RV32IM_ISS()
        iss.load_program_words(prog, 0x1000)
        iss.run(max_cycles=max_cycles)
        return iss

    def test_add_sub(self):
        prog = [
            0x00100093,  # addi x1, x0, 1
            0x00200113,  # addi x2, x0, 2
            0x002081B3,  # add  x3, x1, x2
            0x402081B3,  # sub  x3, x1, x2
            0x00100073,  # ebreak
        ]
        iss = self._run_program(prog)
        assert iss.state.regs[3] == 0xFFFFFFFF  # 1 - 2 = -1

    def test_load_store(self):
        prog = [
            0x10000117,  # auipc x2, 0x10000 -> x2 = 0x10001000
            0x00300193,  # addi x3, x0, 3
            0x00312023,  # sw x3, 0(x2)
            0x00012203,  # lw x4, 0(x2)
            0x00100073,  # ebreak
        ]
        iss = self._run_program(prog)
        assert iss.state.regs[4] == 3

    def test_mul(self):
        prog = [
            0x00700093,  # addi x1, x0, 7
            0x00600113,  # addi x2, x0, 6
            0x022080B3,  # mul x1, x1, x2
            0x00100073,  # ebreak
        ]
        iss = self._run_program(prog)
        assert iss.state.regs[1] == 42

    def test_div_by_zero(self):
        prog = [
            0x00700093,  # addi x1, x0, 7
            0x00000113,  # addi x2, x0, 0
            0x0220C1B3,  # div x3, x1, x2 -> -1
            0x0220E233,  # rem x4, x1, x2 -> 7
            0x00100073,  # ebreak
        ]
        iss = self._run_program(prog)
        assert iss.state.regs[3] == 0xFFFFFFFF
        assert iss.state.regs[4] == 7

    def test_branch(self):
        prog = [
            0x00100093,  # addi x1, x0, 1
            0x00200113,  # addi x2, x0, 2
            0x00209463,  # bne x1, x2, +8
            0x00300193,  # addi x3, x0, 3  (skipped)
            0x00400193,  # addi x3, x0, 4
            0x00100073,  # ebreak
        ]
        iss = self._run_program(prog)
        assert iss.state.regs[3] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
