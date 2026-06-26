"""L1 behavior model tests for ThorSIMTStack."""

import pytest

from thor_gpu.modules.simt_stack import simt_push, simt_pop, simt_functional
from thor_gpu.modules.simt_stack.layer_L1_behavior.src.behavior import describe


class TestSIMTStackBehavior:
    def test_describe(self):
        info = describe()
        assert info["max_depth"] == 8
        assert info["mask_width"] == 8

    def test_push_pop_roundtrip(self):
        stack = []
        simt_push(stack, 0x1000, 0b00001111)
        assert len(stack) == 1
        rpc, mask = simt_pop(stack)
        assert rpc == 0x1000
        assert mask == 0b00001111
        assert len(stack) == 0

    def test_push_functional(self):
        stack = []
        res = simt_functional(stack, push=1, pop=0, branch_pc=0x2000,
                              reconverge_pc=0x3000, taken_mask=0b10101010,
                              active_mask=0b11111111)
        assert res["next_pc"] == 0x2000
        assert res["next_mask"] == 0b10101010  # active & taken
        assert res["stack_depth"] == 1
        # Saved not-taken mask.
        assert stack[0] == (0x3000, 0b01010101)

    def test_pop_functional(self):
        stack = [(0x4000, 0b00000011)]
        res = simt_functional(stack, push=0, pop=1, branch_pc=0,
                              reconverge_pc=0, taken_mask=0, active_mask=0xFF)
        assert res["next_pc"] == 0x4000
        assert res["next_mask"] == 0b00000011
        assert res["stack_depth"] == 0

    def test_pop_empty(self):
        stack = []
        res = simt_functional(stack, push=0, pop=1, branch_pc=0,
                              reconverge_pc=0, taken_mask=0, active_mask=0xFF)
        assert res["next_pc"] == 0
        assert res["next_mask"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
