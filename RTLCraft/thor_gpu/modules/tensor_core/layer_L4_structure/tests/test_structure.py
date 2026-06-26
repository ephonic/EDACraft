"""L4 StructuralIR tests for ThorTensorCore."""

import pytest

from thor_gpu.modules.tensor_core.layer_L4_structure.src.structure import STRUCTURE, describe


class TestTensorCoreStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorTensorCore"
        assert info["layer"] == "L4_structure"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "mac_array" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
