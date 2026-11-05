"""Independent series FE/oxide solves and failure detection for device energy."""
from copy import deepcopy

import numpy as np
import pytest
from scipy.optimize import brentq

from tcad.validation import audit_ferroelectric_device_energy


def series(axis=0, alpha=1e9, beta=1e12, steps=8):
    area=6.4e-13;length=np.array([.4e-6,.4e-6]);eps=np.array([15.,3.9])*8.8542e-12
    t=np.linspace(0,6e-10,steps+1);voltage=np.interp(t,[0,2e-10,6e-10],[0,.02,.02])
    p=np.zeros((len(t),2,3));e=np.zeros_like(p);q=np.zeros((len(t),2));v=np.column_stack([voltage,np.zeros(len(t))])
    # Solve the voltage constraint and local constitutive equation together,
    # independently of the energy identities implemented by the auditor.
    for i in range(1,len(t)):
        rate=.1/(t[i]-t[i-1]);previous=p[i-1,0,axis]
        def constraint(polar):
            field=alpha*polar+beta*polar**3+rate*(polar-previous)
            displacement=eps[0]*field+polar
            return length[0]*field+length[1]*displacement/eps[1]-voltage[i]
        polar=brentq(constraint,-.1,.1,xtol=1e-20,rtol=1e-14)
        p[i,0,axis]=polar
        e[i,0,axis]=alpha*polar+beta*polar**3+rate*(polar-previous)
        displacement=eps[0]*e[i,0,axis]+polar
        e[i,1,axis]=displacement/eps[1];q[i]=[area*displacement,-area*displacement]
    return dict(times_s=t,electric_field_V_m=e,polarization_C_m2=p,
        cell_volumes_m3=area*length,permittivity_F_m=eps,
        ferroelectric_mask=np.array([True,False]),alpha=alpha,beta=beta,viscosity=.1,
        electrode_voltages_V=v,electrode_charges_C=q,
        boundary_coverage_complete=True,converged=True,
        energy_scale_J=1e-18,lk_field_scale_V_m=1e5,charge_scale_C=1e-17,energy_rtol=1e-10,lk_rtol=1e-10)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('alpha,beta',[(1e9,0.),(1e9,1e12),(-1e8,0.),(-1e8,1e12)])
def test_series_closes_storage_loss_and_source_work(axis,alpha,beta):
    args=series(axis,alpha,beta);frozen=deepcopy(args)
    r=audit_ferroelectric_device_energy(**args)
    assert r['valid'] and r['energy_balance_validated'] and r['local_lk_compatible']
    assert not r['complete_device_energy'] and not r['physical_validated']
    assert r['max_energy_relative_residual']<1e-13
    assert r['max_lk_relative_residual']<1e-13
    assert np.all(r['lk_dissipation_J']>=0) and np.all(r['dielectric_be_correction_J']>=0)
    if alpha<0:assert np.any(r['landau_be_correction_J']<0)
    for name,value in args.items():np.testing.assert_array_equal(value,frozen[name])


def test_cells_can_be_split_without_changing_energy():
    args=series();expected=audit_ferroelectric_device_energy(**args)
    for name in ['electric_field_V_m','polarization_C_m2']:
        args[name]=np.repeat(args[name],3,axis=1)
    args['cell_volumes_m3']=np.repeat(args['cell_volumes_m3']/3,3)
    for name in ['permittivity_F_m','ferroelectric_mask']:
        args[name]=np.repeat(args[name],3)
    args['alpha']=np.array([1e9]*3+[0.]*3)
    args['beta']=np.array([1e12]*3+[0.]*3)
    args['viscosity']=np.array([.1]*3+[0.]*3)
    result=audit_ferroelectric_device_energy(**args)
    assert result['valid']
    for k in expected:
        if isinstance(expected[k],np.ndarray):np.testing.assert_allclose(result[k],expected[k],rtol=1e-12,atol=1e-32)


def test_voltage_gauge_invariance_with_balanced_charge():
    args=series();expected=audit_ferroelectric_device_energy(**args)
    args['electrode_voltages_V']+=.25
    actual=audit_ferroelectric_device_energy(**args)
    assert actual['valid']
    np.testing.assert_allclose(actual['source_work_J'],expected['source_work_J'],rtol=1e-13)


