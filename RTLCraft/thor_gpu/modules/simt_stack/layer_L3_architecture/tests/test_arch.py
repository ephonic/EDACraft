"""L3 ArchitectureIR tests for ThorSIMTStack."""

import pytest

from thor_gpu.modules.simt_stack.layer_L3_architecture.src.arch import ARCH, describe


class TestSIMTStackArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSIMTStack"

    def test_arch_contract(self):
        assert ARCH.max_depth == 8
        assert ARCH.mask_width == 8
        assert ARCH.pc_width == 32
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
