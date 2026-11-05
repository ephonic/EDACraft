"""Continuous manufactured fields and actual oblique multiphysics checks."""
import numpy as np
import pytest
from tcad.solver.hybrid_mimetic import HybridMimeticOperator
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.mimetic_electrothermal import MimeticElectrothermalCutCellTransport
from tcad.solver.cut_cell_transport import CutCellState,Q,KB
from tcad.postprocess.cut_cell_energy import audit_cut_cell_energy
from test_mimetic_electrothermal import skew_mesh,boundary


def manufactured(count):
    mesh=skew_mesh(count);operator=HybridMimeticOperator(mesh);L=1e-7
    function=lambda x:1.+np.sin(np.pi*x[0]/L)*np.sin(np.pi*x[1]/L)
    exact=np.array([function(x) for x in mesh.centroids_m])
    source=2*(np.pi/L)**2*(exact-1.)*mesh.volumes_m3
    result=operator.solve(source,1.,dirichlet=boundary(mesh,function))
    error=float(np.sqrt(np.dot(mesh.volumes_m3,(result['cell_values']-exact)**2)/sum(mesh.volumes_m3)))
    return dict(count=count,cells=operator.nc,faces=operator.nf,L2_error=error),result


def test_smooth_manufactured_diffusion_converges_on_skew_cut_cells():
    rows=[manufactured(count)[0] for count in (4,8,16)]
    assert rows[1]['L2_error']<rows[0]['L2_error']/2.5,rows
    assert rows[2]['L2_error']<rows[1]['L2_error']/2.5,rows


@pytest.mark.parametrize('count',[3,5])
def test_log_activity_isothermal_dissipation_is_nonnegative(count):
    mesh=skew_mesh(count);op=HybridMimeticOperator(mesh)
    # For fixed temperature the combined force is the gradient of chemical
    # potential. Test the full hybrid quadratic, including stabilization.
    cell=np.sin(np.arange(op.nc)*.7)+2.
    field=op.reconstruct(cell,np.linspace(.5,2.,op.nc))
    independent=np.dot(cell,mesh.divergence_integrals(field['flux']))
    np.testing.assert_allclose(independent,field['quadratic'],rtol=2e-12)
    assert independent>0


def oblique_fixture():
    mesh=skew_mesh(3);L=1e-7;nc=len(mesh.volumes_m3);x=mesh.centroids_m[:,0]/L
    bc=boundary(mesh,lambda x:.01*x[0]/L)
    contacts={f:CarrierReservoir((1.3-.6*mesh.faces[f].centroid_m[0]/L)*1e21,1e21) for f in bc}
    model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,Nc_m3=1e21,Nv_m3=1e21,
        Ec_J=.04*Q,Eh_J=.04*Q,trap_energy_J=.005*Q,trap_density_m3=2e20,
        capture_n_m3_s=1e-12,capture_p_m3_s=2e-12,quantum_n_J_m2=1e-37,quantum_p_J_m2=5e-38,
        heat_capacity_J_m3_K=.1,thermal_conductivity_W_m_K=.001,
        heat_bath_K={f:300. for f in bc},particle_contacts=contacts)
    state=CutCellState(1e21*(.8+.4*x),1e21*(1.2-.4*x),np.full(nc,.3),np.full(nc,350.))
    return model,state


def test_actual_oblique_coupled_open_contact_energy_and_charge():
    model,state=oblique_fixture();assert model.skew>.1
    for _ in range(2):
        old=state
        state,report=model.step(old,2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        audit=audit_cut_cell_energy(model,old,state,report,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
        assert audit['valid'] and not report['complete_device_energy']
        assert np.max(abs(state.temperature_K-old.temperature_K))>.01


def test_log_activity_flux_refines_toward_continuous_diffusion():
    errors=[];L=1e-7;gradient=np.array([.2,.3,0.])/L;D=.01*KB*300/Q
    for count in (4,8,16):
        mesh=skew_mesh(count);bc=boundary(mesh,lambda x:0.)
        n=1e21*(1.+mesh.centroids_m@gradient);nc=len(n)
        model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
            mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,
            particle_contacts={f:CarrierReservoir(1e21*(1+mesh.faces[f].centroid_m@gradient),
                1e21*(1+mesh.faces[f].centroid_m@gradient)) for f in bc})
        poisson=model._poisson(n,n,np.full(nc,.5),1e-29)
        fn,*_=model.transport(n,n,np.full(nc,.5),np.full(nc,300.),poisson)
        area=np.array([face.area_vector_m2 for face in mesh.faces]);norm=np.linalg.norm(area,axis=1)
        reference=-D*1e21*(area@gradient)
        errors.append(float(np.sqrt(np.sum((fn-reference)**2/norm)/np.sum(reference**2/norm))))
    assert errors[1]<errors[0]/1.5,errors
    assert errors[2]<errors[1]/1.5,errors
