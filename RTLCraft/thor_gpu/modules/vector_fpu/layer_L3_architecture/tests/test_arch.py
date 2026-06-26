"""L3 ArchitectureIR tests for ThorVectorFPU."""

import pytest

from thor_gpu.modules.vector_fpu.layer_L3_architecture.src.arch import ARCH, describe


class TestVectorFPUArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorFPU"
        assert info["layer"] == "L3_architecture"

    def test_arch_contract(self):
        assert ARCH.datatype == "FP32"
        assert ARCH.lane_count == 8
        assert ARCH.function_codes == [0, 1, 2]
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
