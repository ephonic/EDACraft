"""L2 cycle model tests for ThorWarpScheduler."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.warp_scheduler.layer_L2_cycle.src.cycle import scheduler_cycle_model, describe


class TestWarpSchedulerCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorWarpScheduler"

    def test_reset_clears(self):
        model = scheduler_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["warp_sel"] == 0
        assert ctx.outputs["sm_done"] == 0

    def test_advance_when_idle(self):
        model = scheduler_cycle_model()
        ctx = CycleContext()
        ctx.state["warp_sel"] = 0
        ctx.inputs = {"rst_n": 1, "warp_idle": 0b0001, "warp_done": 0, "warp_at_barrier": 0}
        model(ctx)
        assert ctx.outputs["warp_sel"] == 1

    def test_sticky_when_busy(self):
        model = scheduler_cycle_model()
        ctx = CycleContext()
        ctx.state["warp_sel"] = 0
        ctx.inputs = {"rst_n": 1, "warp_idle": 0b0000, "warp_done": 0, "warp_at_barrier": 0}
        model(ctx)
        assert ctx.outputs["warp_sel"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
