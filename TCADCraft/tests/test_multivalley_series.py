"""Independent phase-space moments and actual MB multi-valley device steps."""
from copy import deepcopy
import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit

from tcad.physics.multivalley_thermionic import ThermionicValley, multivalley_thermionic_interface_flux as flux, _fermi
from tcad.physics.thermionic_interface import thermionic_interface_flux
from tcad.postprocess.multivalley_energy import audit_multivalley_interface
from tcad.postprocess.thermionic_electrothermal import audit_thermionic_electrothermal
from tcad.solver.thermionic_electrothermal import ThermionicElectrothermalCutCellTransport
from test_thermionic_electrothermal import fixture as base_fixture, BUDGET, MOMENT

Q=1.602176634e-19; K=1.380649e-23; H=6.62607015e-34; M=9.1093837015e-31
VALLEYS=(ThermionicValley('longitudinal',2,.916,.190,.190),
         ThermionicValley('transverse',4,.190,.916,.190))


@pytest.mark.parametrize('eta',[-30.,-16.,-8.,0.,8.,16.,80.,100.,101.,300.])
@pytest.mark.parametrize('order',[.5,1.,1.5,2.])
def test_fermi_integrals_match_adaptive_phase_space_integral(order,eta):
    expected=quad(lambda t:2*t**(2*order+1)*expit(eta-t*t),0.,math.sqrt(max(60.,eta+60.)),
                  epsabs=1e-22,epsrel=2e-12,limit=250)[0]/math.gamma(order+1)
    assert _fermi(order,eta)==pytest.approx(expected,rel=2e-9,abs=1e-30)


@pytest.mark.parametrize('statistics',['boltzmann','fermi_dirac'])
@pytest.mark.parametrize('densities',[(2e17,8e16),(2e25,8e23),(5e26,3e26)])
@pytest.mark.parametrize('temperatures',[(300.,300.),(300.,450.),(450.,300.)])
def test_all_reservoir_moments_match_independent_quadrature(statistics,densities,temperatures):
    valleys=(VALLEYS[0],ThermionicValley('offset',4,.190,.916,.190,
        band_offset_owner_J=.01*Q,band_offset_neighbor_J=.025*Q))
    args=(*densities,*temperatures,.10*Q,.13*Q,valleys,1e-14)
    result=flux(*args,statistics=statistics,potential_V=.02)
    audit=audit_multivalley_interface(result,*args,statistics=statistics,potential_V=.02,
        particle_flux_atol_s=1e4,energy_flux_atol_W=1e-13,entropy_atol_W_K=1e-15)
    assert audit['valid'],audit
    for key,expected in audit['expected'].items():
        absolute=1e-20 if key.endswith('_s') else 1e-30
        assert result[key]==pytest.approx(expected,rel=2e-9,abs=absolute)


def test_single_valley_MB_all_moments_reduce_to_equal_mass_kernel():
    v=(ThermionicValley('single',1,.2,.2,.2),)
    args=(2e24,8e23,300.,450.,.10*Q,.13*Q)
    result=flux(*args,v,1e-14,statistics='boltzmann',potential_V=.02)
    expected=thermionic_interface_flux(*args,.2*M,1e-14,potential_V=.02)
    for key in expected:
        assert result[key]==pytest.approx(float(expected[key]),rel=1e-12,abs=1e-26),key


@pytest.mark.parametrize('statistics',['boltzmann','fermi_dirac'])
def test_band_step_equilibrium_with_common_chemical_potential(statistics):
    T=320.;mu=.16*Q;bo=.1*Q;bn=.13*Q
    def density(band):
        result=0.
        for v in VALLEYS:
            dos=2*v.degeneracy*(2*np.pi*v.dos_mass_ratio*M*K*T/H**2)**1.5
            eta=(mu-band)/(K*T)
            occupation=math.exp(eta) if statistics=='boltzmann' else 2/math.sqrt(math.pi)*quad(
                lambda t:2*t*t*expit(eta-t*t),0.,math.sqrt(max(60.,eta+60.)),epsabs=1e-13,epsrel=1e-13)[0]
            result+=dos*occupation
        return result
    result=flux(density(bo),density(bn),T,T,bo,bn,VALLEYS,1e-14,statistics=statistics)
    assert abs(result['particle_flux_s'])<1e4
    assert abs(result['material_energy_flux_W'])<1e-17
    assert abs(result['entropy_production_W_K'])<1e-19


