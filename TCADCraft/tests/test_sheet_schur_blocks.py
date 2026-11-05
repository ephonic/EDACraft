"""Blocked elimination: monolithic Poisson, carrier dynamics and workspace."""
import numpy as np
import pytest
from scipy.sparse.linalg import spsolve
import tcad.solver.sheet_dielectric as module
from tcad.solver.sheet_dielectric import SheetDielectricPoisson,DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from tcad.material import graphene_sheet,mos2_sheet
from test_sheet_dielectric_contacts import trap

X=np.array([0.,.04,.2,.6,1.])*200e-9
Y=np.array([0.,.3,1.])*100e-9
Z=np.array([-10.,-5.,-2.5,0.,2.5,5.,10.])*1e-9

def poisson(block,finite,inhomogeneous):
    eps=5*8.8541878128e-12
    if inhomogeneous:eps=eps*(1+np.arange(48).reshape(6,2,4)/48)
    return SheetDielectricPoisson(X,Y,Z,sheet_index=3,permittivity_F_m=eps,
        contact_z_bounds_m=((-5e-9,2.5e-9),(-2.5e-9,5e-9)) if finite else None,
        schur_rhs_block_size=block)

@pytest.mark.parametrize('value',(True,False,0,-1,1.,float('nan'),'2'))
def test_block_size_rejects_non_positive_integers(value):
    with pytest.raises(ValueError,match='schur_rhs_block_size'):
        poisson(value,True,False)

@pytest.mark.parametrize('block',(1,3,np.int64(64)))
@pytest.mark.parametrize('finite',(False,True))
@pytest.mark.parametrize('inhomogeneous',(False,True))
def test_blocked_maps_and_fields_match_monolithic_system(block,finite,inhomogeneous):
    d=poisson(block,finite,inhomogeneous);old=poisson(None,finite,inhomogeneous)
    for a,b in ((d.sheet_matrix_F.toarray(),old.sheet_matrix_F.toarray()),(d._gate_map,old._gate_map),(d._contact_map,old._contact_map)):
        np.testing.assert_allclose(a,b,rtol=2e-12,atol=max(np.max(abs(b),initial=0.),1e-30)*2e-14)
    top=np.arange(15).reshape(3,5)*.001+.02
    drive=dict(top_gate_voltage_V=top,bottom_gate_voltage_V=-.007)
    if finite:drive.update(source_electrode_potential_V=-.01,drain_electrode_potential_V=.015)
    charge=np.linspace(-2e-4,1e-4,15).reshape(3,5)
    out=d.solve_linear(sheet_charge_C_m2=charge,**drive)
    fixed=d.gate_nodes
    if finite:fixed=np.r_[fixed,d.electrode_nodes,d.sheet_nodes[d.sheet_contact_nodes]]
    free=np.setdiff1d(np.arange(np.prod(d.shape)),fixed)
    phi=np.zeros(np.prod(d.shape));phi[fixed]=out['dielectric_phi_V'].ravel()[fixed]
    rhs=np.zeros(len(phi));rhs[d.sheet_nodes]=d.area*charge.ravel()
    phi[free]=spsolve(d.laplacian[free][:,free],rhs[free]-d.laplacian[free][:,fixed]@phi[fixed])
    np.testing.assert_allclose(out['dielectric_phi_V'].ravel(),phi,rtol=2e-12,atol=2e-14)
    assert abs(out['gauss_charge_sum_C'])<1e-10*max(abs(out['sheet_charge_C']),abs(out['top_gate_charge_C']),1e-25)
    reaction=d.laplacian@phi
    np.testing.assert_allclose(out['dielectric_energy_J'],.5*phi@reaction,rtol=2e-12,atol=1e-30)

@pytest.mark.parametrize('contact',('ideal','linear','thermionic','dirac'))
def test_blocked_device_transient_matches_existing_algorithm(contact):
    material=mos2_sheet(reference_eV=-.9) if contact=='thermionic' else graphene_sheet()
    options={}
    if contact=='linear':options['contact_resistance_ohm_m']=.003
    if contact=='thermionic':options['thermionic_barrier_n_eV']=(.12,.15)
    if contact=='dirac':options['dirac_contact_offset_eV']=(-.02,.03)
    runs=[]
    for block in (None,2):
        sim=DielectricSheetDriftDiffusion(X,Y,Z,material,sheet_index=3,permittivity_F_m=5*8.8541878128e-12,
            contact_z_bounds_m=((-5e-9,2.5e-9),(-2.5e-9,5e-9)),schur_rhs_block_size=block,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,transport_scheme='diffusion_enhanced',**options)
        run=SheetTransient(sim,initial_drive=dict(top_gate_voltage_V=.005),traps=trap(sim),
            initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
        states=[run.state]
        for gate,drain in ((.025,.004),(-.01,-.004)):
            states.append(run.step(dt_s=2e-12,top_gate_voltage_V=gate,drain_voltage_V=drain,tolerance=1e-12,max_iter=120))
        assert all(s['converged'] and s['accepted'] for s in states)
        runs.append(states)
    for step,(old,new) in enumerate(zip(*runs)):
        for key in ('phi_V','Fn_eV','Fp_eV','trap_occupancy','dielectric_phi_V'):
            np.testing.assert_allclose(new[key],old[key],rtol=1e-10,atol=1e-12)
        for key in ('contact_charge_C','sheet_contact_charge_C','dielectric_contact_charge_C'):
            for port in ('source','drain'):np.testing.assert_allclose(new[key][port],old[key][port],rtol=1e-9,atol=1e-28)
        keys=('terminal_currents_into_sheet_A',)
        if step:keys+=('terminal_total_currents_A',)
        for key in keys:
            for port in old[key]:np.testing.assert_allclose(new[key][port],old[key][port],rtol=1e-9,atol=1e-16)

def test_requested_workspace_bound_is_observed(monkeypatch):
    original=module.splu;columns=[]
    class Factor:
        def __init__(self,value):self.value=value
        def solve(self,rhs):
            if rhs.ndim==2:columns.append(rhs.shape[1])
            return self.value.solve(rhs)
    monkeypatch.setattr(module,'splu',lambda value:Factor(original(value)))
    d=poisson(3,True,True)
    assert columns and max(columns)<=3
    assert sum(columns)==len(d.sheet_nodes)+len(d.gate_nodes)+len(d.electrode_nodes)
