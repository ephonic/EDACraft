"""Charge routing controls; feature weights are heuristic, not physical closure."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.core import native_constants
from tcad.postprocess.current import QE, contact_current_1d
from tcad.postprocess.mechanism import (
    attribute_mechanism, drift_diffusion_split_1d, btbt_generation,
)
from test_current_charge_consistency import problem


def charge():
    return {'si': 1.602176634e-19, 'legacy-charge': 1.602192e-19}[native_constants()['profile']]


def report_dict(report):
    return dict(J_drift=report.J_drift, J_diff=report.J_diff, I_btbt=report.I_btbt,
                fe_charge=report.fe_charge, dominant=report.dominant,
                weights=report.feature_vector().tolist(), cutline_x=report.cutline_x.tolist())


def manufactured_record(geometry, mode, source):
    sim, x, _ = problem(geometry)
    size = sim.mesh.npts(); q = charge()
    if mode == 'drift':
        state = dict(phi=x*1e4, n=np.full(size, 1e20), p=np.full(size, 2e20))
        expected = dict(J_drift=q*(.1*1e20+.05*2e20)*1e4, J_diff=0.)
    else:
        state = dict(phi=np.zeros(size), n=1e20+1e26*x, p=2e20+2e25*x)
        expected = dict(J_drift=0., J_diff=q*sim.VT*(.1*1e26-.05*2e25))
    state['P'] = np.tile([.01, 0., 0.], (size, 1))
    if source == 'exported':
        state['G_btbt'] = np.full(size, 1e30)
        expected_generation = 1e30
    else:
        # Controlled postprocessing input, not a self-consistent tunneling solve.
        state['Ex'] = np.full(size, 1e9)
        expected_generation = 3.1e21*1e6*1e18*np.exp(-2.)
    volume = .6e-6*1e-6*(.4e-6 if geometry == 'slab_x' else 1e-6)
    expected['I_btbt'] = q*expected_generation*volume
    expected['fe_charge'] = .01
    bound = report_dict(attribute_mechanism(sim, state))
    facade = report_dict(attribute_mechanism(SimpleNamespace(mesh=sim.mesh, VT=sim.VT), state))
    generation, standalone_current = btbt_generation(state, sim.mesh)
    return dict(kind='manufactured', geometry=geometry, mode=mode, source=source,
                temperature_VT=sim.VT, profile=native_constants()['profile'], volume_m3=volume,
                generation_rate_m3_s=float(generation[0]), generation_uniform=bool(np.all(generation==generation[0])),
                standalone_btbt_A=standalone_current, expected=expected, bound=bound, facade=facade,
                terminal_density_A_m2=contact_current_1d(sim, state, 'low'))


def solved_record(geometry, layout, bias):
    sim, x, _ = problem(geometry, layout)
    low=sim._sim; size=sim.mesh.npts(); density=1e16
    low.set_mobility(sim.mesh.fields['mu_n'],sim.mesh.fields['mu_p'])
    low.set_effective_dos(np.full(size,density),np.full(size,density))
    low.set_bandgap(np.zeros(size));low.set_recombination(np.full(size,1e100),np.full(size,1e100))
    contacts=np.flatnonzero(sim.mesh.fields['contact_low']|sim.mesh.fields['contact_high'])
    phi=bias*(1-x/.6e-6)
    low.set_dirichlet_potential({int(i):float(phi[i]) for i in contacts})
    low.set_electron_bc({int(i):density for i in contacts});low.set_hole_bc({int(i):density for i in contacts})
    low.set_initial_guess(phi,np.full(size,density),np.full(size,density));low.set_use_newton(False)
    state=sim.run(max_iter=80,tol=1e-12,physical_step=False)
    return dict(kind='solved',geometry=geometry,layout=layout,bias_V=bias,converged=bool(state['converged']),
                profile=native_constants()['profile'],bound=report_dict(attribute_mechanism(sim,state)),
                native_density_A_m2=contact_current_1d(sim,state,'low'),
                density_min_m3=float(np.min(state['n'])),density_max_m3=float(np.max(state['n'])))


@pytest.mark.parametrize('geometry',['line','slab_x'])
@pytest.mark.parametrize('mode',['drift','diffusion'])
@pytest.mark.parametrize('source',['exported','kane'])
def test_bound_manufactured_mechanism_matches_charge_and_si_facade(geometry,mode,source):
    row=manufactured_record(geometry,mode,source)
    for key,expected in row['expected'].items():
        assert row['bound'][key]==pytest.approx(expected,rel=3e-14,abs=0.)
    for key in ['J_drift','J_diff','I_btbt']:
        assert row['facade'][key]==pytest.approx(row['expected'][key]*QE/charge(),rel=3e-14,abs=0.)
    assert row['facade']['fe_charge']==row['bound']['fe_charge']
    expected_sign=-1. if mode=='drift' else 1.
    assert row['terminal_density_A_m2']==pytest.approx(expected_sign*(row['bound']['J_drift']+row['bound']['J_diff']),rel=3e-14,abs=0.)
    magnitudes=np.array([row['expected']['J_drift'],row['expected']['J_diff'],row['expected']['I_btbt'],.01*.14*1e7])
    np.testing.assert_allclose(row['bound']['weights'],magnitudes/magnitudes.sum(),rtol=3e-14,atol=0.)


@pytest.mark.parametrize('geometry',['line','slab_x'])
@pytest.mark.parametrize('layout',[0,1])
@pytest.mark.parametrize('bias',[.01,-.01])
def test_bound_solved_mechanism_matches_actual_native_density(geometry,layout,bias):
    row=solved_record(geometry,layout,bias)
    assert row['converged']
    expected=charge()*.15*1e16*abs(bias)/.6e-6
    assert row['bound']['J_drift']==pytest.approx(expected,rel=2e-10,abs=0.)
    assert row['bound']['J_drift']==pytest.approx(abs(row['native_density_A_m2']),rel=2e-10,abs=0.)
    assert row['bound']['J_diff']<1e-9
    assert row['bound']['I_btbt']==row['bound']['fe_charge']==0.


@pytest.mark.parametrize('mode',['drift','diffusion'])
@pytest.mark.parametrize('q',[1.602176634e-19,1.602192e-19,2.4e-19])
def test_standalone_components_default_si_and_explicit_charge(mode,q):
    sim,x,_=problem('line');size=sim.mesh.npts()
    if mode=='drift':
        phi=x*1e4;n=np.full(size,1e20);p=np.full(size,2e20)
        expected=[-.1*1e20*1e4,0.,-.05*2e20*1e4,0.]
    else:
        phi=np.zeros(size);n=1e20+1e26*x;p=2e20+2e25*x
        expected=[0.,.1*sim.VT*1e26,0.,-.05*sim.VT*2e25]
    args=(phi,n,p,np.diff(sim.mesh.axis_coordinates()[0]),sim.mesh.fields['mu_n'],sim.mesh.fields['mu_p'],sim.VT)
    for explicit,reference_charge in [(False,QE),(True,q)]:
        values=drift_diffusion_split_1d(*args,**({'elementary_charge_C':q} if explicit else {}))
        for key,value in zip(['Jn_drift','Jn_diff','Jp_drift','Jp_diff'],expected):
            np.testing.assert_allclose(values[key],reference_charge*value,rtol=3e-14,atol=0.)


@pytest.mark.parametrize('source',['exported','kane'])
@pytest.mark.parametrize('q',[1.602176634e-19,1.602192e-19,2.4e-19])
def test_generation_and_coefficients_are_charge_independent(source,q):
    sim,_,_=problem('line');size=sim.mesh.npts()
    state={'G_btbt':np.full(size,1e30)} if source=='exported' else {'Ex':np.full(size,1e9)}
    baseline,current_si=btbt_generation(state,sim.mesh)
    actual,current=btbt_generation(state,sim.mesh,elementary_charge_C=q)
    np.testing.assert_array_equal(actual,baseline)
    assert current/current_si==pytest.approx(q/QE,rel=2e-15)
    expected_g=1e30 if source=='exported' else 3.1e21*1e6*1e18*np.exp(-2.)
    np.testing.assert_allclose(actual,expected_g,rtol=2e-15)
    assert current==pytest.approx(q*expected_g*.6e-6*1e-6*1e-6,rel=3e-15)


@pytest.mark.parametrize('q',[0.,-1.,np.nan,np.inf,-np.inf,True,[1e-19],[[1e-19]],'1e-19',1e-19+0j,None])
@pytest.mark.parametrize('helper',['split','btbt'])
def test_invalid_charge_rejected_without_input_mutation(helper,q):
    sim,x,_=problem('line');size=sim.mesh.npts();a=np.full(size,1e20);before=a.copy()
    with pytest.raises(ValueError,match='elementary_charge_C'):
        if helper=='split':
            drift_diffusion_split_1d(x,a,a,np.diff(x),a,a,sim.VT,elementary_charge_C=q)
        else:
            btbt_generation({'G_btbt':a},sim.mesh,elementary_charge_C=q)
    np.testing.assert_array_equal(a,before)


if __name__=='__main__':
    rows=[manufactured_record(g,m,s) for g in ['line','slab_x'] for m in ['drift','diffusion'] for s in ['exported','kane']]
    rows += [solved_record(g,l,b) for g in ['line','slab_x'] for l in [0,1] for b in [.01,-.01]]
    Path(sys.argv[1]).write_text(json.dumps(dict(constants=native_constants(),records=rows),indent=2))
