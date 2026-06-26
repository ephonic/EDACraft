"""L1 behavior model tests for ThorCluster."""

import pytest

from thor_gpu.modules.gpu_cluster import NSM, cluster_functional
from thor_gpu.modules.gpu_cluster.layer_L1_behavior.src.behavior import describe
from thor_gpu.modules.gpu_sm import OP_SLOAD, OP_VMAC, OP_DONE


def _enc(opcode, rd=0, rs1=0, rs2=0, imm=0):
    return ((opcode & 0xF) << 28) | ((rd & 0xF) << 24) | ((rs1 & 0xF) << 20) | ((rs2 & 0xF) << 16) | (imm & 0xFFFF)


class TestClusterBehavior:
    def test_describe(self):
        info = describe()
        assert info["nsm"] == 2

    def test_both_sms_complete(self):
        imems = [[_enc(OP_DONE)], [_enc(OP_DONE)]]
        res = cluster_functional(imems)
        assert res["all_done"] is True
        assert len(res["sm_results"]) == NSM

    def test_shared_vmac_acc(self):
        # Both SMs run: r1=2, r2=3, VMAC (lane0 2*3=6).
        prog = [_enc(OP_SLOAD, rd=1, imm=2), _enc(OP_SLOAD, rd=2, imm=3),
                _enc(OP_VMAC, rs1=1, rs2=2), _enc(OP_DONE)]
        res = cluster_functional([prog, prog])
        assert res["all_done"] is True
        assert res["warp_acc"][0][0] == 6
        assert res["warp_acc"][1][0] == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
