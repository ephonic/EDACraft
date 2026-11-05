"""Unconfigured carrier/mixed-material LK: independent physics and policy."""
import json
from pathlib import Path
import numpy as np
import pytest
from test_lk_auto_integration import without_policy_overrides
from test_lk_carrier_material import device,block_step
from test_lk_interface_material import interface_device,independent_step,commercial_device,commercial_errors

auto_carrier=without_policy_overrides(device)
auto_interface=without_policy_overrides(interface_device)
auto_interface.__globals__['device']=auto_carrier
auto_commercial=without_policy_overrides(commercial_device)


def make(kind,**kw):
    return (auto_carrier if kind=='carrier' else auto_interface)(**kw)


def check_blocks(sim,spec,kind,states=None):
    if states is None:states=sim.solve_transient()
    old=np.zeros((9,3));nn=spec['nn'];pp=spec['pp']
    for s in states:
        assert s['valid'] and s['lk_coupled'] and s['lk_material_field']
        step=block_step if kind=='carrier' else independent_step
        old,d,phi,nn,pp=step(spec,old,nn,pp,s['dt_s'] or None)
        np.testing.assert_allclose(s['P'].reshape(-1,3),old,rtol=4e-8,atol=3e-13)
        np.testing.assert_allclose(s['phi'],phi,rtol=3e-8,atol=3e-12)
        np.testing.assert_allclose(s['n']/spec['scale'],nn,rtol=4e-9,atol=2e-12)
        np.testing.assert_allclose(s['p']/spec['scale'],pp,rtol=4e-9,atol=2e-12)
        np.testing.assert_allclose(s['D_'+'xyz'[spec['axis']]][:-1],d,rtol=3e-8,atol=3e-15)
    return states


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('log_space',[False,True])
@pytest.mark.parametrize('source',[False,True])
@pytest.mark.parametrize('partial',[False,True])
def test_unconfigured_carrier_matches_full_independent_blocks(axis,stretched,log_space,source,partial):
    sim,spec=auto_carrier(axis,stretched,log_space,source,partial)
    check_blocks(sim,spec,'carrier')


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('log_space',[False,True])
@pytest.mark.parametrize('source',[False,True])
def test_unconfigured_interface_matches_full_independent_blocks(axis,stretched,log_space,source):
    sim,spec=auto_interface(axis,stretched,log_space,source)
    check_blocks(sim,spec,'interface')


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('policy,expected',[
    ('coupled',(True,True)),('both',(True,True)),('split',(False,False)),
    ('centered',(False,False)),('coupled_centered',(True,False))])
def test_explicit_policy_and_single_coupled_override(kind,policy,expected):
    sim,_=make(kind)
    if policy in ('coupled','both','coupled_centered'):sim.set_transient_lk_coupled(True)
    if policy=='both':sim.set_transient_lk_material_field(True)
    elif policy=='split':sim.set_transient_lk_coupled(False)
    elif policy in ('centered','coupled_centered'):sim.set_transient_lk_material_field(False)
    states=sim.solve_transient()
    assert all((s['lk_coupled'],s['lk_material_field'])==expected for s in states)
    if expected==(True,True):
        fresh,_=make(kind);reference=fresh.solve_transient()
        for a,b in zip(states,reference):
            for k in ['phi','n','p','P']:np.testing.assert_array_equal(a[k],b[k])


FALLBACKS=['unpaired','fraction','edge','extra_contact','endpoint_doping','freeze_n','freeze_p',
           'blocked_carrier','blocked_generation','blocked_srh']


