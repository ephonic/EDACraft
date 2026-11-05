"""Storage consistency and independent, explicitly scoped device energy audits."""
from collections.abc import Mapping
import math

import numpy as np


DEFAULT_COMPONENTS = ("carrier", "trap", "thermal", "quantum")
SOLVER_COMPONENTS = (*DEFAULT_COMPONENTS, "electrostatic")


def _scalar(value, name):
    arr = np.asarray(value)
    if arr.ndim != 0 or arr.dtype.kind not in "iuf" or not np.isfinite(arr):
        raise ValueError(f"{name} must be one finite real scalar")
    result = float(arr)
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds supported scalar range")
    return result


def _sum(values, name):
    try:
        return _scalar(math.fsum(values), name)
    except OverflowError as exc:
        raise ValueError(f"{name} exceeds supported scalar range") from exc


def _mapping(state, key, components):
    value = state.get(key)
    if not isinstance(value, Mapping) or set(value) != set(components):
        raise ValueError(f"{key} must contain exactly {tuple(components)!r}")
    return {name: _scalar(value[name], f"{key}.{name}") for name in components}


def audit_complete_device_energy(history, *, components=DEFAULT_COMPONENTS,
                                 rtol=1e-8, atol_J=0.0):
    """Check storage increments; the legacy name does not imply physical closure.

    Every endpoint supplies ``energy_storage_J`` and, after the initial state,
    ``interval_net_energy_J``. These numbers alone cannot establish source work
    or boundary fluxes. Use :func:`audit_solver_device_energy` with actual model
    states for an independent balance of the supported equations.

    Relative budgets use each component's increment in each interval, in J.
    Two storage ULPs allow subtraction roundoff, independently of the physical
    budget. No unit-sized floor or unrelated channel can enlarge a tolerance.
    """
    if not isinstance(components, (tuple, list)) or not components:
        raise ValueError("components must be a nonempty sequence")
    components = tuple(components)
    if any(not isinstance(c, str) or not c for c in components) or len(set(components)) != len(components):
        raise ValueError("components must contain unique nonempty names")
    rtol = _scalar(rtol, "rtol")
    atol_J = _scalar(atol_J, "atol_J")
    if not 0.0 < rtol < 1.0 or atol_J < 0.0:
        raise ValueError("require 0 < rtol < 1 and nonnegative atol_J")
    if not isinstance(history, (list, tuple)) or len(history) < 2:
        raise ValueError("energy history requires an initial state and intervals")
    if any(not isinstance(state, Mapping) for state in history):
        raise ValueError("energy snapshots must be mappings")
    storage = [_mapping(state, "energy_storage_J", components) for state in history]
    if "interval_net_energy_J" in history[0]:
        raise ValueError("initial snapshot cannot carry interval energy")
    intervals = [_mapping(state, "interval_net_energy_J", components) for state in history[1:]]
    residuals, tolerances, roundoffs = [], [], []
    valid = True
    for previous, current, net in zip(storage, storage[1:], intervals):
        row, limits, rounding = {}, {}, {}
        for name in components:
            delta = _sum((current[name], -previous[name]), "storage difference")
            row[name] = _sum((delta, -net[name]), "component residual")
            rounding[name] = 2 * max(math.ulp(previous[name]), math.ulp(current[name]))
            limits[name] = _sum((atol_J, rtol * max(abs(delta), abs(net[name])),
                                 rounding[name]), "component tolerance")
            valid = valid and abs(row[name]) <= limits[name]
        row["total"] = _sum(row.values(), "total residual")
        limits["total"] = _sum(limits.values(), "total tolerance")
        valid = valid and abs(row["total"]) <= limits["total"]
        residuals.append(row)
        tolerances.append(limits)
        roundoffs.append(rounding)
    return {
        "valid": bool(valid),
        "storage_consistency_validated": bool(valid),
        "energy_balance_validated": False,
        "complete_device_energy": False,
        "physical_validated": False,
        "energy_scope": "storage_increment_consistency_only",
        "components": list(components),
        "component_presence": {name: True for name in components},
        "initial_storage_J": storage[0],
        "final_storage_J": storage[-1],
        "interval_residuals_J": residuals,
        "interval_tolerances_J": tolerances,
        "interval_roundoff_allowance_J": roundoffs,
        "max_component_residual_J": max(abs(row[n]) for row in residuals for n in components),
        "max_total_residual_J": max(abs(row["total"]) for row in residuals),
        # Compatibility summary only; acceptance uses the individual limits.
        "tolerance_J": max(row[n] for row in tolerances for n in components),
        "rtol": rtol,
        "atol_J": atol_J,
        "missing_physics": ["independent state and boundary energy balance",
                            "spatially resolved constitutive calibration",
                            "commercial carrier heat-flux semantics"],
    }