@pytest.mark.parametrize('statistics',['boltzmann','fermi_dirac'])
def test_energy_reference_shift_and_reverse_interface(statistics):
    args=(2e24,8e23,300.,450.,.10*Q,.13*Q,VALLEYS,1e-14)
    a=flux(*args,statistics=statistics)
    b=flux(*args[:4],args[4]+.7*Q,args[5]+.7*Q,VALLEYS,1e-14,statistics=statistics)
    assert b['particle_flux_s']==pytest.approx(a['particle_flux_s'],rel=1e-12)
    assert b['material_energy_flux_W']-a['material_energy_flux_W']==pytest.approx(.7*Q*a['particle_flux_s'],rel=1e-12)
    assert b['entropy_production_W_K']==pytest.approx(a['entropy_production_W_K'],rel=1e-12)
    reverse=flux(8e23,2e24,450.,300.,.13*Q,.10*Q,VALLEYS,1e-14,statistics=statistics)
    for key in ('particle_flux_s','material_energy_flux_W'):
        assert reverse[key]==pytest.approx(-a[key],rel=1e-12)
    assert reverse['entropy_production_W_K']==pytest.approx(a['entropy_production_W_K'],rel=1e-12)


def fixture(*,statistics='boltzmann',contacts=False,traps=False,quantum=False,count=2,blocked=False):
    base,state=base_fixture(contacts=contacts,traps=traps,quantum=quantum,count=count)
    dos=sum(2*v.degeneracy*(2*np.pi*v.dos_mass_ratio*M*K*base.T/H**2)**1.5 for v in VALLEYS)
    model=ThermionicElectrothermalCutCellTransport(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Nc_m3=dos,Nv_m3=dos,Ec_J=base.Ec,Eh_J=base.Eh,
        fixed_charge_C_m3=base.rhofix,trap_density_m3=base.Nt,capture_n_m3_s=base.cn,capture_p_m3_s=base.cp,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        quantum_n_J_m2=base.kn,quantum_p_J_m2=base.kp,particle_contacts=base.contacts,heat_bath_K=base.bath,
        thermionic_faces=base.tf,terminal_groups=dict(base.terminal_groups),thermionic_statistics=statistics,
        thermionic_valleys={'electrons':VALLEYS,'holes':VALLEYS},
        emission_factor_n=0. if blocked else 2.,emission_factor_p=0. if blocked else 2.)
    return model,state


@pytest.mark.parametrize('statistics',['boltzmann','fermi_dirac'])
@pytest.mark.parametrize('voltage',[-.02,0.,.02])
@pytest.mark.parametrize('temperatures',[(300.,300.),(300.,450.),(450.,300.)])
@pytest.mark.parametrize('density_scale',[1.,2e4])
def test_interface_obeys_both_half_cell_fluxes(statistics,voltage,temperatures,density_scale):
    model,state=fixture(statistics=statistics)
    T=np.array(temperatures)
    poisson=model._poisson(state.n_m3,state.p_m3,state.trap_fraction,1e-27)
    poisson['cell_potential_V']=np.array([0.,voltage]);poisson['face_potential_V'][model.tf]=voltage/2
    rows=model.interface_moments(state.n_m3*density_scale,state.p_m3*density_scale,T,poisson)
    for label,density,base,exponent,z in (
        ('electrons',state.n_m3,model.mn,model.mn_exponent,-1),
        ('holes',state.p_m3,model.mp,model.mp_exponent,1)):
        density=density*density_scale
        row=rows[label];mu=base*(model.T/T)**exponent
        d=z*Q*voltage/2/(K*T);B=np.ones(2);nonzero=d!=0;B[nonzero]=d[nonzero]/np.expm1(d[nonzero])
        Br=np.ones(2);Br[nonzero]=-d[nonzero]/np.expm1(-d[nonzero])
        left=mu[0]*K*T[0]/Q*model.half_owner_metric*(B[0]*density[0]-Br[0]*row['owner_density_m3'])
        right=mu[1]*K*T[1]/Q*model.half_neighbor_metric*(B[1]*row['neighbor_density_m3']-Br[1]*density[1])
        for half in (left,right):
            np.testing.assert_allclose(half,row['moments']['particle_flux_s'],rtol=2e-11,atol=1.)


