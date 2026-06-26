"""L5 DSL tests for EarphoneSRAM256K."""

import pytest

from earphone.modules.sram256k.layer_L5_dsl.src.dsl import EarphoneSRAM256K
from rtlgen.sim import Simulator


class TestSRAM256KDSL:
    @pytest.fixture
    def sram(self):
        return EarphoneSRAM256K()

    def _apb_write(self, sim, addr, data, pstrb=0b1111):
        sim.poke("paddr", addr)
        sim.poke("pwdata", data)
        sim.poke("pwrite", 1)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.poke("pstrb", pstrb)
        sim.step()

    def _apb_read(self, sim, addr):
        sim.poke("paddr", addr)
        sim.poke("pwrite", 0)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.step()
        return sim.peek("prdata")

    def test_full_word_write_read(self, sram):
        sim = Simulator(sram)
        sim.reset("rst_n", cycles=2)
        self._apb_write(sim, 0x40, 0xDEADBEEF)
        rdata = self._apb_read(sim, 0x40)
        assert rdata == 0xDEADBEEF

    def test_byte_masked_write(self, sram):
        sim = Simulator(sram)
        sim.reset("rst_n", cycles=2)
        self._apb_write(sim, 0x44, 0xFFFFFFFF)
        self._apb_write(sim, 0x44, 0xAABBCCDD, pstrb=0b0101)
        rdata = self._apb_read(sim, 0x44)
        expected = (0xFF << 24) | (0xBB << 16) | (0xFF << 8) | 0xDD
        assert rdata == expected

    def test_unselected_idle(self, sram):
        sim = Simulator(sram)
        sim.reset("rst_n", cycles=2)
        sim.poke("psel", 0)
        sim.poke("penable", 0)
        sim.step()
        # pready should remain 0 when no transfer is selected
        assert sim.peek("pready") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
