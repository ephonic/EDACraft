"""FD storage, independent spectral integrals, actual energy rows and refinement."""
from copy import deepcopy
import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import expit
from tcad.physics.multivalley_thermionic import ThermionicValley,multivalley_thermionic_interface_flux,Q,KB
from tcad.physics.fermi_spectral import fermi_reservoir,spectral_face
from tcad.postprocess.fermi_spectral_energy import reference_reservoir,reference_face,audit_fermi_spectral_energy
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.cut_cell_transport import CutCellState
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal

VALLEYS=(ThermionicValley('z',2,.916,.190,.190),ThermionicValley('xy',4,.190,.916,.190))
BUDGET=dict(charge_atol_C=2e-28,particle_atol=1e-9,energy_atol_J=1e-27)


@pytest.mark.parametrize('density',[1e17,1e24,2e25,1e26])
@pytest.mark.parametrize('temperature',[300.,450.])
def test_FD_storage_matches_independent_DOS_quadrature(density,temperature):
    actual=fermi_reservoir(density,temperature,.04*Q,VALLEYS)
    expected=reference_reservoir(density,temperature,.04*Q,VALLEYS)
    assert actual['density_m3']==pytest.approx(density,rel=2e-12)
    for key in ('chemical_potential_J','energy_density_J_m3'):
        assert actual[key]==pytest.approx(expected[key],rel=2e-9,abs=1e-32)
    if density==1e26:
        classical=density*(.04*Q+1.5*KB*temperature)
        assert abs(actual['energy_density_J_m3']/classical-1)>.1


@pytest.mark.parametrize('A',[None,0.,.5,2.])
@pytest.mark.parametrize('temperature',[(300.,300.),(300.,450.),(450.,300.)])
def test_spectral_moments_match_adaptive_integral_and_positive_entropy(A,temperature):
    one=fermi_reservoir(2e25,temperature[0],.02*Q,VALLEYS)
    two=fermi_reservoir(8e24,temperature[1],.06*Q,VALLEYS)
    actual=spectral_face(one,two,VALLEYS,potential_owner_V=0.,potential_neighbor_V=.002,
        potential_face_V=.001,charge_sign=-1,mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.02,
        area_m2=1e-14,distance_owner_m=2e-8,distance_neighbor_m=3e-8,emission_factor=A)
    expected=reference_face(one,two,VALLEYS,phi_o=0.,phi_n=.002,phi_f=.001,z=-1,
        mu_o=.01,mu_n=.02,area=1e-14,do=2e-8,dn=3e-8,A=A)
    for key in ('particle_flux_s','total_energy_flux_W','material_energy_flux_W','entropy_production_W_K'):
        assert actual[key]==pytest.approx(expected[key],rel=2e-8,abs=1e-24 if key.endswith('_s') else 1e-30),key
    assert actual['entropy_production_W_K']>=-1e-30
    assert 0<=actual['trace_occupation_min']<=actual['trace_occupation_max']<=1


def test_high_mobility_series_converges_to_ideal_FD_thermionic_interface():
    one=fermi_reservoir(2e25,300.,.02*Q,VALLEYS);two=fermi_reservoir(8e24,450.,.06*Q,VALLEYS)
    ideal=multivalley_thermionic_interface_flux(2e25,8e24,300.,450.,.02*Q,.06*Q,VALLEYS,1e-14)
    actual=spectral_face(one,two,VALLEYS,potential_owner_V=0.,potential_neighbor_V=0.,potential_face_V=0.,
        charge_sign=-1,mobility_owner_m2_Vs=1e10,mobility_neighbor_m2_Vs=1e10,
        area_m2=1e-14,distance_owner_m=2e-8,distance_neighbor_m=3e-8,emission_factor=2.)
    for key in ('particle_flux_s','material_energy_flux_W','entropy_production_W_K'):
        assert actual[key]==pytest.approx(ideal[key],rel=2e-8)


