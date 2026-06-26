"""L1 behavior model tests for ThorWarpScheduler."""

import pytest

from thor_gpu.modules.warp_scheduler import NWARP, scheduler_step
from thor_gpu.modules.warp_scheduler.layer_L1_behavior.src.behavior import describe


class TestWarpSchedulerBehavior:
    def test_describe(self):
        info = describe()
        assert info["num_warps"] == 4

    def test_sticky_when_busy(self):
        # warp 0 busy (idle bit 0 = 0) -> sel stays at 0.
        res = scheduler_step(warp_sel=0, warp_idle=0b0000, warp_done=0, warp_at_barrier=0)
        assert res["warp_sel"] == 0

    def test_advance_when_idle(self):
        # warp 0 idle -> sel advances to 1.
        res = scheduler_step(warp_sel=0, warp_idle=0b0001, warp_done=0, warp_at_barrier=0)
        assert res["warp_sel"] == 1

    def test_wraparound(self):
        # warp 3 idle -> sel wraps to 0.
        res = scheduler_step(warp_sel=3, warp_idle=0b1000, warp_done=0, warp_at_barrier=0)
        assert res["warp_sel"] == 0

    def test_barrier_release(self):
        # all warps at barrier -> barrier_release=1.
        res = scheduler_step(warp_sel=0, warp_idle=0, warp_done=0, warp_at_barrier=0b1111)
        assert res["barrier_release"] == 1

    def test_barrier_partial(self):
        res = scheduler_step(warp_sel=0, warp_idle=0, warp_done=0, warp_at_barrier=0b0111)
        assert res["barrier_release"] == 0

    def test_sm_done(self):
        res = scheduler_step(warp_sel=0, warp_idle=0b1111, warp_done=0b1111, warp_at_barrier=0)
        assert res["sm_done"] == 1

    def test_sm_not_done(self):
        res = scheduler_step(warp_sel=0, warp_idle=0b1111, warp_done=0b0111, warp_at_barrier=0)
        assert res["sm_done"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
