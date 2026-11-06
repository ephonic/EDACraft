"""Frozen stage512 protocol, public coupled backend; level4 is a short probe."""
from pathlib import Path
import json, resource, sys, time
import numpy as np
import sheet_electrode_convergence as b
from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
contact, family, level, count, mode, out = sys.argv[1:]
level = int(level)
count = int(count)
start = time.monotonic()
nx = (8 if family == 'space' else 4) * 2 ** level + 1
ny = (1 if family == 'space' else 2) * 2 ** level + 1
nz = 8 * 2 ** level + 1
u = np.linspace(0.0, 1.0, nx)
x = 1e-07 * (1 - np.cos(np.pi * u)) if family == 'space' else 2e-07 * u ** 4 / (u ** 4 + (1 - u) ** 4)
y = np.linspace(0.0, 1e-07, ny)
z = 1e-08 * np.linspace(-1.0, 1.0, nz)

def persist_fields(row, phase):
    arrays = {}

    def encode(v):
        if isinstance(v, np.ndarray):
            k = 'a' + str(len(arrays))
            arrays[k] = v
            return {'__ndarray__': k}
        if isinstance(v, np.generic):
            return v.item()
        if isinstance(v, dict):
            return {k: encode(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [encode(x) for x in v]
        return v
    meta = encode(row)
    stem = out + '.checkpoint_' + str(phase)
    with Path(stem + '.npz.tmp').open('wb') as f:
        np.savez_compressed(f, **arrays)
    Path(stem + '.json.tmp').write_text(json.dumps(meta, allow_nan=False))
    Path(stem + '.npz.tmp').replace(stem + '.npz')
    Path(stem + '.json.tmp').replace(stem + '.json')
z = np.load(Path(__file__).parent / 'meshes.npz', allow_pickle=False)['z_m_level2']
nz = len(z)
x = np.load(Path(__file__).parent / 'meshes.npz', allow_pickle=False)['x_m']
nx = len(x)
y = np.load(Path(__file__).parent / 'meshes.npz', allow_pickle=False)['y_m']
ny = len(y)
material = mos2_sheet(reference_eV=-0.9) if contact == 'thermionic' else graphene_sheet()
options = dict(thermionic_barrier_n_eV=0.12) if contact == 'thermionic' else dict(contact_resistance_ohm_m=0.003)
sim = DielectricSheetDriftDiffusion(x, y, z, material, sheet_index=(nz - 1) // 2, permittivity_F_m=5 * 8.8541878128e-12, contact_z_bounds_m=b.CONTACT_BOUNDS_M, mobility_n_m2_Vs=0.02, mobility_p_m2_Vs=0.01, transport_scheme='diffusion_enhanced', electrostatic_backend='coupled', linear_solver='reused_gmres', **options, linear_ordering='MMD_AT_PLUS_A')
model = b.coefficients(sim)
run = SheetTransient(sim, initial_drive=b.drive(sim, True, 0), traps=model, initial_occupancy='equilibrium', tolerance=1e-12, max_iter=120)
solver_records = [run.state['linear_solver_diagnostics']]
dt = b.PHASE_S / count
checkpoints = [b.row_for(sim, model, run.state, None, None, 0)]
persist_fields(checkpoints[-1], 0)
assert run.clear_linear_cache()
trace = [b.scalar_state(run.state)]
maxnorm = run.state['residual_scaled_linf']
iterations = run.state['iterations']
for phase in (1, 2, 3) if mode == 'full' else (1,):
    for step in range(count if mode == 'full' else 1):
        old = run.state
        result = run.step(dt_s=dt, **b.drive(sim, True, phase), tolerance=1e-12, max_iter=120)
        assert result['accepted'] and result['converged'] and (result['electrostatic_backend'] == 'coupled')
        solver_records.append(result['linear_solver_diagnostics'])
        with Path(out + '.accepted_linear.jsonl').open('a') as f:
            f.write(json.dumps(dict(step=len(solver_records) - 1, diagnostics=solver_records[-1]), allow_nan=False) + '\n')
        with Path(out + '.progress.jsonl').open('a') as progress:
            progress.write(json.dumps(dict(phase=phase, step=step + 1, time_s=result['time_s'], residual_scaled_linf=result['residual_scaled_linf'], linear_solves=result['linear_solver_diagnostics']['linear_solves'], factorizations=result['linear_solver_diagnostics']['factorizations'])) + '\n')
        maxnorm = max(maxnorm, result['residual_scaled_linf'])
        iterations += result['iterations']
        state = b.scalar_state(result)
        state.update(phase=phase, dt_s=dt, conduction=result['terminal_currents_into_sheet_A'], total=result['terminal_total_currents_A'], trap_charge_rate_A=result['trap_charge_rate_A'], free_carrier_charge_rate_A=result['free_carrier_charge_rate_A'])
        trace.append(state)
    checkpoints.append(b.row_for(sim, model, result, old, dt, phase))
    persist_fields(checkpoints[-1], phase)
record = dict(boundary=b.BOUNDARY, contact_z_bounds_m=b.CONTACT_BOUNDS_M, contact=contact, dielectric=True, level=level, steps_per_phase=count, mesh_family=family, phase_s=b.PHASE_S, checkpoints=checkpoints, trace=trace)
Path(out + '.linear.json').write_text(json.dumps(solver_records, allow_nan=False))
arrays = {}

def encode(v):
    if isinstance(v, np.ndarray):
        k = 'a' + str(len(arrays))
        arrays[k] = v
        return {'__ndarray__': k}
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, dict):
        return {k: encode(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)):
        return [encode(x) for x in v]
    return v
meta = encode(record)
np.savez_compressed(out + '.npz', **arrays)
Path(out + '.json').write_text(json.dumps(meta, allow_nan=False))
print(json.dumps(dict(mode=mode, contact=contact, family=family, level=level, count=count, checkpoints=len(checkpoints), dynamic_steps=len(trace) - 1, sheet_nodes=sim.size, total_nodes=nx * ny * nz, seconds=time.monotonic() - start, peak_rss_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, max_residual_scaled_linf=maxnorm, total_newton_iterations=iterations)), flush=True)
