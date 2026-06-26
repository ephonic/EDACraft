"""L5 DSL simulation tests for ThorGpuSM."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.gpu_sm.layer_L5_dsl.src.dsl import ThorGpuSM, describe


class TestGpuSMDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorGpuSM"

    def test_instantiate_and_reset(self):
        dut = ThorGpuSM()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # After reset, sm_done is low (warps not done).
        assert sim.peek("sm_done") == 0

    def test_imem_write_and_start(self):
        dut = ThorGpuSM()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # Write a DONE instruction to imem[0].
        sim.poke("imem_wr_en", 1)
        sim.poke("imem_wr_addr", 0)
        sim.poke("imem_wr_data", 0xF0000000)  # OP_DONE
        sim.step()
        sim.poke("imem_wr_en", 0)
        sim.poke("start", 1)
        sim.step()
        # The execution core is running; sm_done depends on all warps reaching DONE.
        assert sim.peek("debug_w0_acc0") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
