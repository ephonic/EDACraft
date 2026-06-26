"""L1 behavior model tests for EarphoneFFT256."""

import pytest

from earphone.modules.fft256 import fft256_functional


class TestFFT256Functional:
    def test_impulse_response(self):
        samples_re = [32767] + [0] * 255
        samples_im = [0] * 256
        out_re, out_im = fft256_functional(samples_re, samples_im)
        # Impulse -> all bins equal to the input magnitude / 256 * scale = 128
        assert out_re[0] == 128
        assert all(v == 128 for v in out_re)
        assert all(v == 0 for v in out_im)

    def test_dc_response(self):
        samples_re = [1000] * 256
        samples_im = [0] * 256
        out_re, out_im = fft256_functional(samples_re, samples_im)
        # DC input -> energy only in bin 0
        assert out_re[0] == 1000
        assert all(v == 0 for v in out_re[1:])
        assert all(v == 0 for v in out_im)

    def test_describe(self):
        from earphone.modules.fft256.layer_L1_behavior.src.behavior import describe
        info = describe()
        assert info["name"] == "EarphoneFFT256"
        assert info["points"] == 256


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
