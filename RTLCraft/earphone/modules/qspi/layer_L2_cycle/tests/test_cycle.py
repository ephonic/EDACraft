"""L2 cycle model tests for EarphoneQSPI."""

import pytest

from rtlgen import CycleContext
from earphone.modules.qspi.layer_L2_cycle.src.cycle import qspi_cycle_model, describe


class TestQSPICycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneQSPI"
        assert "idle" in info["states"]

    def test_xip_read_fsm_completes(self):
        model = qspi_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 1, "req": 1, "addr": 0x1000}

        model(ctx)
        assert ctx.state["state"] == "cmd"

        ready = 0
        rdata = 0
        for _ in range(100):
            ctx.inputs["req"] = 0
            model(ctx)
            if ctx.outputs.get("ready"):
                ready = 1
                rdata = ctx.outputs.get("rdata", 0)
                break

        assert ready == 1
        assert rdata == 0  # uninitialized flash returns 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
