"""L3 ArchitectureIR tests for ThorSharedMemory."""

import pytest

from thor_gpu.modules.shared_memory.layer_L3_architecture.src.arch import ARCH, describe


class TestSharedMemoryArch:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSharedMemory"

    def test_arch_contract(self):
        assert ARCH.word_width == 256
        assert ARCH.addr_width == 12
        assert ARCH.depth == 4096
        assert ARCH.latency_cycles == 1
        assert ARCH.invariants


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
