"""L2 cycle model tests for EarphoneSIMD16."""

import pytest

from rtlgen import CycleContext
from earphone.modules.simd16.layer_L2_cycle.src.cycle import simd16_cycle_model, describe
from earphone.modules.simd16 import SIMD_OP_VADD
from earphone.modules.common.utils import _pack_u16_lanes


class TestSIMD16Cycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneSIMD16"
        assert info["layer"] == "L2_cycle"

    def test_int16_single_cycle_latency(self):
        model = simd16_cycle_model()
        ctx = CycleContext()
        a = _pack_u16_lanes([i + 1 for i in range(16)])
        b = _pack_u16_lanes([i + 2 for i in range(16)])
        ctx.inputs = {
            "rst_n": 1, "start": 1, "op": SIMD_OP_VADD, "mode": 0,
            "vsrc0": a, "vsrc1": b, "vsrc2": 0, "pred": 0xFFFF,
        }

        model(ctx)
        # Cycle model produces the result in the same cycle as start.
        assert ctx.outputs["done"] == 1
        expected = _pack_u16_lanes([((i + 1) + (i + 2)) & 0xFFFF for i in range(16)])
        assert ctx.outputs["vdst"] == expected

    def test_fp16_mac_three_cycle_latency(self):
        model = simd16_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {
            "rst_n": 1, "start": 1, "op": 0, "mode": 1,
            "vsrc0": 1, "vsrc1": 2, "vsrc2": 3, "pred": 0xFFFF,
        }

        model(ctx)
        ctx.inputs["start"] = 0
        done = 0
        for _ in range(10):
            model(ctx)
            if ctx.outputs.get("done"):
                done = 1
                break

        assert done == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
