"""Maxwell quadrature, reversal, entropy and compensated-ledger damage."""
from copy import deepcopy
import numpy as np
import pytest
from scipy.integrate import quad
from tcad.physics.thermionic_interface import thermionic_interface_flux,thermionic_interface_ledger,H
from tcad.postprocess.thermionic_energy import audit_thermionic_interface,audit_thermionic_ledger,steady_device_interface_energy
from tcad.solver.cut_cell_transport import Q,KB

M=9.1093837139e-31
BUDGETS=dict(particle_flux_atol_s=100.,energy_flux_atol_W=1e-19,entropy_atol_W_K=1e-21)


def arguments():return dict(n_owner_m3=2e22,n_neighbor_m3=7e21,T_owner_K=330.,T_neighbor_K=470.,
    band_owner_J=.11*Q,band_neighbor_J=.18*Q,mass_kg=M,area_m2=1e-13,potential_V=.2)


@pytest.mark.parametrize('temperatures',[(300.,450.),(450.,300.),(300.,300.)])
@pytest.mark.parametrize('barrier_eV',[-.2,0.,.15])
def test_particle_and_both_kinetic_fluxes_match_independent_velocity_integrals(temperatures,barrier_eV):
    To,Tn=temperatures;no,nn=2e22,7e21;bo=0.;bn=barrier_eV*Q;area=1e-13;high=max(bo,bn)
    def moments(n,T,band):
        lower=(high-band)/(KB*T)
        prefactor=2*area*n*np.sqrt(KB*T/(2*np.pi*M))
        count=prefactor*quad(lambda x:np.exp(-x),lower,np.inf,epsabs=1e-14,epsrel=1e-13)[0]
        kinetic=prefactor*KB*T*quad(lambda x:(x+1)*np.exp(-x),lower,np.inf,epsabs=1e-14,epsrel=1e-13)[0]
        return count,kinetic
    f,ef=moments(no,To,bo);r,er=moments(nn,Tn,bn)
    result=thermionic_interface_flux(no,nn,To,Tn,bo,bn,M,area)
    np.testing.assert_allclose(result['particle_flux_s'],f-r,rtol=1e-13,atol=.1)
    np.testing.assert_allclose(result['kinetic_owner_flux_W'],ef-er+(bo-bn)*r,rtol=1e-13,atol=1e-20)
    np.testing.assert_allclose(result['kinetic_neighbor_flux_W'],ef-er+(bo-bn)*f,rtol=1e-13,atol=1e-20)


def test_owner_neighbor_reversal_preserves_entropy_and_exchanges_local_heat():
    a=arguments();b=dict(a)
    for x,y in [('n_owner_m3','n_neighbor_m3'),('T_owner_K','T_neighbor_K'),('band_owner_J','band_neighbor_J')]:b[x],b[y]=a[y],a[x]
    p=thermionic_interface_flux(**a);q=thermionic_interface_flux(**b)
    for name in ('particle_flux_s','material_energy_flux_W','electrochemical_energy_flux_W'):
        np.testing.assert_allclose(p[name],-q[name],rtol=1e-13)
    np.testing.assert_allclose(p['kinetic_owner_flux_W'],-q['kinetic_neighbor_flux_W'],rtol=1e-13)
    np.testing.assert_allclose(p['lattice_heat_owner_W'],q['lattice_heat_neighbor_W'],rtol=1e-13)
    np.testing.assert_allclose(p['entropy_production_W_K'],q['entropy_production_W_K'],rtol=1e-13)


def test_common_band_and_voltage_gauges_leave_heat_and_entropy_invariant():
    a=arguments();original=thermionic_interface_flux(**a)
    a['band_owner_J']+=2*Q;a['band_neighbor_J']+=2*Q;a['potential_V']+=.7
    changed=thermionic_interface_flux(**a)
    for name in ('particle_flux_s','lattice_heat_owner_W','lattice_heat_neighbor_W','entropy_production_W_K'):
        np.testing.assert_allclose(original[name],changed[name],rtol=3e-13)
    np.testing.assert_allclose(changed['electrochemical_energy_flux_W']-original['electrochemical_energy_flux_W'],
        (2-.7)*Q*original['particle_flux_s'],rtol=3e-13)


