"""L4 StructuralIR tests for ThorSharedMemory."""

import pytest

from thor_gpu.modules.shared_memory.layer_L4_structure.src.structure import STRUCTURE, describe


class TestSharedMemoryStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSharedMemory"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "sram_array" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