def fallback(kind,case,split=False):
    sim,spec=make(kind);one=np.ones(9);zero=np.zeros(9)
    if case=='unpaired':sim.set_mobility(one*.1,zero)
    elif case=='fraction':sim.set_charge_volume_fraction(one*.5)
    elif case=='edge':sim.set_edge_permittivity(*[one*1e-10 for _ in range(6)])
    elif case=='extra_contact':sim.set_dirichlet_potential({4:0.})
    elif case=='endpoint_doping':sim.set_doping(one*1e19)
    elif case.startswith('freeze_'):getattr(sim,'set_newton_'+case)(True)
    else:
        mn=one*.1;mp=one*.05;mn[2]=mp[2]=0.;sim.set_mobility(mn,mp)
        nn=spec['nn'].copy()*spec['scale'];pp=spec['pp'].copy()*spec['scale']
        if case=='blocked_carrier':nn[2]=spec['scale']
        else:nn[2]=pp[2]=0.
        sim.set_initial_guess(zero,nn,pp)
        if case=='blocked_generation':g=zero.copy();g[2]=1.;sim.set_optical_generation(g)
        if case=='blocked_srh':t=np.full(9,1e100);t[2]=1e-9;sim.set_recombination(t,t)
    if split:sim.set_transient_lk_coupled(False)
    return sim


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('case',FALLBACKS)
def test_unsupported_automatic_scope_keeps_explicit_split_equations(kind,case):
    a=fallback(kind,case).solve_transient();b=fallback(kind,case,True).solve_transient()
    assert len(a)==len(b)
    for x,y in zip(a,b):
        assert not x['lk_coupled'] and not x['lk_material_field'] and x['valid']==y['valid']
        for k in ['phi','n','p','P']:np.testing.assert_array_equal(x[k],y[k])


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('direction,expected',[(-1,True),(0,False),(1,False)])
def test_automatic_transport_uses_exact_monotone_boundary(kind,direction,expected):
    dt=2.**-30
    if direction:dt=np.nextafter(dt,0. if direction<0 else np.inf)
    sim,spec=make(kind);sim.set_ferroelectric_params(spec['mask'],-2.**27,1e12);sim.set_ferroelectric_gamma(.125)
    sim.set_transient_dt(dt);sim.set_transient_t_final(dt)
    states=sim.solve_transient()
    assert all(s['lk_coupled']==expected and s['lk_material_field']==expected for s in states)


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('waveform',[False,True])
def test_actual_steps_choose_transport_without_changing_configured_clock(kind,waveform):
    sim,spec=make(kind);sim.set_ferroelectric_params(spec['mask'],-1e8,1e12)
    sim.set_transient_dt(1e-7);sim.set_transient_t_final(3e-10 if waveform else 1e-10)
    expected=[0.,1e-10,2e-10,3e-10] if waveform else [0.,1e-10]
    if waveform:sim.set_transient_voltage_waveforms(expected,{8:[0.,.002,-.001,0.]})
    states=sim.solve_transient()
    assert all(s['valid'] and s['lk_coupled'] and s['lk_material_field'] for s in states)
    np.testing.assert_array_equal([s['time_s'] for s in states],expected)


@pytest.mark.parametrize('kind',['carrier','interface'])
def test_automatic_transport_rechecks_each_run_and_does_not_latch(kind):
    sim,_=make(kind);assert sim.solve_transient()[-1]['lk_material_field']
    sim.set_charge_volume_fraction(np.full(9,.5));assert not sim.solve_transient()[-1]['lk_material_field']
    sim.set_charge_volume_fraction(np.ones(9));assert sim.solve_transient()[-1]['lk_material_field']
    for requested in [False,True,False]:
        sim.set_transient_lk_coupled(requested);states=sim.solve_transient()
        assert all(s['lk_coupled']==requested and s['lk_material_field']==requested for s in states)


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('log_space',[False,True])
def test_automatic_transport_failure_rollback_and_retry(kind,log_space):
    sim,_=make(kind,log_space=log_space);sim.set_nonlinear_history_enabled(True);sim.set_gummel_max_iter(0)
    failed=sim.solve_transient();assert not failed[-1]['valid'] and failed[-1]['dt_s']==0.
    assert failed[-1]['lk_coupled'] and failed[-1]['lk_material_field']
    for k in ['phi','n','p','P']:np.testing.assert_array_equal(failed[-1][k],failed[0][k])
    assert sim.get_transient_attempt_history()[0]['trials'][0]['solver']=='newton'
    sim.set_gummel_max_iter(100);retry=sim.solve_transient();fresh,_=make(kind,log_space=log_space)
    for a,b in zip(retry,fresh.solve_transient()):
        for k in ['phi','n','p','P']:np.testing.assert_array_equal(a[k],b[k])


@pytest.mark.parametrize('kind',['carrier','interface'])
def test_controller_and_explicit_material_requirements_are_preserved(kind):
    sim,_=make(kind);sim.set_transient_lk_substepping(True)
    with pytest.raises(ValueError,match='requires enabled coupled LK'):sim.solve_transient()
    sim,_=make(kind);sim.set_transient_lk_material_field(True)
    with pytest.raises(ValueError,match='requires coupled LK'):sim.solve_transient()


