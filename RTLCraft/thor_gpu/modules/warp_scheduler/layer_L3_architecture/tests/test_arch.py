"""L3 ArchitectureIR tests for ThorWarpScheduler."""

import pytest

from thor_gpu.modules.warp_scheduler.layer_L3_architecture.src.arch import ARCH, describe


class TestWarpSchedulerArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorWarpScheduler"

    def test_arch_contract(self):
        assert ARCH.num_warps == 4
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
