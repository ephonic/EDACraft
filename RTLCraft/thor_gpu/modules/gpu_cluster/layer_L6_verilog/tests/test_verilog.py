"""L6 Verilog emission tests for ThorCluster."""

import pytest

from thor_gpu.modules.gpu_cluster.layer_L6_verilog.src.emitter import emit_verilog, describe


class TestClusterVerilog:
    def test_describe(self):
        info = describe()
        assert info["file_name"] == "thor_cluster.v"

    def test_emit_produces_verilog(self):
        source, lines = emit_verilog()
        assert "module ThorCluster" in source
        assert lines > 0
        assert "all_done" in source and "start" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
