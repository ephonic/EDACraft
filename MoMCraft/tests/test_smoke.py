"""阶段 0 冒烟测试：验证 Python↔C++↔NumPy 零拷贝通路与 FreqSweep。"""
import numpy as np

import mom


def test_square_inplace():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    mom.square_inplace(a)
    np.testing.assert_allclose(a, [1.0, 4.0, 9.0, 16.0])


def test_freqsweep_linear_endpoints():
    sw = mom.FreqSweep(start=1e6, stop=10e9, count=11, scale="lin")
    f = sw.frequencies()
    assert f.shape == (11,)
    assert np.isclose(f[0], 1e6)
    assert np.isclose(f[-1], 10e9)
    # 等间距
    diffs = np.diff(f)
    assert np.allclose(diffs, diffs[0])


def test_freqsweep_log_endpoints_and_geometric():
    sw = mom.FreqSweep.linear(1e6, 1e9, 4)  # 4 点对数……但这里用了 linear，下面单独测 log
    sw_log = mom.FreqSweep.logarithmic(1e6, 1e9, 4)
    f = sw_log.frequencies()
    assert np.isclose(f[0], 1e6)
    assert np.isclose(f[-1], 1e9)
    # 对数刻度：相邻频点比为常数
    ratios = f[1:] / f[:-1]
    assert np.allclose(ratios, ratios[0])


def test_freqsweep_single_point():
    f = mom.FreqSweep(1e9, 1e9, 1).frequencies()
    assert f.shape == (1,)
    assert np.isclose(f[0], 1e9)


def test_freqsweep_validation():
    import pytest
    with pytest.raises(ValueError):
        mom.FreqSweep(start=1e9, stop=1e6, count=10)   # stop<start
    with pytest.raises(ValueError):
        mom.FreqSweep(start=0, stop=1e9, count=10, scale="log")  # log start<=0
    with pytest.raises(ValueError):
        mom.FreqSweep(1e6, 1e9, 0)                      # count<=0
