"""Nonfinite faces cannot replace the persistent operator on any steady route."""
import json
import os
from pathlib import Path
import numpy as np
import pytest
from test_steady_edge_permittivity import stack
from test_zero_auger_transient import digest


@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('path',['gummel','hybrid','newton'])
def test_valid_faces_and_signed_fallback_preserve_parent_exports(axis,path):
    sim,x,_,expected=stack(axis,path)
    states=[sim.solve()]
    np.testing.assert_allclose(states[0]['phi'],expected,rtol=1e-9,atol=2e-12)
    for value in [-1.,-0.,0.]:
        sim.set_edge_permittivity(*[np.full(9,value) for _ in range(6)])
        state=sim.solve();assert state['converged']
        np.testing.assert_allclose(state['phi'],.2*x/x[-1],rtol=1e-9,atol=2e-12)
        states.append(state)
    # Acceptance/restore only; never solve extreme material coefficients.
    for value in [-np.finfo(float).max,np.finfo(float).max]:
        sim.set_edge_permittivity(*[np.full(9,value) for _ in range(6)])
    sim.set_edge_permittivity(*[np.array([],dtype=float) for _ in range(6)])
    states.append(sim.solve());assert all(s['converged'] for s in states)
    key=f'{axis}/{path}';h=digest(states)
    print(json.dumps(dict(test='edge_finite_reference',key=key,sha256=h)))
    oracle=os.environ.get('TCAD_EDGE_FINITE_ORACLE')
    if oracle:assert json.loads(Path(oracle).read_bytes())[key]==h


@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('path',['gummel','hybrid','newton'])
@pytest.mark.parametrize('slot',range(6))
def test_nonfinite_faces_preserve_operator_and_allow_valid_retry(axis,path,slot):
    sim,_,_,expected=stack(axis,path)
    # Change every earlier valid field too, exposing partial writes. Unused
    # face directions must be validated even in this one-dimensional mesh.
    for bad in [np.nan,np.inf,-np.inf]:
        for position in [0,4,8]:
            arrays=[np.full(9,17*8.8542e-12) for _ in range(6)]
            arrays[slot][position]=bad
            with pytest.raises(ValueError,match='^edge permittivity values must be finite$'):
                sim.set_edge_permittivity(*arrays)
            state=sim.solve();assert state['converged']
            np.testing.assert_allclose(state['phi'],expected,rtol=1e-9,atol=2e-12)
    empty=np.array([],dtype=float);sim.set_edge_permittivity(*[empty]*6)
    state=sim.solve();control,x,_,_=stack(axis,path);control.set_edge_permittivity(*[empty]*6)
    expected_state=control.solve();assert state['converged'] and expected_state['converged']
    np.testing.assert_allclose(state['phi'],.2*x/x[-1],rtol=1e-9,atol=2e-12)
    for key in ['phi','n','p']:
        np.testing.assert_allclose(state[key],expected_state[key],rtol=1e-9,atol=2e-12)
