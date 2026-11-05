"""Explicit carrier steady state with a prescribed, clamped lattice profile.

This preparation solves Poisson, both particle equations and both carrier
energy equations. It returns a detached seed at the original clock; it does
not model the preparation history or conserve the initial carrier inventory.
The lattice clamp is an external power supply/sink, reported per cell.
"""
from copy import deepcopy
from dataclasses import replace
import numpy as np

from .cut_cell_transport import Q, _array
from .three_temperature import ThreeTemperatureElectrothermal, ThreeTemperatureState

SCOPE = 'fixed_band_source_free_lattice_clamped_FD_carrier_steady_state'


def _validate_configuration(model, state):
    if type(model) is not ThreeTemperatureElectrothermal:
        raise ValueError('unmodified ThreeTemperatureElectrothermal model required')
    model._validate_state(state)
    if (model.temperature_dependent_bands or model.trap_capture_law is not None
            or np.any(model.Nt != 0) or model.auger_events is not None
            or model.radiative_law is not None or np.any(model.pair_generation_rate_m3_s != 0)):
        raise ValueError('clamped initialization requires fixed bands without particle source channels')
    if not 1 <= model.nc <= 256:
        raise ValueError('1..256 cells required by the four-field dense Newton limit')
    # Each carrier needs a reservoir on every connected transport component.
    # A zero-emission internal face is a genuine disconnection, not an anchor.
    for species in ('electrons', 'holes'):
        adjacent = [set() for _ in range(model.nc)]
        for f in model.internal:
            if model.emission[species].get(int(f), 1.) > 0:
                face = model.mesh.faces[int(f)]
                adjacent[face.owner].add(face.neighbor)
                adjacent[face.neighbor].add(face.owner)
        anchored = {model.mesh.faces[int(f)].owner for f in model.contact_faces}
        remaining = set(range(model.nc))
        while remaining:
            component = set(); pending = [next(iter(remaining))]
            while pending:
                i = pending.pop()
                if i in component:
                    continue
                component.add(i); pending.extend(adjacent[i] - component)
            if not component & anchored:
                raise ValueError(species + ' transport component lacks a particle reservoir')
            remaining -= component


