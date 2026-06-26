"""L3 ArchitectureIR tests for ThorCluster."""

import pytest

from thor_gpu.modules.gpu_cluster.layer_L3_architecture.src.arch import ARCH, describe


class TestClusterArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorCluster"

    def test_arch_contract(self):
        assert ARCH.nsm == 2
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
