"""L3 ArchitectureIR tests for ThorTensorCore."""

import pytest

from thor_gpu.modules.tensor_core.layer_L3_architecture.src.arch import ARCH, describe


class TestTensorCoreArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorTensorCore"
        assert info["layer"] == "L3_architecture"

    def test_arch_contract(self):
        assert (ARCH.m, ARCH.n, ARCH.k) == (8, 8, 8)
        assert ARCH.a_dtype == "INT8"
        assert ARCH.c_dtype == "INT32"
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
