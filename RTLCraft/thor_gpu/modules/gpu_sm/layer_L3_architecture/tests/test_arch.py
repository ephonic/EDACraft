"""L3 ArchitectureIR tests for ThorGpuSM."""

import pytest

from thor_gpu.modules.gpu_sm.layer_L3_architecture.src.arch import ARCH, describe


class TestGpuSMArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorGpuSM"

    def test_arch_contract(self):
        assert (ARCH.xlen, ARCH.nlane, ARCH.vlen) == (32, 8, 256)
        assert ARCH.vregs == 8
        assert ARCH.nwarp == 4
        assert ARCH.imem_depth == 32
        assert ARCH.accw == 64
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