def test_MB_diffusion_limit_and_common_potential_gauge():
    one=fermi_reservoir(2e17,300.,.02*Q,VALLEYS);two=fermi_reservoir(8e16,300.,.02*Q,VALLEYS)
    kwargs=dict(potential_owner_V=0.,potential_neighbor_V=0.,potential_face_V=0.,charge_sign=-1,
        mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.01,area_m2=1e-14,
        distance_owner_m=2e-8,distance_neighbor_m=3e-8)
    a=spectral_face(one,two,VALLEYS,**kwargs)
    assert a['particle_flux_s']==pytest.approx(.01*KB*300/Q*1e-14/5e-8*(2e17-8e16),rel=2e-8)
    assert a['material_energy_flux_W']==pytest.approx((.02*Q+2.5*KB*300)*a['particle_flux_s'],rel=2e-8)
    kwargs.update(potential_owner_V=.3,potential_neighbor_V=.3,potential_face_V=.3)
    b=spectral_face(one,two,VALLEYS,**kwargs)
    for key in ('particle_flux_s','material_energy_flux_W','entropy_production_W_K'):
        assert b[key]==pytest.approx(a[key],rel=2e-11)


def fixture(*,count=2,contacts=False,voltage=0.,reverse=False,blocked=False,density_scale=1.):
    L=1e-7;mesh=region_cut_cells([np.linspace(0,L,count+1),np.array([0.,L]),np.array([0.,L])],{'box':[[]]})
    x=mesh.centroids_m[:,0];side=x<L/2
    interface=[f for f,v in enumerate(mesh.faces) if v.neighbor>=0 and side[v.owner]!=side[v.neighbor]]
    groups={name:[f for f,v in enumerate(mesh.faces) if v.neighbor<0 and abs(v.area_vector_m2[0])>0
        and (v.centroid_m[0]<L/2)==(name=='left')] for name in ('left','right')}
    bc={f:0. if name=='left' else voltage for name,faces in groups.items() for f in faces}
    T=np.where(side,320.,440.);T=T[::-1].copy() if reverse else T
    model=FermiSpectralElectrothermal(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Ec_J=np.where(side,.02,.06)*Q,
        Eh_J=np.where(side,.02,.06)*Q,valleys_n=VALLEYS,valleys_p=VALLEYS,
        heat_capacity_J_m3_K=1e3,thermal_conductivity_W_m_K=.001,
        thermionic_faces=interface,emission_factor_n=0. if blocked else 2.,emission_factor_p=0. if blocked else 2.,
        particle_contacts={f:CarrierReservoir(1e25*density_scale,1e25*density_scale,350. if name=='left' else 400.)
            for name,faces in groups.items() for f in faces} if contacts else {},
        heat_bath_K={f:350. if name=='left' else 400. for name,faces in groups.items() for f in faces} if contacts else {},
        terminal_groups=groups)
    density=1e25*density_scale*(1.2-.4*x/L)
    return model,CutCellState(density,density,np.full(count,.3),T)


@pytest.mark.parametrize('density_scale,contacts,voltage,reverse,count',
    [(scale,*case) for scale in (1.,10.) for case in [(False,0.,False,2),(False,0.,True,2),
        (True,0.,False,2),(True,.002,False,2),(True,-.002,False,2),(True,0.,False,4)]
        ])
def test_actual_degenerate_particle_temperature_steps_close_independent_audit(contacts,voltage,reverse,count,density_scale):
    model,old=fixture(contacts=contacts,voltage=voltage,reverse=reverse,count=count,density_scale=density_scale)
    saved=deepcopy(old)
    new,report=model.step(old,2e-13,**BUDGET)
    audit=audit_fermi_spectral_energy(model,old,new,report,**BUDGET)
    assert audit['valid'],audit
    assert max(abs(new.temperature_K-old.temperature_K))>1e-5
    assert new.time_s>old.time_s and report['temperature_feedback']
    for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
        np.testing.assert_array_equal(getattr(old,name),getattr(saved,name))


@pytest.mark.parametrize('voltage',[.002,-.002])
def test_dense_biased_accepted_state_must_retain_density_precision(voltage):
    model,old=fixture(contacts=True,voltage=voltage,density_scale=10.)
    saved=deepcopy(old)
    new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']
    rounded=CutCellState(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K,new.time_s)
    assert not audit_fermi_spectral_energy(model,old,rounded,report,**BUDGET)['valid']
    rounded_report=deepcopy(report)
    rounded_report['density_precision']=dict(dtype=str(rounded.n_m3.dtype),mantissa_bits=53)
    # Even with honest float64 metadata, physical reconstruction must detect
    # the charge/flux error introduced by discarding the accepted density bits.
    assert not audit_fermi_spectral_energy(model,old,rounded,rounded_report,**BUDGET)['valid']
    for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
        np.testing.assert_array_equal(getattr(old,name),getattr(saved,name))


