"""Analytic layered stacks, nonlocal fields and nonlinear sheet conservation."""
import itertools
import numpy as np
import pytest

from tcad.material import graphene_sheet,mos2_sheet
from tcad.material.sheet import Q
from tcad.solver.sheet_dielectric import SheetDielectricPoisson,DielectricSheetDriftDiffusion
from test_sheet_drift_diffusion import ledgers

EPS0=8.8541878128e-12


def device(kind='graphene',nx=9,ny=3,width=100e-9,multiplier=1.):
    x=(.5-.5*np.cos(np.linspace(0.,np.pi,nx)))*200e-9
    y=np.linspace(0.,width,ny)
    z=np.array([-20.,-12.,-5.,0.,3.,8.,16.])*1e-9
    eps=np.ones((6,ny-1,nx-1))*EPS0
    eps[:3]*=3.9;eps[3:]*=9.
    mat=graphene_sheet() if kind=='graphene' else mos2_sheet(reference_eV=-.9)
    stats=mat.statistics()
    return DielectricSheetDriftDiffusion(x,y,z,mat,sheet_index=3,permittivity_F_m=eps,
        mobility_n_m2_Vs=.02*multiplier,mobility_p_m2_Vs=.01*multiplier,
        doping_m2=float(stats.n_m2-stats.p_m2),sheet_permittivity_F=4e-20)


@pytest.mark.parametrize('charge,nonuniform',itertools.product((-.003,0.,.003),(False,True)))
def test_layered_capacitor_exact_potential_charge_and_displacement_jump(charge,nonuniform):
    x=np.array([0.,.2,.7,1.])*100e-9;y=np.array([0.,.3,1.])*80e-9
    z=np.array([-20.,-13.,-5.,0.,2.,8.,16.])*1e-9 if nonuniform else np.arange(-3,4)*5e-9
    epsilon=np.array([3.9,3.9,7.,9.,9.,12.])*EPS0
    sim=SheetDielectricPoisson(x,y,z,sheet_index=3,permittivity_F_m=epsilon[:,None,None])
    top,bottom=.2,-.1;ct=1/np.sum(np.diff(z)[3:]/epsilon[3:]);cb=1/np.sum(np.diff(z)[:3]/epsilon[:3])
    expected=(ct*top+cb*bottom+charge)/(ct+cb)
    result=sim.solve_linear(sheet_charge_C_m2=charge,top_gate_voltage_V=top,bottom_gate_voltage_V=bottom)
    np.testing.assert_allclose(result['phi_V'],expected,atol=2e-14,rtol=2e-13)
    # Exact piecewise linear series-stack profile on every dielectric node.
    p=np.r_[bottom+(expected-bottom)*np.r_[0,np.cumsum(np.diff(z)[:3]/epsilon[:3])]/np.sum(np.diff(z)[:3]/epsilon[:3]),
        expected+(top-expected)*np.cumsum(np.diff(z)[3:]/epsilon[3:])/np.sum(np.diff(z)[3:]/epsilon[3:])]
    np.testing.assert_allclose(result['dielectric_phi_V'],np.broadcast_to(p[:,None,None],sim.shape),atol=3e-14,rtol=2e-13)
    area=(x[-1]-x[0])*(y[-1]-y[0])
    assert result['top_gate_charge_C']==pytest.approx(ct*(top-expected)*area,rel=2e-12,abs=1e-30)
    assert result['bottom_gate_charge_C']==pytest.approx(cb*(bottom-expected)*area,rel=2e-12,abs=1e-30)
    assert abs(result['gauss_charge_sum_C'])<1e-12*(abs(charge)+ct+cb)*area
    plane=result['dielectric_node_flux_sum_C'][3].ravel()
    np.testing.assert_allclose(plane,charge*sim.area,rtol=2e-12,atol=1e-30)


