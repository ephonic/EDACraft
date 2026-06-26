"""L4 StructuralIR tests for ThorVectorALU."""

import pytest

from thor_gpu.modules.vector_alu.layer_L4_structure.src.structure import STRUCTURE, describe


class TestVectorALUStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorALU"
        assert info["layer"] == "L4_structure"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "lane_slice_array" in names
        assert "result_register" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces  # each sub-block declares interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
