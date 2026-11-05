"""Finite side electrodes: independent electrostatics and transient charge."""
import copy
import itertools

import numpy as np
import pytest
from scipy.sparse import diags, kron
from scipy.sparse.linalg import spsolve

from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_dielectric import SheetDielectricPoisson, DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from tcad.solver.sheet_trap_balance import EnergySheetTrap

EPS=5*8.8541878128e-12
CONTACTS=('ideal','linear','thermionic','dirac')


def device(contact='linear',scheme='diffusion_enhanced'):
    material=mos2_sheet(reference_eV=-.9) if contact=='thermionic' else graphene_sheet()
    options=dict(transport_scheme=scheme)
    if contact=='linear':options['contact_resistance_ohm_m']=.003
    if contact=='thermionic':options['thermionic_barrier_n_eV']=(.12,.15)
    if contact=='dirac':options['dirac_contact_offset_eV']=(-.02,.03)
    return DielectricSheetDriftDiffusion(np.array([0.,.08,.3,.6,.9,1.])*200e-9,
        np.array([0.,.4,1.])*100e-9,np.linspace(-10e-9,10e-9,9),material,
        sheet_index=4,permittivity_F_m=EPS,contact_z_bounds_m=((-5e-9,2.5e-9),(-2.5e-9,5e-9)),
        mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,**options)


def trap(sim):
    offset=sim.material.gap_eV/2-.04 if sim.material.dispersion=='parabolic' else .01
    return EnergySheetTrap(1e14,2e-6,1e-6,offset,1.5,
        'donor' if sim.material.dispersion=='parabolic' else 'acceptor')


def check_reactions(sim,result):
    d=sim.dielectric;phi=result['dielectric_phi_V'].ravel()
    # Reconstruct divergence directly from reported D-face fluxes, without
    # using the solver's Laplacian or Schur complement.
    reaction=np.zeros(phi.size)
    edges=result['dielectric_edge_nodes'];flux=result['dielectric_edge_displacement_C']
    np.add.at(reaction,edges[:,0],flux);np.add.at(reaction,edges[:,1],-flux)
    scale=max(np.max(abs(reaction)),1e-30)
    np.testing.assert_allclose(reaction,result['dielectric_node_flux_sum_C'].ravel(),rtol=2e-12,atol=scale*2e-12)
    assert np.max(abs(reaction[d.free_nodes]))<1e-10*scale
    for name,nodes in (('source',d.source_electrode_nodes),('drain',d.drain_electrode_nodes)):
        assert np.max(abs(phi[nodes]-result['dielectric_electrode_potential_V'][name]))<1e-14
        assert result['dielectric_contact_charge_C'][name]==pytest.approx(float(np.sum(reaction[nodes])),rel=1e-10,abs=1e-30)
        assert result['contact_charge_C'][name]==result['sheet_contact_charge_C'][name]+result['dielectric_contact_charge_C'][name]
    charges=[result['sheet_charge_C'],result['top_gate_charge_C'],result['bottom_gate_charge_C'],*result['contact_charge_C'].values()]
    assert abs(sum(charges))<1e-8*max(map(abs,charges))


