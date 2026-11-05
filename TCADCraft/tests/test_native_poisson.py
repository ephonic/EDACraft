"""Actual C++ HMM assembly and its independently audited FD integration."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import native_precision
from tcad.core._bindings import native_hybrid_poisson_raw
from tcad.mesh.polyhedral_cut_cell import convex_cut_cells
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.native_poisson import solve_native_cut_cell_poisson,solve_native_state_poisson
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal
from tcad.postprocess.native_poisson import audit_native_cut_cell_poisson
from tcad.postprocess.fermi_spectral_energy import audit_fermi_spectral_energy
from test_fermi_spectral import fixture,BUDGET
from test_native_spectral import constructor_arguments


def patch(*,skew=False,offset=.1):
    L=1e-7
    axes=[np.array([0.,.3,1.])*L]*3
    mesh=convex_cut_cells(axes,[[1.,.7,1.2,1.41*L]] if skew else [])
    gradient=np.array([.2,-.3,.4])/L
    bc={f:float(offset+gradient@face.centroid_m) for f,face in enumerate(mesh.faces) if face.neighbor<0}
    return mesh,gradient,bc


def audit(result,mesh,eps,rho,bc):
    return audit_native_cut_cell_poisson(result,mesh,eps,rho,dirichlet_V=bc,
        charge_atol_C=BUDGET['charge_atol_C'],energy_atol_J=BUDGET['energy_atol_J'])


@pytest.mark.parametrize('skew',[False,True])
@pytest.mark.parametrize('offset',[0.,.1,.4])
def test_native_affine_potential_D_and_E_match_analytic_three_axis_field(skew,offset):
    mesh,gradient,bc=patch(skew=skew,offset=offset);eps=2e-10
    result=solve_native_cut_cell_poisson(mesh,eps,0.,dirichlet_V=bc,charge_atol_C=2e-28)
    assert audit(result,mesh,eps,0.,bc)['valid']
    np.testing.assert_allclose(result['cell_potential_V'],offset+mesh.centroids_m@gradient,rtol=0.,atol=1e-12)
    np.testing.assert_allclose(result['electric_field_V_m'],np.broadcast_to(-gradient,(len(mesh.volumes_m3),3)),rtol=0.,atol=1e-5)
    exact=np.array([-eps*gradient@f.area_vector_m2 for f in mesh.faces])
    np.testing.assert_allclose(result['integrated_D_flux_C'],exact,rtol=0.,atol=2e-28)
    assert native_precision()['mantissa_bits']==113


@pytest.mark.parametrize('skew',[False,True])
def test_native_nonuniform_charge_and_permittivity_match_independent_HMM(skew):
    mesh,_,bc=patch(skew=skew)
    eps=1e-10*(1+mesh.centroids_m[:,0]/1e-7)
    rho=1000*(1+mesh.centroids_m[:,1]/1e-7)
    result=solve_native_cut_cell_poisson(mesh,eps,rho,dirichlet_V=bc,charge_atol_C=2e-28)
    assert audit(result,mesh,eps,rho,bc)['valid']
    assert max(abs(result['integrated_D_flux_C']))>0


def test_native_dielectric_jump_and_natural_boundaries_preserve_normal_D():
    L=1e-7;axes=[np.array([0.,.25,1.])*L,np.array([0.,L]),np.array([0.,L])]
    mesh=convex_cut_cells(axes,[]);eps=np.array([1e-10,3e-10]);bias=.03
    bc={f:0. if abs(face.centroid_m[0])<1e-20 else bias for f,face in enumerate(mesh.faces)
        if face.neighbor<0 and abs(face.area_vector_m2[0])>0}
    result=solve_native_cut_cell_poisson(mesh,eps,0.,dirichlet_V=bc,charge_atol_C=2e-28)
    assert audit(result,mesh,eps,0.,bc)['valid']
    D=-bias/(.25*L/eps[0]+.75*L/eps[1])
    for f,face in enumerate(mesh.faces):
        assert result['integrated_D_flux_C'][f]==pytest.approx(D*face.area_vector_m2[0],abs=2e-28)


def test_native_Poisson_charge_boundary_keeps_sub_float64_density_bits():
    mesh=convex_cut_cells([[0.,1e-7]]*3,[])
    before=np.longdouble('1e26');after=before+np.longdouble('1e9')
    assert float(before)==float(after) and before!=after
    bc={f:0. for f in range(len(mesh.faces))}
    result=solve_native_state_poisson(mesh,1e-10,0.,before,after,0.,.5,dirichlet_V=bc,charge_atol_C=2e-28)
    rho=1.602176634e-19*(after-before)
    assert result['valid'] and result['gauss_audit']['total_charge_C']>0
    assert audit(result,mesh,1e-10,rho,bc)['valid']


@pytest.mark.parametrize('field',['cell_potential_V','electric_field_V_m','integrated_D_flux_C',
    'electrostatic_energy_J','shared_flux_mismatch_C','algebraic_residual_C','gauss_audit','execution_backend'])
def test_independent_Poisson_audit_rejects_forged_native_result(field):
    mesh,_,bc=patch(skew=True);result=solve_native_cut_cell_poisson(mesh,2e-10,0.,dirichlet_V=bc,charge_atol_C=2e-28)
    bad=deepcopy(result)
    if field=='gauss_audit':bad[field]['total_charge_C']+=1e-20
    elif field=='execution_backend':bad[field]='python'
    elif field=='electrostatic_energy_J':bad[field]+=1e-22
    else:bad[field].flat[0]+=1. if field=='electric_field_V_m' else (1e-3 if field=='cell_potential_V' else 1e-20)
    assert not audit(bad,mesh,2e-10,0.,bc)['valid']


@pytest.mark.parametrize('scale,voltage,count',[(1.,0.,2),(1.,.002,2),(1.,-.002,2),
    (10.,0.,2),(10.,.002,2),(10.,-.002,2),(10.,.002,4),(10.,-.002,4)])
def test_native_Poisson_participates_in_actual_continuous_FD_steps(scale,voltage,count):
    model,state=fixture(contacts=True,voltage=voltage,count=count,density_scale=scale)
    model.spectral_backend=model.local_backend=model.poisson_backend='native'
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        check=audit_fermi_spectral_energy(model,old,state,report,**BUDGET)
        assert check['valid'],check
        assert report['poisson_backend']=='native' and not report['native_nonlinear_driver']
        assert max(abs(state.temperature_K-old.temperature_K))>1e-6


def test_native_Poisson_step_runs_with_Python_assembly_and_solve_disabled(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Python production Poisson invoked')
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend=model.local_backend=model.poisson_backend='native'
    with monkeypatch.context() as m:
        m.setattr('tcad.solver.cut_cell_transport.solve_cut_cell_poisson',forbidden)
        m.setattr('tcad.solver.cut_cell_poisson.solve_cut_cell_poisson',forbidden)
        m.setattr('scipy.sparse.linalg.spsolve',forbidden)
        new,report=model.step(old,2e-13,**BUDGET)
    # The audit must still use Python after the production path is restored.
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def test_energy_audit_does_not_call_model_Poisson(monkeypatch):
    model,old=fixture();model.spectral_backend=model.local_backend=model.poisson_backend='native'
    new,report=model.step(old,2e-13,**BUDGET)
    def forbidden(*args,**kwargs):raise AssertionError('auditor called production Poisson')
    monkeypatch.setattr(model,'_poisson',forbidden)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


def test_constructor_checks_native_Poisson_selection_and_symbol(monkeypatch):
    mesh,old,kwargs=constructor_arguments()
    model=FermiSpectralElectrothermal(mesh,spectral_backend='native',local_backend='native',poisson_backend='native',**kwargs)
    new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']
    with pytest.raises(ValueError,match='poisson_backend'):
        FermiSpectralElectrothermal(mesh,poisson_backend='automatic',**kwargs)
    monkeypatch.delattr('tcad.core._bindings.native_hybrid_poisson_raw')
    with pytest.raises(ImportError):FermiSpectralElectrothermal(mesh,poisson_backend='native',**kwargs)


def test_energy_audit_rejects_false_native_Poisson_flag():
    model,old=fixture();model.poisson_backend='native'
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report);bad['poisson_backend']='python'
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


def test_native_Poisson_failed_step_keeps_input_immutable():
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend=model.local_backend=model.poisson_backend='native'
    saved=[getattr(old,k).tobytes() for k in ('n_m3','p_m3','temperature_K','trap_fraction')]
    with pytest.raises(ValueError):model.step(old,2e-13,max_nfev=1,**BUDGET)
    assert saved==[getattr(old,k).tobytes() for k in ('n_m3','p_m3','temperature_K','trap_fraction')]


def raw_fixture():
    mesh=convex_cut_cells([[0.,1e-7]]*3,[])
    cells=[_decimal(v) for v in (mesh.volumes_m3[0],1e-10,0,1e25,1e25,0,.5,*mesh.centroids_m[0])]
    faces=[_decimal(v) for face in mesh.faces for v in (0,-1,*face.area_vector_m2,*face.centroid_m,1,0)]
    return cells,faces


@pytest.mark.parametrize('damage',['size','owner','fractional','neighbor','area','centroid','mode',
    'no_anchor','epsilon','volume','negative_density','fraction','nan','decimal','budget','limit','disconnected'])
def test_native_raw_Poisson_rejects_invalid_and_unanchored_inputs(damage):
    cells,faces=raw_fixture();budget=2e-28
    if damage=='size':cells.pop()
    elif damage=='owner':faces[0]='1'
    elif damage=='fractional':faces[0]='.5'
    elif damage=='neighbor':faces[1]='-2'
    elif damage=='area':faces[2:5]=['0']*3
    elif damage=='centroid':cells[7]='-1'
    elif damage=='mode':faces[8]='2'
    elif damage=='no_anchor':faces[8::10]=['0']*6
    elif damage=='epsilon':cells[1]='0'
    elif damage=='volume':cells[0]='-1'
    elif damage=='negative_density':cells[3]='-1'
    elif damage=='fraction':cells[6]='2'
    elif damage=='nan':cells[0]='nan'
    elif damage=='decimal':cells[3]='1junk'
    elif damage=='budget':budget=-1.
    elif damage=='limit':cells*=513
    else:
        cells*=2;extra=faces.copy();extra[0::10]=['1']*6;extra[8::10]=['0']*6;faces+=extra
    with pytest.raises(ValueError):native_hybrid_poisson_raw(cells,faces,budget)
