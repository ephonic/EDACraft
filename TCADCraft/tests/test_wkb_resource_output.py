"""Bounded WKB requests must reject atomically and allow a legal retry."""
import sys
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator
from test_native_setter_exceptions import fixture

LIMIT=1<<20
BAD=[LIMIT+1,LIMIT+2,2*sys.maxsize,2*sys.maxsize+1]

@pytest.mark.parametrize('segments',BAD)
@pytest.mark.parametrize('route',['gummel','newton'])
@pytest.mark.parametrize('after_solve',[False,True])
def test_oversized_wkb_setter_keeps_parameters(segments,route,after_solve):
    sim=fixture('btbt_nonlocal_params',0)
    sim.set_use_newton(route=='newton');sim.set_newton_primary(route=='newton')
    if after_solve:assert sim.solve()['converged']
    with pytest.raises(ValueError,match='WKB segment count exceeds resource limit'):
        sim.set_btbt_nonlocal_params(.08,segments)
    actual=sim.solve();assert actual['converged']
    control=fixture('btbt_nonlocal_params',0)
    control.set_use_newton(route=='newton');control.set_newton_primary(route=='newton')
    if after_solve:assert control.solve()['converged']
    expected=control.solve();assert expected['converged']
    for name in ['phi','n','p','G_btbt']:np.testing.assert_array_equal(actual[name],expected[name])
    # A legal change after the rejection must still take effect.
    sim.set_btbt_nonlocal_params(.08,5);changed=sim.solve();assert changed['converged']
    control.set_btbt_nonlocal_params(.08,5);retry=control.solve()
    for name in ['phi','n','p','G_btbt']:np.testing.assert_array_equal(changed[name],retry[name])

@pytest.mark.parametrize('nodes',[63,64,65])
@pytest.mark.parametrize('segments',[LIMIT-1,LIMIT])
def test_grid_work_limit_includes_simpson_endpoints(nodes,segments):
    sim=PyDeviceSimulator(nodes,1,1,1e-8,1.,1.)
    if nodes==63:sim.set_btbt_nonlocal_params(.08,segments)
    else:
        with pytest.raises(ValueError,match='WKB grid quadrature exceeds resource limit'):
            sim.set_btbt_nonlocal_params(.08,segments)
    # Constructor/setter boundary only: never evaluate a maximum-size quadrature.
    sim.set_btbt_nonlocal_params(.2,32)