def test_be_corrections_decrease_under_time_refinement():
    corrections=[]
    for steps in [24,48,96]:
        result=audit_ferroelectric_device_energy(**series(beta=0,steps=steps))
        assert result['valid']
        correction=sum(result['dielectric_be_correction_J']+result['landau_be_correction_J'])
        corrections.append(correction)
    assert 1.8<corrections[0]/corrections[1]<2.2
    assert 1.8<corrections[1]/corrections[2]<2.2


@pytest.mark.parametrize('damage',['charge_sign','oxide_storage','polarization','viscosity','endpoint_voltage','charge_offset_jump'])
def test_detects_independent_energy_or_constitutive_errors(damage):
    args=series()
    if damage=='charge_sign':args['electrode_charges_C']*=-1
    if damage=='oxide_storage':args['cell_volumes_m3'][1]*=.5
    if damage=='polarization':args['polarization_C_m2'][3,0,1]=1e-4
    if damage=='viscosity':args['viscosity']*=2
    if damage=='endpoint_voltage':args['electrode_voltages_V'][1:]=args['electrode_voltages_V'][:-1].copy()
    if damage=='charge_offset_jump':args['electrode_charges_C'][3,0]+=1e-17
    result=audit_ferroelectric_device_energy(**args)
    assert not result['valid']
    if damage in ['polarization','viscosity']:assert not result['local_lk_compatible']
    else:assert not result['energy_balance_compatible']


@pytest.mark.parametrize('name,value',[
    ('boundary_coverage_complete',False),('boundary_coverage_complete',1),
    ('converged',False),('converged',[True,False]),('converged',1),
    ('energy_scale_J',0.),('energy_scale_J',-1.),('energy_scale_J',True),
    ('lk_field_scale_V_m',0.),('energy_rtol',1.),('energy_rtol',-.1),
    ('lk_rtol',1.),('lk_atol_V_m',-1.),('energy_atol_J',-1.),
    ('alpha',[1.,2.,3.]),('alpha',np.nan),('beta',-1.),('viscosity',0.),
    ('ferroelectric_mask',[1,0]),('ferroelectric_mask',[False,False]),
    ('permittivity_F_m',[0.,1.]),('cell_volumes_m3',[-1.,1.]),
    ('times_s',[0.,1.,1.]),('times_s',[0.]),
    ('electric_field_V_m',np.zeros((9,2,2))),('polarization_C_m2',np.zeros((9,2))),
    ('electrode_voltages_V',np.zeros((9,1))),('electrode_charges_C',np.zeros((8,2))),
    ('alpha',1j),('beta','1'),('electric_field_V_m',np.full((9,2,3),np.inf)),
    ('charge_scale_C',0.),('charge_rtol',1.),('charge_atol_C',-1.),
])
def test_rejects_invalid_contract(name,value):
    args=series();args[name]=value
    with pytest.raises(ValueError):audit_ferroelectric_device_energy(**args)


def test_rejects_nonzero_polarization_in_oxide():
    args=series();args['polarization_C_m2'][2,1,0]=1e-30
    with pytest.raises(ValueError,match='non-FE'):audit_ferroelectric_device_energy(**args)


def test_rejects_unrepresentable_energy_export():
    args=series();args['cell_volumes_m3'][:]=1e308
    args['electric_field_V_m'][-1]=1e200
    with pytest.raises(ValueError,match='range'):audit_ferroelectric_device_energy(**args)


def test_constant_charge_baselines_do_not_change_work():
    args=series();expected=audit_ferroelectric_device_energy(**args)
    args['electrode_charges_C']+=np.array([1e-16,-1e-16])
    actual=audit_ferroelectric_device_energy(**args)
    assert actual['valid']
    np.testing.assert_allclose(actual['source_work_J'],expected['source_work_J'],rtol=1e-12,atol=1e-32)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('alpha',[1e8,-1e8])
