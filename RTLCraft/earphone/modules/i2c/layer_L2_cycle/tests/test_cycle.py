"""L2 cycle model tests for EarphoneI2C."""

import pytest

from rtlgen import CycleContext
from earphone.modules.i2c.layer_L2_cycle.src.cycle import i2c_master_cycle_model, describe


class TestI2CCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneI2C"
        assert "idle" in info["states"]

    def test_write_transaction_completes(self):
        model = i2c_master_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 1, "start": 1, "addr": 0x50, "data": 0xAB, "rw": 0}

        # First call leaves idle and enters START condition
        model(ctx)
        assert ctx.state["state"] == "start"

        busy_seen = False
        done = 0
        for _ in range(100):
            ctx.inputs["start"] = 0
            model(ctx)
            if ctx.outputs.get("busy"):
                busy_seen = True
            if ctx.outputs.get("done"):
                done = 1
                break

        assert busy_seen
        assert done == 1
        assert ctx.state["state"] == "idle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
