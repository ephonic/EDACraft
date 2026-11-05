"""Series trace solutions, monolithic temperature evolution and false-data gates."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.cut_cell_transport import CutCellState,Q,KB
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.thermionic_electrothermal import ThermionicElectrothermalCutCellTransport
from tcad.postprocess.thermionic_electrothermal import audit_thermionic_electrothermal

BUDGET=dict(charge_atol_C=2e-28,particle_atol=1e-9,energy_atol_J=1e-27)
MOMENT=dict(particle_flux_atol_s=1e4,energy_flux_atol_W=1e-17,entropy_atol_W_K=1e-19)


def fixture(*,count=2,contacts=False,traps=False,blocked=False,neutral=False,quantum=False):
    L=1e-7;mesh=region_cut_cells([np.linspace(0,L,count+1),np.array([0.,L]),np.array([0.,L])],{'box':[[]]})
    nc=len(mesh.volumes_m3);side=mesh.centroids_m[:,0]<L/2
    faces=[f for f,v in enumerate(mesh.faces) if v.neighbor>=0 and side[v.owner]!=side[v.neighbor]]
    groups={name:[f for f,v in enumerate(mesh.faces) if v.neighbor<0 and abs(v.area_vector_m2[0])>0
        and (v.centroid_m[0]<L/2)==(name=='left')] for name in ('left','right')}
    bc={f:(0. if name=='left' or neutral else .002) for name,ids in groups.items() for f in ids}
    density=1e21*(1.2-.4*mesh.centroids_m[:,0]/L)
    holes=density.copy() if neutral else 1e21*(.8+.4*mesh.centroids_m[:,0]/L)
    Nt=2e20 if traps else 0.
    model=ThermionicElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01 if neutral else .005,Nc_m3=1e25,Nv_m3=1e25,
        Ec_J=np.where(side,.02,.06)*Q,Eh_J=np.where(side,.02,.06)*Q if neutral else np.where(side,.03,.01)*Q,
        fixed_charge_C_m3=0. if neutral else Q*(density-holes+Nt*.3),
        trap_density_m3=Nt,capture_n_m3_s=1e-12 if traps else 0.,capture_p_m3_s=1e-12 if traps else 0.,
        heat_capacity_J_m3_K=.1,thermal_conductivity_W_m_K=.001,
        quantum_n_J_m2=5e-38 if quantum else 0.,quantum_p_J_m2=5e-38 if quantum else 0.,
        particle_contacts={f:CarrierReservoir(1e21,1e21,350.) for f in bc} if contacts else {},
        heat_bath_K={f:350. for f in bc} if contacts else {},
        thermionic_faces=faces,emission_factor_n=0. if blocked else 2.,emission_factor_p=0. if blocked else 2.,terminal_groups=groups)
    state=CutCellState(density,holes,np.full(nc,.3),np.where(side,320.,440.))
    return model,state


@pytest.mark.parametrize('temperature',[(300.,300.),(300.,450.),(450.,300.)])
@pytest.mark.parametrize('voltage',[0.,.02,-.02])
def test_eliminated_traces_match_independent_three_equation_linear_system(temperature,voltage):
    model,state=fixture();T=np.array(temperature);p=model._poisson(state.n_m3,state.p_m3,state.trap_fraction,1e-27)
    p['cell_potential_V']=np.array([0.,voltage]);p['face_potential_V'][model.tf]=voltage/2
    rows=model.interface_moments(state.n_m3,state.p_m3,T,p);i,j=model.ti,model.tj
    for label,density,band,mu0,exponent,z,A in [('electrons',state.n_m3,model.Ec,model.mn,model.mn_exponent,-1,model.An),
            ('holes',state.p_m3,model.Eh,model.mp,model.mp_exponent,1,model.Ap)]:
        mu=mu0*(model.T/T)**exponent;mass=model.masses[label][0];high=max(band)
        def bern(d):return 1. if d==0 else d/np.expm1(d)
        d1=z*Q*voltage/2/(KB*T[0]);d2=z*Q*voltage/2/(KB*T[1])
        a=mu[0]*KB*T[0]/Q*model.half_owner_metric[0];b=mu[1]*KB*T[1]/Q*model.half_neighbor_metric[0]
        go=A[0]*model.ta[0]*np.sqrt(KB*T[0]/(2*np.pi*mass))*np.exp(-(high-band[0])/(KB*T[0]))
        gn=A[0]*model.ta[0]*np.sqrt(KB*T[1]/(2*np.pi*mass))*np.exp(-(high-band[1])/(KB*T[1]))
        # Unknowns are the two traces and the number flux; row scaling keeps
        # the independent linear solve well conditioned despite SI units.
        matrix=np.array([[1.,0.,1/(a*bern(-d1))],[0.,1.,-1/(b*bern(d2))],[-go,gn,1.]])
        rhs=np.array([bern(d1)/bern(-d1)*density[0],bern(-d2)/bern(d2)*density[1],0.])
        matrix[2]/=max(go,gn);expected=np.linalg.solve(matrix,rhs)
        row=rows[label]
        np.testing.assert_allclose(row['owner_density_m3'],expected[0],rtol=2e-13)
        np.testing.assert_allclose(row['neighbor_density_m3'],expected[1],rtol=2e-13)
        np.testing.assert_allclose(row['moments']['particle_flux_s'],expected[2],rtol=1e-11,atol=.1)


@pytest.mark.parametrize('contacts,traps,count',[(False,False,2),(True,False,2),(False,True,2),(True,True,2),(True,True,4)])
def test_actual_monolithic_steps_close_local_heat_particles_and_terminal_energy(contacts,traps,count):
    model,old=fixture(contacts=contacts,traps=traps,count=count)
    initial=deepcopy(old)
    for _ in range(2):
        new,report=model.step(old,2e-12,**BUDGET)
        audit=audit_thermionic_electrothermal(model,old,new,report,**BUDGET,**MOMENT)
        assert audit['valid'] and report['state_advanced']
        assert np.max(abs(new.temperature_K-old.temperature_K))>.001
        assert new.time_s>old.time_s and not report['complete_device_energy']
        assert abs(report['energy_residual_J'])<BUDGET['energy_atol_J']
        old=new
    assert not old.temperature_K.flags.writeable
    np.testing.assert_array_equal(initial.temperature_K,np.array([320.,440.]) if count==2 else [320.,320.,440.,440.])


def test_zero_emission_is_blocked_but_thermal_conduction_still_advances():
    model,old=fixture(blocked=True);new,report=model.step(old,2e-12,**BUDGET)
    np.testing.assert_allclose(new.n_m3,old.n_m3,rtol=2e-14)
    np.testing.assert_allclose(new.p_m3,old.p_m3,rtol=2e-14)
    for r in report['thermionic_interfaces'].values():
        assert np.all(r['moments']['particle_flux_s']==0) and np.all(r['moments']['material_energy_flux_W']==0)
    assert new.temperature_K[0]>old.temperature_K[0] and new.temperature_K[1]<old.temperature_K[1]
    assert audit_thermionic_electrothermal(model,old,new,report,**BUDGET,**MOMENT)['valid']


def test_quantum_thermionic_face_reconstruction_closes_energy():
    model,old=fixture(quantum=True,contacts=True,traps=True)
    new,report=model.step(old,2e-12,**BUDGET)
    audit=audit_thermionic_electrothermal(model,old,new,report,**BUDGET,**MOMENT)
    assert audit['valid']
    assert model.kn>0 and model.kp>0
    for row in report['thermionic_interfaces'].values():
        assert np.any(np.abs(row['quantum_face_J'])>0)
    assert abs(report['energy_residual_J'])<BUDGET['energy_atol_J']


def test_common_potential_reference_does_not_change_nonisothermal_traces_or_material_energy():
    model,state=fixture();p=model._poisson(state.n_m3,state.p_m3,state.trap_fraction,1e-27)
    first=model.interface_moments(state.n_m3,state.p_m3,state.temperature_K,p)
    p['cell_potential_V']+=.35;p['face_potential_V']+=.35
    second=model.interface_moments(state.n_m3,state.p_m3,state.temperature_K,p)
    for label in first:
        for k in ('owner_density_m3','neighbor_density_m3'):np.testing.assert_allclose(first[label][k],second[label][k],rtol=2e-13)
        for k in ('particle_flux_s','material_energy_flux_W','entropy_production_W_K'):
            np.testing.assert_allclose(first[label]['moments'][k],second[label]['moments'][k],rtol=1e-11,atol=1e-25)


@pytest.mark.parametrize('damage',['trace','moment','compensated_moment','energy_flux','temperature','cell_heat','terminal','face_coverage','state_flag'])
def test_audit_rejects_false_interface_and_device_data(damage):
    model,old=fixture(contacts=True,traps=True);new,report=model.step(old,2e-12,**BUDGET);bad=deepcopy(report)
    if damage=='trace':bad['thermionic_interfaces']['electrons']['owner_density_m3']*=1.01
    elif damage=='moment':bad['thermionic_interfaces']['electrons']['moments']['kinetic_owner_flux_W']*=1.01
    elif damage=='compensated_moment':
        bad['thermionic_interfaces']['electrons']['moments']['material_energy_flux_W']+=1e-8
        bad['thermionic_interfaces']['holes']['moments']['material_energy_flux_W']-=1e-8
    elif damage=='energy_flux':bad['integrated_carrier_energy_flux_W'][model.tf]+=1e-8
    elif damage=='temperature':new=CutCellState(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K+.1,new.time_s)
    elif damage=='cell_heat':bad['energy_increments_J']['thermal_J']+=1e-23
    elif damage=='terminal':bad['terminals']['right']['current_A']+=1e-6
    elif damage=='face_coverage':bad['thermionic_faces']=[]
    else:bad['state_advanced']=False
    assert not audit_thermionic_electrothermal(model,old,new,bad,**BUDGET,**MOMENT)['valid']


@pytest.mark.parametrize('bad',['boundary','duplicate','mass','mobility','missing_band_jump','empty'])
def test_unsupported_physics_and_invalid_interface_inputs_rejected(bad):
    model,_=fixture();kwargs=dict(permittivity_F_m=1e-10,dirichlet_V=model.bc,mobility_n_m2_Vs=.01,
        mobility_p_m2_Vs=.01,thermionic_faces=model.tf.tolist())
    if bad=='boundary':kwargs['thermionic_faces']=[next(iter(model.bc))]
    elif bad=='duplicate':kwargs['thermionic_faces']*=2
    elif bad=='mass':kwargs['Nc_m3']=[1e25,2e25]
    elif bad=='mobility':kwargs['mobility_n_m2_Vs']=0.
    elif bad=='missing_band_jump':
        m,_=fixture(count=4);model=m;kwargs['dirichlet_V']=m.bc;kwargs['Ec_J']=[0.,.1*Q,.2*Q,.3*Q];kwargs['thermionic_faces']=m.tf.tolist()
    else:kwargs['thermionic_faces']=[]
    with pytest.raises(ValueError):ThermionicElectrothermalCutCellTransport(model.mesh,**kwargs)


def test_failed_step_does_not_mutate_the_owned_input():
    model,old=fixture();saved=deepcopy(old)
    with pytest.raises(ValueError):model.step(old,2e-12,charge_atol_C=1e-42,particle_atol=1e-32,energy_atol_J=1e-42)
    for key in ('n_m3','p_m3','trap_fraction','temperature_K'):np.testing.assert_array_equal(getattr(old,key),getattr(saved,key))
