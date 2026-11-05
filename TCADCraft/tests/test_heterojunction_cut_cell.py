"""Two-sided interface resistance, detailed balance and self-consistent fields."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.heterojunction_cut_cell import HeterojunctionActivityOperator,IsothermalHeterojunctionDevice
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.cut_cell_transport import Q,KB


def mesh_and_interfaces(oblique=True,count=3):
    L=1e-7;normal=np.array([1.,.37 if oblique else 0.,0.]);offset=.53*L if oblique else .5*L
    axes=[np.linspace(0,L,count+1),np.linspace(0,L,count+1) if oblique else np.array([0.,L]),np.array([0.,L])]
    mesh=region_cut_cells(axes,{'left':[[[*normal,offset]]],'right':[[[*(-normal),-offset]]]})
    side=mesh.centroids_m@normal<offset
    interfaces=[f for f,face in enumerate(mesh.faces) if face.neighbor>=0 and side[face.owner]!=side[face.neighbor]]
    return mesh,interfaces,side,normal,offset


@pytest.mark.parametrize('contrast',[1.,10.,1000.])
def test_oblique_two_trace_operator_matches_exact_jump_and_normal_flux(contrast):
    mesh,faces,side,normal,offset=mesh_and_interfaces();operator=HeterojunctionActivityOperator(mesh,faces)
    coefficient=np.where(side,1.,contrast);per_area=3e7;current=1e7;unit=normal/np.linalg.norm(normal)
    def exact(x):
        signed=(x@normal-offset)/np.linalg.norm(normal)
        return 3.-current*signed/(1. if signed<=0 else contrast)-(0. if signed<=0 else current/per_area)
    bc={f:exact(face.centroid_m) for f,face in enumerate(mesh.faces) if face.neighbor<0}
    g=[per_area*np.linalg.norm(mesh.faces[f].area_vector_m2) for f in operator.interfaces]
    result=operator.solve(np.zeros(operator.nc),coefficient,dirichlet=bc,interface_conductance=g)
    np.testing.assert_allclose(result['cell_values'],[exact(x) for x in mesh.centroids_m],rtol=0,atol=2e-11)
    expected=[current*unit@face.area_vector_m2 for face in mesh.faces]
    np.testing.assert_allclose(result['flux'],expected,rtol=2e-9,atol=3e-17)
    for f in operator.interfaces:
        owner_left=side[mesh.faces[f].owner]
        np.testing.assert_allclose(result['owner_trace'][f]-result['neighbor_trace'][f],
            current/per_area*(1 if owner_left else -1),atol=1e-11)
    assert max(abs(result['shared_flux_mismatch']))<2e-17
    assert max(abs(result['interface_law_residual']))<2e-17


def test_zero_interface_velocity_separates_independent_equilibria():
    mesh,faces,side,_,_=mesh_and_interfaces(False)
    op=HeterojunctionActivityOperator(mesh,faces)
    bc={f:1. if side[face.owner] else 2. for f,face in enumerate(mesh.faces) if face.neighbor<0}
    result=op.solve(np.zeros(op.nc),1.,dirichlet=bc,interface_conductance=np.zeros(len(faces)))
    np.testing.assert_allclose(result['cell_values'],np.where(side,1.,2.),atol=1e-14)
    assert max(abs(result['flux']))<1e-20


@pytest.mark.parametrize('bad',['boundary','boolean','duplicate','negative'])
def test_interface_geometry_and_conductance_reject_bad_inputs(bad):
    mesh,faces,_,_,_=mesh_and_interfaces()
    with pytest.raises(ValueError):
        if bad=='boundary':HeterojunctionActivityOperator(mesh,[next(f for f,v in enumerate(mesh.faces) if v.neighbor<0)])
        elif bad=='boolean':HeterojunctionActivityOperator(mesh,[True])
        elif bad=='duplicate':HeterojunctionActivityOperator(mesh,[faces[0],faces[0]])
        else:HeterojunctionActivityOperator(mesh,faces).matrix(1.,-1.)


def equilibrium_device(oblique=True):
    mesh,faces,side,_,_=mesh_and_interfaces(oblique)
    Ec=np.where(side,.12,.19)*Q;Eh=np.where(side,.16,.09)*Q
    Nc=np.where(side,2.8e25,1.1e25);Nv=np.where(side,1.04e25,3.2e25)
    n=Nc*np.exp(-Ec/(KB*300));p=Nv*np.exp(-Eh/(KB*300))
    bc={f:0. for f,face in enumerate(mesh.faces) if face.neighbor<0}
    model=IsothermalHeterojunctionDevice(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        particle_contacts={f:CarrierReservoir(n[mesh.faces[f].owner],p[mesh.faces[f].owner]) for f in bc},
        terminal_groups={'outer':list(bc)},mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,
        Nc_m3=Nc,Nv_m3=Nv,Ec_J=Ec,Eh_J=Eh,fixed_charge_C_m3=Q*(n-p),
        interface_velocity_n_m_s={f:3e4 for f in faces},interface_velocity_p_m_s={f:2e4 for f in faces})
    return model,n,p


@pytest.mark.parametrize('oblique',[False,True])
def test_band_and_DOS_jumps_preserve_zero_current_equilibrium(oblique):
    model,n,p=equilibrium_device(oblique)
    result=model.solve(n,p,charge_atol_C=1e-24,particle_flux_atol_s=1e5,current_atol_A=1e-12)
    assert result['audit']['valid']
    np.testing.assert_allclose(result['n_m3'],n,rtol=1e-12)
    np.testing.assert_allclose(result['p_m3'],p,rtol=1e-12)
    assert max(abs(result['electrons']['flux']))<1e4
    assert not result['energy_closure_accepted']


@pytest.mark.parametrize('damage',['flux','trace','current','potential','displacement'])
def test_independent_audit_rejects_corrupted_interface_results(damage):
    model,n,p=equilibrium_device(False)
    result=model.solve(n,p,charge_atol_C=1e-24,particle_flux_atol_s=1e5,current_atol_A=1e-12)
    bad=deepcopy(result)
    if damage=='flux':bad['electrons']['flux'][model.operator.interfaces[0]]+=1e9
    elif damage=='trace':bad['electrons']['interface_owner_density_m3'][0]*=1.2
    elif damage=='current':bad['terminal_currents_A']['outer']+=1e-6
    elif damage=='potential':bad['poisson']['cell_potential_V'][0]+=.01
    else:bad['poisson']['integrated_D_flux_C'][0]+=1e-20
    assert not model.audit(bad,charge_atol_C=1e-24,particle_flux_atol_s=1e5,current_atol_A=1e-12)['valid']


def test_full_self_consistent_neutral_resistor_has_ohmic_small_signal_current():
    mesh,_,_,_,_=mesh_and_interfaces(False,8)
    groups={'left':[],'right':[]};bc={}
    for f,face in enumerate(mesh.faces):
        if face.neighbor<0 and abs(face.area_vector_m2[0])>0:
            name='left' if face.centroid_m[0]<1e-12 else 'right';groups[name].append(f);bc[f]=0. if name=='left' else 1e-4
    model=IsothermalHeterojunctionDevice(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        particle_contacts={f:CarrierReservoir(1e21,1e21) for f in bc},terminal_groups=groups,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Nc_m3=1e25,Nv_m3=1e25,Ec_J=0.,Eh_J=0.)
    result=model.solve(1e21,1e21,charge_atol_C=1e-26,particle_flux_atol_s=1e4,current_atol_A=1e-14)
    expected=Q*2e21*.01*1e-4/1e-7*1e-14
    np.testing.assert_allclose(result['terminal_currents_A']['right'],expected,rtol=1e-4)
