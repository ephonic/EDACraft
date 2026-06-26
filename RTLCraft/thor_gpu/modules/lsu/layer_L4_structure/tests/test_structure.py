"""L4 StructuralIR tests for ThorLSU."""

import pytest

from thor_gpu.modules.lsu.layer_L4_structure.src.structure import STRUCTURE, describe


class TestLSUStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorLSU"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "request_gen" in names
        assert "response_cap" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