@pytest.mark.parametrize('level,cap,phi5',[
    (0,1.3994113668494256e-17,.005540671092349764),
    (1,1.3009983061032276e-17,.005775221521065983),
])
def test_finite_contact_matches_independent_cross_section_reference(level,cap,phi5):
    # Frozen stage510 reference used an independent x-z FV assembly.
    nx,nz=80*2**level+1,8*2**level+1
    sim=SheetDielectricPoisson(np.linspace(0,200e-9,nx),[0.,100e-9],np.linspace(-10e-9,10e-9,nz),
        sheet_index=nz//2,permittivity_F_m=EPS,contact_z_bounds_m=(-2.5e-9,2.5e-9))
    r=sim.solve_linear(sheet_charge_C_m2=0.,top_gate_voltage_V=.01,bottom_gate_voltage_V=.01,
        source_electrode_potential_V=0.,drain_electrode_potential_V=0.)
    assert -sum(r['contact_charge_C'].values())/.01==pytest.approx(cap,rel=1e-12)
    assert r['phi_V'][0,2*2**level]==pytest.approx(phi5,abs=1e-14)
    assert abs(r['gauss_charge_sum_C'])<1e-10*cap*.01


def axis_forms(axis):
    delta=np.diff(axis);g=1/delta
    stiffness=diags((-g,np.r_[g,0.]+np.r_[0.,g],-g),(-1,0,1),format='csr')
    widths=np.r_[delta[0]/2,(axis[2:]-axis[:-2])/2,delta[-1]/2]
    return stiffness,diags(widths,format='csr')


def test_asymmetric_contacts_match_independent_monolithic_tensor_operator():
    x=np.array([0.,.3,.7,1.])*80e-9;y=np.array([0.,.2,1.])*50e-9
    z=np.array([-10.,-5.,-2.5,0.,2.5,5.,10.])*1e-9
    sim=SheetDielectricPoisson(x,y,z,sheet_index=3,permittivity_F_m=EPS,
        contact_z_bounds_m=((-5e-9,2.5e-9),(-2.5e-9,5e-9)))
    kx,wx=axis_forms(x);ky,wy=axis_forms(y);kz,wz=axis_forms(z)
    matrix=EPS*(kron(wz,kron(wy,kx))+kron(wz,kron(ky,wx))+kron(kz,kron(wy,wx))).tocsr()
    rng=np.random.default_rng(511);charge=rng.normal(0,.001,sim.sheet_shape)
    top=rng.normal(0,.01,sim.sheet_shape);bottom=rng.normal(0,.01,sim.sheet_shape)
    r=sim.solve_linear(sheet_charge_C_m2=charge,top_gate_voltage_V=top,bottom_gate_voltage_V=bottom,
        source_electrode_potential_V=.003,drain_electrode_potential_V=-.004)
    ids=np.arange(np.prod(sim.shape)).reshape(sim.shape)
    contacts=np.r_[ids[(z>=-5e-9)&(z<=2.5e-9),:,0].ravel(),ids[(z>=-2.5e-9)&(z<=5e-9),:,-1].ravel()]
    gates=np.r_[ids[0].ravel(),ids[-1].ravel()]
    fixed=np.r_[gates,contacts];free=np.setdiff1d(ids.ravel(),fixed)
    phi=np.zeros(ids.size);phi[gates]=np.r_[bottom.ravel(),top.ravel()]
    phi[contacts[:len(contacts)//2]]=.003;phi[contacts[len(contacts)//2:]]=-.004
    # Charge is prescribed on all sheet boxes; fixed-node charges appear
    # only in electrode reactions and cannot alter the free-node solution.
    rhs=np.zeros(ids.size);rhs[ids[3].ravel()]=sim.area*charge.ravel()
    phi[free]=spsolve(matrix[free][:,free],rhs[free]-matrix[free][:,fixed]@phi[fixed])
    np.testing.assert_allclose(r['dielectric_phi_V'].ravel(),phi,rtol=2e-12,atol=1e-14)
    reaction=matrix@phi-rhs
    for name,nodes in (('source',contacts[:len(contacts)//2]),('drain',contacts[len(contacts)//2:])):
        assert r['contact_charge_C'][name]==pytest.approx(float(np.sum(reaction[nodes])),rel=1e-12,abs=1e-30)


@pytest.mark.parametrize('contact,scheme',itertools.product(CONTACTS,('midpoint','diffusion_enhanced')))
def test_dd_pinned_alignment_and_full_jacobian(contact,scheme):
    sim=device(contact,scheme);source,drain,offset=.002,.006,.001
    r=sim.solve(top_gate_voltage_V=.012,source_voltage_V=source,drain_voltage_V=drain,
        fermi_offset_eV=offset,tolerance=1e-12,max_iter=120)
    assert r['converged'];check_reactions(sim,r)
    bc=sim._contact_boundary_conditions(source,drain,offset)
    assert r['dielectric_electrode_potential_V']==dict(source=float(bc[0][0]),drain=float(bc[0][-1]))
    for name,index in (('source',0),('drain',-1)):
        np.testing.assert_array_equal(r['phi_V'][:,index],r['dielectric_electrode_potential_V'][name])
    vg=sim.dielectric.gate_drive(top_gate_voltage_V=.012,bottom_gate_voltage_V=0.,
        source_electrode_potential_V=float(bc[0][0]),drain_electrode_potential_V=float(bc[0][-1]))
    rng=np.random.default_rng(511);u=np.concatenate([r[k].ravel() for k in ('phi_V','Fn_eV','Fp_eV')])
    u+=rng.normal(0,.001,u.size);direction=rng.normal(size=u.size)
    _,scale,jac,*_=sim._evaluate(u,vg,bc);h=1e-7
    fd=(sim._evaluate(u+h*direction,vg,bc,False)[0]-sim._evaluate(u-h*direction,vg,bc,False)[0])/(2*h)
    assert np.max(abs((jac@direction-fd)/scale))<2e-5


@pytest.mark.parametrize('contact,with_traps',itertools.product(CONTACTS,(False,True)))
def test_transient_merged_electrode_charge_and_rollback(contact,with_traps):
    sim=device(contact)
    cfg=dict(traps=trap(sim),initial_occupancy='equilibrium') if with_traps else {}
    run=SheetTransient(sim,initial_drive=dict(top_gate_voltage_V=.005),tolerance=1e-12,max_iter=120,**cfg)
    for gate,source,drain in ((.025,.001,.004),(-.01,-.002,-.004),(.008,0.,.002)):
        old=run.state;dt=2e-12
        r=run.step(dt_s=dt,top_gate_voltage_V=gate,source_voltage_V=source,drain_voltage_V=drain,
            tolerance=1e-12,max_iter=120)
        assert r['accepted'];check_reactions(sim,r)
        for name in ('source','drain'):
            expected=((r['sheet_contact_charge_C'][name]-old['sheet_contact_charge_C'][name])+
                (r['dielectric_contact_charge_C'][name]-old['dielectric_contact_charge_C'][name]))/dt
            assert r['contact_displacement_currents_A'][name]==pytest.approx(expected,rel=1e-12,abs=1e-20)
        current_scale=max(max(map(abs,r['terminal_total_currents_A'].values())),abs(r['sheet_charge_rate_A']),1e-12)
        assert abs(r['terminal_total_current_sum_A'])<1e-8*current_scale
    before=run.state;time=run.time_s
    failed=run.step(dt_s=dt,top_gate_voltage_V=.2,drain_voltage_V=.04,max_iter=1,tolerance=1e-14)
    assert not failed['accepted'] and run.time_s==time
    np.testing.assert_array_equal(run.state['dielectric_phi_V'],before['dielectric_phi_V'])
    with pytest.raises(ValueError):run.step(dt_s=dt,source_voltage_V=np.nan)
    np.testing.assert_array_equal(run.state['dielectric_phi_V'],before['dielectric_phi_V'])
    retry=run.step(dt_s=dt,top_gate_voltage_V=.009,tolerance=1e-12,max_iter=120)
    assert retry['accepted'];check_reactions(sim,retry)


def test_geometry_and_drive_ownership_and_no_accumulated_reaction():
    bounds=np.array([[-5e-9,2.5e-9],[-2.5e-9,5e-9]])
    sim=SheetDielectricPoisson([0.,50e-9,100e-9],[0.,100e-9],np.linspace(-10e-9,10e-9,9),
        sheet_index=4,permittivity_F_m=EPS,contact_z_bounds_m=bounds)
    bounds[:]=99.
    kwargs=dict(sheet_charge_C_m2=.001,top_gate_voltage_V=.01,bottom_gate_voltage_V=0.,
        source_electrode_potential_V=.002,drain_electrode_potential_V=-.003)
    r=sim.solve_linear(**kwargs);expected=copy.deepcopy(r)
    r['contact_z_bounds_m'][:]=99.;r['dielectric_electrode_nodes']['source'][:]=0
    r['dielectric_phi_V'][:]=99.;r['dielectric_contact_charge_C']['source']=99.
    repeat=sim.solve_linear(**kwargs)
    np.testing.assert_array_equal(repeat['dielectric_phi_V'],expected['dielectric_phi_V'])
    assert repeat['contact_charge_C']==expected['contact_charge_C']
    with pytest.raises(ValueError):sim.contact_z_bounds_m[:]=0.


@pytest.mark.parametrize('bounds',[True,0.,[0.],[-5e-9,0.],[0.,5e-9],[-10e-9,5e-9],
    [-5e-9,10e-9],[-3e-9,5e-9],[5e-9,-5e-9],[-5e-9,np.nan],np.ones((2,3)),[-1e-25,5e-9]])
def test_invalid_or_nonconforming_contact_bounds_rejected(bounds):
    with pytest.raises(ValueError):
        SheetDielectricPoisson([0.,1e-7],[0.,1e-7],np.linspace(-10e-9,10e-9,9),
            sheet_index=4,permittivity_F_m=EPS,contact_z_bounds_m=bounds)


@pytest.mark.parametrize('value',[None,True,np.nan,[0.,0.]])
def test_electrode_potential_must_be_explicit_finite_scalar(value):
    sim=device().dielectric
    with pytest.raises(ValueError):sim.gate_drive(top_gate_voltage_V=0.,bottom_gate_voltage_V=0.,
        source_electrode_potential_V=value,drain_electrode_potential_V=0.)


def test_electrode_drive_without_geometry_is_rejected():
    sim=SheetDielectricPoisson([0.,1e-7],[0.,1e-7],[-1e-8,0.,1e-8],sheet_index=1,permittivity_F_m=EPS)
    with pytest.raises(ValueError):sim.solve_linear(sheet_charge_C_m2=0.,top_gate_voltage_V=0.,bottom_gate_voltage_V=0.,
        source_electrode_potential_V=0.,drain_electrode_potential_V=0.)
