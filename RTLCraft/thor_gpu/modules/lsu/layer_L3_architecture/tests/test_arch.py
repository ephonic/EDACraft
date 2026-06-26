"""L3 ArchitectureIR tests for ThorLSU."""

import pytest

from thor_gpu.modules.lsu.layer_L3_architecture.src.arch import ARCH, describe


class TestLSUArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorLSU"

    def test_arch_contract(self):
        assert ARCH.data_width == 256
        assert ARCH.addr_width == 32
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
