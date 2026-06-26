"""L6 Verilog emission tests for ThorVectorALU."""

import pytest

from thor_gpu.modules.vector_alu.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestVectorALUVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_vector_alu.v"
        assert info["dsl_class"] == "ThorVectorALU"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        # Emitter uses the DSL class name for the module declaration.
        assert "module ThorVectorALU" in source
        assert lines > 0
        # Core ports present.
        assert "src1" in source and "result" in source and "alu_fn" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
