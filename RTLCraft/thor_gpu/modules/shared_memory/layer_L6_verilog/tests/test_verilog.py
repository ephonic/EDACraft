"""L6 Verilog emission tests for ThorSharedMemory."""

import pytest

from thor_gpu.modules.shared_memory.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestSharedMemoryVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_shared_memory.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorSharedMemory" in source
        assert lines > 0
        assert "rdata" in source and "addr" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
