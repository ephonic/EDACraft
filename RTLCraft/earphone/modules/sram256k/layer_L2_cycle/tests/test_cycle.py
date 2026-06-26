"""L2 cycle model tests for EarphoneSRAM256K."""

import pytest

from earphone.modules.sram256k.layer_L2_cycle.src.cycle import describe


class TestSRAM256KCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneSRAM256K"
        assert info["layer"] == "L2_cycle"
        assert info["read_latency_cycles"] == 1
        assert info["write_latency_cycles"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
