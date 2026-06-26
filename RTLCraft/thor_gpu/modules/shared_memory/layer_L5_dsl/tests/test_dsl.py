"""L5 DSL simulation tests for ThorSharedMemory."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.shared_memory.layer_L5_dsl.src.dsl import ThorSharedMemory, describe


class TestSharedMemoryDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorSharedMemory"

    def test_write_then_read(self):
        dut = ThorSharedMemory()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        # Write addr=4, data=0xBEEF.
        sim.poke("addr", 4)
        sim.poke("wdata", 0xBEEF)
        sim.poke("we", 1)
        sim.poke("re", 0)
        sim.step()
        # Read addr=4 (registered read: data valid after the step).
        sim.poke("we", 0)
        sim.poke("re", 1)
        sim.poke("addr", 4)
        sim.step()
        assert sim.peek("rdata") == 0xBEEF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
