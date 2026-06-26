"""L4 StructuralIR tests for ThorSIMTStack."""

import pytest

from thor_gpu.modules.simt_stack.layer_L4_structure.src.structure import STRUCTURE, describe


class TestSIMTStackStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSIMTStack"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "stack_storage" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
