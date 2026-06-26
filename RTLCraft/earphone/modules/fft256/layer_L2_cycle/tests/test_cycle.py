"""L2 cycle model tests for EarphoneFFT256."""

import pytest

from earphone.modules.fft256.layer_L2_cycle.src.cycle import describe


class TestFFT256Cycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "fft256"
        assert info["layer"] == "L2_cycle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