@pytest.mark.parametrize('damage',['density','temperature','particle','energy','compensated_energy','storage',
    'absolute_storage','work','entropy','valley','terminal','flag'])
def test_independent_audit_rejects_corrupted_states_and_reports(damage):
    model,old=fixture();new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    f=model.thermionic_faces[0]
    if damage=='density':new=CutCellState(new.n_m3*1.0001,new.p_m3,new.trap_fraction,new.temperature_K,new.time_s)
    elif damage=='temperature':new=CutCellState(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K+.01,new.time_s)
    elif damage=='particle':bad['integrated_electron_particle_flux_s'][f]*=1.01
    elif damage=='energy':bad['integrated_carrier_energy_flux_W'][f]*=1.01
    elif damage=='compensated_energy':
        bad['face_moments']['electrons'][f]['material_energy_flux_W']+=1e-8
        bad['face_moments']['holes'][f]['material_energy_flux_W']-=1e-8
    elif damage=='storage':bad['energy_increments_J']['carrier_J']+=1e-24
    elif damage=='absolute_storage':bad['energy_before_J']['carrier_J']+=1e-24
    elif damage=='work':bad['cell_electrical_work_J'][0]+=1e-24
    elif damage=='entropy':bad['face_moments']['electrons'][f]['entropy_production_W_K']=-1e-9
    elif damage=='valley':
        bad['face_moments']['electrons'][f]['valley_moments'][0]['particle_flux_s']+=1e10
        bad['face_moments']['electrons'][f]['valley_moments'][1]['particle_flux_s']-=1e10
    elif damage=='terminal':bad['terminals']['right']['current_A']+=1e-6
    else:bad['state_advanced']=False
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


def test_blocked_particles_still_allow_lattice_heat():
    model,old=fixture(blocked=True);new,report=model.step(old,2e-13,**BUDGET)
    np.testing.assert_allclose(new.n_m3,old.n_m3,rtol=1e-13)
    assert new.temperature_K[0]>old.temperature_K[0]
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def test_failed_budget_does_not_change_input_state():
    model,old=fixture();saved=deepcopy(old)
    with pytest.raises(ValueError):model.step(old,2e-13,charge_atol_C=1e-45,particle_atol=1e-35,energy_atol_J=1e-45)
    np.testing.assert_array_equal(old.temperature_K,saved.temperature_K)
    np.testing.assert_array_equal(old.n_m3,saved.n_m3)


def test_bulk_cosine_manufactured_solution_grid_refinement():
    errors=[];L=1e-7;D=.01*KB*300/Q
    for count in (4,8,16):
        x=(np.arange(count)+.5)*L/count;n=1e17*(1+.1*np.cos(np.pi*x/L));dx=L/count
        r=[fermi_reservoir(a,300.,0.,VALLEYS) for a in n];flux=np.zeros(count+1)
        for j in range(count-1):
            flux[j+1]=spectral_face(r[j],r[j+1],VALLEYS,potential_owner_V=0.,potential_neighbor_V=0.,potential_face_V=0.,
                charge_sign=-1,mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.01,area_m2=1.,
                distance_owner_m=dx/2,distance_neighbor_m=dx/2)['particle_flux_s']
        rate=-np.diff(flux)/dx;exact=-D*.1e17*(np.pi/L)**2*np.cos(np.pi*x/L)
        errors.append(float(np.linalg.norm(rate-exact)/np.linalg.norm(exact)))
    assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3


def test_actual_FD_time_refinement():
    endpoints=[]
    for count in (1,2,4,8):
        model,state=fixture()
        for _ in range(count):state,_=model.step(state,4e-13/count,**BUDGET)
        endpoints.append(np.r_[state.n_m3/1e25,state.temperature_K/350.])
    errors=[float(np.linalg.norm(v-endpoints[-1])) for v in endpoints[:-1]]
    assert errors[1]<errors[0] and errors[2]<errors[1]


