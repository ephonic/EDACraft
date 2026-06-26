"""L4 StructuralIR tests for ThorGpuSM."""

import pytest

from thor_gpu.modules.gpu_sm.layer_L4_structure.src.structure import STRUCTURE, describe


class TestGpuSMStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorGpuSM"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "warp_scheduler" in names
        assert "vrf" in names
        assert "imem" in names
        assert "vmac_acc" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