def test_zero_number_flux_still_transports_heat_from_hot_to_cold():
    a=arguments();a['n_neighbor_m3']=a['n_owner_m3']*np.sqrt(a['T_owner_K']/a['T_neighbor_K'])*np.exp(
        -(a['band_neighbor_J']-a['band_owner_J'])/(KB*a['T_owner_K']))
    result=thermionic_interface_flux(**a)
    assert abs(result['particle_flux_s'])<1.
    assert result['material_energy_flux_W']<0
    assert result['lattice_heat_owner_W']>0 and result['lattice_heat_neighbor_W']<0
    assert result['entropy_production_W_K']>0


def test_temperature_equal_equilibrium_is_zero_current_heat_and_entropy():
    a=arguments();a['T_neighbor_K']=a['T_owner_K'];a['n_neighbor_m3']=a['n_owner_m3']*np.exp(
        (a['band_owner_J']-a['band_neighbor_J'])/(KB*a['T_owner_K']))
    result=thermionic_interface_flux(**a)
    assert abs(result['particle_flux_s'])<1.
    assert abs(result['material_energy_flux_W'])<1e-19
    assert abs(result['entropy_production_W_K'])<1e-30


def test_broadcast_sweep_has_nonnegative_entropy_and_locally_conserves_energy():
    rng=np.random.default_rng(62831);a=arguments();count=300
    a.update(n_owner_m3=10**rng.uniform(19,25,count),n_neighbor_m3=10**rng.uniform(19,25,count),
        T_owner_K=rng.uniform(100,1400,count),T_neighbor_K=rng.uniform(100,1400,count),
        band_owner_J=rng.uniform(-.5,.5,count)*Q,band_neighbor_J=rng.uniform(-.5,.5,count)*Q)
    ledger=thermionic_interface_ledger(**a,dt_s=2e-12)
    assert np.all(ledger['flux']['entropy_production_W_K']>=0)
    scale=abs(ledger['carrier_storage_total_J'])+abs(ledger['lattice_heat_owner_J'])+abs(ledger['lattice_heat_neighbor_J'])
    assert np.all(abs(ledger['local_energy_residual_J'])<=5e-14*scale+1e-35)
    assert not ledger['state_advanced'] and not ledger['complete_device_energy']


def test_blocked_interface_has_no_particle_heat_energy_or_entropy_flux():
    a=arguments();a['emission_factor']=0
    result=thermionic_interface_flux(**a)
    assert all(v==0 for v in result.values())


@pytest.mark.parametrize('field,value',[
    ('mass_kg',-M),('T_owner_K',0.),('n_neighbor_m3',-1.),('emission_factor',-1.),
    ('area_m2',True),('potential_V',np.nan),('band_owner_J',1j),('charge_sign',0),
    ('T_neighbor_K',np.ones((2,3))),])
def test_invalid_interface_inputs_rejected(field,value):
    a=arguments();a[field]=value
    if field=='T_neighbor_K':a['T_owner_K']=np.ones(4)
    with pytest.raises(ValueError):thermionic_interface_flux(**a)


@pytest.mark.parametrize('field',['particle_flux_s','kinetic_owner_flux_W','material_energy_flux_W',
    'lattice_heat_neighbor_W','entropy_production_W_K'])
def test_extended_precision_audit_rejects_corrupted_moments(field):
    a=arguments();report=thermionic_interface_flux(**a)
    assert audit_thermionic_interface(report,**a,**BUDGETS)['valid']
    report[field]=report[field]*1.2
    assert not audit_thermionic_interface(report,**a,**BUDGETS)['valid']


