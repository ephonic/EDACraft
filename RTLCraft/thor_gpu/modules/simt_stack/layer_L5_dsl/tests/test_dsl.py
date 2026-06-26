"""L5 DSL simulation tests for ThorSIMTStack."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.simt_stack.layer_L5_dsl.src.dsl import ThorSIMTStack, describe


class TestSIMTStackDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorSIMTStack"

    def test_instantiate_and_push(self):
        dut = ThorSIMTStack()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        sim.poke("push", 1)
        sim.poke("pop", 0)
        sim.poke("branch_pc", 0x2000)
        sim.poke("reconverge_pc", 0x3000)
        sim.poke("taken_mask", 0b10101010)
        sim.poke("active_mask", 0xFF)
        sim.step()
        # Combinational outputs reflect the push path.
        assert sim.peek("next_pc") == 0x2000
        assert sim.peek("next_mask") == 0b10101010
        assert sim.peek("stack_depth") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