def prepare_lattice_clamped_state(model, initial, *, charge_atol_C,
                                  particle_flux_atol_s, energy_power_atol_W,
                                  current_atol_A, max_nfev=2000):
    """Return ``(seed, report)`` after an independent stationary audit.

    n, p, Te and Th are solved; Tl, trap fractions and time are held fixed.
    Python orchestrates existing native Poisson, DOS, spectral and local-row
    primitives and the native Newton driver. There is no automatic use by a
    transient session and no fallback on preparation failure.
    """
    for name, value in (('charge', charge_atol_C), ('particle flux', particle_flux_atol_s),
                        ('energy power', energy_power_atol_W), ('current', current_atol_A)):
        _array(value, 1, name, positive=True)
    if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)) or max_nfev < 1:
        raise ValueError('positive integer residual evaluation budget required')
    model = deepcopy(model); initial = replace(initial)
    _validate_configuration(model, initial)
    nc = model.nc; ld = np.longdouble; cache = {}; calls = 0
    origin = np.r_[np.log(initial.n_m3), np.log(initial.p_m3),
                   np.log(initial.electron_temperature_K), np.log(initial.hole_temperature_K)]
    lower = np.r_[np.full(2*nc, -600.), np.full(2*nc, 0.)] - origin
    upper = np.r_[np.full(2*nc, 600.), np.full(2*nc, np.log(1e5))] - origin

    def evaluate(x):
        nonlocal calls
        calls += 1
        x = np.asarray(x, float)
        n = initial.n_m3 * np.exp(x[:nc].astype(ld))
        p = initial.p_m3 * np.exp(x[nc:2*nc].astype(ld))
        tn = initial.electron_temperature_K * np.exp(x[2*nc:3*nc])
        tp = initial.hole_temperature_K * np.exp(x[3*nc:])
        state = ThreeTemperatureState(n, p, initial.trap_fraction, initial.temperature_K,
                                      initial.time_s, tn, tp)
        poisson = model._poisson(n, p, state.trap_fraction, charge_atol_C)
        if not poisson['valid']:
            raise ValueError('clamped preparation Poisson budget failed')
        rates, energies, records, reservoirs = model.split_face_transport(n, p, tn, tp, state.temperature_K, poisson)
        equilibrium = model.carrier_reservoirs(n, p, state.temperature_K, state.temperature_K)
        u = {s: np.array([r['energy_density_J_m3'] for r in rows], ld) for s, rows in reservoirs.items()}
        ue = {s: np.array([r['energy_density_J_m3'] for r in rows], ld) for s, rows in equilibrium.items()}
        from tcad.physics.native_three_temperature import native_three_temperature_local
        # Equal old/new states cancel every storage term. A one-second unit
        # interval converts the existing local assembler to rates; no clock is advanced.
        local = native_three_temperature_local(model, state, n, p, state.temperature_K,
            u, u, ue, poisson, poisson, rates, energies, 1., Tn=tn, Tp=tp)
        charge_rate = Q*np.sum(local['rp'].astype(ld)-local['rn'], dtype=ld)
        energy_rate = np.sum(local['energy_n'].astype(ld)+local['energy_p'], dtype=ld)
        merit = max(np.max(abs(local['rn']))/particle_flux_atol_s,
                    np.max(abs(local['rp']))/particle_flux_atol_s,
                    np.max(abs(local['energy_n']))/energy_power_atol_W,
                    np.max(abs(local['energy_p']))/energy_power_atol_W,
                    abs(charge_rate)/current_atol_A, abs(energy_rate)/energy_power_atol_W)
        cache.update(x=x.copy(), state=state, poisson=poisson, rates=rates,
                     energies=energies, records=records, local=local, merit=float(merit))
        # Fixed physical units make the residual scale independent of each
        # trial. Native Newton still stops on the absolute budgets above.
        return np.r_[local['rn']/particle_flux_atol_s, local['rp']/particle_flux_atol_s,
                     local['energy_n']/energy_power_atol_W, local['energy_p']/energy_power_atol_W], float(merit)

    from tcad.core._bindings import native_fermi_newton_raw
    solution, statistics, history = native_fermi_newton_raw(evaluate, np.zeros(4*nc),
        np.asarray(lower, float), np.asarray(upper, float), int(max_nfev))
    if (not np.array_equal(cache['x'], solution) or cache['merit'] > 1
            or calls != int(statistics[0]) or calls > max_nfev):
        raise ValueError('clamped preparation did not retain an accepted, budgeted iterate')
    local = cache['local']
    report = dict(scope=SCOPE, carrier_steady_state=True, lattice_temperature_clamped=True,
        lattice_energy_equation_solved=False, clock_advanced=False,
        complete_device_energy=False, physical_validated=False,
        residual_orchestration='python_with_native_primitives',
        residual_evaluations=calls, max_nfev=int(max_nfev), nonlinear_statistics=statistics,
        nonlinear_history=history, poisson=cache['poisson'],
        integrated_particle_flux_s=cache['rates'], integrated_carrier_energy_flux_W=cache['energies'],
        face_moments=cache['records'], cell_clamp_heat_input_W=local['energy_l'],
        cell_particle_residual_s=dict(electrons=local['rn'], holes=local['rp']),
        cell_carrier_energy_residual_W=dict(electrons=local['energy_n'], holes=local['energy_p']),
        bulk_potential_path=model.bulk_potential_path)
    from tcad.postprocess.three_temperature_initialization import audit_lattice_clamped_state
    audit = audit_lattice_clamped_state(model, initial, cache['state'], report,
        charge_atol_C=charge_atol_C, particle_flux_atol_s=particle_flux_atol_s,
        energy_power_atol_W=energy_power_atol_W, current_atol_A=current_atol_A)
    if not audit['valid']:
        raise ValueError('independent clamped preparation audit failed: ' + str(audit))
    report['independent_audit'] = audit
    return cache['state'], report
