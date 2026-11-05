"""Audit local polarization step-doubling estimates, not global accuracy."""
from collections.abc import Mapping
from decimal import Decimal, localcontext
import math

import numpy as np

from .terminal_trace import _real_array, _real_scalar


def audit_transient_lk_error_control(history, *, rtol=1e-8):
    """Recompute the native P estimator for every pair of accepted BE steps.

    A coarse trial is discarded; its final P and a stable fine-minus-coarse
    increment accompany the second accepted half step. Estimate per component
    is abs(delta)/(atol+rtol_native*max(abs(P_fine),abs(P_coarse))). Both half
    steps share the macro-interval estimate. This only audits local P control;
    it cannot bound global trajectory error, potential/carrier error, material
    fidelity or energy closure. Invalid inputs raise; finite defects return
    valid=False. No extrapolated state is inferred.
    """
    rtol = _real_scalar(rtol, "rtol", positive=True)
    if rtol >= 1. or not isinstance(history, (list, tuple)) or len(history) < 3 or len(history) % 2 != 1:
        raise ValueError("LK error audit requires initial state and complete half-step pairs, 0<rtol<1")
    scope = "lk_polarization_step_doubling_BE"
    coarse_key, delta_key = "lk_coarse_P_C_per_m2", "lk_error_delta_P_C_per_m2"
    validated = []; ratios = []; rejected = 0
    eps = np.finfo(float).eps
    # Three independently rounded vectors can differ by a few subnormal ULPs
    # even when their native fine-coarse increment is consistent. Relative
    # epsilon alone underflows to zero for such small polarization values.
    subnormal_roundoff = 2*float(np.nextafter(0., 1.))

    def flag(state, key, expected):
        value = state.get(key)
        if not isinstance(value, (bool, np.bool_)) or bool(value) != expected:
            raise ValueError(f"LK error audit requires explicit {key}={expected}")

    for i, state in enumerate(history):
        if not isinstance(state, Mapping) or state.get("lk_error_scope") != scope:
            raise ValueError("LK local error scope is unavailable")
        for key in ("valid", "converged", "lk_coupled", "lk_substepping", "lk_error_control"):
            flag(state, key, True)
        flag(state, "initial_state", i == 0)
        flag(state, "lk_error_estimate_available", i != 0)
        t = _real_scalar(state.get("time_s"), "time_s")
        dt = _real_scalar(state.get("dt_s"), "dt_s")
        attempted = _real_scalar(state.get("attempted_time_s"), "attempted_time_s")
        p = _real_array(state.get("P"), "P")
        relative = _real_scalar(state.get("lk_error_rtol"), "lk_error_rtol", positive=True)
        absolute = _real_scalar(state.get("lk_error_atol_C_per_m2"), "lk_error_atol_C_per_m2", positive=True)
        limit = _real_scalar(state.get("lk_step_limit_s"), "lk_step_limit_s", positive=True)
        end = _real_scalar(state.get("lk_error_end_s"), "lk_error_end_s")
        interval = _real_scalar(state.get("lk_error_interval_s"), "lk_error_interval_s")
        ratio = _real_scalar(state.get("lk_error_ratio"), "lk_error_ratio")
        count = state.get("lk_rejected_attempts")
        if (p.ndim != 1 or not p.size or p.size % 3 or relative >= 1. or ratio < 0.
                or isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)) or count < 0):
            raise ValueError("invalid LK polarization, tolerances or rejection count")
        params = (relative, absolute, limit, p.shape)
        if i == 0:
            reference = params
            if (t != 0. or dt != 0. or attempted != 0. or end != 0. or interval != 0.
                    or ratio != 0. or count != 0 or state.get("lk_error_status") != "initial"
                    or coarse_key in state or delta_key in state):
                raise ValueError("invalid LK error initial state")
        else:
            if (params != reference or t <= previous_time or dt <= 0. or attempted != t
                    or not np.isclose(dt, t-previous_time, rtol=1e-10, atol=0.)
                    or interval <= 0. or interval > limit*(1.+64*eps)
                    or end < t or state.get("lk_error_status") != "accepted"):
                raise ValueError("LK error clock, mode, tolerances and macro interval must be consistent")
        validated.append((t, dt, p, end, interval, ratio, int(count)))
        previous_time = t

    accepted = True
    for i in range(1, len(history), 2):
        a, b = validated[i:i+2]
        start = validated[i-1][0]
        if (a[3:] != b[3:] or b[3] != b[0]
                or not np.isclose(b[4], b[0]-start, rtol=1e-10, atol=0.)
                or abs(a[1]-b[1]) > 4*eps*max(abs(start), abs(b[0]), b[4])
                or coarse_key in history[i] or delta_key in history[i]):
            raise ValueError("LK error estimate must describe exactly two half steps with one macro endpoint")
        coarse = _real_array(history[i+1].get(coarse_key), coarse_key)
        delta = _real_array(history[i+1].get(delta_key), delta_key)
        if coarse.shape != b[2].shape or delta.shape != coarse.shape:
            raise ValueError("LK coarse polarization and stable error increment must match P")
        estimate = Decimal(0)
        with localcontext() as context:
            context.prec = 80
            relative, absolute = map(Decimal.from_float, reference[:2])
            for fine, trial, change in zip(b[2], coarse, delta):
                if abs(math.fsum([float(fine), -float(trial), -float(change)])) > (
                        8*eps*max(abs(fine), abs(trial)) + subnormal_roundoff):
                    raise ValueError("LK stable error increment disagrees with fine/coarse snapshots")
                norm = abs(Decimal.from_float(float(change))) / (absolute + relative*
                    max(abs(Decimal.from_float(float(fine))), abs(Decimal.from_float(float(trial)))))
                estimate = max(estimate, norm)
        recomputed = float(estimate)
        accepted = accepted and recomputed <= 1.+8*eps and b[5] <= 1.
        accepted = accepted and bool(np.isclose(recomputed, b[5], rtol=rtol, atol=0.))
        ratios.append(recomputed); rejected += b[6]
    return dict(valid=accepted, scope=scope, lk_local_error_control_validated=accepted,
        global_temporal_error_validated=False, physical_validated=False, energy_balance_validated=False,
        groups=len(ratios), accepted_half_steps=len(history)-1, rejected_attempts=rejected,
        max_error_ratio=max(ratios), recomputed_error_ratios=np.array(ratios), rtol=rtol)