def solver_energy_history(report, *, include_electrostatic=True):
    """Adapt Python cut-cell storage fields, without asserting port balance."""
    if not isinstance(include_electrostatic, bool):
        raise ValueError("include_electrostatic must be bool")
    if not isinstance(report, Mapping):
        raise ValueError("solver energy report must be a mapping")
    names = SOLVER_COMPONENTS if include_electrostatic else DEFAULT_COMPONENTS
    values = []
    for key in ("energy_before_J", "energy_after_J", "energy_increments_J"):
        mapping = report.get(key)
        if not isinstance(mapping, Mapping):
            raise ValueError(f"solver energy report requires mapping {key}")
        values.append({name: _scalar(mapping.get(name + "_J"), key + "." + name + "_J") for name in names})
    return [{"energy_storage_J": values[0]},
            {"energy_storage_J": values[1], "interval_net_energy_J": values[2]}]


def audit_solver_device_energy(model, old, new, report, *, charge_atol_C,
                               particle_atol, energy_atol_J, rtol=1e-8,
                               particle_flux_atol_s=None, energy_flux_atol_W=None,
                               entropy_atol_W_K=None):
    """Recompute state, constitutive and boundary balances for Python cut cells.

    Covers the equations supported by the existing cut-cell, electrothermal,
    mimetic and thermionic auditors. It does not certify complete device
    physics, commercial agreement, or the C++ backend. Thermionic interfaces
    require explicit moment and entropy budgets; they never silently fall back
    to the bulk audit. No report validity flag is used as evidence of closure.
    """
    from tcad.solver.cut_cell_transport import CutCellTransport
    from tcad.solver.thermionic_electrothermal import ThermionicElectrothermalCutCellTransport
    from .cut_cell_energy import audit_cut_cell_energy
    from .thermionic_electrothermal import audit_thermionic_electrothermal

    if not isinstance(model, CutCellTransport):
        raise ValueError("supported Python cut-cell transport model required")
    budgets = dict(charge_atol_C=charge_atol_C, particle_atol=particle_atol, energy_atol_J=energy_atol_J)
    for name, value in budgets.items():
        budgets[name] = _scalar(value, name)
        if budgets[name] <= 0:
            raise ValueError(f"{name} must be positive")
    history = solver_energy_history(report)
    storage = audit_complete_device_energy(history, components=SOLVER_COMPONENTS,
                                          rtol=rtol, atol_J=budgets['energy_atol_J'])
    moment = dict(particle_flux_atol_s=particle_flux_atol_s, energy_flux_atol_W=energy_flux_atol_W,
                  entropy_atol_W_K=entropy_atol_W_K)
    if isinstance(model, ThermionicElectrothermalCutCellTransport):
        for name, value in moment.items():
            moment[name] = _scalar(value, name)
            if moment[name] <= 0:
                raise ValueError(f"{name} must be positive")
        independent = audit_thermionic_electrothermal(model, old, new, report, **budgets, **moment)
    else:
        if any(value is not None for value in moment.values()):
            raise ValueError("interface budgets require a thermionic model")
        independent = audit_cut_cell_energy(model, old, new, report, **budgets)
    errors = {}
    snapshots_valid = True
    for key, state, snapshot in zip(('energy_before_J', 'energy_after_J'), (old, new), history):
        expected, _ = model.energies(state, charge_atol_C=budgets['charge_atol_C'])
        errors[key] = {}
        for name in SOLVER_COMPONENTS:
            value = _scalar(expected[name + '_J'], 'recomputed ' + name)
            given = snapshot['energy_storage_J'][name]
            error = _sum((given, -value), 'snapshot error')
            errors[key][name + '_J'] = error
            snapshots_valid = snapshots_valid and abs(error) <= budgets['energy_atol_J']
    valid = bool(storage['valid'] and independent['valid'] and snapshots_valid)
    return dict(valid=valid, energy_balance_validated=valid,
                modeled_energy_balance_validated=valid, complete_device_energy=False,
                physical_validated=False, backend='python_cut_cell',
                energy_scope='independent_supported_cut_cell_equations',
                storage_audit=storage, independent_audit=independent,
                snapshot_errors_J=errors, snapshots_valid=bool(snapshots_valid),
                missing_physics=['complete device physics and material calibration',
                                 'commercial carrier heat-flux semantics',
                                 'C++ backend energy balance'])
