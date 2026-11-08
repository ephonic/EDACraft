"""Fixed physical pulse protocol; separate energy-trap time/space refinement.

These are numerical convergence checks for representative, uncalibrated models.
The read phase measures a driven transistor, not a nonvolatile memory window.
"""
from dataclasses import asdict
from functools import lru_cache
import itertools
import json
import os
import numpy as np
import pytest
from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_trap_balance import EnergySheetTrap
from tcad.solver.sheet_transient import SheetTransient

CASES=list(itertools.product(('linear','thermionic'),(False,True)))
TIME_COUNTS=(32,64,128,256)
SPACE_LEVELS=(1,2,3)
PHASE_S=20e-12
FIELD_SCALE_V=.025
CURRENT_SCALE_A=1e-7
CHARGE_SCALE_C=1e-18
RATIO_LIMIT=.7
DIFFERENCE_LIMIT=.01


def space_levels(contact,dielectric):
    # The zero-in-plane-permittivity local MoS2 case needs one more level
    # to resolve charge in the pinned contact control boxes. Retain every
    # coarser level and the original difference/order acceptance limits.
    return SPACE_LEVELS+(4,) if contact=='thermionic' and not dielectric else SPACE_LEVELS


def device(contact,dielectric,level,mesh_family='time'):
    if mesh_family not in ('time','space'):raise ValueError('unknown convergence mesh family')
    nx=(8 if mesh_family=='space' else 4)*2**level+1
    ny=(1 if mesh_family=='space' else 2)*2**level+1
    u=np.linspace(0.,1.,nx)
    # Nested contact refinement resolves the endpoint control volumes without
    # changing the physical density, gate profile, or zero in-plane permittivity.
    x=100e-9*(1-np.cos(np.pi*u)) if mesh_family=='space' else 200e-9*u**4/(u**4+(1-u)**4)
    y=np.linspace(0.,100e-9,ny)
    material=mos2_sheet(reference_eV=-.9) if contact=='thermionic' else graphene_sheet()
    common=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,transport_scheme='diffusion_enhanced')
    common.update(thermionic_barrier_n_eV=.12) if contact=='thermionic' else common.update(contact_resistance_ohm_m=.003)
    if dielectric:
        nz=8*2**level+1
        return DielectricSheetDriftDiffusion(x,y,np.linspace(-10e-9,10e-9,nz),material,
            sheet_index=(nz-1)//2,permittivity_F_m=5*8.8541878128e-12,**common)
    return SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.006,**common)


def coefficients(sim):
    yy,xx=np.meshgrid(sim.y/100e-9,sim.x/200e-9,indexing='ij')
    offset=sim.material.gap_eV/2-.04 if sim.material.dispersion=='parabolic' else .01
    return EnergySheetTrap(1e14*(1+.2*xx+.1*yy),2e-6,1e-6,
        offset+.003*(xx-yy),1.5+.3*yy,
        'donor' if sim.material.dispersion=='parabolic' else 'acceptor')


def drive(sim,dielectric,phase):
    yy,xx=np.meshgrid(sim.y/100e-9,sim.x/200e-9,indexing='ij')
    # Same smooth spatial gate and abrupt phase boundaries on every mesh.
    vg=.005+.002*np.cos(np.pi*xx)*np.cos(np.pi*yy)+(0.,.03,-.02,.01)[phase]
    gate=dict(top_gate_voltage_V=vg,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=vg)
    return dict(**gate,drain_voltage_V=0. if phase==0 else .003,source_voltage_V=0.)


