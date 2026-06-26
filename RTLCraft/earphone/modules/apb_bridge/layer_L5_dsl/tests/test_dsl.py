"""L5 DSL tests for EarphoneAPBBridge."""

import pytest

from earphone.modules.apb_bridge.layer_L5_dsl.src.dsl import EarphoneAPBBridge
from rtlgen.sim import Simulator


class TestAPBBridgeDSL:
    @pytest.fixture
    def bridge(self):
        return EarphoneAPBBridge()

    def _make_sim(self, bridge):
        sim = Simulator(bridge)
        sim.reset("rst_n", cycles=1)
        return sim

    def test_decode_qspi_region(self, bridge):
        sim = self._make_sim(bridge)
        sim.poke("m_paddr", 0x4000_0000)
        sim.poke("m_psel", 1)
        sim.step()
        assert sim.peek("s_psel") == 0b0000_0001

    def test_decode_sram_region(self, bridge):
        sim = self._make_sim(bridge)
        # slot 1 occupies region 1: base + 1<<22
        sim.poke("m_paddr", 0x4000_0000 + (1 << 22))
        sim.poke("m_psel", 1)
        sim.step()
        assert sim.peek("s_psel") == 0b0000_0010

    def test_decode_simd16_region(self, bridge):
        sim = self._make_sim(bridge)
        sim.poke("m_paddr", 0x4000_0000 + (7 << 22))
        sim.poke("m_psel", 1)
        sim.step()
        assert sim.peek("s_psel") == 0b1000_0000

    def test_slave_response_mux(self, bridge):
        sim = self._make_sim(bridge)
        sim.poke("m_paddr", 0x4000_0000 + (2 << 22))  # SPI slot 2
        sim.poke("m_psel", 1)
        sim.poke("m_penable", 1)
        # Only slot 2 asserts pready/pslverr when its bit is set
        sim.poke("s_pready", 0b0000_0100)
        sim.poke("s_pslverr", 0b0000_0100)
        sim.poke("s_prdata", 0xDEADBEEF)
        sim.step()
        assert sim.peek("m_pready") == 1
        assert sim.peek("m_pslverr") == 1
        assert sim.peek("m_prdata") == 0xDEADBEEF

    def test_unselected_no_pready(self, bridge):
        sim = self._make_sim(bridge)
        sim.poke("m_psel", 0)
        sim.poke("s_pready", 0)
        sim.step()
        assert sim.peek("m_pready") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
