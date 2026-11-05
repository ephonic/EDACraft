"""Actual coupled steps, independent charge/energy and negative budgets."""
import numpy as np
import pytest
from copy import deepcopy
from tcad.postprocess.cut_cell_energy import audit_cut_cell_energy
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.cut_cell_transport import CutCellTransport,CutCellState,Q,KB


def fixture(*,nonconvex=False,quantum=False,traps=False,bath=False,bias=.01):
    length=1e-7;axes=[np.linspace(0,length,3)]*3
    regions={'L':[[[1,0,0,.65*length]],[[0,1,0,.65*length]]]} if nonconvex else {'box':[[]]}
    mesh=region_cut_cells(axes,regions);nc=len(mesh.volumes_m3)
    bc={f:bias*face.centroid_m[0]/length for f,face in enumerate(mesh.faces) if face.neighbor<0}
    baths={f:300. for f,face in enumerate(mesh.faces) if face.neighbor<0} if bath else None
    solver=CutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,Nc_m3=1e21,Nv_m3=1e21,
        Ec_J=.04*Q,Eh_J=.04*Q,trap_energy_J=.005*Q,
        trap_density_m3=2e20 if traps else 0.,capture_n_m3_s=1e-12 if traps else 0.,
        capture_p_m3_s=2e-12 if traps else 0.,quantum_n_J_m2=1e-37 if quantum else 0.,
        quantum_p_J_m2=5e-38 if quantum else 0.,heat_capacity_J_m3_K=1e3,
        thermal_conductivity_W_m_K=.01,heat_bath_K=baths)
    x=mesh.centroids_m[:,0]/length
    state=CutCellState(1e21*(.8+.4*x),1e21*(1.2-.4*x),np.full(nc,.3),np.full(nc,300.))
    return solver,state


@pytest.mark.parametrize('nonconvex',[False,True])
@pytest.mark.parametrize('traps,quantum,bath',[(False,False,False),(True,False,True),(True,True,False),(True,True,True)])
def test_actual_particle_trap_quantum_heat_step_closes(nonconvex,traps,quantum,bath):
    solver,state=fixture(nonconvex=nonconvex,traps=traps,quantum=quantum,bath=bath)
    charge=lambda s:np.sum(solver.vol*Q*(s.p_m3-s.n_m3-solver.Nt*s.trap_fraction),dtype=np.longdouble)
    original=state.n_m3.copy()
    for _ in range(2):
        before=state
        state,report=solver.step(state,2e-12,charge_atol_C=1e-29,particle_atol=1e-9,energy_atol_J=2e-28)
        assert report['valid'] and report['modeled_energy_components_complete']
        assert abs(charge(state)-charge(before))<1e-28
        assert np.any(state.n_m3!=before.n_m3)
        assert np.max(abs(report['particle_residuals']))<1e-9
        assert abs(report['energy_residual_J'])<2e-28
        independent=report['source_work_J']-report['outward_heat_J']-sum(report['energy_increments_J'].values())
        assert abs(independent)<2e-28
        if traps:assert abs(report['capture_heat_J'])>1e-27
        if quantum:assert report['energy_before_J']['quantum_J']>0
        assert not report['complete_device_energy']
        assert audit_cut_cell_energy(solver,before,state,report,charge_atol_C=1e-29,
            particle_atol=1e-9,energy_atol_J=2e-28)['valid']
    assert not np.array_equal(state.n_m3,original)


def test_graph_quantum_variational_derivative_and_exact_discrete_chain_rule():
    solver,state=fixture(quantum=True);n=state.n_m3;k=solver.kn
    energy=lambda a:np.sum(k*solver.metric*(np.sqrt(a[solver.i])-np.sqrt(a[solver.j]))**2)
    gradient=solver._quantum(n,k)
    for i in range(solver.nc):
        h=n[i]*1e-5;plus=n.copy();minus=n.copy();plus[i]+=h;minus[i]-=h
        fd=(energy(plus)-energy(minus))/(2*h)
        np.testing.assert_allclose(fd,solver.vol[i]*gradient[i],rtol=2e-7,atol=1e-55)
    new=n*np.linspace(.6,1.7,solver.nc)
    np.testing.assert_allclose(energy(new)-energy(n),np.dot(solver.vol*(new-n),solver._quantum(new,k,n)),rtol=1e-13)


def test_heterogeneous_band_and_dos_detailed_balance():
    solver,state=fixture(bias=0)
    # Exact graph equilibrium with fixed self-consistent neutral charge.
    x=solver.mesh.centroids_m[:,0]/1e-7
    solver.Ec=Q*.02*x;solver.Nc=1e21*(1+x)
    n=solver.Nc*np.exp(-solver.Ec/solver.kt);p=np.full(solver.nc,1e21)
    solver.rhofix=Q*(n-p)
    state=CutCellState(n,p,np.full(solver.nc,.5),np.full(solver.nc,300.))
    after,report=solver.step(state,1e-11,charge_atol_C=1e-29,particle_atol=1e-9,energy_atol_J=1e-28)
    np.testing.assert_allclose(after.n_m3,n,rtol=1e-12)
    np.testing.assert_allclose(after.p_m3,p,rtol=1e-12)


def test_fixed_absolute_budgets_reject_and_source_state_is_immutable():
    solver,state=fixture(quantum=True,traps=True)
    before=state.n_m3.copy()
    with pytest.raises(ValueError,match='budget'):
        solver.step(state,2e-12,charge_atol_C=1e-29,particle_atol=1e-25,energy_atol_J=1e-60)
    np.testing.assert_array_equal(state.n_m3,before)
    assert not state.n_m3.flags.writeable


@pytest.mark.parametrize('damage',['quantum','capture','flux','source','temperature'])
def test_independent_energy_audit_detects_corrupted_terms(damage):
    solver,old=fixture(quantum=True,traps=True,bath=True)
    new,report=solver.step(old,2e-12,charge_atol_C=1e-29,particle_atol=1e-9,energy_atol_J=2e-28)
    damaged=deepcopy(report)
    if damage=='quantum':damaged['energy_increments_J']['quantum_J']=0.
    elif damage=='capture':damaged['capture_heat_J']=0.
    elif damage=='flux':damaged['integrated_electron_particle_flux_s'][solver.internal[0]]*=1.1
    elif damage=='source':damaged['source_work_J']+=1e-24
    else:new=CutCellState(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K+1e-5,new.time_s)
    audit=audit_cut_cell_energy(solver,old,new,damaged,charge_atol_C=1e-29,particle_atol=1e-9,energy_atol_J=2e-28)
    assert not audit['valid']