@pytest.mark.parametrize('contacts,traps,quantum,count',[(False,False,False,2),(True,False,False,2),
    (True,True,False,2),(True,True,True,2),(True,True,False,4)])
def test_actual_MB_multivalley_steps_close_independent_local_audit(contacts,traps,quantum,count):
    model,old=fixture(contacts=contacts,traps=traps,quantum=quantum,count=count)
    for _ in range(2):
        new,report=model.step(old,2e-12,**BUDGET)
        audit=audit_thermionic_electrothermal(model,old,new,report,**BUDGET,**MOMENT)
        assert audit['valid'],audit
        assert 'multivalley_MB' in report['scope']
        assert max(abs(new.temperature_K-old.temperature_K))>.001
        old=new


@pytest.mark.parametrize('damage',['owner_trace','particle','material','kinetic','statistics'])
def test_multivalley_device_audit_rejects_damaged_report(damage):
    model,old=fixture(contacts=True);new,report=model.step(old,2e-12,**BUDGET)
    bad=deepcopy(report);row=bad['thermionic_interfaces']['electrons']
    if damage=='owner_trace':row['owner_density_m3']*=1.01
    elif damage=='statistics':row['moments']['statistics']='fermi_dirac'
    else:
        key={'particle':'particle_flux_s','material':'material_energy_flux_W','kinetic':'kinetic_owner_flux_W'}[damage]
        row['moments'][key]*=1.01
    assert not audit_thermionic_electrothermal(model,old,new,bad,**BUDGET,**MOMENT)['valid']


@pytest.mark.parametrize('unsupported',['FD','offset','DOS'])
def test_unsupported_device_physics_rejected_without_state_mutation(unsupported):
    model,old=fixture(statistics='fermi_dirac' if unsupported=='FD' else 'boltzmann')
    saved=deepcopy(old)
    if unsupported=='offset':model.thermionic_valleys['electrons']=(ThermionicValley('offset',1,.2,.2,.2,.01*Q),)
    if unsupported=='DOS':model.Nc*=1.01
    with pytest.raises(ValueError):model.step(old,2e-12,**BUDGET)
    for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
        np.testing.assert_array_equal(getattr(old,name),getattr(saved,name))


def test_blocked_multivalley_device_retains_heat_conduction():
    model,old=fixture(blocked=True);new,report=model.step(old,2e-12,**BUDGET)
    np.testing.assert_allclose(new.n_m3,old.n_m3,rtol=1e-13)
    assert new.temperature_K[0]>old.temperature_K[0]
    assert audit_thermionic_electrothermal(model,old,new,report,**BUDGET,**MOMENT)['valid']


@pytest.mark.parametrize('kwargs',[{'emission_factor':-1.},{'charge_sign':0},{'charge_sign':True}])
def test_invalid_emission_inputs_rejected(kwargs):
    with pytest.raises(ValueError):flux(1e21,1e21,300.,300.,0.,0.,VALLEYS,1e-14,**kwargs)
