"""L6 Verilog emission tests for ThorWarpScheduler."""

import pytest

from thor_gpu.modules.warp_scheduler.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestWarpSchedulerVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_warp_scheduler.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorWarpScheduler" in source
        assert lines > 0
        assert "warp_sel" in source and "barrier_release" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