def row_for(sim,model,dielectric,r,old,dt,phase):
    d=drive(sim,dielectric,phase)
    row=dict(contact='thermionic' if sim.thermionic_barrier_n_eV is not None else 'linear',
        material=asdict(sim.material),x_m=sim.x,y_m=sim.y,drain_V=d['drain_voltage_V'],source_V=0.,
        fermi_offset_eV=0.,doping_m2=sim.doping.reshape(sim.shape),fixed_charge_C_m2=sim.fixed_charge.reshape(sim.shape),
        sheet_permittivity_F=sim.epsilon,mobility_n_m2_Vs=sim.mu_n,mobility_p_m2_Vs=sim.mu_p,
        temperature_K=sim.temperature_K,traps=asdict(model),initial_occupancy='equilibrium',
        equilibrium_fermi_eV=0.,equilibrium_hold=False,result=r)
    if old is not None:row.update(previous=old,dt_s=dt)
    for k in ('contact_resistance_ohm_m','thermionic_barrier_n_eV'):
        if getattr(sim,k) is not None:row[k]=getattr(sim,k)
    if dielectric:
        row.update(z_m=sim.dielectric.z,sheet_index=sim.dielectric.sheet_index,
            permittivity_F_m=sim.dielectric.permittivity_F_m,top_gate_V=d['top_gate_voltage_V'],bottom_gate_V=np.zeros(sim.shape))
    else:row.update(capacitance_F_m2=sim.cap.reshape(sim.shape),gate_V=d['gate_voltage_V'])
    return row


def scalar_state(r):
    return dict(time_s=r['time_s'],sheet_charge_C=r['sheet_charge_C'],trap_charge_C=r['trap_charge_C'],
        untrapped_sheet_charge_C=r['untrapped_sheet_charge_C'],contact_charge_C=r['contact_charge_C'],
        gates={k:r[k+'_charge_C'] for k in ('top_gate','bottom_gate') if k+'_charge_C' in r}
        or {'gate':r['gate_charge_C']})