def test_laplace_fringe_field_against_three_dimensional_separable_solution():
    errors=[]
    for nx,ny,nz in ((9,5,9),(17,9,17),(25,13,25)):
        x=np.linspace(0,100e-9,nx);y=np.linspace(0,80e-9,ny);z=np.linspace(-20e-9,20e-9,nz)
        wave=np.cos(np.pi*x/100e-9)[None,:]*np.cos(np.pi*y/80e-9)[:,None]
        sim=SheetDielectricPoisson(x,y,z,sheet_index=nz//2,permittivity_F_m=4*EPS0)
        result=sim.solve_linear(sheet_charge_C_m2=0.,top_gate_voltage_V=wave,bottom_gate_voltage_V=wave)
        k=np.hypot(np.pi/100e-9,np.pi/80e-9)
        exact=np.cosh(k*z)[:,None,None]/np.cosh(k*20e-9)*wave[None,:,:]
        errors.append(np.max(np.abs(result['dielectric_phi_V']-exact)))
    assert errors[2]<.65*errors[1] and errors[1]<.65*errors[0],errors
    assert errors[2]<.002,errors


def test_schur_reconstruction_matches_direct_monolithic_poisson():
    from scipy.sparse.linalg import spsolve
    rng=np.random.default_rng(500)
    sim=SheetDielectricPoisson([0.,.3e-7,1e-7],[0.,.2e-7,1e-7],[-1e-8,-.2e-8,0.,.4e-8,1e-8],
        sheet_index=2,permittivity_F_m=EPS0*(1+rng.random((4,2,2))))
    charge=rng.normal(0,.001,(3,3));top=rng.normal(0,.1,(3,3));bottom=rng.normal(0,.1,(3,3))
    result=sim.solve_linear(sheet_charge_C_m2=charge,top_gate_voltage_V=top,bottom_gate_voltage_V=bottom)
    matrix=sim.laplacian.tolil();rhs=np.zeros(np.prod(sim.shape));rhs[sim.sheet_nodes]=charge.ravel()*sim.area
    for i,v in zip(sim.gate_nodes,np.r_[bottom.ravel(),top.ravel()]):matrix.rows[i]=[i];matrix.data[i]=[1.];rhs[i]=v
    direct=spsolve(matrix.tocsr(),rhs).reshape(sim.shape)
    np.testing.assert_allclose(result['dielectric_phi_V'],direct,rtol=1e-12,atol=1e-14)
    # Reciprocity is a property of eliminating this symmetric dielectric network.
    np.testing.assert_allclose(sim.sheet_matrix_F.toarray(),sim.sheet_matrix_F.toarray().T,rtol=1e-12,atol=1e-30)


@pytest.mark.parametrize('kind,drain',itertools.product(('graphene','mos2'),(-.02,0.,.02)))
def test_self_consistent_two_material_dc_and_dielectric_flux_ledger(kind,drain):
    sim=device(kind);gate=.08*np.outer(np.linspace(.6,1.,3),np.sin(np.pi*sim.x/sim.x[-1]))
    result=sim.solve(top_gate_voltage_V=gate,bottom_gate_voltage_V=-.015,drain_voltage_V=drain)
    ledgers(result);assert result['model']=='isothermal_sheet_dd_cartesian_dielectric'
    np.testing.assert_array_equal(result['dielectric_phi_V'][3],result['phi_V'])
    flux=result['dielectric_node_flux_sum_C'].ravel();free=sim.dielectric.free_nodes
    scale=np.max(np.abs(result['dielectric_edge_displacement_C']))
    assert np.max(np.abs(flux[free]))<1e-12*scale
    if drain==0:assert np.max(np.abs(result['edge_currents_A']))<1e-20
    else:assert np.sign(result['terminal_currents_into_sheet_A']['drain'])==np.sign(drain)
    assert result['dielectric_energy_J']>0


@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_nonlocal_dielectric_analytic_jacobian(kind):
    sim=device(kind,nx=5,ny=3);rng=np.random.default_rng(50);N=sim.size
    u=rng.normal(0.,.01,3*N);v=rng.normal(0.,1.,3*N)
    drive=sim.dielectric.gate_drive(top_gate_voltage_V=.04,bottom_gate_voltage_V=-.02)
    bc=(np.zeros(len(sim.contacts)),)*3
    r,scale,J,*_=sim._evaluate(u,drive,bc)
    h=1e-6
    fd=(sim._evaluate(u+h*v,drive,bc,False)[0]-sim._evaluate(u-h*v,drive,bc,False)[0])/(2*h)
    assert np.max(np.abs((J@v-fd)/scale))<2e-5


@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_genuine_y_transport_and_mobility_scaling(kind):
    sim=device(kind,ny=5);gate=.1*np.outer(np.linspace(.1,1.,5),np.sin(np.pi*sim.x/sim.x[-1]))
    result=sim.solve(top_gate_voltage_V=gate,drain_voltage_V=.02);ledgers(result)
    other=device(kind,ny=5,multiplier=3.).solve(top_gate_voltage_V=gate,drain_voltage_V=.02);ledgers(other)
    np.testing.assert_allclose(other['phi_V'],result['phi_V'],atol=2e-10,rtol=0)
    assert other['terminal_currents_into_sheet_A']['drain']==pytest.approx(3*result['terminal_currents_into_sheet_A']['drain'],rel=2e-8)
    assert np.max(np.abs(result['edge_currents_A'][[e[3]==1 for e in sim.edges]]))>1e-12


def test_solver_failure_reuse_and_gate_data_are_not_shared_between_calls():
    sim=device();top=np.full(sim.shape,.15)
    failed=sim.solve(top_gate_voltage_V=top,drain_voltage_V=.04,max_iter=1,tolerance=1e-14)
    assert not failed['converged'] and failed['status']=='max_iterations'
    good=sim.solve(top_gate_voltage_V=.04,drain_voltage_V=.02);ledgers(good)
    top[:]=99.;failed['dielectric_phi_V'][:]=99.
    repeat=sim.solve(top_gate_voltage_V=.04,drain_voltage_V=.02)
    np.testing.assert_array_equal(repeat['phi_V'],good['phi_V'])
    resumed=sim.solve(top_gate_voltage_V=.04,drain_voltage_V=.02,initial=good)
    ledgers(resumed);assert resumed['iterations']==0


@pytest.mark.parametrize('changes',[
    dict(sheet_index=0),dict(sheet_index=4),dict(sheet_index=True),dict(permittivity_F_m=0.),
    dict(permittivity_F_m=np.nan),dict(permittivity_F_m=np.ones((5,3,3))),
    dict(z_m=[0.,0.,1.,2.,3.]),dict(x_m=np.linspace(0,1,600)),
])
def test_invalid_dielectric_configuration_rejected(changes):
    args=dict(x_m=[0.,1.,2.],y_m=[0.,1.,2.],z_m=[-2.,-1.,0.,1.,2.],sheet_index=2,permittivity_F_m=EPS0)
    args.update(changes)
    with pytest.raises(ValueError):SheetDielectricPoisson(**args)


def test_local_gate_double_counting_and_bad_boundary_inputs_rejected():
    with pytest.raises(ValueError):
        DielectricSheetDriftDiffusion([0.,1.],[0.,1.],[-1.,0.,1.],graphene_sheet(),sheet_index=1,
            permittivity_F_m=EPS0,gate_capacitance_F_m2=.01,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01)
    sim=device()
    for value in (True,np.nan,np.ones((2,2))):
        with pytest.raises(ValueError):sim.solve(top_gate_voltage_V=value)
