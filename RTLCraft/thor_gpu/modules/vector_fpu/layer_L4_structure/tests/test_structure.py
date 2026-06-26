"""L4 StructuralIR tests for ThorVectorFPU."""

import pytest

from thor_gpu.modules.vector_fpu.layer_L4_structure.src.structure import STRUCTURE, describe


class TestVectorFPUStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorFPU"
        assert info["layer"] == "L4_structure"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "fp_lane_array" in names
        assert "result_register" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