@lru_cache(maxsize=None)
def trajectory(contact,dielectric,level,count,mesh_family='time'):
    # Pytest may check the separately executed, frozen export instead of
    # solving identical trajectories twice. The exporter never sets this env.
    path=os.environ.get('TCAD_SHEET_CONVERGENCE_RECORDS')
    if path:
        records=load_records(path)
        key=(contact,dielectric,level,count,mesh_family)
        if key not in records:raise ValueError('missing frozen convergence trajectory')
        return records[key]
    sim=device(contact,dielectric,level,mesh_family);model=coefficients(sim)
    run=SheetTransient(sim,initial_drive=drive(sim,dielectric,0),traps=model,
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
    dt=PHASE_S/count;checkpoints=[row_for(sim,model,dielectric,run.state,None,None,0)]
    trace=[scalar_state(run.state)]
    for phase in (1,2,3):
        for k in range(count):
            old=run.state;r=run.step(dt_s=dt,**drive(sim,dielectric,phase),tolerance=1e-12,max_iter=120)
            assert r['accepted'] and r['converged']
            s=scalar_state(r);s.update(phase=phase,dt_s=dt,
                conduction=r['terminal_currents_into_sheet_A'],total=r['terminal_total_currents_A'],
                trap_charge_rate_A=r['trap_charge_rate_A'],free_carrier_charge_rate_A=r['free_carrier_charge_rate_A'])
            trace.append(s)
        checkpoints.append(row_for(sim,model,dielectric,r,old,dt,phase))
    return dict(contact=contact,dielectric=dielectric,level=level,steps_per_phase=count,mesh_family=mesh_family,
        phase_s=PHASE_S,checkpoints=checkpoints,trace=trace)


@lru_cache(maxsize=None)
def load_records(path):
    with open(path,encoding='utf-8') as stream:rows=[json.loads(line) for line in stream]
    result={}
    for row in rows:
        key=(row['contact'],row['dielectric'],row['level'],row['steps_per_phase'],row['mesh_family'])
        if key in result:raise ValueError('duplicate frozen convergence trajectory')
        if row['phase_s']!=PHASE_S or len(row['checkpoints'])!=4 or len(row['trace'])!=3*key[3]+1:
            raise ValueError('inconsistent frozen convergence trajectory')
        result[key]=row
    return result


def observables(record):
    level=record['level'];stride=2**(level-1)
    result={}
    for phase,row in enumerate(record['checkpoints']):
        r=row['result']
        for key in ('trap_occupancy','phi_V','Fn_eV','Fp_eV'):
            scale=1. if key=='trap_occupancy' else FIELD_SCALE_V
            result[f'{phase}_{key}']=np.asarray(r[key])[::stride,::stride].ravel()/scale
        for key in ('trap_charge_C','sheet_charge_C'):
            result[f'{phase}_{key}']=np.array([r[key]/CHARGE_SCALE_C])
        if phase:
            for key in ('terminal_currents_into_sheet_A','terminal_total_currents_A'):
                result[f'{phase}_{key}']=np.array([r[key][p] for p in sorted(r[key])])/CURRENT_SCALE_A
    return result


def differences(records):
    vectors=[observables(r) for r in records];names=list(vectors[0]);out={}
    for key in names:
        d=[float(np.max(abs(b[key]-a[key]))) for a,b in zip(vectors,vectors[1:])]
        # Negligible quantities must remain small; roundoff cannot define order.
        ratios=[b/a for a,b in zip(d,d[1:]) if a>1e-8]
        out[key]=dict(differences=d,ratios=ratios)
    return out


@pytest.mark.parametrize('contact,dielectric',CASES)
def test_physical_coefficients_and_gate_match_at_nested_nodes(contact,dielectric):
    for family in ('time','space'):
        levels=space_levels(contact,dielectric) if family=='space' else SPACE_LEVELS
        sims=[device(contact,dielectric,l,family) for l in levels]
        for level,sim in enumerate(sims[1:],1):
            a=asdict(coefficients(sims[0]));b=asdict(coefficients(sim))
            for k in ('density_m2','energy_offset_eV','degeneracy'):
                np.testing.assert_allclose(a[k],np.asarray(b[k])[::2**level,::2**level],rtol=2e-15,atol=0.)
            for phase in range(4):
                k='top_gate_voltage_V' if dielectric else 'gate_voltage_V'
                np.testing.assert_array_equal(drive(sims[0],dielectric,phase)[k],drive(sim,dielectric,phase)[k][::2**level,::2**level])


@pytest.mark.parametrize('contact,dielectric',CASES)
@pytest.mark.parametrize('direction',('time','space'))
def test_fixed_pulse_observables_converge(contact,dielectric,direction):
    records=[trajectory(contact,dielectric,1,n) for n in TIME_COUNTS] if direction=='time' else [trajectory(contact,dielectric,l,128,'space') for l in space_levels(contact,dielectric)]
    for key,metric in differences(records).items():
        assert metric['differences'][-1]<DIFFERENCE_LIMIT,(contact,dielectric,direction,key,metric)
        assert all(r<RATIO_LIMIT for r in metric['ratios']),(contact,dielectric,direction,key,metric)


@pytest.mark.parametrize('count',(8,16,32))
def test_reservoir_backward_euler_refinement_has_first_order_error(count):
    # Independent exact solution of constant-reservoir first-order kinetics.
    a=2e9;b=3e9;f0=.2;end=3/(a+b);eq=a/(a+b)
    exact=eq+(f0-eq)*np.exp(-(a+b)*end)
    errors=[]
    for n in (count,2*count):
        h=n/end;f=f0
        for _ in range(n):f=(h*f+a)/(h+a+b)
        errors.append(abs(f-exact))
    assert .45<errors[1]/errors[0]<.55


@pytest.mark.parametrize('duplicate',(False,True))
def test_frozen_trajectory_cache_rejects_invalid_evidence(tmp_path,duplicate):
    record=dict(contact='linear',dielectric=False,level=1,steps_per_phase=32,mesh_family='time',
        phase_s=PHASE_S,checkpoints=[{}]*4,trace=[{}]*97)
    path=tmp_path/'invalid.jsonl'
    if duplicate:path.write_text((json.dumps(record)+'\n')*2,encoding='utf-8')
    else:
        record['phase_s']*=2;path.write_text(json.dumps(record)+'\n',encoding='utf-8')
    with pytest.raises(ValueError):load_records(str(path))
