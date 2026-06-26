"""L5 DSL simulation tests for ThorWarpScheduler."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.warp_scheduler.layer_L5_dsl.src.dsl import ThorWarpScheduler, describe


class TestWarpSchedulerDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorWarpScheduler"

    def test_advance_when_current_idle(self):
        dut = ThorWarpScheduler()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # warp_sel starts at 0; warp 0 idle -> advances to 1.
        sim.poke("warp_idle", 0b0001)
        sim.poke("warp_done", 0)
        sim.poke("warp_at_barrier", 0)
        sim.step()
        assert sim.peek("warp_sel") == 1

    def test_sticky_when_current_busy(self):
        dut = ThorWarpScheduler()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        sim.poke("warp_idle", 0b0000)  # warp 0 busy
        sim.poke("warp_done", 0)
        sim.poke("warp_at_barrier", 0)
        sim.step()
        assert sim.peek("warp_sel") == 0

    def test_sm_done(self):
        dut = ThorWarpScheduler()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        sim.poke("warp_idle", 0b1111)
        sim.poke("warp_done", 0b1111)
        sim.poke("warp_at_barrier", 0)
        sim.step()
        assert sim.peek("sm_done") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
