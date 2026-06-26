"""L2 cycle model tests for ThorLSU."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.lsu.layer_L2_cycle.src.cycle import lsu_cycle_model, describe


class TestLSUCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorLSU"

    def test_reset_clears(self):
        model = lsu_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["mem_req"] == 0

    def test_request_then_response(self):
        model = lsu_cycle_model()
        ctx = CycleContext()
        # Issue a load.
        ctx.inputs = {"rst_n": 1, "valid_in": 1, "op": 0, "addr": 0x40, "wdata": 0,
                      "mem_ready": 1, "mem_valid": 0, "mem_rdata": 0}
        model(ctx)
        assert ctx.outputs["mem_req"] == 1
        assert ctx.outputs["mem_wen"] == 0
        assert ctx.outputs["done"] == 0
        # Deliver response.
        ctx.inputs = {"rst_n": 1, "valid_in": 0, "op": 0, "addr": 0x40, "wdata": 0,
                      "mem_ready": 1, "mem_valid": 1, "mem_rdata": 0xBEEF}
        model(ctx)
        assert ctx.outputs["rdata"] == 0xBEEF
        assert ctx.outputs["done"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