@pytest.mark.parametrize('damage',['compensated_heat','compensated_storage','residual','entropy','state_advanced'])
def test_ledger_audit_checks_components_even_when_false_corrections_cancel(damage):
    a=arguments();ledger=thermionic_interface_ledger(**a,dt_s=2e-12)
    assert audit_thermionic_ledger(ledger,**a,dt_s=2e-12,**BUDGETS,energy_atol_J=1e-29)['valid']
    bad=deepcopy(ledger)
    if damage=='compensated_heat':bad['lattice_heat_owner_J']+=1e-22;bad['lattice_heat_neighbor_J']-=1e-22
    elif damage=='compensated_storage':bad['carrier_storage_owner_J']+=1e-22;bad['carrier_storage_neighbor_J']-=1e-22
    elif damage=='residual':bad['local_energy_residual_J']+=1e-22
    elif damage=='entropy':bad['entropy_produced_J_K']*=1.2
    else:bad['state_advanced']=True
    assert not audit_thermionic_ledger(bad,**a,dt_s=2e-12,**BUDGETS,energy_atol_J=1e-29)['valid']


@pytest.mark.parametrize('dt',[0.,-1.,True,np.nan])
def test_invalid_ledger_intervals_rejected(dt):
    with pytest.raises(ValueError):thermionic_interface_ledger(**arguments(),dt_s=dt)


def device():
    from tcad.mesh.polyhedral_regions import region_cut_cells
    from tcad.solver.heterojunction_cut_cell import IsothermalHeterojunctionDevice
    from tcad.solver.electrothermal_cut_cell import CarrierReservoir
    L=1e-7;mesh=region_cut_cells([np.linspace(0,L,7),np.array([0.,L]),np.array([0.,L])],{'box':[[]]})
    groups={'left':[],'right':[]};bc={}
    for f,face in enumerate(mesh.faces):
        if face.neighbor<0 and abs(face.area_vector_m2[0])>0:
            name='left' if face.centroid_m[0]<L/2 else 'right';groups[name].append(f);bc[f]=0. if name=='left' else .001
    face=min((f for f,v in enumerate(mesh.faces) if v.neighbor>=0),key=lambda f:abs(mesh.faces[f].centroid_m[0]-L/2))
    dos=1e25;mass=H**2/(2*np.pi*KB*300)*(dos/2)**(2/3);speed=2*np.sqrt(KB*300/(2*np.pi*mass))
    model=IsothermalHeterojunctionDevice(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        particle_contacts={f:CarrierReservoir(1e21,1e21) for f in bc},terminal_groups=groups,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Nc_m3=dos,Nv_m3=dos,Ec_J=0.,Eh_J=0.,
        interface_velocity_n_m_s={face:speed},interface_velocity_p_m_s={face:speed})
    return model


def test_steady_device_adapter_reuses_actual_traces_without_modifying_state():
    model=device();result=model.solve(1e21,1e21,charge_atol_C=1e-26,particle_flux_atol_s=1e4,current_atol_A=1e-14)
    previous=deepcopy(result)
    report=steady_device_interface_energy(model,result,2e-12,charge_atol_C=1e-26,current_atol_A=1e-14,
        **BUDGETS,energy_atol_J=1e-29)
    assert report['valid'] and not report['temperature_solved']
    np.testing.assert_array_equal(previous['n_m3'],result['n_m3'])
    assert 'carriers' not in result


def test_steady_device_adapter_rejects_phenomenological_transfer_velocity():
    model=device();model.vn*=.5
    result=model.solve(1e21,1e21,charge_atol_C=1e-26,particle_flux_atol_s=1e4,current_atol_A=1e-14)
    with pytest.raises(ValueError,match='Maxwell emission velocity'):
        steady_device_interface_energy(model,result,2e-12,charge_atol_C=1e-26,current_atol_A=1e-14,
            **BUDGETS,energy_atol_J=1e-29)
