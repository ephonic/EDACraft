"""Check sparse material LK against independent full nonlinear blocks."""
import numpy as np
import pytest
from test_lk_material_multidimensional import device,independent_step


@pytest.mark.parametrize('shape',[(17,16,1),(17,1,16),(1,17,16),(7,7,6)])
def test_large_material_capacitor_matches_independent_block(shape):
    # More than 256 nodes selects sparse projection and sparse Newton. Include
    # interfaces, nonuniform axes, fixed charge, imprint and depolarization.
    sim,spec=device(shape,True,2,True)
    sim.set_transient_t_final(1e-10)
    states=sim.solve_transient();assert len(states)==2 and all(s['valid'] for s in states)
    state=states[-1]
    assert state['total_terminal_current_available']
    np.testing.assert_array_equal(state['n'],state['p'])
    assert np.max(state['n'])<=1e-20
    phi,p=independent_step(spec,np.zeros((spec['count'],3)),states[0]['phi'],state['dt_s'])
    np.testing.assert_allclose(state['phi'],phi,rtol=2e-8,atol=2e-10)
    np.testing.assert_allclose(state['P'].reshape(-1,3),p,rtol=2e-8,atol=2e-11)
    _,div,ports=spec['fields'](state['phi'],state['P'].reshape(-1,3))
    assert np.max(abs((div-1.602176634e-19*spec['doping'])[~spec['contacts']]))<1e-5
    np.testing.assert_allclose(state['electrode_charges_C'],ports,rtol=1e-8,atol=1e-25)


def test_large_sparse_failure_does_not_commit_state():
    sim,_=device((17,16,1),True,1,True)
    sim.set_gummel_max_iter(0);sim.set_transient_t_final(1e-10)
    states=sim.solve_transient();assert not states[-1]['valid']
    for key in ['phi','n','p','P']:np.testing.assert_array_equal(states[0][key],states[-1][key])


def test_large_blocked_capacitor_retains_terminal_current_on_every_interval():
    from test_sentaurus_multidimensional_fe import native
    times=(0.,5e-11,1e-10,1.5e-10,2e-10,3e-10,4e-10,5e-10,6e-10)
    actual=native(20,times)
    assert np.all(np.isfinite(actual['current']))
    np.testing.assert_allclose(actual['current'][1:],np.diff(actual['charge'],axis=0)/np.diff(times)[:,None],
        rtol=1e-8,atol=1e-20)
    assert np.max(abs(actual['current'].sum(axis=1)))<np.max(abs(actual['current']))*1e-8
