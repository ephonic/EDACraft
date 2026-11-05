"""Independent analytic ledgers; manufactured cases do not certify Poisson solutions."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.postprocess.commercial_volume_energy import audit_sentaurus_mesh_integrals,Q


def fixture():
    rows=[]
    cumulative=dict(electrons=0.,holes=0.,lattice=0.)
    times=[0.,1e-12,3e-12]
    powers=[(0.,0.,0.),(2e-10,-8e-11,4e-10),(7e-10,1e-10,-2e-10)]
    for i,t in enumerate(times):
        heat=dict(zip(cumulative,powers[i]))
        if i:
            for s in cumulative:cumulative[s]+=(t-times[i-1])*heat[s]
        port=dict(phi_V=0.,Ec_eV=.5,Ev_eV=-.6,electron_current_A=0.,hole_current_A=0.,
                  displacement_current_A=0.,total_current_A=0.,inward_heat_W=heat)
        right=deepcopy(port);right['inward_heat_W']={s:0. for s in cumulative}
        rows.append(dict(time_s=t,storage_J={**{s:(i0+4)*1e-18+cumulative[s] for i0,s in enumerate(cumulative)},
            'material_bands':8e-18,'electrostatic':5e-17},particles=dict(electrons=100.,holes=80.),
            joule_power_W={s:0. for s in cumulative},collision_power_W={s:0. for s in cumulative},
            ports={'left':port,'right':right}))
    return rows


def audit(rows,**kwargs):
    options=dict(reference_energy_eV=0.,energy_atol_J=1e-28,energy_rtol=1e-12,
        particle_atol=1e-9,particle_rtol=1e-12,current_atol_A=1e-15,
        source_contract='source_free_MB_HD_fixed_material_bands_mesh_integrals',
        time_discretization='backward_euler_all_solved_times',
        field_energy_contract='mesh_vertex_electric_field_quadrature')
    return audit_sentaurus_mesh_integrals(rows,**{**options,**kwargs})


@pytest.mark.parametrize('field',['mesh_vertex_electric_field_quadrature','uniform_permittivity_discrete_box'])
def test_nonuniform_be_exact_analytic_heat(field):
    rows=fixture();before=deepcopy(rows);r=audit(rows,field_energy_contract=field)
    assert r['accepted'] and r['samples']==3 and rows==before
    end=r['checkpoints'][-1]
    # Exact right-endpoint integral; a trapezoid produces a different answer.
    assert end['energy_increments_J']['electrons']==pytest.approx(1.6e-21,abs=1e-32)
    assert max(abs(c['full_storage_residual_J']) for c in r['checkpoints'])<1e-29
    assert not any(r[k] for k in ('physical_validated','complete_device_energy','experimental_validated','general_complex_physics_closed'))


def test_opposite_channel_corruption_cannot_hide_in_total():
    rows=fixture()
    for row in rows[1:]:
        row['joule_power_W']['electrons']=3e-10
        row['joule_power_W']['holes']=-3e-10
    r=audit(rows)
    assert r['full_storage_balance_valid'] and not r['reservoir_balances_valid'] and not r['accepted']


def test_field_storage_corruption_is_independent_of_heat_channels():
    rows=fixture();rows[-1]['storage_J']['electrostatic']+=1e-21
    r=audit(rows)
    assert r['reservoir_balances_valid'] and not r['full_storage_balance_valid']


def test_energy_budget_uses_net_drive_instead_of_turnover():
    rows=fixture()
    for row in rows[1:]:
        row['joule_power_W']['electrons']=100.
        row['collision_power_W']['electrons']=-100.
    rows[-1]['storage_J']['electrons']+=1e-21
    r=audit(rows,energy_rtol=.01)
    assert not r['accepted'] and r['checkpoints'][-1]['reservoir_budgets_J']['electrons']<1e-22


def charging_rows(reference):
    rows=fixture();rate=1e12
    for row in rows:
        row['particles']['electrons']=100.+rate*row['time_s']
        for p in row['ports'].values():p['inward_heat_W']={s:0. for s in ('electrons','holes','lattice')}
        row['ports']['left']['electron_current_A']=-Q*rate
        row['ports']['left']['displacement_current_A']=Q*rate
        row['storage_J'].update(electrons=4e-18,holes=5e-18,lattice=6e-18)
        n=row['particles']['electrons'];p=row['particles']['holes']
        row['storage_J']['material_bands']=Q*(n*(.5-reference)+p*(.6+reference))
    return rows


def test_charge_inflow_and_common_energy_reference_covariance():
    a=audit(charging_rows(0.));b=audit(charging_rows(.3),reference_energy_eV=.3)
    assert a['accepted'] and b['accepted']
    assert a['checkpoints'][-1]['cumulative_contact_work_J']!=b['checkpoints'][-1]['cumulative_contact_work_J']
    assert abs(b['checkpoints'][-1]['full_storage_residual_J'])<1e-29


def test_wrong_reference_or_particle_inflow_rejected():
    rows=charging_rows(.3)
    assert not audit(rows,reference_energy_eV=0.)['full_storage_balance_valid']
    rows[-1]['particles']['electrons']+=1.
    assert not audit(rows,reference_energy_eV=.3)['particle_balance_valid']


@pytest.mark.parametrize('mutation',[
    lambda r:r[-1]['ports'].pop('right'),
    lambda r:r[-1]['ports']['left'].__setitem__('phi_V',.01),
    lambda r:r[-1]['ports']['left']['inward_heat_W'].pop('holes'),
    lambda r:r[-1]['storage_J'].pop('material_bands'),
    lambda r:r[-1]['storage_J'].__setitem__('electrostatic',-1.),
    lambda r:r[-1]['joule_power_W'].__setitem__('lattice',1e-10),
    lambda r:r[-1]['particles'].__setitem__('electrons',0.),
])
def test_incomplete_or_invalid_inputs(mutation):
    rows=fixture();mutation(rows)
    with pytest.raises((ValueError,KeyError)):audit(rows)


@pytest.mark.parametrize('clock',[0.,1e-12,np.nan,np.inf,-1.])
def test_solved_clocks_must_be_finite_strictly_increasing(clock):
    rows=fixture();rows[-1]['time_s']=clock
    with pytest.raises(ValueError):audit(rows)


@pytest.mark.parametrize('key,value',[
    ('source_contract','general_device'),('time_discretization','trapezoid'),('field_energy_contract','inferred'),
    ('energy_atol_J',-1.),('energy_rtol',np.inf),('particle_atol',True),('current_atol_A',np.nan),
])
def test_contracts_and_budgets_are_explicit(key,value):
    with pytest.raises(ValueError):audit(fixture(),**{key:value})


def test_current_decomposition_and_kcl_are_separate_checks():
    rows=fixture();rows[-1]['ports']['left']['total_current_A']=1e-10
    assert not audit(rows)['current_balance_valid']
    rows=fixture()
    for p in rows[-1]['ports'].values():
        p['electron_current_A']=1e-10;p['total_current_A']=1e-10
    assert not audit(rows)['current_balance_valid']
