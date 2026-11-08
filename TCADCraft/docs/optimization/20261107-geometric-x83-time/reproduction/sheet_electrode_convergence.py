"""Fixed finite side electrodes: a new, explicit full-pulse benchmark group.

Shares the stage509 pulse/material protocol, but never replaces its line-contact
evidence. Time and space checks are separate; no joint error bound is implied.
"""
from dataclasses import asdict
from functools import lru_cache
import json
import os

import numpy as np
import pytest

import sheet_trap_convergence as protocol
from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient

CASES=(('linear',True),('thermionic',True))
TIME_COUNTS=protocol.TIME_COUNTS
SPACE_LEVELS=protocol.SPACE_LEVELS
PHASE_S=protocol.PHASE_S
CONTACT_BOUNDS_M=((-2.5e-9,2.5e-9),(-2.5e-9,2.5e-9))
BOUNDARY='finite_side_electrodes_5nm_v1'
coefficients=protocol.coefficients
drive=protocol.drive


def device(contact,dielectric,level,mesh_family='time'):
    if contact not in ('linear','thermionic') or dielectric is not True:
        raise ValueError('finite electrode benchmark requires an explicit dielectric case')
    if mesh_family not in ('time','space') or level not in SPACE_LEVELS:
        raise ValueError('unknown finite electrode mesh')
    nx=(8 if mesh_family=='space' else 4)*2**level+1
    ny=(1 if mesh_family=='space' else 2)*2**level+1
    u=np.linspace(0.,1.,nx)
    x=100e-9*(1-np.cos(np.pi*u)) if mesh_family=='space' else 200e-9*u**4/(u**4+(1-u)**4)
    y=np.linspace(0.,100e-9,ny);nz=8*2**level+1
    material=mos2_sheet(reference_eV=-.9) if contact=='thermionic' else graphene_sheet()
    options=dict(thermionic_barrier_n_eV=.12) if contact=='thermionic' else dict(contact_resistance_ohm_m=.003)
    return DielectricSheetDriftDiffusion(x,y,10e-9*np.linspace(-1.,1.,nz),material,
        sheet_index=(nz-1)//2,permittivity_F_m=5*8.8541878128e-12,
        contact_z_bounds_m=CONTACT_BOUNDS_M,mobility_n_m2_Vs=.02,
        mobility_p_m2_Vs=.01,transport_scheme='diffusion_enhanced',**options)


def row_for(sim,model,result,old,dt,phase):
    row=protocol.row_for(sim,model,True,result,old,dt,phase)
    row['contact_z_bounds_m']=sim.dielectric.contact_z_bounds_m
    return row


def scalar_state(result):
    out=protocol.scalar_state(result)
    out.update(sheet_contact_charge_C=result['sheet_contact_charge_C'],
        dielectric_contact_charge_C=result['dielectric_contact_charge_C'],
        dielectric_energy_J=result['dielectric_energy_J'])
    return out