@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('cells',[32,64])
@pytest.mark.parametrize('log_space',[False,True])
def test_automatic_entry_matches_actual_nonzero_fe_sentaurus_stack(index,cells,log_space):
    data=json.loads((Path(__file__).parent/'data/sentaurus_fe_si_interface.json').read_text());case=data['cases'][index]
    sim,x=auto_commercial(case,cells,log_space);states=sim.solve_transient()
    assert all(s['valid'] and s['lk_coupled'] and s['lk_material_field'] for s in states)
    assert max(commercial_errors(case,states,x).values())<data['predeclared_waveform_peak_normalized_budget']


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('axis',[0,1,2])
def test_high_level_run_transient_without_policy_setters_matches_independent_blocks(kind,axis):
    from tcad.simulator import Simulator
    from tcad.mesh.structured_grid import StructuredGrid
    _,s=make(kind,axis=axis,stretched=False,source=True)
    shape=[1,1,1];shape[axis]=9
    bounds=[(0.,1e-7)]*3;bounds[axis]=(0.,8e-7)
    host=Simulator(StructuredGrid(tuple(bounds),*shape));core=host._sim
    mobile=np.ones(9) if kind=='carrier' else (~s['blocked']).astype(float)
    core.set_permittivity(s['eps']);core.set_doping(s['c']);core.set_mobility(.1*mobile,.05*mobile)
    core.set_effective_dos(np.full(9,s['scale']),np.full(9,s['scale']));core.set_bandgap(np.zeros(9))
    core.set_thermal_voltage(.025852)
    core.set_recombination(np.broadcast_to(s['tau'],(9,)).copy(),np.broadcast_to(s['tau'],(9,)).copy())
    core.set_optical_generation(np.broadcast_to(s['gen'],(9,)).copy())
    core.set_dirichlet_potential({0:0.,8:-.01})
    core.set_electron_bc({0:s['nn'][0]*s['scale'],8:s['scale']})
    core.set_hole_bc({0:s['pp'][0]*s['scale'],8:s['scale']})
    core.set_initial_guess(np.zeros(9),s['nn']*s['scale'],s['pp']*s['scale'])
    host.set_ferroelectric(alpha=1e8,beta=1e12,polar_axis='xyz'[(axis+1)%3],
        fe_mask_override=s['mask'],extra_depolarization_eps_r=30.)
    host.set_ferroelectric_builtin_field(2e4);host.set_transient(1e-10,2.5e-10,.1)
    states=host.run_transient(100,1e-12)
    check_blocks(core,s,kind,states)
    assert host.results['lk_coupled'] and host.results['lk_material_field']
    for k in ['phi','n','p','P']:np.testing.assert_array_equal(host.results[k],states[-1][k])


@pytest.mark.parametrize('kind',['carrier','interface'])
@pytest.mark.parametrize('axis',[0,1,2])
def test_adaptive_default_material_coarse_and_committed_steps_match_full_blocks(kind,axis):
    from test_transient_lk_error_control import controlled
    from tcad.postprocess import audit_transient_lk_energy,audit_transient_lk_electrical_error_control
    sim,spec=make(kind,axis=axis,source=True);controlled(sim,rtol=1e-3,atol=1e-8)
    sim.set_transient_lk_electrical_error_control(phi_atol=1e-5,carrier_rtol=1e-3,carrier_atol=1e10)
    states=sim.solve_transient();old=np.zeros((9,3));nn=spec['nn'];pp=spec['pp']
    step=block_step if kind=='carrier' else independent_step
    assert len(states)%2==1
    for i in range(1,len(states),2):
        a,b=states[i:i+2]
        pc,dc,phic,nc,hc=step(spec,old,nn,pp,a['dt_s']+b['dt_s'])
        for key,value in [('lk_coarse_P_C_per_m2',pc.ravel()),('lk_coarse_phi_V',phic)]:
            np.testing.assert_allclose(b[key],value,rtol=4e-8,atol=3e-12 if key=='lk_coarse_phi_V' else 3e-13)
        for key,value in [('lk_coarse_n_per_m3',nc),('lk_coarse_p_per_m3',hc)]:
            np.testing.assert_allclose(b[key]/spec['scale'],value,rtol=4e-9,atol=2e-12)
            if kind=='interface':assert max(abs(b[key][spec['blocked']]))<=np.nextafter(1e-20,np.inf)
        for s in [a,b]:old,_,_,nn,pp=step(spec,old,nn,pp,s['dt_s'])
    check_blocks(sim,spec,kind,states)
    assert audit_transient_lk_energy(states)['valid']
    assert audit_transient_lk_electrical_error_control(states)['valid']
