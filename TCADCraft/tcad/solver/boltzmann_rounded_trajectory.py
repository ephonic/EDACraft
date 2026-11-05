"""Bounded-memory native rounded trajectories with replayable JSONL evidence."""
from dataclasses import asdict
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_accounted_rounding import advance_mb_rounded_conducting_split
from tcad.postprocess.boltzmann_rounded_trajectory import (
    trajectory_contract,maintained_faces,canonical_bytes,record_digest,audit_mb_rounded_trajectory,
)


def advance_mb_rounded_trajectory(configurations,states,faces,thermal_faces,dt_s,steps,*,
                                  impulses_J=None,particle_atol=1e-9,energy_atol_J=1e-27,
                                  record_sink=None,checkpoint_stride=64):
    states=tuple(states);configurations=tuple(configurations);faces=tuple(faces);thermal_faces=tuple(thermal_faces)
    if any(type(s) is not MBScaledTransportState for s in states):raise ValueError('typed trajectory states required')
    if record_sink is not None and not callable(record_sink):raise ValueError('callable immutable-byte journal sink required')
    contract=trajectory_contract(configurations,states,faces,thermal_faces,dt_s,steps,impulses_J=impulses_J,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J)
    if record_sink is not None:record_sink(canonical_bytes(dict(contract=contract,contract_sha256=record_digest(contract)))+b'\n')
    current=states
    def records():
        nonlocal current
        previous=record_digest(contract)
        for index in range(steps):
            fs=maintained_faces(contract,list(map(asdict,current)))
            fs=[{**f,'reservoir':MBScaledTransportState(**f['reservoir'])} if 'reservoir' in f else f for f in fs]
            new,report=advance_mb_rounded_conducting_split(contract['configurations'],current,fs,contract['thermal_faces'],
                contract['dt_s'],impulses_J=contract['impulses_J'],particle_atol=1e-9,energy_atol_J=1e-27)
            payload=dict(index=index,previous_sha256=previous,new=list(map(asdict,new)),report=report)
            row={**payload,'sha256':record_digest(payload)}
            if record_sink is not None:record_sink(canonical_bytes(row)+b'\n')
            current=new;previous=row['sha256'];yield row
    check=audit_mb_rounded_trajectory(contract,records(),checkpoint_stride=checkpoint_stride)
    return current,dict(scope='native_streamed_rounded_trajectory',contract=contract,independent_audit=check,
        accepted_steps=steps,journal_complete=True,rounding_error_included=True,
        exact_recurrence_preserved=False,complete_device_energy=False,physical_validated=False)
