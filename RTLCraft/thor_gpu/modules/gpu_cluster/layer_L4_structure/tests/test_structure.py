"""L4 StructuralIR tests for ThorCluster."""

import pytest

from thor_gpu.modules.gpu_cluster.layer_L4_structure.src.structure import STRUCTURE, describe


class TestClusterStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorCluster"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "sm_array" in names
        assert "l2_arbiter" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
