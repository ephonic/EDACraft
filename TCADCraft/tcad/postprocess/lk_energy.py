"""Local LK kinetic checks; no total electrical device energy closure."""
from collections.abc import Mapping
import math

import numpy as np

from .terminal_trace import _real_array, _real_scalar, _finite_sum, _scaled_product


def audit_transient_lk_energy(history, *, rtol=1e-8, atol_J=0.):
    """Audit native Landau increments, gamma loss and the signed BE correction.

    Free energy includes the configured imprint and optional extra quadratic
    depolarization term. Field work uses the actual kinetic drive: the
    pre-kinetic field for split solving, or the accepted final field for coupled
    LK. Coupled mode metadata requires that final field match. Geometric dual-node quadrature
    includes half-width boundary nodes and explicit singleton extrusion;
    zero-volume entries are outside the FE mask. No gradient/domain energy,
    thermal solve or cut-cell FE geometry is inferred. This local identity
    cannot validate device source work or total energy conservation.

    Missing/invalid inputs raise ValueError. Finite kinetic defects return
    valid=False. energy_balance_validated and physical_validated remain False.
    Incremental polynomial scales supply the same float64 export allowance
    for node, component and aggregate checks. Raw aggregate residuals and
    allowances are returned separately; a pass does not certify changes below
    the resolution of the exported coefficients and snapshots.
    """
    rtol = _real_scalar(rtol, "rtol", positive=True)
    atol_J = _real_scalar(atol_J, "atol_J")
    if rtol >= 1. or atol_J < 0.:
        raise ValueError("require 0 < rtol < 1 and nonnegative atol_J")
    if not isinstance(history, (list, tuple)) or len(history) < 2:
        raise ValueError("LK audit requires an initial state and accepted intervals")
    scope = "lk_local_backward_euler_nodal_quadrature"
    keys = ("lk_free_energy_increment_J", "lk_dissipation_J",
            "lk_field_work_J", "lk_be_correction_J")
    interval_keys = keys + ("lk_drive_field_V_per_m", "lk_polarization_increment_C_per_m2")
    totals = {key: [] for key in keys}
    residuals, errors, local_errors, consistency = [], [], [], []
    export_allowances, raw_errors = [], []
    accepted = True

    def flag(state, key, expected=True):
        value = state.get(key)
        if not isinstance(value, (bool, np.bool_)) or bool(value) != expected:
            raise ValueError(f"LK audit requires explicit {key}={expected}")

    def compare(actual, expected, scale=None, rounding=0.):
        nonlocal accepted
        difference = _finite_sum([actual, -expected])
        scale = max(abs(actual), abs(expected)) if scale is None else scale
        excess = max(abs(difference) - atol_J - rounding, 0.)
        error = excess / scale if scale else (math.inf if excess else 0.)
        accepted = accepted and error <= rtol
        return difference, error

    for index, state in enumerate(history):
        if not isinstance(state, Mapping) or state.get("lk_energy_scope") != scope:
            raise ValueError("native LK local energy scope is unavailable")
        for key in ("valid", "converged", "lk_energy_available"):
            flag(state, key)
        flag(state, "initial_state", not bool(index))
        flag(state, "lk_energy_increment_available", bool(index))
        coupled = state.get("lk_coupled", False)  # Histories predating this option are split.
        if not isinstance(coupled, (bool, np.bool_)):
            raise ValueError("lk_coupled must be an explicit boolean")
        material_field = state.get("lk_material_field", False)
        if not isinstance(material_field, (bool, np.bool_)) or (material_field and not coupled):
            raise ValueError("lk_material_field must be an explicit boolean and requires coupled LK")
        if not index:
            material_reference = bool(material_field)
        elif bool(material_field) != material_reference:
            raise ValueError("LK field discretization must be consistent across the history")
        substepping = state.get("lk_substepping", False)
        if not isinstance(substepping, (bool, np.bool_)):
            raise ValueError("lk_substepping must be an explicit boolean")
        step_limit = _real_scalar(state.get("lk_step_limit_s", 0.), "lk_step_limit_s")
        if ((substepping and (not coupled or step_limit <= 0.))
                or (not substepping and step_limit != 0.)):
            raise ValueError("LK substepping requires coupled mode and a positive step limit")
        if not index:
            coupled_reference = bool(coupled)
            substep_reference, limit_reference = bool(substepping), step_limit
        elif bool(coupled) != coupled_reference:
            raise ValueError("LK integration mode must be consistent across the history")
        elif bool(substepping) != substep_reference or step_limit != limit_reference:
            raise ValueError("LK substepping policy must be consistent across the history")
        time = _real_scalar(state.get("time_s"), "time_s")
        dt = _real_scalar(state.get("dt_s"), "dt_s")
        attempted = _real_scalar(state.get("attempted_time_s"), "attempted_time_s")
        params = _real_array(state.get("lk_parameters"), "lk_parameters")
        volume = _real_array(state.get("lk_node_volumes_m3"), "lk_node_volumes_m3")
        polarization = _real_array(state.get("P"), "P")
        energy = _real_scalar(state.get("lk_free_energy_J"), "lk_free_energy_J")
        if (params.shape != (6,) or params[1] <= 0 or params[2] <= 0
                or params[4] < 0 or params[5] not in (0., 1., 2.)
                or volume.ndim != 1 or not volume.size or np.any(volume < 0)
                or not np.any(volume > 0) or polarization.shape != (3*volume.size,)):
            raise ValueError("invalid LK parameters, nodal volumes or vector polarization")
        if not index:
            if time < 0. or dt != 0. or attempted != time or any(key in state for key in interval_keys):
                raise ValueError("LK initial state requires a nonnegative absolute clock without interval quantities")
            reference_params, reference_volume = params.copy(), volume.copy()
        elif (not np.array_equal(params, reference_params) or not np.array_equal(volume, reference_volume)
              or time <= previous_time or dt <= 0.
              or not np.isclose(dt, time-previous_time, rtol=1e-10, atol=0.) or attempted != time):
            raise ValueError("LK accepted clock, parameters and geometry must be consistent")
        alpha, beta, gamma, imprint, depol, axis = map(float, params)
        if index and substepping:
            if dt > step_limit * (1.+64*np.finfo(float).eps):
                raise ValueError("accepted LK interval exceeds the substep limit")
        axis = int(axis)
        # Same declared vacuum constant as native EPS0; no material fitting.
        depol_alpha = 0. if depol == 0. else 1. / (depol * 8.854187817e-12)
        if not math.isfinite(depol_alpha):
            raise ValueError("LK effective depolarization coefficient is unrepresentable")
        absolute_terms = []
        interval_terms = [[] for _ in keys]
        interval_rounding_scales = [[] for _ in keys]
        interval_local_errors = []
        if index:
            delta = _real_array(state.get(interval_keys[-1]), interval_keys[-1])
            field = _real_array(state.get(interval_keys[-2]), interval_keys[-2])
            if delta.shape != polarization.shape or field.shape != polarization.shape:
                raise ValueError("LK drive field and stable increments require three components per node")
            if coupled:
                final_components = [_real_array(state.get(key), key) for key in ("Ex", "Ey", "Ez")]
                if (any(values.shape != volume.shape for values in final_components)
                        or not np.array_equal(field, np.column_stack(final_components).ravel())):
                    raise ValueError("coupled LK drive field must equal the accepted final field")
            # Snapshot rounding may erase small deltas; native increments must
            # still agree where the two float64 snapshots resolve the change.
            for old, new, change in zip(previous_p, polarization, delta):
                rounding = 8*np.finfo(float).eps*max(abs(old), abs(new))
                if abs(math.fsum([float(new), -float(old), -float(change)])) > rounding:
                    raise ValueError("LK polarization increment disagrees with accepted snapshots")
        for node, v in enumerate(volume):
            if not v:
                if np.any(polarization[3*node:3*node+3] != 0.):
                    raise ValueError("polarization outside the LK mask must be zero")
                continue
            for c in range(3):
                a = alpha + (depol_alpha if c == axis else 0.)
                b = imprint if c == axis else 0.
                p = float(polarization[3*node+c])
                def product(*factors):
                    return _scaled_product((float(v), *factors))
                absolute_terms.extend((product(.5, a, p, p), product(.25, beta, p, p, p, p), product(b, p)))
                if not index:
                    continue
                d, e = float(delta[3*node+c]), float(field[3*node+c])
                df_terms = [product(a, p, d), product(-.5, a, d, d), product(b, d),
                    product(beta, p, p, p, d), product(-1.5, beta, p, p, d, d),
                    product(beta, p, d, d, d), product(-.25, beta, d, d, d, d)]
                df = _finite_sum(df_terms)
                loss = _scaled_product((float(v), gamma, d, d), (dt,))
                work = product(e, d)
                correction_terms = [product(.5, a, d, d), product(1.5, beta, p, p, d, d),
                                    product(-1., beta, p, d, d, d), product(.25, beta, d, d, d, d)]
                correction = _finite_sum(correction_terms)
                norms = (_finite_sum([abs(t) for t in df_terms]), loss, abs(work),
                         _finite_sum([abs(t) for t in correction_terms]))
                for scales, norm in zip(interval_rounding_scales, norms):
                    scales.append(norm)
                for terms, value in zip(interval_terms, (df, loss, work, correction)):
                    terms.append(value)
                _, error = compare(work, _finite_sum([df, loss, correction]),
                    max(abs(work), abs(df), loss, abs(correction)),
                    rounding=8*np.finfo(float).eps*_finite_sum(norms))
                interval_local_errors.append(error)
        ref_energy = _finite_sum(absolute_terms)
        energy_scale = _finite_sum([abs(term) for term in absolute_terms])
        compare(energy, ref_energy, energy_scale)
        if index:
            values = [_real_scalar(state.get(key), key) for key in keys]
            if values[1] < 0.:
                raise ValueError("LK gamma dissipation must be nonnegative")
            for key, value, terms, norms in zip(keys, values, interval_terms, interval_rounding_scales):
                totals[key].append(value)
                # Downcast fields can lose a nearly cancelling net work. The
                # allowance comes from incremental polynomial/work terms,
                # never from a large static free-energy background.
                compare(value, _finite_sum(terms),
                        rounding=8*np.finfo(float).eps*_finite_sum(norms))
            df, loss, work, correction = values
            # Use the same incremental polynomial export allowance as the
            # node and component checks. Near rest, quad increments can be
            # much smaller than the resolution of the exported P/coefficients;
            # testing their cancelling sum without this allowance contradicts
            # those checks. No static free-energy background enters this scale.
            export_rounding = 8*np.finfo(float).eps*_finite_sum(
                norm for group in interval_rounding_scales for norm in group)
            scale = max(abs(work), abs(df), loss, abs(correction))
            residual, error = compare(work, _finite_sum([df, loss, correction]),
                                      scale, rounding=export_rounding)
            residuals.append(residual); errors.append(error)
            export_allowances.append(export_rounding)
            raw_errors.append(abs(residual)/scale if scale else (math.inf if residual else 0.))
            local_errors.append(max(interval_local_errors, default=0.))
            difference, _ = compare(_finite_sum([energy, -previous_energy]), df,
                rounding=8*np.finfo(float).eps*max(previous_energy_scale, energy_scale))
            consistency.append(difference)
        previous_time, previous_p, previous_energy = time, polarization.copy(), energy
        previous_energy_scale = energy_scale
    return {
        "valid": bool(accepted), "lk_kinetics_validated": bool(accepted),
        "energy_balance_validated": False, "physical_validated": False,
        "energy_scope": scope, "duration_s": previous_time, "samples": len(history),
        "lk_coupled": coupled_reference,
        "lk_material_field": material_reference,
        "lk_substepping": substep_reference,
        "lk_step_limit_s": limit_reference,
        "free_energy_initial_J": float(history[0]["lk_free_energy_J"]),
        "free_energy_final_J": previous_energy,
        "free_energy_change_J": _finite_sum(totals[keys[0]]),
        "lk_dissipation_J": _finite_sum(totals[keys[1]]),
        "lk_field_work_J": _finite_sum(totals[keys[2]]),
        "be_discretization_correction_J": _finite_sum(totals[keys[3]]),
        "interval_kinetic_residuals_J": np.array(residuals),
        "interval_export_rounding_allowances_J": np.array(export_allowances),
        "interval_storage_consistency_residuals_J": np.array(consistency),
        "max_interval_relative_residual": max(errors),
        "max_interval_raw_relative_residual": max(raw_errors),
        "max_local_relative_residual": max(local_errors),
        "rtol": rtol, "atol_J": atol_J,
    }
