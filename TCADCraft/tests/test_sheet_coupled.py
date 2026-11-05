"""Sparse bulk/sheet coupling: independent fluxes, Jacobian and BE history."""
import copy
import itertools
import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_dielectric import SheetDielectricPoisson,DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from test_sheet_dielectric_contacts import trap

X=np.array([0.,.04,.2,.6,1.])*200e-9
Y=np.array([0.,.3,1.])*100e-9
Z=np.array([-10.,-5.,-2.5,0.,2.5,5.,10.])*1e-9
BOUNDS=((-5e-9,2.5e-9),(-2.5e-9,5e-9))
CASES=(('ideal','graphene'),('ideal','mos2'),('linear','graphene'),('linear','mos2'),
       ('thermionic','mos2'),('dirac','graphene'))

def device(backend='coupled',contact='linear',material='graphene',finite=True,inhomogeneous=False,scheme='diffusion_enhanced'):
    eps=5*8.8541878128e-12
    if inhomogeneous:eps=eps*(1+np.arange(48).reshape(6,2,4)/48)
    options={}
    if contact=='linear':options['contact_resistance_ohm_m']=.003
    if contact=='thermionic':options['thermionic_barrier_n_eV']=(.12,.15)
    if contact=='dirac':options['dirac_contact_offset_eV']=(-.02,.03)
    band=mos2_sheet(reference_eV=-.9) if material=='mos2' else graphene_sheet()
    return DielectricSheetDriftDiffusion(X,Y,Z,band,sheet_index=3,permittivity_F_m=eps,
        contact_z_bounds_m=BOUNDS if finite else None,electrostatic_backend=backend,
        mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,sheet_permittivity_F=2e-20,
        doping_m2=np.linspace(-1e13,2e13,15).reshape(3,5),fixed_charge_C_m2=1e-7,
        transport_scheme=scheme,**options)

def independent_edges(d):
    """Scalar cell integration; no solver conductances or sparse blocks."""
    nodes=np.arange(np.prod(d.shape)).reshape(d.shape);edges={}
    axes=(d.z,d.y,d.x)
    for cell in itertools.product(*(range(len(a)-1) for a in axes)):
        lengths=[a[k+1]-a[k] for a,k in zip(axes,cell)]
        for axis in range(3):
            other=[k for k in range(3) if k!=axis]
            g=d.permittivity_F_m[cell]*lengths[other[0]]*lengths[other[1]]/(4*lengths[axis])
            for bits in itertools.product((0,1),repeat=2):
                start=list(cell)
                for k,bit in zip(other,bits):start[k]+=bit
                end=start.copy();end[axis]+=1
                pair=(int(nodes[tuple(start)]),int(nodes[tuple(end)]))
                edges[pair]=edges.get(pair,0.)+g
    return edges

def check_fluxes(sim,r):
    d=sim.dielectric;phi=r['dielectric_phi_V'].ravel();edges=independent_edges(d)
    reported=dict(zip(map(tuple,r['dielectric_edge_nodes']),r['dielectric_edge_displacement_C']))
    assert edges.keys()==reported.keys()
    reaction=np.zeros(len(phi));energy=0.
    for (i,j),g in edges.items():
        delta=phi[i]-phi[j];flux=g*delta
        assert reported[i,j]==pytest.approx(flux,rel=3e-13,abs=1e-33)
        reaction[i]+=flux;reaction[j]-=flux;energy+=.5*g*delta**2
    np.testing.assert_allclose(r['dielectric_node_flux_sum_C'].ravel(),reaction,rtol=3e-12,atol=1e-32)
    assert np.max(abs(reaction[d.free_nodes]),initial=0.)<1e-10*max(np.max(abs(reaction)),1e-30)
    assert r['dielectric_energy_J']==pytest.approx(energy,rel=3e-12,abs=1e-32)
    for name,nodes in (('bottom_gate',d.gate_nodes[:d.size]),('top_gate',d.gate_nodes[d.size:])):
        assert r[name+'_charge_C']==pytest.approx(float(sum(reaction[nodes])),rel=3e-12,abs=1e-31)
    if d.contact_z_bounds_m is not None:
        for name,nodes in (('source',d.source_electrode_nodes),('drain',d.drain_electrode_nodes)):
            assert r['dielectric_contact_charge_C'][name]==pytest.approx(float(sum(reaction[nodes])),rel=3e-12,abs=1e-31)
            assert r['contact_charge_C'][name]==r['sheet_contact_charge_C'][name]+r['dielectric_contact_charge_C'][name]
    scale=max(abs(r['sheet_charge_C']),abs(r['top_gate_charge_C']),abs(r['bottom_gate_charge_C']),
              *map(abs,r['contact_charge_C'].values()),1e-25)
    assert abs(r['gauss_charge_sum_C'])<1e-8*scale

@pytest.mark.parametrize('value',(None,True,1,'sparse','Coupled',[]))
def test_backend_rejects_invalid_values(value):
    with pytest.raises(ValueError,match='backend'):device(value)

