"""Independent contact reservoirs, lattice constitutive laws and native ownership."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import _bindings
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal, ThreeTemperatureState
from tcad.solver.three_temperature_contacts import normalize_contact_temperatures
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy

BUDGET=dict(charge_atol_C=2e-28,particle_atol=1e-9,energy_atol_J=1e-27)
FIELDS=('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K')


def make(configured=True, **kwargs):
    mesh=region_cut_cells([np.linspace(0,1e-7,6),np.array([0.,1e-7]),np.array([0.,1e-6])],{'box':[[]]})
    contacts={f:CarrierReservoir(1e22,1e22,600.) for f,face in enumerate(mesh.faces)
              if face.neighbor<0 and face.area_vector_m2[0]!=0}
    mapping={f:(599.8,600.3) for f in contacts} if configured else None
    model=ThreeTemperatureElectrothermal(mesh,permittivity_F_m=1e-10,
        dirichlet_V={f:0. for f in contacts},particle_contacts=contacts,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,
        mobility_temperature_exponent_n=1.5,mobility_temperature_exponent_p=1.5,
        Ec_J=.5*1.602176634e-19,Eh_J=.5*1.602176634e-19,
        valleys_n=(ThermionicValley('e',1,.3,.3,.3),),valleys_p=(ThermionicValley('h',1,.4,.4,.4),),
        heat_bath_K={f:600. for f in contacts},heat_capacity_J_m3_K=1.,thermal_conductivity_W_m_K=1e-4,
        relaxation_time_n_s=1e-13,relaxation_time_p_s=4e-13,bulk_potential_path='linear_series',
        contact_carrier_temperature_K=mapping,**kwargs)
    t=np.full(5,600.);n=np.full(5,np.longdouble('1e22'))
    return model,ThreeTemperatureState(n,n,np.full(5,.3),t,0.,t,t)


@pytest.mark.parametrize('mode',['cell_mean','quadratic_entropy_limited_1d'])
def test_native_independent_contact_reservoirs_pass_independent_energy_audit(mode):
    model,old=make(transport_reconstruction=mode)
    new,report=model.step(old,1e-20,**BUDGET)
    assert report['independent_audit']['valid'] and new.time_s==1e-20
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
    assert not report['complete_device_energy'] and not report['physical_validated']
    wrong=deepcopy(model);wrong.contact_carrier_temperature_K={}
    try:checked=audit_three_temperature_energy(wrong,old,new,report,**BUDGET)
    except ValueError:return
    assert not checked['valid']


def test_native_matches_python_reference_with_separate_carrier_and_lattice_temperatures():
    model,old=make();other=deepcopy(model);other.residual_orchestration='python'
    a,ra=model.step(old,1e-20,**BUDGET);b,rb=other.step(old,1e-20,**BUDGET)
    assert ra['independent_audit']['valid'] and rb['independent_audit']['valid']
    for s in ('electrons','holes'):
        np.testing.assert_allclose(ra['integrated_carrier_energy_flux_W'][s],rb['integrated_carrier_energy_flux_W'][s],rtol=1e-8,atol=1e-15)
    for f in FIELDS:np.testing.assert_allclose(getattr(a,f),getattr(b,f),rtol=1e-13,atol=1e-10)


@pytest.mark.parametrize('extra',[dict(band_temperature_slope_n_J_K=1e-24,band_temperature_slope_p_J_K=2e-24),
                                dict(pair_generation_rate_m3_s=1e22)])
def test_contact_wrapper_preserves_band_and_source_schemas(extra):
    model,old=make(**extra);new,r=model.step(old,1e-20,**BUDGET)
    assert audit_three_temperature_energy(model,old,new,r,**BUDGET)['valid']


def test_owned_configuration_detaches_and_failed_step_rolls_back():
    model,old=make();device=DeviceThreeTemperature(model,old);before=device.native_state()
    model.contact_carrier_temperature_K.clear()
    with pytest.raises((ValueError,RuntimeError)):device.advance(1e-12,max_nfev=1,**BUDGET)
    assert before==device.native_state() and device.state.time_s==0
    new,r=device.advance(1e-20,**BUDGET)
    assert r['independent_audit']['valid'] and new.time_s==1e-20


def test_shared_temperature_default_packet_and_trajectory_are_unchanged():
    model,old=make(False);empty=deepcopy(model);empty.contact_carrier_temperature_K={}
    args=pack_three_temperature_inputs(model,old,1e-20,**BUDGET)
    assert args==pack_three_temperature_inputs(empty,old,1e-20,**BUDGET)
    explicit=deepcopy(model);explicit.contact_carrier_temperature_K={f:(600.,600.) for f in model.contacts}
    a,ra=model.step(old,1e-20,**BUDGET);b,rb=explicit.step(old,1e-20,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(a,f),getattr(b,f))
    for key in ('face_moments','integrated_particle_flux_s','integrated_carrier_energy_flux_W'):
        assert repr(ra[key])==repr(rb[key])


def test_normalization_detaches_input_and_preserves_unconfigured_contact():
    model,old=make(False);face=next(iter(model.contacts));pair=[599.,601.]
    config=normalize_contact_temperatures(model.contacts,{face:pair});pair[0]=900.
    assert config[face]==(599.,601.)
    model.contact_carrier_temperature_K=config
    new,r=model.step(old,1e-20,**BUDGET)
    assert r['independent_audit']['valid']


@pytest.mark.parametrize('bad',[True,600.,[600.],[600.,600.,600.],[True,600.],[600.,np.nan],
                                [600.,np.inf],[1.,600.],[600.,1e5],['600','600'],[600.,1+2j]])
def test_invalid_contact_values_rejected_before_native_call(bad):
    model,old=make(False);face=next(iter(model.contacts));model.contact_carrier_temperature_K={face:bad}
    with pytest.raises(ValueError):pack_three_temperature_inputs(model,old,1e-20,**BUDGET)


@pytest.mark.parametrize('kind',['float','bool','missing','lateral','not_mapping'])
def test_invalid_contact_mapping_rejected(kind):
    model,old=make(False);f=next(iter(model.contacts))
    key={'float':float(f),'bool':True,'missing':100000,'lateral':next(i for i,x in enumerate(model.mesh.faces) if x.area_vector_m2[0]==0)}
    model.contact_carrier_temperature_K=[] if kind=='not_mapping' else {key[kind]:(600.,600.)}
    with pytest.raises(ValueError):pack_three_temperature_inputs(model,old,1e-20,**BUDGET)


@pytest.mark.parametrize('damage',['short','fractional','nonfinite','zero_contact','noncontact','nested'])
def test_raw_contact_packet_cannot_silently_discard_boundary_option(damage):
    model,old=make();c,f,vn,vp,p=pack_three_temperature_inputs(model,old,1e-20,**BUDGET)
    assert p[7]==-13.;b=9+int(p[8]);face=next(iter(model.contacts))
    if damage=='short':p.pop()
    elif damage=='fractional':p[8]=.5
    elif damage=='nonfinite':p[b+2*face]=np.nan
    elif damage=='zero_contact':p[b+2*face]=0.
    elif damage=='noncontact':p[b+2*next(i for i in range(len(model.mesh.faces)) if i not in model.contacts)]=600.
    else:p=p[:7]+[-13.,len(p)-7]+p[7:]+p[b:]
    with pytest.raises((ValueError,RuntimeError)):_bindings.native_three_temperature_dispatch_raw(c,f,vn,vp,p,600)


def test_energy_coordinate_api_rejects_unsupported_independent_contacts():
    from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates
    model,old=make()
    with pytest.raises(ValueError,match='contact temperatures'):initialize_energy_coordinates(model,old)