def test_strongly_degenerate_bulk_manufactured_grid_convergence():
    from tcad.physics.fermi_spectral import valley_dos
    errors=[];L=1e-7;T=300.;D=.01*KB*T/Q;dos=sum(valley_dos(T,VALLEYS))
    for count in (4,8,16):
        dx=L/count;x=(np.arange(count)+.5)*dx
        eta=2.+.2*np.cos(np.pi*x/L)
        Fhalf=np.array([2/math.sqrt(math.pi)*quad(lambda t:2*t*t*expit(a-t*t),0.,10.,epsabs=1e-12)[0] for a in eta])
        Fminus=np.array([2/math.sqrt(math.pi)*quad(lambda t:2*expit(a-t*t),0.,10.,epsabs=1e-12)[0] for a in eta])
        # F_-1/2 normalization is 1/sqrt(pi); x=t^2 supplies factor 2.
        Fminus/=2
        reservoirs=[fermi_reservoir(n,T,0.,VALLEYS) for n in dos*Fhalf]
        flux=np.zeros(count+1)
        for j in range(count-1):
            flux[j+1]=spectral_face(reservoirs[j],reservoirs[j+1],VALLEYS,potential_owner_V=0.,potential_neighbor_V=0.,
                potential_face_V=0.,charge_sign=-1,mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.01,
                area_m2=1.,distance_owner_m=dx/2,distance_neighbor_m=dx/2)['particle_flux_s']
        eta_x=-.2*np.pi/L*np.sin(np.pi*x/L);eta_xx=-.2*(np.pi/L)**2*np.cos(np.pi*x/L)
        expected=D*dos*(Fhalf*eta_xx+Fminus*eta_x**2)
        errors.append(float(np.linalg.norm(-np.diff(flux)/dx-expected)/np.linalg.norm(expected)))
    assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3


def test_unsupported_trap_and_quantum_configuration_cannot_be_silently_used():
    model,old=fixture()
    model.Nt[:]=1e20
    with pytest.raises(ValueError,match='traps or quantum'):model.step(old,2e-13,**BUDGET)


def test_generic_public_transport_and_storage_do_not_fall_back_to_MB():
    model,old=fixture(density_scale=10.)
    new,report=model.step(old,2e-13,**BUDGET)
    _,a=model.energies(old,charge_atol_C=BUDGET['charge_atol_C'])
    _,b=model.energies(new,charge_atol_C=BUDGET['charge_atol_C'])
    fn,fp,*_=model.transport(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K,b)
    np.testing.assert_array_equal(fn,report['integrated_electron_particle_flux_s'])
    np.testing.assert_array_equal(fp,report['integrated_hole_particle_flux_s'])
    for key,value in model.energy_increments(old,new,a,b).items():
        assert value==pytest.approx(report['energy_increments_J'][key],rel=1e-12,abs=1e-30)
    with pytest.raises(ValueError,match='combined local energy'):model.heat_terms()


def test_unequal_bulk_half_distances_and_contact_use_physical_resistances():
    one=fermi_reservoir(2e17,300.,0.,VALLEYS);two=fermi_reservoir(8e16,300.,0.,VALLEYS)
    for dn in (0.,3e-8):
        moment=spectral_face(one,two,VALLEYS,potential_owner_V=0.,potential_neighbor_V=0.,
            potential_face_V=0.,charge_sign=-1,mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.02,
            area_m2=1e-14,distance_owner_m=2e-8,distance_neighbor_m=dn)
        expected=1e-14/(2e-8/.01+dn/.02)*KB*300/Q*(2e17-8e16)
        assert moment['particle_flux_s']==pytest.approx(expected,rel=2e-8)


def test_emission_arrays_follow_supplied_face_order():
    old,_=fixture(count=4)
    faces=list(reversed(old.internal.tolist()))
    model=FermiSpectralElectrothermal(old.mesh,permittivity_F_m=1e-10,dirichlet_V=old.bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,valleys_n=VALLEYS,valleys_p=VALLEYS,
        heat_capacity_J_m3_K=1e3,thermal_conductivity_W_m_K=.001,thermionic_faces=faces,
        emission_factor_n=[.2,.4,.8],emission_factor_p=[.3,.6,.9])
    assert model.emission['electrons']==dict(zip(faces,[.2,.4,.8]))
    assert model.emission['holes']==dict(zip(faces,[.3,.6,.9]))