def test_coupled_rejects_schur_workspace_option():
    with pytest.raises(ValueError,match='schur_rhs_block_size'):
        SheetDielectricPoisson(X,Y,Z,sheet_index=3,permittivity_F_m=1.,backend='coupled',schur_rhs_block_size=2)

@pytest.mark.parametrize('finite,inhomogeneous',itertools.product((False,True),repeat=2))
def test_linear_poisson_matches_independent_monolithic_cell_operator(finite,inhomogeneous):
    sim=device(finite=finite,inhomogeneous=inhomogeneous);d=sim.dielectric
    edges=independent_edges(d);pairs=np.array(list(edges));g=np.array(list(edges.values()))
    i,j=pairs.T;L=coo_matrix((np.r_[g,g,-g,-g],(np.r_[i,j,i,j],np.r_[i,j,j,i])),shape=d.laplacian.shape).tocsr()
    drive=dict(top_gate_voltage_V=np.arange(15).reshape(3,5)*.001+.02,bottom_gate_voltage_V=-.007)
    if finite:drive.update(source_electrode_potential_V=-.01,drain_electrode_potential_V=.015)
    charge=np.linspace(-2e-4,1e-4,15).reshape(3,5)
    result=d.solve_linear(sheet_charge_C_m2=charge,**drive)
    fixed=d.gate_nodes
    if finite:fixed=np.r_[fixed,d.electrode_nodes,d.sheet_nodes[d.sheet_contact_nodes]]
    free=np.setdiff1d(np.arange(np.prod(d.shape)),fixed)
    phi=np.zeros(np.prod(d.shape));phi[fixed]=result['dielectric_phi_V'].ravel()[fixed]
    rhs=np.zeros(len(phi));rhs[d.sheet_nodes]=d.area*charge.ravel()
    phi[free]=spsolve(L[free][:,free],rhs[free]-L[free][:,fixed]@phi[fixed])
    np.testing.assert_allclose(result['dielectric_phi_V'].ravel(),phi,rtol=2e-12,atol=2e-14)
    scale=max(abs(result['sheet_charge_C']),abs(result['top_gate_charge_C']),1e-25)
    assert abs(result['gauss_charge_sum_C'])<1e-10*scale

@pytest.mark.parametrize('contact,material',CASES)
@pytest.mark.parametrize('scheme',('midpoint','diffusion_enhanced'))
def test_all_coupled_jacobian_columns_nonzero_fermi_storage_traps(contact,material,scheme):
    sim=device(contact=contact,material=material,inhomogeneous=True,scheme=scheme);d=sim.dielectric
    bc=sim._contact_boundary_conditions(.002,.006,.001)
    drive=d.gate_drive(top_gate_voltage_V=.012,bottom_gate_voltage_V=-.003,
        source_electrode_potential_V=float(bc[0][0]),drain_electrode_potential_V=float(bc[0][-1]))
    rng=np.random.default_rng(518)
    sheet=rng.normal(0,.003,3*sim.size);u=sim._initial_unknowns(sheet,drive,None)
    u[3*sim.size:]+=rng.normal(0,.002,len(d.free_nodes))
    st=sim.material.statistics(*sheet.reshape(3,sim.size),sim.temperature_K)
    sim._transient_storage=(st.n_m2*.99,st.p_m2*1.01,2e-12)
    sim._sheet_trap=(trap(sim).bind(sim.shape),np.full(sim.size,.4),2e-12)
    r,scale,J,*_=sim._evaluate(u,drive,bc);h=1e-7
    finite=np.empty(J.shape)
    for col in range(len(u)):
        delta=np.zeros(len(u));delta[col]=h
        finite[:,col]=(sim._evaluate(u+delta,drive,bc,False)[0]-sim._evaluate(u-delta,drive,bc,False)[0])/(2*h)
    np.testing.assert_allclose(J.toarray()/scale[:,None],finite/scale[:,None],rtol=2e-5,atol=2e-6)
    assert J[:sim.size,3*sim.size:].nnz and J[3*sim.size:,:sim.size].nnz
    assert J[sim.contacts,3*sim.size:].nnz==0

