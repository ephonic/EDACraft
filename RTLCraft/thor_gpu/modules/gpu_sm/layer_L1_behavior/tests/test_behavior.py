"""L1 behavior model tests for ThorGpuSM."""

import pytest

from thor_gpu.modules.gpu_sm import (
    OP_SLOAD, OP_VADD, OP_VMUL, OP_VMAC, OP_DONE,
    sm_functional,
)
from thor_gpu.modules.gpu_sm.layer_L1_behavior.src.behavior import describe, _decode
from thor_gpu.modules.common.utils import _unpack_u32_lanes


def _enc(opcode, rd=0, rs1=0, rs2=0, imm=0):
    return ((opcode & 0xF) << 28) | ((rd & 0xF) << 24) | ((rs1 & 0xF) << 20) | ((rs2 & 0xF) << 16) | (imm & 0xFFFF)


class TestGpuSMBehavior:
    def test_describe(self):
        info = describe()
        assert info["nwarp"] == 4
        assert info["nlane"] == 8

    def test_decode(self):
        d = _decode(_enc(OP_VADD, rd=3, rs1=1, rs2=2, imm=0x1234))
        assert d["opcode"] == OP_VADD
        assert d["rd"] == 3 and d["rs1"] == 1 and d["rs2"] == 2
        assert d["imm"] == 0x1234

    def test_sload_vadd_done(self):
        # r1 = 5 (all lanes); r2 = 3 (all lanes); r3 = r1 + r2; done.
        imem = [
            _enc(OP_SLOAD, rd=1, imm=5),
            _enc(OP_SLOAD, rd=2, imm=3),
            _enc(OP_VADD, rd=3, rs1=1, rs2=2),
            _enc(OP_DONE),
        ]
        res = sm_functional(imem)
        assert all(res["warp_done"])
        # warp 0 VRF base = 0; r3 = index 3.
        r3 = _unpack_u32_lanes(res["vrf"][3])
        assert r3 == [8] * 8

    def test_vmul(self):
        imem = [
            _enc(OP_SLOAD, rd=1, imm=4),
            _enc(OP_SLOAD, rd=2, imm=5),
            _enc(OP_VMUL, rd=3, rs1=1, rs2=2),
            _enc(OP_DONE),
        ]
        res = sm_functional(imem)
        r3 = _unpack_u32_lanes(res["vrf"][3])
        assert r3 == [20] * 8

    def test_vmac_accumulator(self):
        # r1 = 2, r2 = 3; VMAC (lane0: 2*3=6) twice -> 12.
        imem = [
            _enc(OP_SLOAD, rd=1, imm=2),
            _enc(OP_SLOAD, rd=2, imm=3),
            _enc(OP_VMAC, rs1=1, rs2=2),
            _enc(OP_VMAC, rs1=1, rs2=2),
            _enc(OP_DONE),
        ]
        res = sm_functional(imem)
        assert res["warp_acc"][0] == 12

    def test_all_warps_run(self):
        imem = [_enc(OP_DONE)]
        res = sm_functional(imem)
        assert all(res["warp_done"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
