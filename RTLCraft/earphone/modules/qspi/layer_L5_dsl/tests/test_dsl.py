"""L5 DSL tests for EarphoneQSPI."""

import pytest

from earphone.modules.qspi.layer_L5_dsl.src.dsl import EarphoneQSPI
from rtlgen.sim import Simulator


class TestQSPIDSL:
    @pytest.fixture
    def qspi(self):
        return EarphoneQSPI()

    def test_xip_read_completes(self, qspi):
        sim = Simulator(qspi)
        sim.reset("rst_n", cycles=2)

        sim.poke("req", 1)
        sim.poke("addr", 0x1000)
        sim.poke("qspi_io_i", 0xA)
        sim.step()

        sim.poke("req", 0)
        ready = 0
        for _ in range(100):
            sim.poke("qspi_io_i", 0xA)
            sim.step()
            if sim.peek("ready"):
                ready = 1
                break

        assert ready == 1
        # The FSM loads 8 nibbles (32 bits) before asserting ready.
        assert sim.peek("rdata") == 0xAAAAAAAA

    def test_idle_cs_n_high(self, qspi):
        sim = Simulator(qspi)
        sim.reset("rst_n", cycles=2)
        sim.poke("req", 0)
        sim.step()
        assert sim.peek("qspi_cs_n") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
