"""L6 Verilog emission tests for ThorGpuSM."""

import pytest

from thor_gpu.modules.gpu_sm.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestGpuSMVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_gpu_sm.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorGpuSM" in source
        assert lines > 0
        assert "sm_done" in source and "imem_wr_en" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
