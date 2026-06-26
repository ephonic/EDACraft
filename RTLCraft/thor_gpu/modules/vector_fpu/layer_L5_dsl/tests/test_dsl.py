"""L5 DSL simulation tests for ThorVectorFPU.

The L5 block is a structural datapath (FP core black-box in v0.1), so these
tests verify structural behavior: instantiation, predication, result-mask,
reset, and that the routed operand appears on the result. FP32 numerical
correctness is covered by L1/L2.
"""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.vector_fpu.layer_L5_dsl.src.dsl import ThorVectorFPU, describe
from thor_gpu.modules.common.utils import _pack_u32_lanes, _unpack_u32_lanes, _fp32_to_f32_bits


class TestVectorFPUDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorVectorFPU"

    def test_instantiate_and_simulate(self):
        dut = ThorVectorFPU()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        a = _pack_u32_lanes([_fp32_to_f32_bits(1.0)] * 8)
        sim.poke("src1", a)
        sim.poke("src2", 0)
        sim.poke("src3", 0)
        sim.poke("active_mask", 0xFF)
        sim.poke("fpu_fn", 0)
        sim.poke("valid_in", 1)
        sim.step()
        # Structural v0.1 routes src1 to result; all lanes active.
        assert sim.peek("result") == a
        assert sim.peek("result_mask") == 0xFF
        assert sim.peek("valid") == 1

    def test_predication_zeros_disabled_lanes(self):
        dut = ThorVectorFPU()
        sim = Simulator(dut)
        sim.reset(rst="rst_n")
        a = _pack_u32_lanes([_fp32_to_f32_bits(i + 1) for i in range(8)])
        sim.poke("src1", a)
        sim.poke("src2", 0)
        sim.poke("src3", 0)
        sim.poke("active_mask", 0b00000001)
        sim.poke("fpu_fn", 0)
        sim.poke("valid_in", 1)
        sim.step()
        lanes = _unpack_u32_lanes(sim.peek("result"))
        assert lanes[0] == _fp32_to_f32_bits(1.0)
        assert all(v == 0 for v in lanes[1:])
        assert sim.peek("result_mask") == 0b00000001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
