"""Skew linear fields, equilibrium, variational energy and coupled trajectories."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.hybrid_mimetic import HybridMimeticOperator
from tcad.solver.mimetic_electrothermal import MimeticElectrothermalCutCellTransport
from tcad.solver.cut_cell_transport import CutCellState,Q,KB
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.postprocess.cut_cell_energy import audit_cut_cell_energy


def skew_mesh(count=3):
    L=1e-7
    return region_cut_cells([np.linspace(0,L,count+1),np.linspace(0,L,count+1),np.array([0.,L])],
        {'cut':[[[1.,.37,0.,.83*L]]]})


def boundary(mesh,function):
    return {f:float(function(face.centroid_m)) for f,face in enumerate(mesh.faces) if face.neighbor<0}


def model_from(base):
    return MimeticElectrothermalCutCellTransport(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,temperature_K=base.T,Nc_m3=base.Nc,Nv_m3=base.Nv,
        Ec_J=base.Ec,Eh_J=base.Eh,trap_density_m3=base.Nt,trap_energy_J=base.Et,
        capture_n_m3_s=base.cn,capture_p_m3_s=base.cp,fixed_charge_C_m3=base.rhofix,
        quantum_n_J_m2=base.kn,quantum_p_J_m2=base.kp,heat_capacity_J_m3_K=base.capacity,
        thermal_conductivity_W_m_K=base.conductivity,heat_bath_K=base.bath,particle_contacts=base.contacts)


@pytest.mark.parametrize('count',[2,3,5])
def test_skew_linear_diffusion_flux_and_energy_are_exact(count):
    mesh=skew_mesh(count);operator=HybridMimeticOperator(mesh);gradient=np.array([2e6,-3e6,1e6])
    function=lambda x:4.+gradient@x
    result=operator.solve(np.zeros(operator.nc),2.,dirichlet=boundary(mesh,function))
    np.testing.assert_allclose(result['cell_values'],4.+mesh.centroids_m@gradient,atol=4e-13)
    exact=np.array([-2*gradient@face.area_vector_m2 for face in mesh.faces])
    np.testing.assert_allclose(result['flux'],exact,rtol=3e-11,atol=1e-20)
    np.testing.assert_allclose(result['quadratic'],2*np.dot(gradient,gradient)*sum(mesh.volumes_m3),rtol=1e-12)
    assert max(abs(result['shared_flux_mismatch']))<1e-19
    assert np.max(abs(mesh.divergence_integrals(result['flux'])))<1e-19


@pytest.mark.parametrize('quantum',[False,True])
def test_affine_electric_drift_and_linear_heat_flux_on_skew_cells(quantum):
    mesh=skew_mesh();n=1e21;phi_gradient=np.array([1e5,-2e5,0.]);T_gradient=np.array([2e8,-1e8,0.])
    bc=boundary(mesh,lambda x:phi_gradient@x)
    model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,
        quantum_n_J_m2=1e-37 if quantum else 0.,quantum_p_J_m2=1e-37 if quantum else 0.,
        particle_contacts={f:CarrierReservoir(n,n) for f in bc},
        thermal_conductivity_W_m_K=.7,heat_bath_K=boundary(mesh,lambda x:300.+T_gradient@x))
    poisson=model._poisson(np.full(model.nc,n),np.full(model.nc,n),np.full(model.nc,.5),1e-29)
    fn,fp,*_=model.transport(np.full(model.nc,n),np.full(model.nc,n),np.full(model.nc,.5),np.full(model.nc,300.),poisson)
    exact=np.array([.01*n*phi_gradient@face.area_vector_m2 for face in mesh.faces])
    np.testing.assert_allclose(fn,exact,rtol=3e-10,atol=2e-3)
    np.testing.assert_allclose(fp,-exact,rtol=3e-10,atol=2e-3)
    heat=model.conduction(300.+mesh.centroids_m@T_gradient)
    expected=np.array([-.7*T_gradient@face.area_vector_m2 for face in mesh.faces])
    np.testing.assert_allclose(heat,expected,rtol=2e-10,atol=2e-16)
    assert model.skew>.1


def test_nonuniform_boltzmann_equilibrium_has_zero_flux_on_skew_cells():
    mesh=skew_mesh();g=np.array([1e5,-2e5,0.]);nc=len(mesh.volumes_m3)
    bc=boundary(mesh,lambda x:g@x)
    model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,
        particle_contacts={f:CarrierReservoir(1e21*np.exp(Q*v/(KB*300)),1e21*np.exp(-Q*v/(KB*300))) for f,v in bc.items()})
    phi=mesh.centroids_m@g;n=1e21*np.exp(Q*phi/(KB*300));p=1e21*np.exp(-Q*phi/(KB*300))
    model.rhofix=Q*(n-p)
    poisson=model._poisson(n,p,np.full(nc,.5),1e-29)
    fn,fp,*_=model.transport(n,p,np.full(nc,.5),np.full(nc,300.),poisson)
    assert max(np.max(abs(fn)),np.max(abs(fp)))<.01


def test_affine_root_quantum_energy_and_variational_chain_rule():
    mesh=skew_mesh();g=np.array([1e16,-2e16,0.]);root=lambda x:3e10+g@x
    bc=boundary(mesh,lambda x:0.)
    model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,quantum_n_J_m2=1e-37,quantum_p_J_m2=1e-37,
        particle_contacts={f:CarrierReservoir(root(mesh.faces[f].centroid_m)**2,1e21) for f in bc})
    n=(3e10+mesh.centroids_m@g)**2;p=np.full(model.nc,1e21)
    old=CutCellState(n,p,np.full(model.nc,.5),np.full(model.nc,300.))
    ea,pa=model.energies(old,charge_atol_C=1e-28)
    np.testing.assert_allclose(ea['quantum_J'],1e-37*np.dot(g,g)*sum(mesh.volumes_m3),rtol=1e-12)
    qn,qp=model.quantum_potentials(n,p)
    assert max(abs(qn))<1e-30
    new=CutCellState(n*np.linspace(.8,1.2,model.nc),p*np.linspace(.9,1.1,model.nc),old.trap_fraction,old.temperature_K,1e-12)
    eb,pb=model.energies(new,charge_atol_C=1e-28)
    qn,qp=model.quantum_potentials(new.n_m3,new.p_m3,n,p)
    expected=sum(model.vol*(qn*(new.n_m3-n)+qp*(new.p_m3-p)))
    difference=model.energy_increments(old,new,pa,pb)['quantum_J']
    np.testing.assert_allclose(expected,difference,rtol=2e-12)
    np.testing.assert_allclose(difference,eb['quantum_J']-ea['quantum_J'],rtol=2e-12)


@pytest.mark.parametrize('open_contacts',[False,True])
@pytest.mark.parametrize('nonconvex',[False,True])
def test_coupled_mimetic_trajectory_and_independent_audit(open_contacts,nonconvex):
    from test_electrothermal_cut_cell import fixture
    base,state=fixture(open_contacts=open_contacts,nonconvex=nonconvex,quantum=True,traps=True)
    model=model_from(base)
    for _ in range(2):
        old=state;state,report=model.step(old,2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        audit=audit_cut_cell_energy(model,old,state,report,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        assert audit['valid'] and report['linear_consistent_spatial_operator']
        assert not report['complete_device_energy'] and not report['SG_large_field_monotonicity']
        bad=deepcopy(report);bad['integrated_heat_flux_W']*=1.1
        assert not audit_cut_cell_energy(model,old,state,bad,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)['valid']


def test_zero_mobility_natural_flux_and_heterojunction_rejection():
    mesh=skew_mesh();operator=HybridMimeticOperator(mesh)
    result=operator.reconstruct(np.arange(operator.nc),0.)
    assert np.all(result['flux']==0.)
    with pytest.raises(ValueError,match='uniform band'):
        MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V={0:0.},
            mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Ec_J=np.arange(operator.nc)*Q)
    with pytest.raises(ValueError):operator.reconstruct(np.ones(operator.nc),1.,dirichlet={-1:0.})