def test_native_nonuniform_fe_oxide_device_closes_energy(axis,alpha):
    from tcad.core import PyDeviceSimulator
    count=17;shape=[1,1,1];shape[axis]=count
    spacing=[.8e-6/(count-1),.8e-6/(count-1),.8e-6/(count-1)]
    x=.8e-6*(np.arange(count)/(count-1))**1.3
    mask=x<.4e-6;eps=8.8542e-12*np.where(mask,15.,3.9)
    sim=PyDeviceSimulator(*shape,*spacing);getattr(sim,'set_'+'xyz'[axis]+'_positions')(x)
    zero=np.zeros(count);sim.set_permittivity(eps);sim.set_mobility(zero,zero);sim.set_doping(zero)
    sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16));sim.set_bandgap(np.full(count,6.))
    sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
    sim.set_dirichlet_potential({0:0.,count-1:0.});sim.set_initial_guess(zero,zero,zero)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(mask.astype(np.int8),alpha,1e12);sim.set_ferroelectric_gamma(.1)
    sim.set_ferroelectric_polar_axis(axis);sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_material_field(True);sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    times=np.array([0.,5e-11,1e-10,2e-10,4e-10,6e-10]);voltage=np.minimum(times/2e-10,1.)*.02
    sim.set_transient_dt(times[-1]);sim.set_transient_t_final(times[-1])
    sim.set_transient_voltage_waveforms(times,{0:voltage})
    states=sim.solve_transient();assert all(s['valid'] for s in states)
    area=np.prod([h for a,h in enumerate(spacing) if a!=axis])
    widths=(np.r_[0.,np.diff(x)]+np.r_[np.diff(x),0.])/2
    args=dict(times_s=times,
        electric_field_V_m=np.array([np.column_stack([s['E'+a] for a in 'xyz']) for s in states]),
        polarization_C_m2=np.array([s['P'].reshape(count,3) for s in states]),
        cell_volumes_m3=widths*area,permittivity_F_m=eps,ferroelectric_mask=mask,
        alpha=alpha,beta=1e12,viscosity=.1,
        electrode_voltages_V=np.column_stack([voltage,np.zeros(len(times))]),
        electrode_charges_C=np.array([s['electrode_charges_C'] for s in states]),
        boundary_coverage_complete=True,converged=True,energy_scale_J=1e-20,
        lk_field_scale_V_m=1e5,charge_scale_C=1e-19,energy_rtol=1e-9,lk_rtol=1e-9)
    result=audit_ferroelectric_device_energy(**args)
    assert result['valid'],result
    assert result['max_energy_relative_residual']<1e-11
    assert result['max_lk_relative_residual']<1e-11


def test_zero_voltage_and_zero_energy_cannot_hide_unbalanced_charge():
    args=series()
    for name in ['electric_field_V_m','polarization_C_m2','electrode_voltages_V','electrode_charges_C']:
        args[name][:]=0.
    args['electrode_charges_C'][3,0]=1e-17
    r=audit_ferroelectric_device_energy(**args)
    assert r['energy_balance_compatible'] and r['local_lk_compatible']
    assert not r['charge_balance_compatible'] and not r['valid'] and not r['energy_balance_validated']


def test_multiple_materials_and_six_terminals_close_all_three_components():
    branches=[series(axis,alpha,beta) for axis,alpha,beta in
        [(0,1e9,1e12),(1,-1e8,0.),(2,3e8,2e12)]]
    args=deepcopy(branches[0])
    for name in ['electric_field_V_m','polarization_C_m2','electrode_voltages_V','electrode_charges_C']:
        args[name]=np.concatenate([b[name] for b in branches],axis=1)
    for name in ['cell_volumes_m3','permittivity_F_m','ferroelectric_mask']:
        args[name]=np.concatenate([b[name] for b in branches])
    for name in ['alpha','beta','viscosity']:
        args[name]=np.repeat([b[name] for b in branches],2)
    r=audit_ferroelectric_device_energy(**args)
    assert r['valid'] and r['max_energy_relative_residual']<1e-13
    expected=[audit_ferroelectric_device_energy(**b) for b in branches]
    for name in ['source_work_J','dielectric_storage_change_J','landau_storage_change_J',
        'lk_dissipation_J','dielectric_be_correction_J','landau_be_correction_J']:
        np.testing.assert_allclose(r[name],sum(e[name] for e in expected),rtol=1e-13,atol=1e-34)


@pytest.mark.parametrize('scale',[1e-300,1e308])
def test_rejects_unrepresentable_relative_residual(scale):
    args=series();args['energy_scale_J']=scale
    args['electrode_charges_C'][-1,0]+=1e300 if scale<1 else 1e-17
    with pytest.raises(ValueError,match='range'):audit_ferroelectric_device_energy(**args)


def test_rejects_nonzero_storage_below_float64_range():
    args=series()
    args['electric_field_V_m'][:]=0.;args['electric_field_V_m'][-1,0,0]=1e-100
    args['polarization_C_m2'][:]=0.;args['electrode_charges_C'][:]=0.
    args['permittivity_F_m'][:]=1e-300;args['cell_volumes_m3'][:]=1e-300
    with pytest.raises(ValueError,match='range'):audit_ferroelectric_device_energy(**args)