def audit_transient_lk_electrical_error_control(history, *, rtol=1e-8):
    """Audit joint local P/phi/n/p control, with stable native increments.

    Voltage uses an absolute budget; carriers use absolute plus relative
    budgets. The discarded full step and both accepted half steps share the
    initial state and forcing. This checks local estimates, not global error.
    """
    polarization = audit_transient_lk_error_control(history, rtol=rtol)
    rtol = polarization["rtol"]
    scope = "lk_electrical_step_doubling_BE"
    fields = (("phi", "V"), ("n", "per_m3"), ("p", "per_m3"))
    params = None
    ratios = []
    eps = np.finfo(float).eps
    subnormal_roundoff = 2*float(np.nextafter(0., 1.))
    accepted = polarization["valid"]
    for i, state in enumerate(history):
        enabled = state.get("lk_electrical_error_control")
        if (not isinstance(enabled, (bool, np.bool_)) or not enabled
                or state.get("lk_electrical_error_scope") != scope):
            raise ValueError("LK electrical error control scope is unavailable")
        phi_atol = _real_scalar(state.get("lk_phi_atol_V"), "lk_phi_atol_V", positive=True)
        carrier_rtol = _real_scalar(state.get("lk_carrier_rtol"), "lk_carrier_rtol", positive=True)
        carrier_atol = _real_scalar(state.get("lk_carrier_atol_per_m3"), "lk_carrier_atol_per_m3", positive=True)
        ratio = _real_scalar(state.get("lk_electrical_error_ratio"), "lk_electrical_error_ratio")
        if carrier_rtol >= 1. or ratio < 0.:
            raise ValueError("invalid LK electrical error tolerances or norm")
        current = (phi_atol, carrier_rtol, carrier_atol)
        if params is None:
            params = current
        if current != params or (i == 0 and ratio != 0.):
            raise ValueError("LK electrical error tolerances must be constant and initial norm zero")
        estimate = Decimal(0)
        for field, unit in fields:
            fine = _real_array(state.get(field), field)
            if fine.ndim != 1 or 3*fine.size != len(state["P"]) or (field != "phi" and np.any(fine < 0.)):
                raise ValueError("electrical snapshots must match the LK mesh with nonnegative carriers")
            coarse_key, delta_key = f"lk_coarse_{field}_{unit}", f"lk_delta_{field}_{unit}"
            if i == 0 or i % 2 == 1:
                if coarse_key in state or delta_key in state:
                    raise ValueError("electrical estimate belongs only to the second half step")
                continue
            coarse = _real_array(state.get(coarse_key), coarse_key)
            delta = _real_array(state.get(delta_key), delta_key)
            if coarse.shape != fine.shape or delta.shape != fine.shape or (field != "phi" and np.any(coarse < 0.)):
                raise ValueError("electrical trial/increment must match the accepted mesh")
            with localcontext() as context:
                context.prec = 80
                absolute = Decimal.from_float(phi_atol if field == "phi" else carrier_atol)
                relative = Decimal(0) if field == "phi" else Decimal.from_float(carrier_rtol)
                for value, trial, change in zip(fine, coarse, delta):
                    if abs(math.fsum([float(value), -float(trial), -float(change)])) > (
                            8*eps*max(abs(value), abs(trial)) + subnormal_roundoff):
                        raise ValueError("electrical stable increment disagrees with fine/coarse snapshots")
                    norm = abs(Decimal.from_float(float(change))) / (absolute + relative *
                        max(abs(Decimal.from_float(float(value))), abs(Decimal.from_float(float(trial)))))
                    estimate = max(estimate, norm)
        if i and i % 2 == 0:
            if ratio != history[i-1]["lk_electrical_error_ratio"]:
                raise ValueError("both half steps must share one electrical estimate")
            recomputed = float(estimate)
            accepted = accepted and recomputed <= 1.+8*eps and ratio <= 1.
            accepted = accepted and bool(np.isclose(recomputed, ratio, rtol=rtol, atol=0.))
            ratios.append(recomputed)
    return dict(valid=accepted, scope=scope, lk_electrical_local_error_control_validated=accepted,
        global_temporal_error_validated=False, physical_validated=False, energy_balance_validated=False,
        groups=len(ratios), accepted_half_steps=len(history)-1,
        rejected_attempts=polarization["rejected_attempts"],
        max_electrical_error_ratio=max(ratios),
        max_joint_error_ratio=max(max(ratios), polarization["max_error_ratio"]),
        recomputed_electrical_error_ratios=np.array(ratios), polarization=polarization, rtol=rtol)
