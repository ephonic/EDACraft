"""L3 ArchitectureIR tests for ThorVectorALU."""

import pytest

from thor_gpu.modules.vector_alu.layer_L3_architecture.src.arch import ARCH, describe


class TestVectorALUArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorALU"
        assert info["layer"] == "L3_architecture"

    def test_arch_contract(self):
        assert ARCH.lane_count == 8
        assert ARCH.lane_width == 32
        assert ARCH.vector_width == 256
        assert ARCH.latency_cycles == 1
        assert len(ARCH.stages) == 2
        assert ARCH.invariants  # non-empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
