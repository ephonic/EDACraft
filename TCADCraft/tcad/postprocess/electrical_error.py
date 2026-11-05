"""Independent audit of classical phi/n/p local BE step-doubling estimates."""
from collections.abc import Mapping
from decimal import Decimal, localcontext
import math

import numpy as np

from .terminal_trace import _real_array, _real_scalar


def audit_transient_electrical_error_control(history, *, rtol=1e-8):
    """Recompute local estimates and check their two-half-step provenance.

    Requires classical unfrozen phi/n/p, explicit scope/status and complete
    accepted groups. Voltage has an absolute budget in V; carrier budgets are
    absolute (m^-3) plus relative. Invalid inputs raise; finite norm defects
    return valid=False. This does not validate global error or device physics.
    """
    return _audit_step_doubling(history, rtol=rtol, prefix="electrical")


def audit_transient_nls_error_control(history, *, rtol=1e-8):
    """Audit joint P/phi/n/p estimates for split volume-ensemble NLS.

    Coarse/fine estimates include time integration and field-predictor split
    differences. This does not validate full coupling or global error bounds.
    """
    return _audit_step_doubling(history, rtol=rtol, prefix="nls")


def _audit_step_doubling(history, *, rtol, prefix):
    nls = prefix == "nls"
    rtol = _real_scalar(rtol, "rtol", positive=True)
    if rtol >= 1. or not isinstance(history, (list, tuple)) or len(history) < 3 or len(history) % 2 != 1:
        raise ValueError("electrical error audit requires complete half-step pairs and 0<rtol<1")
    scope = "split_nls_polarization_electrical_step_doubling" if nls else "classical_electrical_step_doubling_BE"
    eps = np.finfo(float).eps
    floor = 2*float(np.nextafter(0., 1.))
    fields = (("phi", "V"), ("n", "per_m3"), ("p", "per_m3"))
    if nls:
        fields += (("P", "C_per_m2"),)
    rows = []; ratios = []; rejected = 0

    def flag(state, key, expected):
        value = state.get(key)
        if not isinstance(value, (bool, np.bool_)) or bool(value) != expected:
            raise ValueError(f"electrical error audit requires explicit {key}={expected}")

    for i, state in enumerate(history):
        if not isinstance(state, Mapping) or state.get(f"{prefix}_error_scope") != scope:
            raise ValueError(f"{prefix} local error scope is unavailable")
        for key in ("valid", "converged", f"{prefix}_error_control"):
            flag(state, key, True)
        for key in ("phi_frozen", "majority_frozen", "lk_coupled", "lk_substepping"):
            flag(state, key, False)
        flag(state, "initial_state", i == 0)
        flag(state, f"{prefix}_error_estimate_available", i != 0)
        if "lk_error_scope" in state or "lk_electrical_error_scope" in state:
            raise ValueError(f"{prefix} and LK error scopes must not be mixed")
        for key in ("lk_error_control", "lk_electrical_error_control",
                    "electrical_error_control" if nls else "nls_error_control"):
            if key in state:
                flag(state, key, False)
        if _real_scalar(state.get("lk_step_limit_s"), "lk_step_limit_s") != 0.:
            raise ValueError(f"{prefix} error scope requires zero LK step limit")
        if not nls and "P" in state and _real_array(state["P"], "P").size:
            raise ValueError("classical error control cannot include ferroelectric polarization")
        if ("electrical_error_scope" if nls else "nls_error_scope") in state:
            raise ValueError("classical and NLS error scopes must not be mixed")
        t = _real_scalar(state.get("time_s"), "time_s")
        dt = _real_scalar(state.get("dt_s"), "dt_s")
        attempted = _real_scalar(state.get("attempted_time_s"), "attempted_time_s")
        end = _real_scalar(state.get(f"{prefix}_error_end_s"), "electrical_error_end_s")
        interval = _real_scalar(state.get(f"{prefix}_error_interval_s"), "electrical_error_interval_s")
        ratio = _real_scalar(state.get(f"{prefix}_error_ratio"), "electrical_error_ratio")
        limit = _real_scalar(state.get(f"{prefix}_step_limit_s"), "electrical_step_limit_s", positive=True)
        absolute = _real_scalar(state.get(f"{prefix}_phi_atol_V"), "electrical_phi_atol_V", positive=True)
        relative = _real_scalar(state.get(f"{prefix}_carrier_rtol"), "electrical_carrier_rtol", positive=True)
        carrier_absolute = _real_scalar(state.get(f"{prefix}_carrier_atol_per_m3"), "electrical_carrier_atol_per_m3", positive=True)
        count = state.get(f"{prefix}_rejected_attempts")
        arrays = tuple(_real_array(state.get(field), field) for field, _ in fields)
        p_atol = _real_scalar(state.get("nls_polarization_atol_C_per_m2"), "nls_polarization_atol_C_per_m2", positive=True) if nls else 0.
        p_rtol = _real_scalar(state.get("nls_polarization_rtol"), "nls_polarization_rtol", positive=True) if nls else 0.
        if (relative >= 1. or ratio < 0. or arrays[0].ndim != 1 or not arrays[0].size
                or any(a.shape != arrays[0].shape for a in arrays[1:3])
                or any(np.any(a < 0.) for a in arrays[1:3])
                or (nls and (p_rtol >= 1. or arrays[3].shape != (3*arrays[0].size,)))
                or isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)) or count < 0):
            raise ValueError("invalid electrical fields, tolerances, norm or rejection count")
        params = (absolute, relative, carrier_absolute, limit, arrays[0].shape, p_atol, p_rtol)
        if i == 0:
            reference = params
            if (t != 0. or dt != 0. or attempted != 0. or end != 0. or interval != 0.
                    or ratio != 0. or count != 0 or state.get(f"{prefix}_error_status") != "initial"):
                raise ValueError("invalid electrical error initial state")
        elif (params != reference or t <= rows[-1][0] or dt <= 0. or attempted != t
                or not np.isclose(dt, t-rows[-1][0], rtol=1e-10, atol=0.)
                or interval <= 0. or interval > limit*(1.+64*eps) or end < t
                or state.get(f"{prefix}_error_status") != "accepted"):
            raise ValueError("electrical error clock, mode, tolerances or macro interval is inconsistent")
        if i == 0 or i % 2:
            for field, unit in fields:
                if f"{prefix}_coarse_{field}_{unit}" in state or f"{prefix}_delta_{field}_{unit}" in state:
                    raise ValueError("electrical reference belongs only to the second half step")
        rows.append((t, dt, end, interval, ratio, int(count), arrays))

    accepted = True
    for i in range(1, len(history), 2):
        a, b = rows[i:i+2]
        start = rows[i-1][0]
        if (a[2:6] != b[2:6] or b[2] != b[0]
                or not np.isclose(b[3], b[0]-start, rtol=1e-10, atol=0.)
                or abs(a[1]-b[1]) > 4*eps*max(abs(start), abs(b[0]), b[3])):
            raise ValueError("electrical estimate must describe exactly two half steps and one endpoint")
        estimate = Decimal(0)
        with localcontext() as context:
            context.prec = 80
            for j, (field, unit) in enumerate(fields):
                state = history[i+1]
                coarse_key, delta_key = f"{prefix}_coarse_{field}_{unit}", f"{prefix}_delta_{field}_{unit}"
                coarse = _real_array(state.get(coarse_key), coarse_key)
                delta = _real_array(state.get(delta_key), delta_key)
                fine = b[6][j]
                if coarse.shape != fine.shape or delta.shape != fine.shape or (j in (1, 2) and np.any(coarse < 0.)):
                    raise ValueError("electrical trial/increment must match the accepted mesh")
                absolute = Decimal.from_float(reference[5] if j == 3 else (reference[0] if j == 0 else reference[2]))
                relative = Decimal(0) if j == 0 else Decimal.from_float(reference[6] if j == 3 else reference[1])
                for value, trial, change in zip(fine, coarse, delta):
                    if abs(math.fsum([float(value), -float(trial), -float(change)])) > (
                            8*eps*max(abs(value), abs(trial)) + floor):
                        raise ValueError("electrical stable increment disagrees with fine/coarse snapshots")
                    norm = abs(Decimal.from_float(float(change))) / (absolute + relative *
                        max(abs(Decimal.from_float(float(value))), abs(Decimal.from_float(float(trial)))))
                    estimate = max(estimate, norm)
        recomputed = float(estimate)
        if not math.isfinite(recomputed):
            raise ValueError("electrical norm cannot be represented as finite float64")
        accepted = accepted and recomputed <= 1.+8*eps and b[4] <= 1.
        accepted = accepted and bool(np.isclose(recomputed, b[4], rtol=rtol, atol=0.))
        ratios.append(recomputed); rejected += b[5]
    return dict(valid=accepted, scope=scope,
        **{("nls_local_error_control_validated" if nls else "electrical_local_error_control_validated"): accepted},
        global_temporal_error_validated=False, physical_validated=False, energy_balance_validated=False,
        groups=len(ratios), accepted_half_steps=len(history)-1, rejected_attempts=rejected,
        max_error_ratio=max(ratios), recomputed_error_ratios=np.array(ratios), rtol=rtol)
