"""Physical terminal totals, ownership, complete coverage and bad-data gates."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.mimetic_electrothermal import MimeticElectrothermalCutCellTransport
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.cut_cell_transport import CutCellState,Q
from tcad.postprocess.cut_cell_energy import audit_cut_cell_energy
from tcad.postprocess.cut_cell_terminals import validate_terminal_groups,integrate_cut_cell_terminals


def fixture():
    L=1e-7;mesh=region_cut_cells([np.linspace(0,L,3)]*2+[np.array([0.,L])],{'box':[[]]})
    groups={'left':[],'right':[]};bc={}
    for f,face in enumerate(mesh.faces):
        if face.neighbor<0 and abs(face.area_vector_m2[0])>0:
            name='left' if face.area_vector_m2[0]<0 else 'right'
            groups[name].append(f);bc[f]=0. if name=='left' else .01
    model=MimeticElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.005,Nc_m3=1e21,Nv_m3=1e21,
        Ec_J=.04*Q,Eh_J=.04*Q,terminal_groups=groups,
        particle_contacts={f:CarrierReservoir(1e21,1e21) for f in bc},
        heat_bath_K={f:300. for f in bc},heat_capacity_J_m3_K=.1,thermal_conductivity_W_m_K=.001)
    state=CutCellState(np.full(4,1e21),np.full(4,1e21),np.full(4,.5),np.full(4,350.))
    return model,state,groups


def test_real_multiple_face_terminals_match_independent_integrals_and_global_energy():
    model,old,groups=fixture();groups['left'].clear()
    assert len(model.terminal_groups['left'])==2
    with pytest.raises(TypeError):model.terminal_groups['other']=()
    new,report=model.step(state=old,dt_s=2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
    audit=audit_cut_cell_energy(model,old,new,report,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
    assert audit['valid'] and audit['named_terminal_audit']['valid']
    for name,faces in model.terminal_groups.items():
        value=report['terminals'][name]
        np.testing.assert_allclose(value['current_A'],sum(report['terminal_currents_A'][f] for f in faces),rtol=1e-13)
        np.testing.assert_allclose(value['area_m2'],1e-14,rtol=1e-13)
        # Every physical terminal has two equal subfaces in this symmetric case.
        np.testing.assert_allclose(value['current_A'],2*report['terminal_currents_A'][faces[0]],rtol=1e-12)
    np.testing.assert_allclose(sum(v['source_work_J'] for v in report['terminals'].values()),report['source_work_J'],atol=1e-30)
    np.testing.assert_allclose(sum(v['outward_heat_J'] for v in report['terminals'].values()),report['outward_heat_J'],atol=1e-30)
    assert abs(2e-12*sum(v['current_A'] for v in report['terminals'].values()))<2e-29


@pytest.mark.parametrize('damage',['one_face_current','work','charge','heat','carrier_energy','area','voltage','partition'])
def test_audit_rejects_corrupt_named_physical_terminal_values(damage):
    model,old,_=fixture()
    new,report=model.step(old,2e-12,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)
    bad=deepcopy(report);value=bad['terminals']['right']
    if damage=='one_face_current':value['current_A']=report['terminal_currents_A'][model.terminal_groups['right'][0]]
    elif damage=='work':value['source_work_J']+=1e-22
    elif damage=='charge':value['charge_after_C']+=1e-21
    elif damage=='heat':value['outward_heat_J']*=1.1
    elif damage=='carrier_energy':value['outward_carrier_energy_J']+=1e-22
    elif damage=='area':value['area_m2']*=1.1
    elif damage=='voltage':value['voltage_V']+=.001
    else:bad['terminal_groups']['right'].pop()
    assert not audit_cut_cell_energy(model,old,new,bad,charge_atol_C=2e-29,particle_atol=1e-10,energy_atol_J=1e-28)['valid']


@pytest.mark.parametrize('damage',['missing','duplicate','overlap','interior','boolean','unequal_voltage','empty_name'])
def test_invalid_terminal_partition_rejected(damage):
    model,_,groups=fixture();bc=dict(model.bc)
    if damage=='missing':groups['right'].pop()
    elif damage=='duplicate':groups['right'].append(groups['right'][0])
    elif damage=='overlap':groups['right'].append(groups['left'][0])
    elif damage=='interior':groups['right'][0]=next(f for f,face in enumerate(model.mesh.faces) if face.neighbor>=0)
    elif damage=='boolean':groups['right'][0]=True
    elif damage=='unequal_voltage':bc[groups['right'][0]]+=.01
    else:groups['']=groups.pop('right')
    with pytest.raises(ValueError):validate_terminal_groups(model.mesh,bc,groups)


def test_named_displacement_and_conduction_signs_from_synthetic_fields():
    model,_,groups=fixture();nf=len(model.mesh.faces);dt=2e-12
    old=np.zeros(nf);new=np.zeros(nf);fn=np.zeros(nf)
    left,right=groups['left'],groups['right']
    new[left]=2e-20;new[right]=-2e-20;fn[left]=-1e10;fn[right]=1e10
    totals=integrate_cut_cell_terminals(model.mesh,model.bc,groups,dict(integrated_D_flux_C=old),
        dict(integrated_D_flux_C=new),fn,np.zeros(nf),np.zeros(nf),np.zeros(nf),dt)
    np.testing.assert_allclose(totals['right']['displacement_current_A'],4e-20/dt,rtol=1e-15)
    np.testing.assert_allclose(totals['right']['conduction_current_A'],2e10*Q,rtol=1e-15)
    np.testing.assert_allclose(totals['right']['source_work_J'],.01*(4e-20+dt*2e10*Q),rtol=1e-15)
    np.testing.assert_allclose(totals['left']['current_A'],-totals['right']['current_A'],rtol=1e-15)
