"""L6 Verilog emission tests for ThorSIMTStack."""

import pytest

from thor_gpu.modules.simt_stack.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestSIMTStackVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_simt_stack.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorSIMTStack" in source
        assert lines > 0
        assert "next_pc" in source and "push" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
