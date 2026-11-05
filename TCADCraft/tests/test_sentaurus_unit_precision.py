"""A nonzero extended-precision coefficient must not silently become zero."""
import numpy as np
import pytest

from tcad.validation import native_lk_to_sentaurus, sentaurus_lk_to_native


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("direction", ["import", "export"])
def test_extended_precision_alpha_underflow_is_rejected(sign, direction):
    if np.finfo(np.longdouble).minexp >= np.finfo(float).minexp:
        pytest.skip("extended exponent range is unavailable on this platform")
    value = sign * np.ldexp(np.longdouble(1), -1100)
    assert value != 0 and float(value) == 0.
    with pytest.raises(ValueError, match="underflow"):
        if direction == "export":
            native_lk_to_sentaurus(value, 1e12, .1)
        else:
            sentaurus_lk_to_native(dict(alpha=value, beta=2.5e21, gamma=0., g=0., rho=10.))


@pytest.mark.parametrize("alpha", [np.longdouble(0), np.longdouble(-1e8),
                                 np.longdouble(1e-300), np.longdouble(-1e-300)])
def test_representable_extended_precision_alpha_keeps_its_sign(alpha):
    result = sentaurus_lk_to_native(native_lk_to_sentaurus(alpha, 1e12, .1))
    assert result["alpha"] == pytest.approx(float(alpha), rel=1e-14, abs=0.)