@pytest.mark.parametrize('contact,material',CASES)
@pytest.mark.parametrize('finite,inhomogeneous',itertools.product((False,True),repeat=2))
def test_non_equilibrium_dc_and_trap_transients_match_schur(contact,material,finite,inhomogeneous):
    trajectories=[]
    for backend in ('schur','coupled'):
        sim=device(backend,contact,material,finite,inhomogeneous)
        dc=sim.solve(top_gate_voltage_V=.012,bottom_gate_voltage_V=-.003,drain_voltage_V=.004,
            tolerance=1e-12,max_iter=120)
        assert dc['converged'];check_fluxes(sim,dc)
        assert np.max(abs(dc['Fn_eV']-dc['Fp_eV']))>1e-8
        run=SheetTransient(sim,initial_drive=dict(top_gate_voltage_V=.005),traps=trap(sim),
            initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
        states=[dc,run.state]
        for gate,drain in ((.025,.004),(-.01,-.004)):
            old=run.state
            state=run.step(dt_s=2e-12,top_gate_voltage_V=gate,drain_voltage_V=drain,tolerance=1e-12,max_iter=120)
            assert state['accepted'];check_fluxes(sim,state)
            scale=max(max(map(abs,state['terminal_total_currents_A'].values())),abs(state['sheet_charge_rate_A']),1e-12)
            assert abs(state['terminal_total_current_sum_A'])<1e-8*scale
            for name in ('source','drain'):
                assert state['contact_displacement_currents_A'][name]==pytest.approx(
                    (state['contact_charge_C'][name]-old['contact_charge_C'][name])/2e-12,rel=1e-12,abs=1e-20)
            states.append(state)
        trajectories.append(states)
    for old,new in zip(*trajectories):
        for key in ('phi_V','Fn_eV','Fp_eV','trap_occupancy','dielectric_phi_V','n_m2','p_m2'):
            if key in old:np.testing.assert_allclose(new[key],old[key],rtol=2e-9,atol=1e-12)
        for key in ('contact_charge_C','terminal_currents_into_sheet_A','terminal_total_currents_A'):
            if key in old:
                for name in old[key]:np.testing.assert_allclose(new[key][name],old[key][name],rtol=2e-8,atol=1e-28 if 'charge' in key else 1e-16)

def assert_state_equal(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a:assert_state_equal(a[key],b[key])
    elif isinstance(a,np.ndarray):np.testing.assert_array_equal(a,b)
    else:assert a==b

def test_transient_owns_bulk_geometry_and_rolls_back_every_state_field():
    sim=device();run=SheetTransient(sim,initial_drive=dict(top_gate_voltage_V=.005),traps=trap(sim),
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
    clean=copy.deepcopy(run)
    # A caller changing its original sparse block must not change the driver.
    sim.dielectric._lff.data[:]=0.;sim.dielectric._lsf.data[:]=0.
    public=run.state;public['dielectric_phi_V'][:]=99.;public['trap_occupancy'][:]=0.
    before=run.state;time=run.time_s
    failed=run.step(dt_s=2e-12,top_gate_voltage_V=.2,drain_voltage_V=.04,max_iter=1,tolerance=1e-14)
    assert not failed['accepted'] and run.time_s==time
    assert_state_equal(run.state,before)
    for bad in (np.nan,np.ones((2,2))):
        with pytest.raises(ValueError):run.step(dt_s=2e-12,top_gate_voltage_V=bad)
        assert_state_equal(run.state,before)
    # Compare a no-voltage retry with a fresh history: rejected drive did not commit.
    retry=run.step(dt_s=2e-12,tolerance=1e-12,max_iter=120)
    reference=clean.step(dt_s=2e-12,tolerance=1e-12,max_iter=120)
    assert retry['accepted'];assert_state_equal(retry,reference)

def test_coupled_exceeds_old_sheet_cap_without_dense_maps(monkeypatch):
    import tcad.solver.sheet_dielectric as module
    def forbidden(*args,**kwargs):raise AssertionError('Schur bulk factor must not be constructed')
    monkeypatch.setattr(module,'splu',forbidden)
    x=np.linspace(0.,200e-9,129);y=np.linspace(0.,100e-9,9);z=np.linspace(-10e-9,10e-9,5)
    sim=DielectricSheetDriftDiffusion(x,y,z,graphene_sheet(),sheet_index=2,permittivity_F_m=5*8.8541878128e-12,
        electrostatic_backend='coupled',mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,transport_scheme='diffusion_enhanced')
    assert sim.size==1161 and sim.dielectric._factor is None
    assert sim.dielectric.sheet_matrix_F.nnz<5*sim.size
    assert sim.dielectric._gate_map.nnz<3*sim.size
    r=sim.solve(top_gate_voltage_V=.01,drain_voltage_V=.004,tolerance=1e-12,max_iter=120)
    assert r['converged'] and r['electrostatic_backend']=='coupled'
    assert r['dielectric_free_residual_scaled_linf']<1e-12

@pytest.mark.parametrize('bad',(np.nan,np.zeros((1,2)),True))
def test_bulk_warm_start_requires_finite_full_shape(bad):
    sim=device();initial=dict(phi_V=np.zeros(sim.shape),Fn_eV=np.zeros(sim.shape),Fp_eV=np.zeros(sim.shape),dielectric_phi_V=bad)
    with pytest.raises(ValueError):sim.solve(top_gate_voltage_V=.01,initial=initial)

def test_no_free_bulk_nodes_still_solves():
    sim=DielectricSheetDriftDiffusion([0.,1e-7],[0.,1e-7],[-1e-8,0.,1e-8],graphene_sheet(),
        sheet_index=1,permittivity_F_m=5*8.8541878128e-12,electrostatic_backend='coupled',
        mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01)
    r=sim.solve(top_gate_voltage_V=.01,drain_voltage_V=.004,tolerance=1e-12)
    assert r['converged'] and r['dielectric_free_residual_scaled_linf']==0.
