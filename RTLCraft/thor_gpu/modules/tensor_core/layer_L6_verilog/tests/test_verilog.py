"""L6 Verilog emission tests for ThorTensorCore."""

import pytest

from thor_gpu.modules.tensor_core.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestTensorCoreVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_tensor_core.v"
        assert info["dsl_class"] == "ThorTensorCore"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorTensorCore" in source
        assert lines > 0
        assert "result" in source and "start" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
