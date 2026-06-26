"""L2 cycle model tests for ThorSIMTStack."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.simt_stack.layer_L2_cycle.src.cycle import simt_cycle_model, describe


class TestSIMTStackCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSIMTStack"

    def test_reset_clears(self):
        model = simt_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["stack_depth"] == 0

    def test_push_then_pop(self):
        model = simt_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 1, "push": 1, "pop": 0, "branch_pc": 0x2000,
                      "reconverge_pc": 0x3000, "taken_mask": 0b10101010,
                      "active_mask": 0xFF}
        model(ctx)
        assert ctx.outputs["next_pc"] == 0x2000
        assert ctx.outputs["next_mask"] == 0b10101010
        assert ctx.outputs["stack_depth"] == 1
        # Pop.
        ctx.state["stack"] = [(0x3000, 0b01010101)]  # ensure frame present
        ctx.inputs = {"rst_n": 1, "push": 0, "pop": 1, "branch_pc": 0,
                      "reconverge_pc": 0, "taken_mask": 0, "active_mask": 0xFF}
        model(ctx)
        assert ctx.outputs["next_pc"] == 0x3000
        assert ctx.outputs["next_mask"] == 0b01010101
        assert ctx.outputs["stack_depth"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
