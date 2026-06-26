"""L5 DSL simulation tests for ThorCluster."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.gpu_cluster.layer_L5_dsl.src.dsl import ThorCluster, describe


class TestClusterDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorCluster"

    def test_instantiate_and_reset(self):
        dut = ThorCluster()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # After reset, all_done is low.
        assert sim.peek("all_done") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
