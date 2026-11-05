"""Compiled precision is observable independently of build-time environment."""
import os
import numpy as np
from tcad.core import native_precision, PyDeviceSimulator


def test_precision_reports_the_loaded_binary_and_owns_its_metadata(monkeypatch):
    info = native_precision()
    assert info['backend'] in ('float128', 'long_double')
    assert info['mantissa_bits'] >= 53
    assert info['max_decimal_exponent'] >= 308
    assert info['exported_array_dtype'] == 'float64'
    if info['backend'] == 'float128':
        assert info['mantissa_bits'] == 113
        assert info['max_decimal_exponent'] == 4932
    expected = os.environ.get('TCAD_EXPECT_PRECISION')
    if expected:
        assert info['backend'] == expected
    monkeypatch.setenv('TCAD_FORCE_LONG_DOUBLE', '0' if info['backend']=='long_double' else '1')
    assert native_precision() == info
    info['mantissa_bits'] = 0
    assert native_precision()['mantissa_bits'] >= 53


def test_native_backend_pb_solve_retains_double_export_contract():
    core = PyDeviceSimulator(5,1,1,1e-9,1e-9,1e-9)
    core.set_effective_dos(np.full(5,1e22),np.full(5,1e22))
    core.set_bandgap(np.full(5,.5))
    core.set_dirichlet_potential({0:0.,4:.03})
    result=core.solve_equilibrium()
    assert result['converged'] and result['initial_guess_committed']
    assert result['residual_history'][-1] <= 1e-10
    for name in ('phi','n','p'):
        assert result[name].dtype == np.float64
        assert np.isfinite(result[name]).all()
    assert result['phi'][0] == 0. and result['phi'][-1] == .03