@lru_cache(maxsize=None)
def trajectory(contact,dielectric,level,count,mesh_family='time'):
    path=os.environ.get('TCAD_ELECTRODE_CONVERGENCE_RECORDS')
    if path:
        key=(contact,dielectric,level,count,mesh_family)
        records=load_records(path)
        if key not in records:raise ValueError('missing frozen finite electrode trajectory')
        return records[key]
    if count not in TIME_COUNTS:raise ValueError('unknown steps per phase')
    sim=device(contact,dielectric,level,mesh_family);model=coefficients(sim)
    run=SheetTransient(sim,initial_drive=drive(sim,True,0),traps=model,
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
    dt=PHASE_S/count
    checkpoints=[row_for(sim,model,run.state,None,None,0)]
    trace=[scalar_state(run.state)]
    for phase in (1,2,3):
        for step in range(count):
            old=run.state
            result=run.step(dt_s=dt,**drive(sim,True,phase),tolerance=1e-12,max_iter=120)
            assert result['accepted'] and result['converged']
            state=scalar_state(result)
            state.update(phase=phase,dt_s=dt,
                conduction=result['terminal_currents_into_sheet_A'],total=result['terminal_total_currents_A'],
                trap_charge_rate_A=result['trap_charge_rate_A'],free_carrier_charge_rate_A=result['free_carrier_charge_rate_A'])
            trace.append(state)
        checkpoints.append(row_for(sim,model,result,old,dt,phase))
    return dict(boundary=BOUNDARY,contact_z_bounds_m=CONTACT_BOUNDS_M,contact=contact,dielectric=True,
        level=level,steps_per_phase=count,mesh_family=mesh_family,phase_s=PHASE_S,
        checkpoints=checkpoints,trace=trace)


@lru_cache(maxsize=None)
def load_records(path):
    records={}
    with open(path,encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            key=(row['contact'],row['dielectric'],row['level'],row['steps_per_phase'],row['mesh_family'])
            if key in records:raise ValueError('duplicate finite electrode trajectory')
            if row.get('boundary')!=BOUNDARY or row.get('contact_z_bounds_m')!=[list(b) for b in CONTACT_BOUNDS_M]:
                raise ValueError('wrong finite electrode geometry identity')
            if row['phase_s']!=PHASE_S or len(row['checkpoints'])!=4 or len(row['trace'])!=3*key[3]+1:
                raise ValueError('inconsistent finite electrode trajectory')
            for checkpoint in row['checkpoints']:
                for obj in (checkpoint,checkpoint['result']):
                    if obj.get('contact_z_bounds_m')!=row['contact_z_bounds_m']:
                        raise ValueError('checkpoint finite electrode geometry differs')
            records[key]=row
    return records


def observables(record):
    result=protocol.observables(record);stride=2**(record['level']-1)
    for phase,row in enumerate(record['checkpoints']):
        state=row['result']
        result[f'{phase}_dielectric_phi_V']=np.asarray(state['dielectric_phi_V'])[::stride,::stride,::stride].ravel()/protocol.FIELD_SCALE_V
        for key in ('contact_charge_C','sheet_contact_charge_C','dielectric_contact_charge_C'):
            result[f'{phase}_{key}']=np.array([state[key][p] for p in ('source','drain')])/protocol.CHARGE_SCALE_C
        result[f'{phase}_gate_charges']=np.array([state[p+'_charge_C'] for p in ('bottom_gate','top_gate')])/protocol.CHARGE_SCALE_C
        result[f'{phase}_dielectric_energy_J']=np.array([state['dielectric_energy_J']])/(protocol.CHARGE_SCALE_C*protocol.FIELD_SCALE_V)
    return result


def differences(records):
    vectors=[observables(record) for record in records];out={}
    for key in vectors[0]:
        delta=[float(np.max(abs(b[key]-a[key]))) for a,b in zip(vectors,vectors[1:])]
        ratios=[b/a for a,b in zip(delta,delta[1:]) if a>1e-8]
        out[key]=dict(differences=delta,ratios=ratios)
    return out


@pytest.mark.parametrize('contact,dielectric',CASES)
def test_fixed_electrode_geometry_and_coefficients_at_nested_nodes(contact,dielectric):
    for family in ('time','space'):
        sims=[device(contact,dielectric,level,family) for level in ((1,) if family=='time' else SPACE_LEVELS)]
        base=sims[0]
        for index,sim in enumerate(sims):
            stride=2**index
            for axis in ('x','y'):
                np.testing.assert_array_equal(getattr(base,axis),getattr(sim,axis)[::stride])
            np.testing.assert_array_equal(base.dielectric.z,sim.dielectric.z[::stride])
            np.testing.assert_allclose(sim.dielectric.contact_z_bounds_m,CONTACT_BOUNDS_M,rtol=0.,atol=1e-23)
            a=asdict(coefficients(base));b=asdict(coefficients(sim))
            for key in ('density_m2','energy_offset_eV','degeneracy'):
                np.testing.assert_allclose(a[key],np.asarray(b[key])[::stride,::stride],rtol=2e-15,atol=0.)
            for phase in range(4):
                np.testing.assert_array_equal(drive(base,True,phase)['top_gate_voltage_V'],drive(sim,True,phase)['top_gate_voltage_V'][::stride,::stride])


@pytest.mark.parametrize('contact,dielectric',CASES)
@pytest.mark.parametrize('direction',('time','space'))
def test_finite_electrode_full_pulse_observables_converge(contact,dielectric,direction):
    records=[trajectory(contact,dielectric,1,n) for n in TIME_COUNTS] if direction=='time' else [trajectory(contact,dielectric,l,128,'space') for l in SPACE_LEVELS]
    for key,metric in differences(records).items():
        assert metric['differences'][-1]<protocol.DIFFERENCE_LIMIT,(contact,direction,key,metric)
        assert all(r<protocol.RATIO_LIMIT for r in metric['ratios']),(contact,direction,key,metric)


@pytest.mark.parametrize('fault',('duplicate','missing_boundary','wrong_range','bad_phase'))
def test_finite_electrode_cache_rejects_wrong_geometry(tmp_path,fault):
    bounds=[list(b) for b in CONTACT_BOUNDS_M]
    row=dict(boundary=BOUNDARY,contact_z_bounds_m=bounds,contact='linear',dielectric=True,level=1,
        steps_per_phase=32,mesh_family='time',phase_s=PHASE_S,
        checkpoints=[dict(contact_z_bounds_m=bounds,result=dict(contact_z_bounds_m=bounds))]*4,trace=[{}]*97)
    if fault=='missing_boundary':row.pop('boundary')
    elif fault=='wrong_range':row['contact_z_bounds_m']=[[0.,0.],[0.,0.]]
    elif fault=='bad_phase':row['phase_s']*=2
    path=tmp_path/'invalid.jsonl'
    path.write_text((json.dumps(row)+'\n')*(2 if fault=='duplicate' else 1),encoding='utf-8')
    with pytest.raises(ValueError):load_records(str(path))
