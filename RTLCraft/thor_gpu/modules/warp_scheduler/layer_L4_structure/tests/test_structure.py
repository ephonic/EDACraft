"""L4 StructuralIR tests for ThorWarpScheduler."""

import pytest

from thor_gpu.modules.warp_scheduler.layer_L4_structure.src.structure import STRUCTURE, describe


class TestWarpSchedulerStructure:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorWarpScheduler"

    def test_subblocks_present(self):
        names = [sb.name for sb in STRUCTURE.subblocks]
        assert "sticky_rr_logic" in names
        assert "barrier_sync" in names
        for sb in STRUCTURE.subblocks:
            assert sb.interfaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
