"""L5 DSL simulation tests for ThorLSU."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.lsu.layer_L5_dsl.src.dsl import ThorLSU, describe


class TestLSUDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorLSU"

    def test_request_and_response(self):
        dut = ThorLSU()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # Issue a load request.
        sim.poke("valid_in", 1)
        sim.poke("op", 0)
        sim.poke("addr", 0x40)
        sim.poke("wdata", 0)
        sim.poke("mem_ready", 1)
        sim.poke("mem_valid", 1)
        sim.poke("mem_rdata", 0xBEEF)
        sim.step()
        assert sim.peek("mem_req") == 1
        assert sim.peek("mem_wen") == 0
        assert sim.peek("rdata") == 0xBEEF
        assert sim.peek("done") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
