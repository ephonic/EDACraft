"""L5 DSL tests for EarphoneFFT256."""

import pytest

from earphone.modules.fft256.layer_L5_dsl.src.dsl import EarphoneFFT256
from rtlgen.codegen import VerilogEmitter
from rtlgen.sim import Simulator


class TestFFT256DSL:
    def test_instantiation(self):
        mod = EarphoneFFT256()
        assert mod.name == "earphone_fft256"

    def test_verilog_emit_non_empty(self):
        mod = EarphoneFFT256()
        verilog = VerilogEmitter().emit(mod)
        assert "module EarphoneFFT256" in verilog

    def test_simulator_reset(self):
        mod = EarphoneFFT256()
        sim = Simulator(mod)
        sim.reset("rst", cycles=2)
        assert sim.peek("do_en") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
