"""Independent manufactured storage, missing-band-work, and port conservation cases."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.postprocess.commercial_transient_energy import audit_sentaurus_planar_transient,KB,Q

X=np.array([0.,.3,.7,1.])*1e-7
AREA=1e-13
VOLUME=1e-20
ARGS=dict(x_m=X,cross_section_m2=AREA,heat_capacity_J_m3_K=1.,permittivity_F_m=1e-10,
    energy_atol_J=1e-30,energy_rtol=1e-8,particle_atol=1e-10,particle_rtol=1e-8,
    current_atol_A=1e-18,source_contract='source_free_MB_HD_constant_capacity_planar',
    time_discretization='backward_euler_all_solved_times')

def sample(t):
    z=np.zeros(4)
    return dict(time_s=t,n_m3=z+1e21,p_m3=z+2e21,Tn_K=z+600,Tp_K=z+600,Tl_K=z+600,
        phi_V=z.copy(),Ec_eV=z+.5,Ev_eV=z-.5,electric_field_V_m=z.copy(),
        joule_power_W=dict(electrons=0.,holes=0.,lattice=0.),
        collision_power_W=dict(electrons=0.,holes=0.,lattice=0.),
        ports={p:dict(phi_V=0.,Ec_eV=.5,Ev_eV=-.5,electron_current_A=0.,hole_current_A=0.,
            displacement_current_A=0.,total_current_A=0.,inward_heat_W=dict(electrons=0.,holes=0.,lattice=0.)) for p in ('left','right')})

def test_closed_three_reservoir_exchange_conserves_each_channel():
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    for r in rows:
        dt=r['time_s'];en=-2e-11*dt;hp=-1e-11*dt
        r['Tn_K']+=en/(1.5*KB*1e21*VOLUME)
        r['Tp_K']+=hp/(1.5*KB*2e21*VOLUME)
        r['Tl_K']-= (en+hp)/VOLUME
        r['collision_power_W'].update(electrons=-2e-11,holes=-1e-11,lattice=3e-11)
    result=audit_sentaurus_planar_transient(rows,**ARGS)
    assert result['accepted'] and result['reservoir_balances_valid']
    assert result['maximum_full_storage_residual_J']<1e-30
    assert not result['complete_device_energy'] and not result['physical_validated']
    assert not result['commercial_transient_band_storage_validated']

def test_variable_band_storage_cannot_be_hidden_by_kinetic_lattice_closure():
    old,new=sample(0),sample(1e-12)
    # Change only interior material bands, maintaining exactly fixed contacts.
    d=np.array([0.,.01,.02,0.])
    new['Ec_eV']+=d;new['Ev_eV']-=d
    result=audit_sentaurus_planar_transient([old,new],**ARGS)
    c=result['checkpoints'][-1]
    independent=np.trapezoid(Q*3e21*d,X)*AREA
    assert not result['accepted'] and not c['full_storage_balance_valid']
    assert result['reservoir_balances_valid']
    assert c['full_storage_residual_J']==pytest.approx(independent,rel=1e-12)
    assert c['cumulative_prescribed_band_work_J']==pytest.approx(independent,rel=1e-12)
    assert abs(c['residual_minus_band_work_J'])<1e-32

def test_particle_injection_includes_band_storage_and_contact_work():
    old,new=sample(0),sample(1e-12)
    dn=1e17;new['n_m3']+=dn
    inc=dn*VOLUME
    port=new['ports']['left'];port['electron_current_A']=-Q*inc/1e-12
    port['displacement_current_A']=-port['electron_current_A']
    kinetic=inc*1.5*KB*600
    port['inward_heat_W']['electrons']=kinetic/1e-12
    result=audit_sentaurus_planar_transient([old,new],**ARGS)
    assert result['accepted']
    # Hole material reference is 1 eV; electron material reference is zero here.
    assert result['checkpoints'][-1]['particle_balance_valid']
    broken=deepcopy(new);broken['ports']['left']['electron_current_A']=0.
    result=audit_sentaurus_planar_transient([old,broken],**ARGS)
    assert not result['accepted'] and not result['particle_balance_valid']

def test_electrostatic_storage_requires_displacement_work():
    old,new=sample(0),sample(1e-12)
    for r in (old,new):r['ports']['right']['phi_V']=.1
    new['electric_field_V_m'][:]=1e4
    energy=.5*1e-10*1e8*VOLUME
    for name,sign in (('left',-1),('right',1)):
        p=new['ports'][name];p['displacement_current_A']=sign*energy/(.1e-12)
        p['total_current_A']=p['displacement_current_A']
    # This manufactured ledger tests field power accounting; no Poisson claim.
    result=audit_sentaurus_planar_transient([old,new],**ARGS)
    assert result['accepted']
    new['ports']['right']['phi_V']=0.;old['ports']['right']['phi_V']=0.
    assert not audit_sentaurus_planar_transient([old,new],**ARGS)['accepted']

@pytest.mark.parametrize('mutation',[
    lambda r:r[1].update(time_s=0.),
    lambda r:r[1].update(n_m3=np.ones(3)),
    lambda r:r[1]['Tl_K'].__setitem__(0,np.nan),
    lambda r:r[1]['ports']['left']['inward_heat_W'].pop('holes'),
    lambda r:r[1]['ports'].pop('right'),
    lambda r:r[1]['ports']['right'].update(phi_V=.1),
    lambda r:r[1]['joule_power_W'].update(lattice=1.),
])
def test_incomplete_or_incompatible_exports_reject(mutation):
    rows=[sample(0),sample(1e-12)];mutation(rows)
    with pytest.raises((ValueError,KeyError)):audit_sentaurus_planar_transient(rows,**ARGS)

@pytest.mark.parametrize('override',[
    dict(source_contract='SRH'),dict(time_discretization='sampled_interpolation'),
    dict(cross_section_m2=True),dict(energy_rtol=-1.),dict(x_m=X[::-1]),
])
def test_unsupported_contract_and_invalid_budgets_reject(override):
    with pytest.raises(ValueError):audit_sentaurus_planar_transient([sample(0),sample(1e-12)],**(ARGS|override))
