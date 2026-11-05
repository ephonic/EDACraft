"""Open contacts, temperature feedback, actual energy/charge and bad-data gates."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.electrothermal_cut_cell import ElectrothermalCutCellTransport,CarrierReservoir,logarithmic_mean_temperature
from tcad.solver.cut_cell_transport import CutCellState,KB,Q
from tcad.postprocess.cut_cell_energy import audit_cut_cell_energy


def fixture(*,open_contacts=True,quantum=True,traps=True,nonconvex=False,count=2,temperature=350.,equal_kappa=False):
    L=1e-7;axes=[np.linspace(0,L,count+1),np.linspace(0,L,3),np.array([0.,L])]
    regions={'L':[[[1,0,0,.65*L]],[[0,1,0,.65*L]]]} if nonconvex else {'box':[[]]}
    mesh=region_cut_cells(axes,regions);nc=len(mesh.volumes_m3)
    bc={f:.01*face.centroid_m[0]/L for f,face in enumerate(mesh.faces) if face.neighbor<0}
    contacts={f:CarrierReservoir((1.3 if face.centroid_m[0]<L/2 else .7)*1e21,1e21,300.)
        for f,face in enumerate(mesh.faces) if face.neighbor<0 and abs(face.area_vector_m2[0])>0} if open_contacts else {}
    solver=ElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,temperature_K=300.,Nc_m3=1e21,Nv_m3=1e21,
        Ec_J=.04*Q,Eh_J=.04*Q,trap_energy_J=.005*Q,
        trap_density_m3=2e20 if traps else 0.,capture_n_m3_s=1e-12 if traps else 0.,capture_p_m3_s=2e-12 if traps else 0.,
        quantum_n_J_m2=1e-37 if quantum else 0.,quantum_p_J_m2=(1e-37 if equal_kappa else 5e-38) if quantum else 0.,
        heat_capacity_J_m3_K=.1,thermal_conductivity_W_m_K=.001,
        heat_bath_K={f:300. for f,face in enumerate(mesh.faces) if face.neighbor<0},particle_contacts=contacts)
    x=mesh.centroids_m[:,0]/L
    state=CutCellState(1e21*(.8+.4*x),1e21*(1.2-.4*x),np.full(nc,.3),np.full(nc,temperature))
    return solver,state


@pytest.mark.parametrize('a,b',[(300.,300.),(300.,300.+1e-11),(200.,600.),(600.,200.)])
def test_log_mean_temperature_stable_symmetric_and_bounded(a,b):
    value=logarithmic_mean_temperature(a,b)
    np.testing.assert_allclose(value,logarithmic_mean_temperature(b,a),rtol=1e-15)
    assert min(a,b)<=value<=max(a,b)
    if abs(a-b)>1e-6:np.testing.assert_allclose(value,(b-a)/np.log(b/a),rtol=1e-14)


@pytest.mark.parametrize('open_contacts',[False,True])
@pytest.mark.parametrize('quantum,traps,nonconvex',[(False,False,False),(True,True,False),(True,True,True)])
def test_actual_coupled_temperature_contact_and_energy_closure(open_contacts,quantum,traps,nonconvex):
    solver,state=fixture(open_contacts=open_contacts,quantum=quantum,traps=traps,nonconvex=nonconvex)
    for _ in range(2):
        old=state
        state,report=solver.step(old,2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        audit=audit_cut_cell_energy(solver,old,state,report,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        assert report['valid'] and audit['valid'] and report['temperature_feedback']
        assert np.max(abs(state.temperature_K-old.temperature_K))>.01
        assert abs(report['energy_residual_J'])<1e-28
        assert abs(report['charge_balance_residual_C'])<2e-29
        assert abs(2e-12*sum(report['terminal_currents_A'].values()))<2e-29
        assert not report['complete_device_energy']
        if open_contacts:assert abs(report['outward_carrier_energy_J'])>1e-25
        else:assert report['outward_carrier_energy_J']==0.
    assert not state.n_m3.flags.writeable


def test_single_cell_injection_matches_exact_BE_and_carried_energy():
    L=1e-7;mesh=region_cut_cells([np.array([0.,L])]*3,{'box':[[]]})
    faces=[f for f,face in enumerate(mesh.faces) if abs(face.area_vector_m2[0])>0]
    solver=ElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,
        dirichlet_V={f:0. for f in range(len(mesh.faces))},mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,
        particle_contacts={faces[0]:CarrierReservoir(2e21,2e21),faces[1]:CarrierReservoir(1.5e21,1.5e21)},
        heat_capacity_J_m3_K=.1)
    old=CutCellState(np.array([1e21]),np.array([1e21]),np.array([.5]),np.array([300.]))
    dt=2e-12;new,report=solver.step(old,dt,charge_atol_C=1e-29,particle_atol=1e-10,energy_atol_J=1e-28)
    coefficient=dt*.01*KB*300/Q*solver.contact_metric
    expected=(L**3*1e21+np.dot(coefficient,solver.res_n))/(L**3+coefficient.sum())
    np.testing.assert_allclose(new.n_m3,expected,rtol=1e-12);np.testing.assert_allclose(new.p_m3,expected,rtol=1e-12)
    np.testing.assert_allclose(new.temperature_K,300.,atol=1e-10)
    independent_energy=3*KB*300*L**3*(expected-1e21)
    np.testing.assert_allclose(report['outward_carrier_energy_J'],-independent_energy,rtol=1e-12)
    assert abs(report['source_work_J'])<1e-30


def test_temperature_feedback_changes_flux_emission_and_keeps_gauge_invariance():
    solver,state=fixture()
    poisson=solver._poisson(state.n_m3,state.p_m3,state.trap_fraction,1e-29)
    cold=solver.transport(state.n_m3,state.p_m3,state.trap_fraction,np.full(solver.nc,300.),poisson)
    hot=solver.transport(state.n_m3,state.p_m3,state.trap_fraction,np.full(solver.nc,600.),poisson)
    assert np.max(abs(hot[0]-cold[0]))>.01*np.max(abs(cold[0]))
    assert np.max(abs(hot[2]-cold[2]))>1e5
    # A voltage reference shift may not become a temperature-gradient force.
    temperature=np.linspace(300.,600.,solver.nc);original=solver.transport(state.n_m3,state.p_m3,state.trap_fraction,temperature,poisson)
    shifted=deepcopy(poisson);shifted['cell_potential_V']+=.25;shifted['face_potential_V']+=.25
    solver.bc={f:v+.25 for f,v in solver.bc.items()}
    shifted_flux=solver.transport(state.n_m3,state.p_m3,state.trap_fraction,temperature,shifted)
    for key in (0,1):np.testing.assert_allclose(original[key],shifted_flux[key],rtol=2e-13,atol=1e-4)


def test_quantum_reservoir_storage_has_exact_chain_rule_even_equal_kappas():
    solver,old=fixture(equal_kappa=True);new=CutCellState(old.n_m3*np.linspace(.8,1.3,solver.nc),
        old.p_m3*np.linspace(1.2,.7,solver.nc),old.trap_fraction,old.temperature_K,1e-12)
    ea,pa=solver.energies(old,charge_atol_C=1e-29);eb,pb=solver.energies(new,charge_atol_C=1e-29)
    qn,qp=solver.quantum_potentials(new.n_m3,new.p_m3,old.n_m3,old.p_m3)
    independent=np.sum(solver.vol*(qn*(new.n_m3-old.n_m3)+qp*(new.p_m3-old.p_m3)))
    np.testing.assert_allclose(independent,eb['quantum_J']-ea['quantum_J'],rtol=1e-12)
    assert ea['quantum_J']>0


@pytest.mark.parametrize('damage',['carrier_energy','conduction_work','energy_flux','particle_flux','heat_flux','temperature','terminal'])
def test_independent_audit_rejects_broken_open_contact_or_thermal_accounting(damage):
    solver,old=fixture();new,report=solver.step(old,2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
    bad=deepcopy(report)
    if damage=='carrier_energy':bad['outward_carrier_energy_J']=0.
    elif damage=='conduction_work':bad['conduction_work_J']=0.
    elif damage=='energy_flux':bad['integrated_carrier_energy_flux_W'][solver.contact_faces[0]]*=1.1
    elif damage=='particle_flux':bad['integrated_electron_particle_flux_s'][solver.contact_faces[0]]*=1.1
    elif damage=='heat_flux':bad['integrated_heat_flux_W']*=1.1
    elif damage=='temperature':new=CutCellState(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K+.1,new.time_s)
    else:bad['terminal_currents_A'][solver.contact_faces[0]]+=1e-6
    assert not audit_cut_cell_energy(solver,old,new,bad,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)['valid']


def test_invalid_contact_and_failed_step_leave_owned_input_unchanged():
    with pytest.raises(ValueError):CarrierReservoir(-1,1)
    with pytest.raises(ValueError):CarrierReservoir(1,1,np.nan)
    solver,state=fixture();copy=state.n_m3.copy()
    with pytest.raises(ValueError,match='budget'):
        solver.step(state,2e-12,charge_atol_C=1e-40,particle_atol=1e-30,energy_atol_J=1e-40)
    np.testing.assert_array_equal(state.n_m3,copy)
