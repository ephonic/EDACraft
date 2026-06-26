"""L6 Verilog emission tests for ThorVectorFPU."""

import pytest

from thor_gpu.modules.vector_fpu.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestVectorFPUVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_vector_fpu.v"
        assert info["dsl_class"] == "ThorVectorFPU"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorVectorFPU" in source
        assert lines > 0
        assert "result" in source and "src1" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
