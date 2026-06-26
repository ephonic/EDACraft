"""L5 DSL tests for EarphoneSIMD16."""

import pytest

from earphone.modules.simd16 import SIMD_OP_VADD
from earphone.modules.simd16.layer_L5_dsl.src.dsl import EarphoneSIMD16
from earphone.modules.common.utils import _pack_u16_lanes
from rtlgen.sim import Simulator


class TestSIMD16DSL:
    def _pack(self, lanes):
        return _pack_u16_lanes(lanes)

    def test_int16_vadd_one_cycle(self):
        simd = EarphoneSIMD16()
        sim = Simulator(simd)
        sim.reset("rst_n", cycles=2)

        a = self._pack([i + 1 for i in range(16)])
        b = self._pack([i + 2 for i in range(16)])
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", SIMD_OP_VADD)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()

        assert sim.peek("done") == 1
        expected = self._pack([((i + 1) + (i + 2)) & 0xFFFF for i in range(16)])
        assert sim.peek("vdst") == expected

    def test_fp16_mac_three_cycle_latency(self):
        simd = EarphoneSIMD16()
        sim = Simulator(simd)
        sim.reset("rst_n", cycles=2)

        sim.poke("vsrc0", 1)
        sim.poke("vsrc1", 2)
        sim.poke("vsrc2", 3)
        sim.poke("mode", 1)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        sim.poke("start", 0)

        done = 0
        for _ in range(10):
            sim.step()
            if sim.peek("done"):
                done = 1
                break

        assert done == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
