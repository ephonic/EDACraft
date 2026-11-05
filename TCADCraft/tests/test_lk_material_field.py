"""Independent material-side LK, Gauss law, ports and rollback checks."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest
from scipy.optimize import root

from tcad.core import PyDeviceSimulator
from tcad.postprocess import audit_transient_lk_energy
from tcad.simulator import Simulator
from test_transient_displacement import film, EPS0
from test_fe_series_stack import stack


def stack_device(times, top_voltage, oxide_nm=.5, cells=8, axis=0, enabled=True):
    """Geometry explicitly places the FE/oxide interface between two nodes."""
    delta=min(20e-9/cells,oxide_nm*1e-9/4)/4
    x=np.r_[np.linspace(0,20e-9-delta,cells+1),
            np.linspace(20e-9+delta,20e-9+oxide_nm*1e-9,5)]
    mask=(x<20e-9).astype(np.int8)
    eps=np.where(mask,15.,3.9)*8.8542e-12
    shape=[1,1,1];shape[axis]=len(x)
    spacing=[1.,1.,1.];spacing[axis]=x[1]
    other=[a for a in range(3) if a!=axis]
    spacing[other[0]]=1e-7;spacing[other[1]]=1e-6
    sim=PyDeviceSimulator(*shape,*spacing)
    getattr(sim,f'set_{"xyz"[axis]}_positions')(x)
    n=len(x);zero=np.zeros(n)
    sim.set_permittivity(eps);sim.set_mobility(zero,zero);sim.set_doping(zero)
    sim.set_effective_dos(np.full(n,1e16),np.full(n,1e16));sim.set_bandgap(np.full(n,6.))
    sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_dirichlet_potential({0:0.,n-1:0.});sim.set_initial_guess(zero,zero,zero)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_model(0)
    s=stack(thickness_oxide=oxide_nm*1e-9)
    sim.set_ferroelectric_params(mask,s.alpha,s.beta);sim.set_ferroelectric_gamma(s.viscosity)
    sim.set_ferroelectric_polar_axis(axis);sim.set_transient_lk_coupled(True)
    if enabled is not None:
        sim.set_transient_lk_material_field(enabled)
    sim.set_transient_dt(float(times[-1]));sim.set_transient_t_final(float(times[-1]))
    sim.set_transient_voltage_waveforms(np.asarray(times),{n-1:np.asarray(top_voltage)})
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    return sim,x,eps,mask


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('oxide',[.2,.5,1.])
@pytest.mark.parametrize('cells',[8,32])
def test_uniform_series_target_has_no_checkerboard_and_correct_ports(axis,oxide,cells):
    times=np.linspace(0.,1e-9,41);voltage=-8*np.sin(2*np.pi*times/1e-9)
    sim,x,eps,mask=stack_device(times,voltage,oxide,cells,axis)
    states=sim.solve_transient()
    expected=stack(thickness_oxide=oxide*1e-9).solve_backward_euler(times,-voltage)
    for i,s in enumerate(states):
        assert s['valid'] and s['lk_material_field']
        p=s['P'].reshape(-1,3)[:,axis]
        np.testing.assert_allclose(p[mask!=0],expected['polarization_C_m2'][i],atol=2e-12,rtol=2e-11)
        np.testing.assert_array_equal(p[mask==0],0.)
        np.testing.assert_allclose(s['electrode_charges_C'][1],expected['top_charge_C'][i],atol=1e-25,rtol=3e-11)
        field=s['E'+'xyz'[axis]]
        np.testing.assert_allclose(eps*field+p,-s['electrode_charges_C'][1]/1e-13,atol=2e-14,rtol=1e-11)
        if i:
            np.testing.assert_allclose(s['electrode_total_currents_A'][1],expected['top_current_A'][i],atol=2e-15,rtol=1e-9)
    assert audit_transient_lk_energy(states)['valid']


def independent_block_step(x,eps,mask,old,dt,voltage,axis,polar_axis,imprint,depol):
    """Solve 3N local vector LK equations plus one voltage equation directly."""
    n=len(x);width=np.r_[np.diff(x),0.]/2+np.r_[0.,np.diff(x)]/2
    rate=.1/dt;extra=1/(depol*EPS0) if depol else 0.
    def equations(y):
        p=y[:-1].reshape(n,3);d=y[-1]
        field=np.zeros_like(p);field[:,axis]=(d-p[:,axis])/eps
        f=(-1e8*p+1e12*p**3+rate*(p-old)-field)
        f[:,polar_axis]+=imprint+extra*p[:,polar_axis]
        f[mask==0]=p[mask==0]*1e10
        return np.r_[f.ravel()/1e10,(np.dot(width,(d-p[:,axis])/eps)-voltage)]
    solution=root(equations,np.r_[old.ravel(),0.],tol=1e-11)
    assert max(abs(equations(solution.x)))<1e-11
    return solution.x[:-1].reshape(n,3),solution.x[-1]


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('polar_axis',[0,1,2])
@pytest.mark.parametrize('depol',[0.,30.])
def test_nonuniform_material_polarization_matches_full_vector_block(axis,polar_axis,depol):
    sim,x,eps,mask,area=film(axis,0,True,True)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_ferroelectric_polar_axis(polar_axis)
    sim.set_ferroelectric_builtin_field(2e5);sim.set_ferroelectric_depol(depol)
    states=sim.solve_transient();old=np.zeros((len(x),3))
    for s in states[1:]:
        p,d=independent_block_step(x,eps,mask,old,s['dt_s'],.01,axis,polar_axis,2e5,depol)
        assert s['valid']
        np.testing.assert_allclose(s['P'].reshape(-1,3),p,rtol=1e-9,atol=2e-13)
        np.testing.assert_allclose(s['electrode_charges_C'],[area*d,-area*d],rtol=1e-10,atol=1e-27)
        old=p
    assert np.ptp(old[mask!=0,axis])>1e-8  # Never force a uniform FE state.
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('case_index',range(5))
def test_native_against_actual_sentaurus_series_stack(case_index):
    data=json.loads((Path(__file__).parent/'data/sentaurus_fe_oxide_stack.json').read_text())
    c=data['cases'][case_index];times=np.array(c['times_s']);top=-np.array(c['drive_voltage_V'])
    sim,_,_,mask=stack_device(times,top,c['oxide_nm'],8,c['axis'])
    states=sim.solve_transient();assert all(s['valid'] for s in states)
    expected=c['reference'];axis=c['axis']
    actual=dict(polarization_C_m2=np.array([s['P'].reshape(-1,3)[3,axis] for s in states]),
        top_charge_C=np.array([s['electrode_charges_C'][1] for s in states]),
        top_current_A=np.r_[0.,[s['electrode_total_currents_A'][1] for s in states[1:]]],
        field_fe_V_m=np.array([s['E'+'xyz'[axis]][3] for s in states]),
        field_oxide_V_m=np.array([s['E'+'xyz'[axis]][-1] for s in states]))
    errors={k:float(max(abs(v-np.array(expected[k])))/max(abs(np.array(expected[k])))) for k,v in actual.items()}
    assert all(e<1e-3 for e in errors.values())==c['comparison_passed']
    if c['comparison_passed']:assert max(errors.values())<1e-8
    assert max(np.ptp(s['P'].reshape(-1,3)[mask!=0,axis]) for s in states)<1e-12


@pytest.mark.parametrize('value',[0,1,'true',None,[],np.array([True])])
def test_strict_boolean_low_and_high_level(value):
    sim,*_=film(0,0,True,True)
    with pytest.raises(ValueError,match='boolean'):sim.set_transient_lk_material_field(value)
    host=type('Host',(),{'_sim':sim})()
    with pytest.raises(ValueError,match='boolean'):Simulator.set_transient_lk_material_field(host,value)


@pytest.mark.parametrize('case',['split','mobility','endpoint_doping','generation','carrier','contact_carrier',
    'freeze_n','freeze_p','fraction','edge','srh','extra_contact'])
def test_unsupported_physics_rejected_before_evolving_state(case):
    sim,x,*_=film(0,0,True,True);n=len(x);zero=np.zeros(n)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    if case=='split':sim.set_transient_lk_coupled(False)
    elif case=='mobility':sim.set_mobility(np.ones(n),zero)
    elif case=='endpoint_doping':sim.set_doping(np.ones(n))
    elif case=='generation':sim.set_optical_generation(np.ones(n))
    elif case=='carrier':sim.set_initial_guess(zero,np.ones(n),zero)
    elif case=='contact_carrier':sim.set_electron_bc({0:1.})
    elif case.startswith('freeze_'):getattr(sim,'set_newton_'+case)(True)
    elif case=='srh':sim.set_recombination(np.full(n,1e-9),np.full(n,1e-9))
    elif case=='fraction':sim.set_charge_volume_fraction(np.full(n,.5))
    elif case=='edge':sim.set_edge_permittivity(*[np.ones(n)*1e-10 for _ in range(6)])
    elif case=='extra_contact':sim.set_dirichlet_potential({0:0.,4:0.,n-1:-.01})
    with pytest.raises(ValueError,match='material-field LK'):sim.solve_transient()


def test_failure_rollback_budget_and_diagnostic_ownership():
    sim,*_=film(0,0,True,True)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_nonlinear_history_enabled(True);sim.set_gummel_max_iter(0)
    failed=sim.solve_transient();assert not failed[-1]['valid']
    np.testing.assert_array_equal(failed[-1]['P'],failed[0]['P'])
    trial=sim.get_transient_attempt_history()[0]['trials'][0]
    assert trial['solver']=='lk_material_field_1d' and trial['solver_called'] and not trial['converged']
    assert trial['voltage_residual_V'].shape==(0,)
    sim.set_gummel_max_iter(80);retry=sim.solve_transient()
    fresh,*_=film(0,0,True,True)
    fresh.set_transient_lk_coupled(True);fresh.set_transient_lk_material_field(True)
    for a,b in zip(retry,fresh.solve_transient()):
        for key in ('phi','P'):np.testing.assert_array_equal(a[key],b[key])
    history=sim.get_transient_attempt_history()
    trial=history[0]['trials'][0]
    assert trial['sample_scope']=='voltage_constraint_base_states'
    assert np.all(trial['d_voltage_d_displacement_m2_F']>0)
    assert len(trial['voltage_residual_V'])==retry[1]['iterations']
    trial['voltage_residual_V'][:]=np.nan
    assert np.isfinite(sim.get_transient_attempt_history()[0]['trials'][0]['voltage_residual_V']).all()


def test_adaptive_rejections_do_not_consume_polarization():
    sim,x,eps,mask,area=film(0,0,True,True)
    sim.set_dirichlet_potential({0:0.,len(x)-1:-1.})
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_transient_lk_substepping(True)
    sim.set_transient_lk_error_control(True,rtol=1e-4,atol=1e-9,min_dt=1e-15,max_reject=30)
    sim.set_nonlinear_history_enabled(True)
    states=sim.solve_transient();assert all(s['valid'] for s in states)
    groups=sim.get_transient_attempt_history();assert any(not g['accepted'] for g in groups)
    old=np.zeros((len(x),3))
    for s in states[1:]:
        p,_=independent_block_step(x,eps,mask,old,s['dt_s'],1.,0,0,0.,0.)
        np.testing.assert_allclose(s['P'].reshape(-1,3),p,rtol=2e-9,atol=2e-12)
        old=p
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('bad',[1,False])
def test_energy_audit_rejects_tampered_material_field_metadata(bad):
    sim,*_=film(0,0,True,True)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    states=deepcopy(sim.solve_transient());states[-1]['lk_material_field']=bad
    with pytest.raises(ValueError):audit_transient_lk_energy(states)


@pytest.fixture(scope='module')
def quad_probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('native C++ probe requires GCC')
    project=Path(__file__).resolve().parents[1]
    exe=tmp_path_factory.mktemp('material_field')/'quad_probe'
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals',
        '-I'+str(project/'src'),str(project/'tests/cpp/lk_material_field_probe.cpp'),
        '-lquadmath','-o',str(exe)],check=True,capture_output=True,text=True)
    return exe


@pytest.mark.parametrize('sign',[1,-1])
def test_alternating_initial_p_and_voltage_jacobian_at_quad_precision(quad_probe,sign):
    import mpmath as mp
    lines=subprocess.check_output([str(quad_probe),'positive' if sign==1 else 'negative'],text=True).splitlines()
    assert int(lines[0])==113
    with mp.workdps(90):
        values=list(map(mp.mpf,lines[1:]));x=values[:9];eps=values[9:18]
        old=values[18:45];actual=values[45:72];phi=values[72:81];samples=values[81:83]
        width=[((x[i]-x[i-1] if i else 0)+(x[i+1]-x[i] if i<8 else 0))/2 for i in range(9)]
        a=mp.mpf('-649519052.838329');b=mp.mpf('331387271.85629034');rate=mp.mpf('.1')/mp.mpf('5e-11')
        def equations(*y):
            p=list(y[:7])+[mp.mpf(0)]*2;d=y[7]
            return tuple((a*p[i]+b*p[i]**3+rate*(p[i]-old[3*i])-(d-p[i])/eps[i])/mp.mpf('1e10')
                for i in range(7))+(sum(width[i]*(d-p[i])/eps[i] for i in range(9))-sign*mp.mpf('.25'),)
        edgeeps=2*eps[0]*eps[1]/(eps[0]+eps[1])
        d_actual=edgeeps*((phi[0]-phi[1])/(x[1]-x[0])+(actual[0]/eps[0]+actual[3]/eps[1])/2)
        expected=mp.findroot(equations,tuple(actual[3*i] for i in range(7))+(d_actual,),tol=mp.mpf('1e-80'))
        assert max(abs(v) for v in equations(*expected))<mp.mpf('1e-75')
        assert max(abs(actual[3*i]-expected[i]) for i in range(7))<mp.mpf('1e-28')
        assert abs(d_actual-expected[7])<mp.mpf('1e-28')
        def voltage(d):
            pol=[mp.findroot(lambda p:(a+rate+1/eps[i])*p+b*p**3-rate*old[3*i]-d/eps[i],expected[i])
                 for i in range(7)]+[mp.mpf(0)]*2
            return sum(width[i]*(d-pol[i])/eps[i] for i in range(9))
        derivative=mp.diff(voltage,expected[7])
        assert abs(samples[1]/derivative-1)<mp.mpf('1e-28')
        assert abs(samples[0])<mp.mpf('1e-28')
        tiny_root=mp.findroot(lambda p:p+mp.mpf('1e-25')*p**3-1,1)
        assert values[-1]!=1 and abs(values[-1]-tiny_root)<mp.mpf('1e-32')
