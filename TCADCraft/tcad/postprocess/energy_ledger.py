"""Explicit scoped energy-component auditing for transient histories.

The native transient result deliberately exposes several ledgers with
different physical domains.  This module composes those ledgers without
promoting their union to a full device energy balance.  Missing components
are reported as unavailable rather than silently treated as zero.
"""

from collections.abc import Mapping

import numpy as np

from .lk_energy import audit_transient_lk_energy
from .terminal_trace import (
    audit_transient_dielectric_energy,
    integrate_transient_terminal_history,
    _real_scalar, _finite_sum,
    _validated_dielectric_storage, _dielectric_storage_consistency,
)


def _bool_flag(state, name):
    value = state.get(name)
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f"energy ledger requires explicit boolean {name}")
    return bool(value)


def _audit_dielectric_storage_only(history, *, rtol, atol_J):
    """Validate dielectric snapshots when terminal current is unavailable."""
    energies, increments = _validated_dielectric_storage(history)
    residuals, error = _dielectric_storage_consistency(energies, increments, atol_J=atol_J)
    return {
        "valid": bool(error <= rtol), "energy_balance_validated": False,
        "storage_consistency_validated": bool(error <= rtol),
        "physical_validated": False,
        "energy_balance_scope": "linear_lossless_charge_free_dielectric_storage_only",
        "energy_initial_J": energies[0], "energy_final_J": energies[-1],
        "stored_energy_change_J": _finite_sum(increments),
        "dissipated_energy_J": 0.,
        "energy_balance_residual_J": None,
        "interval_energy_balance_residuals_J": None,
        "interval_storage_consistency_residuals_J": residuals,
        "max_storage_relative_residual": error,
        "rtol": rtol, "atol_J": atol_J,
    }


def audit_transient_energy_ledger(history, *, rtol=1e-8, atol_J=0.,
                                  require_source_work=False):
    """Audit the native transient energy components with explicit scope.

    ``history`` may contain the native linear-dielectric ledger, the native
    local LK ledger, and terminal currents.  Every component must be present
    on every snapshot when enabled; a partial history is rejected.  The
    returned report exposes component reports and terminal source work, while
    ``energy_balance_validated`` is true only for the limited linear-lossless
    dielectric closure.  LK and terminal source work remain scoped evidence;
    this function never claims full device energy conservation, thermal,
    trap, quantum, domain-wall, or carrier dissipation closure.

    Entirely unavailable source current data is allowed unless
    ``require_source_work`` is true. Declared available but malformed source
    data always raises. Initial snapshots must have no current interval;
    accepted endpoints must all provide one or all declare it unavailable.
    A storage-only check validates snapshot/increment consistency, without
    establishing source-work closure or increments below snapshot resolution.
    Linear-dielectric and LK scopes are mutually exclusive in native results.
    """
    rtol = _real_scalar(rtol, "rtol", positive=True)
    atol_J = _real_scalar(atol_J, "atol_J")
    if rtol >= 1. or atol_J < 0.:
        raise ValueError("require 0 < rtol < 1 and nonnegative atol_J")
    if not isinstance(require_source_work, (bool, np.bool_)):
        raise ValueError("require_source_work must be an explicit boolean")
    if not isinstance(history, (list, tuple)) or len(history) < 2:
        raise ValueError("energy ledger requires an initial state and intervals")
    if any(not isinstance(state, Mapping) for state in history):
        raise ValueError("energy ledger history entries must be mappings")

    dielectric = [_bool_flag(state, "dielectric_energy_available") for state in history]
    lk = [_bool_flag(state, "lk_energy_available") for state in history]
    if any(dielectric) and not all(dielectric):
        raise ValueError("dielectric energy availability must be consistent across history")
    if any(lk) and not all(lk):
        raise ValueError("LK energy availability must be consistent across history")
    if not any(dielectric) and not any(lk):
        raise ValueError("native energy component scope is unavailable")
    if all(dielectric) and all(lk):
        raise ValueError("native dielectric and LK energy scopes are mutually exclusive")

    total_current_flags = [_bool_flag(state, "total_terminal_current_available")
                           for state in history]
    accepted_current = (not total_current_flags[0]
                        and all(total_current_flags[1:]))
    if any(total_current_flags) and not accepted_current:
        raise ValueError("terminal current availability requires no initial interval and every accepted interval")
    if require_source_work and not accepted_current:
        raise ValueError("native terminal source work is unavailable")
    reports = {}
    if all(dielectric):
        if accepted_current:
            reports["dielectric"] = audit_transient_dielectric_energy(
                history, rtol=rtol, atol_J=atol_J)
        else:
            reports["dielectric"] = _audit_dielectric_storage_only(
                history, rtol=rtol, atol_J=atol_J)
    if all(lk):
        reports["lk"] = audit_transient_lk_energy(
            history, rtol=rtol, atol_J=atol_J)

    source_work = None
    if accepted_current:
        source_work = integrate_transient_terminal_history(
            history, current_kind="total", voltage_quadrature="linear")

    component_valid = all(report["valid"] for report in reports.values())
    dielectric_closure = (
        "dielectric" in reports and reports["dielectric"]["energy_balance_validated"]
        and "lk" not in reports
    )
    # A source-work trace is useful evidence, but does not turn a local LK
    # ledger into total stored/dissipated device energy.
    return {
        "valid": bool(component_valid),
        "energy_balance_validated": bool(dielectric_closure),
        "energy_balance_scope": (
            reports["dielectric"]["energy_balance_scope"]
            if "dielectric" in reports and accepted_current else None
        ),
        "physical_validated": False,
        "energy_scope": "scoped_native_component_energy_ledger",
        "complete_device_energy": False,
        "component_presence": {
            "dielectric": bool(all(dielectric)),
            "lk": bool(all(lk)),
            "terminal_source_work": bool(accepted_current),
        },
        "component_reports": reports,
        "terminal_source_work": source_work,
        "terminal_source_work_error": None,
        "missing_physics": [
            "carrier_dissipation", "traps", "thermal", "quantum",
            "ferroelectric_gradient_or_domain", "cut_cell_geometry",
        ],
        "rtol": rtol,
        "atol_J": atol_J,
    }

