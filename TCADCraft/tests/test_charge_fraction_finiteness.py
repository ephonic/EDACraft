"""Native charge occupancy must reject NaN before changing solver inputs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_field_input_contract import ROUTES, fixture, observe
from test_steady_edge_permittivity import stack
from test_transient_selfconsistent import QE, central_cell, reference_step
from test_zero_auger_transient import digest, snapshot


BAD = {'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf,
       'negative': -.01, 'above_one': 1.01}
FRACTIONS = [-0., 0., .25, .5, 1.]


def reference(key, result):
    value = digest(result)
    print(json.dumps(dict(test='fraction_reference', key=key, sha256=value)))
    oracle = os.environ.get('TCAD_FRACTION_ORACLE')
    if oracle:assert json.loads(Path(oracle).read_text(encoding='utf8'))[key] == value


@pytest.mark.parametrize('fraction', FRACTIONS, ids=['negative_zero','zero','quarter','half','one'])
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
def test_valid_fraction_scales_initial_gauss_projection(fraction, axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True, final=0.)
    sim.set_quantum_enabled(False)
    sim.set_nonlinear_history_enabled(True)
    sim.set_charge_volume_fraction(np.array([1., fraction, 1.]))
    result = snapshot(sim)
    state, = result[0]
    assert state['valid']
    phi, _, _ = reference_step(nn, pp, 0., x, 1e16, .15)
    np.testing.assert_allclose(state['phi'], [0., fraction*phi, 0.], rtol=1e-12, atol=1e-25)
    np.testing.assert_array_equal(state['n'], 1e16*np.array([1., nn, 1.]))
    np.testing.assert_array_equal(state['p'], 1e16*np.array([1., pp, 1.]))
    assert state['charge_ledger_available'] == (fraction == 1.)
    key = f'initial/{float(fraction).hex()}/{axis}/{log_space}'
    reference(key, result)
    print(json.dumps(dict(test='fraction_physics', key=key,
        max_phi_error_V=float(np.max(abs(state['phi']-np.array([0.,fraction*phi,0.])))))))


@pytest.mark.parametrize('fraction', FRACTIONS, ids=['negative_zero','zero','quarter','half','one'])
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('route', ROUTES)
def test_valid_fraction_matches_charged_face_finite_volume_solution(fraction, axis, route):
    sim, x, faces, _ = stack(axis, route)
    sim.set_quantum_enabled(False)
    doping = np.array([0.,1.,2.,3.,4.,0.,0.,0.,0.])*1e21
    occupancy = fraction*np.array([1.,1.,1.,1.,.5,0.,0.,0.,0.])
    sim.set_doping(doping)
    sim.set_charge_volume_fraction(occupancy)
    matrix = np.zeros((9,9));rhs=np.zeros(9)
    matrix[0,0]=matrix[-1,-1]=1.;rhs[-1]=.2
    for i in range(1,8):
        left=faces[i-1]/(x[i]-x[i-1]);right=faces[i]/(x[i+1]-x[i])
        matrix[i,i]=left+right;matrix[i,i-1]=-left;matrix[i,i+1]=-right
        rhs[i]=QE*doping[i]*occupancy[i]*(x[i+1]-x[i-1])/2
    expected=np.linalg.solve(matrix,rhs)
    result=sim.solve();assert result['converged']
    np.testing.assert_allclose(result['phi'],expected,rtol=1e-8,atol=2e-11)
    key=f'steady/{float(fraction).hex()}/{axis}/{route}'
    reference(key,result)
    print(json.dumps(dict(test='fraction_physics',key=key,max_phi_error_V=float(np.max(abs(result['phi']-expected))))))


def child(route, bad, position):
    actual, expected = fixture(route), fixture(route)
    if bad == 'size':
        request=np.full(position,.8);message='charge volume fraction size mismatch'
    else:
        request=np.full(3,.8);request[position]=BAD[bad]
        message=r'charge volume fraction must be in \[0,1\]'
    with pytest.raises(ValueError,match='^'+message+'$'):
        actual.set_charge_volume_fraction(request)
    a,b=observe(actual),observe(expected)
    assert digest(a)==digest(b)
    # The retry must be observable while leaving the time integration scope
    # unchanged: modify signed doping with a valid full-volume fraction.
    for sim in [actual,expected]:
        sim.set_charge_volume_fraction(np.ones(3))
        sim.set_doping(np.array([0.,-.3e16,0.]))
    retry,control=observe(actual),observe(expected)
    assert digest(retry)==digest(control) and digest(retry)!=digest(a)
    return dict(route=route,bad=bad,position=position,requests=1,sha256=digest([a,retry]))


CASES=[(bad,pos) for bad in BAD for pos in range(3)]+[('size',n) for n in [0,2,4]]


@pytest.mark.parametrize('route',ROUTES)
@pytest.mark.parametrize('bad,position',CASES)
def test_invalid_fraction_preserves_both_solvers_and_allows_retry(route,bad,position):
    code=("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
          "from test_charge_fraction_finiteness import child\n"
          f"print(json.dumps(dict(test='fraction_atomic',**child({route!r},{bad!r},{position!r}))))\n")
    env=dict(os.environ)
    env['PYTHONPATH']=str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH','')
    r=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,encoding='utf8',timeout=60)
    print(json.dumps(dict(test='fraction_child_exit',route=route,bad=bad,position=position,returncode=r.returncode)))
    assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
    rows=[line for line in r.stdout.splitlines() if line.startswith('{"test": "fraction_atomic"')]
    assert len(rows)==1
    print(rows[0])
