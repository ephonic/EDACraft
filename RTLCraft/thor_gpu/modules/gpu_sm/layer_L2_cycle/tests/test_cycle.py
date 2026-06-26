"""L2 cycle model tests for ThorGpuSM."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.gpu_sm.layer_L2_cycle.src.cycle import sm_cycle_model, describe
from thor_gpu.modules.gpu_sm import OP_VMAC, OP_DONE, OP_SLOAD, sm_functional


def _enc(opcode, rd=0, rs1=0, rs2=0, imm=0):
    return ((opcode & 0xF) << 28) | ((rd & 0xF) << 24) | ((rs1 & 0xF) << 20) | ((rs2 & 0xF) << 16) | (imm & 0xFFFF)


class TestGpuSMCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorGpuSM"

    def test_reset_clears(self):
        model = sm_cycle_model([_enc(OP_DONE)])
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["sm_done"] == 0

    def test_start_completes(self):
        imem = [_enc(OP_SLOAD, rd=1, imm=2), _enc(OP_SLOAD, rd=2, imm=3),
                _enc(OP_VMAC, rs1=1, rs2=2), _enc(OP_DONE)]
        model = sm_cycle_model(imem)
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 1, "start": 1}
        model(ctx)
        assert ctx.outputs["sm_done"] == 1
        # VMAC lane0 2*3 = 6.
        assert ctx.outputs["debug_w0_acc0"] == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
