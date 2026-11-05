"""Native reconstruction, independently rebuilt branches and atomic ownership."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import _bindings
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.solver.electrothermal_cut_cell import CarrierReservoir

BUDGET=dict(charge_atol_C=2e-28,particle_atol=1e-9,energy_atol_J=1e-27)


def manufactured():
    from tcad.mesh.polyhedral_regions import region_cut_cells
    from tcad.physics.multivalley_thermionic import ThermionicValley
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    mesh=region_cut_cells([np.linspace(0,1e-7,6),np.array([0.,1e-7]),np.array([0.,1e-6])],{'box':[[]]})
    n=np.array([1,2,2.01,6,10],np.longdouble)*np.longdouble('1e19')
    contacts={f:CarrierReservoir(float(n[face.owner]),float(n[face.owner]),600.) for f,face in enumerate(mesh.faces) if face.neighbor<0 and face.area_vector_m2[0]!=0}
    bc={f:0. for f in contacts}
    model=ThreeTemperatureElectrothermal(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,Ec_J=.5*1.602176634e-19,Eh_J=.5*1.602176634e-19,
        valleys_n=(ThermionicValley('e',1,.3,.3,.3),),valleys_p=(ThermionicValley('h',1,.4,.4,.4),),
        particle_contacts=contacts,heat_bath_K={f:600. for f in bc},heat_capacity_J_m3_K=1.,thermal_conductivity_W_m_K=1e-4,
        relaxation_time_n_s=1e-13,relaxation_time_p_s=4e-13,bulk_potential_path='linear_series',
        transport_reconstruction='quadratic_entropy_limited_1d')
    t=np.full(5,600.);state=ThreeTemperatureState(n,n,np.full(5,.3),t,0.,t,t)
    return model,state


def test_native_active_limiter_has_two_audited_spectral_branches():
    model,old=manufactured();new,report=model.step(old,1e-20,**BUDGET)
    assert report['independent_audit']['valid'] and not report['fully_discrete_entropy_closed']
    assert report['transport_reconstruction']=='quadratic_entropy_limited_1d'
    active=[]
    for rows in report['face_moments'].values():
        for row in rows.values():
            assert row['trace_closure']=='convex_mixture_of_two_spectral_faces'
            assert row['single_spectral_reservoir_pair'] is False
            assert row['entropy_production_W_K']>=0
            if row['high_order_fraction']<1:active.append(row)
    assert len(active)>=2
    assert any(r['reconstructed_face']['entropy_production_W_K']>0 for r in active)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']


def test_new_device_owned_step_and_failed_candidate_are_atomic():
    model,old=manufactured();device=DeviceThreeTemperature(model,old)
    before=device.native_state()
    with pytest.raises((ValueError,RuntimeError)):
        device.advance(1e-12,max_nfev=1,**BUDGET)
    assert device.state is not None and device.state.time_s==0
    assert device.native_state()==before
    new,report=device.advance(1e-20,**BUDGET)
    assert report['independent_audit']['valid'] and new.time_s==1e-20
    assert device.native_state()['time_s']==new.time_s
    for s,k in [('n','n_m3'),('p','p_m3')]:np.testing.assert_array_equal(np.array(device.native_state()[s],np.longdouble),getattr(new,k))


def test_native_iteration_has_no_python_physics_or_residual_callback(monkeypatch):
    model,old=manufactured()
    def denied(*a,**k):raise AssertionError('native physics reentered Python')
    for name in ('_poisson','energies','carrier_reservoirs','split_face_transport','conduction'):
        monkeypatch.setattr(model,name,denied)
    for name in ('native_fermi_newton_raw','native_fermi_reservoir_raw','native_spectral_face_raw','native_hybrid_poisson_raw','native_three_temperature_local_raw'):
        monkeypatch.setattr(_bindings,name,denied)
    new,report=model.step(old,1e-20,**BUDGET)
    assert report['independent_audit']['valid'] and new.time_s>0


@pytest.mark.parametrize('damage',['weight','low_branch','high_branch','entropy','descriptor','valley','nonfinite_valley'])
def test_independent_auditor_rejects_mixture_damage(damage):
    model,old=manufactured();new,report=model.step(old,1e-20,**BUDGET);report=deepcopy(report)
    row=next(iter(report['face_moments']['electrons'].values()))
    if damage=='weight':row['high_order_fraction']=.123
    elif damage=='low_branch':del row['low_order_face']
    elif damage=='high_branch':row['reconstructed_face']['material_energy_flux_W']+=1e-8
    elif damage=='entropy':row['entropy_production_W_K']=-1.
    elif damage=='descriptor':row['trace_closure']='energy_resolved_nonthermal_occupations'
    elif damage=='valley':row['low_order_face']['valley_moments'][0]['particle_flux_s']+=1e12
    else:row['low_order_face']['valley_moments'][0]['particle_flux_s']=np.nan
    try:result=audit_three_temperature_energy(model,old,new,report,**BUDGET)
    except ValueError:return
    assert not result['valid']


@pytest.mark.parametrize('damage',['mode','source','bands','orchestration','count','side_contact'])
def test_scoped_option_rejects_unsupported_configuration(damage):
    model,old=manufactured()
    if damage=='mode':model.transport_reconstruction='unknown'
    elif damage=='source':model.intercarrier_conductance_W_m3_K=np.ones(model.nc)
    elif damage=='bands':model.band_temperature_slopes=(np.ones(model.nc)*1e-24,model.band_temperature_slopes[1])
    elif damage=='orchestration':model.residual_orchestration='python'
    elif damage=='count':model.nc=2
    else:
        cells,faces,vn,vp,args=pack_three_temperature_inputs(model,old,1e-20,**BUDGET)
        lateral=next(i for i,f in enumerate(model.mesh.faces) if f.area_vector_m2[0]==0)
        faces[22*lateral+13]='1';faces[22*lateral+14]='600'
        with pytest.raises((ValueError,RuntimeError)):_bindings.native_three_temperature_dispatch_raw(cells,faces,vn,vp,args,600)
        return
    with pytest.raises(ValueError):pack_three_temperature_inputs(model,old,1e-20,**BUDGET)


@pytest.mark.parametrize('damage',['width','fractional_width','nested_band','nonfinite'])
def test_raw_reconstruction_wrapper_cannot_ignore_malformed_option(damage):
    model,old=manufactured();cells,faces,vn,vp,args=pack_three_temperature_inputs(model,old,1e-20,**BUDGET)
    assert args[7]==-12
    if damage=='width':args[8]+=1
    elif damage=='fractional_width':args[8]=.5
    elif damage=='nested_band':args=args[:7]+[-12.,3+2*model.nc,-10.,0.,300.]+[0.]*(2*model.nc)
    else:args[8]=np.nan
    with pytest.raises((ValueError,RuntimeError)):_bindings.native_three_temperature_dispatch_raw(cells,faces,vn,vp,args,600)
