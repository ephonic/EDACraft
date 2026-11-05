"""Ohmic setter exception translation, scalar Poisson reference and recovery."""
import math
import os
import subprocess
import sys
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator

D=1e16
VT=.02585
EPS=20*8.854187817e-12
BASE=({1},{1:.003},{1:-.005},D)


def configured(axis=0,stretched=False):
    dims=[1,1,1];dims[axis]=3
    sim=PyDeviceSimulator(*dims,1e-6,1e-6,1e-6)
    positions=np.array([0.,.7e-6,2.2e-6] if stretched else [0.,1e-6,2e-6])
    if stretched:getattr(sim,'set_'+'xyz'[axis]+'_positions')(positions)
    sim.set_permittivity(np.full(3,EPS));sim.set_doping(np.zeros(3))
    sim.set_mobility(np.full(3,.01),np.full(3,.02))
    sim.set_effective_dos(np.full(3,D),np.full(3,D));sim.set_bandgap(np.zeros(3))
    sim.set_thermal_voltage(VT);sim.set_use_newton(False)
    sim.set_poisson_solver_type(6);sim.set_continuity_solver_type(6)
    sim.set_dirichlet_potential({0:0.,2:0.});sim.set_electron_bc({i:D for i in range(3)});sim.set_hole_bc({i:D for i in range(3)})
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-12)
    sim.set_ohmic_contacts(*BASE)
    return sim,positions


def solve(sim):
    sim.set_initial_guess(np.zeros(3),np.full(3,D),np.full(3,D))
    state=sim.solve();assert state['converged']
    np.testing.assert_array_equal(state['n'],np.full(3,D));np.testing.assert_array_equal(state['p'],np.full(3,D))
    return np.r_[state['phi'],state['n'],state['p']]


def target(positions,request):
    nodes,en,ep,ni=request
    if 1 not in nodes:return 0.
    q=1.602192e-19 if os.environ.get('TCAD_EXPECT_CONSTANTS_PROFILE')=='legacy-charge' else 1.602176634e-19
    stiffness=2*EPS/((positions[1]-positions[0])*(positions[2]-positions[1]))
    low,high=-.1,.1
    for _ in range(100):
        phi=(low+high)/2
        residual=stiffness*phi-q*ni*(math.exp(-(phi+ep.get(1,0.))/VT)-math.exp((phi-en.get(1,0.))/VT))
        if residual>0:high=phi
        else:low=phi
    return (low+high)/2


def legal_requests():
    result=[BASE,({1},BASE[1],BASE[2],1.5*D),({1},{1:.02},BASE[2],D),({1},BASE[1],{1:-.02},D),(set(),BASE[1],BASE[2],D)]
    result += [(nodes,BASE[1],BASE[2],D) for nodes in [set(),{0},{1},{2},{0,2},{0,1,2}]]
    result += [({1},{},BASE[2],D),({1},BASE[1],{},D),({1},{},{},D),({1},{0:.2,1:.003},{1:-.005,2:-.3},D),({1},{0:.2},BASE[2],D),({1},BASE[1],{2:-.3},D),BASE]
    return result


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
def test_legal_ohmic_reference_and_clear(axis,stretched):
    sim,positions=configured(axis,stretched);states=[]
    for request in legal_requests():
        sim.set_ohmic_contacts(*request);state=solve(sim)
        np.testing.assert_allclose(state[:3],[0.,target(positions,request),0.],rtol=0,atol=2e-15)
        states.append(state)
    for state in states[1:5]:assert abs(state[1]-states[0][1])>1e-8
    np.testing.assert_array_equal(states[-1],states[0])
    sim.clear_ohmic_contacts();np.testing.assert_array_equal(solve(sim)[:3],np.zeros(3))
    sim.set_ohmic_contacts(*BASE);np.testing.assert_array_equal(solve(sim),states[0])


def bad_requests(kind):
    if kind=='index':
        for field in range(3):
            for index in [3,4,2**64-1]:
                for ni in [D,float('nan'),0.]:
                    nodes={0};en={0:float('nan'),1:.02};ep={1:.03}
                    if field==0:nodes.add(index)
                    elif field==1:en[index]=.02
                    else:ep[index]=float('inf')
                    yield (nodes,en,ep,ni),IndexError,'ohmic contact node is outside the grid' if field==0 else 'ohmic quasi-Fermi node is outside the grid'
    elif kind=='shift':
        for field in range(2):
            for node in range(3):
                for value in [float('nan'),float('inf'),-float('inf')]:
                    en={1:.02};ep={1:.03};(en if field==0 else ep)[node]=value
                    yield ({0},en,ep,D),ValueError,'ohmic quasi-Fermi values must be finite'
    elif kind=='density':
        for ni in [float('nan'),float('inf'),-float('inf'),0.,-sys.float_info.epsilon,-D]:
            yield ({0},{1:.02},{1:.03},ni),ValueError,'ohmic intrinsic density must be finite and positive'
    elif kind=='negative_index':
        for request in [({-1},{},{},D),({1},{-1:.02},{},D),({1},{},{-1:.02},D)]:yield request,OverflowError,None
    else:raise AssertionError(kind)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('kind',['index','shift','density','negative_index'])
def test_rejected_ohmic_preserves_next_solve(axis,stretched,kind):
    sim,_=configured(axis,stretched);control=solve(sim)
    for request,error,message in bad_requests(kind):
        with pytest.raises(error) as caught:sim.set_ohmic_contacts(*request)
        if message is not None:assert str(caught.value)==message
        np.testing.assert_array_equal(solve(sim),control)
        sim.set_ohmic_contacts(*BASE);np.testing.assert_array_equal(solve(sim),control)


def probe_once(kind):
    sim,_=configured();request,error,message=next(bad_requests(kind))
    try:sim.set_ohmic_contacts(*request)
    except error as e:
        assert str(e)==message
        assert solve(sim).size==9
        print('ohmic_exception_translated_and_process_survived',flush=True)
    else:raise AssertionError('invalid ohmic input was accepted')


@pytest.mark.parametrize('kind',['index','shift','density'])
def test_exception_translation_survives_child(kind):
    script='import sys;sys.path.insert(0,"tests");from test_ohmic_entry_contract import probe_once;probe_once('+repr(kind)+')'
    run=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True,env=os.environ,timeout=30)
    assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    assert 'ohmic_exception_translated_and_process_survived' in run.stdout
