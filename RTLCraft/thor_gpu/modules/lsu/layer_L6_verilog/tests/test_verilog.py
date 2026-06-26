"""L6 Verilog emission tests for ThorLSU."""

import pytest

from thor_gpu.modules.lsu.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestLSUVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_lsu.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorLSU" in source
        assert lines > 0
        assert "mem_req" in source and "rdata" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
