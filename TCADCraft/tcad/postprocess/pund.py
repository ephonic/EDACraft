"""Continuous native PUND drive and accepted BE terminal-charge extraction."""
from collections.abc import Mapping

import numpy as np

from .terminal_trace import (
    _real_array, _real_scalar, _finite_sum, _pund_charge_report,
    integrate_transient_terminal_history,
)


LABELS = ("preset", "P", "U", "N", "D")


def _contact_electrode(sim, name):
    """Map an exact full contact plane to the native geometric face label."""
    keys = ([key for key in sim.mesh.fields
             if key == "contact_gate" or key.startswith("contact_gate_")]
            if name == "gate" else [f"contact_{name}"])
    mask = np.zeros(sim.mesh.npts(), dtype=bool)
    for key in keys:
        if key not in sim.mesh.fields:
            raise ValueError("PUND contact requires an existing mesh mask")
        values = np.asarray(sim.mesh.fields[key])
        if (values.size != mask.size or values.dtype.kind not in "biuf"
                or not np.all(np.isfinite(values))
                or not np.all((values == 0) | (values == 1))):
            raise ValueError("PUND contact mask must be finite binary data matching the mesh")
        mask |= values.astype(bool).ravel()
    matches = []
    for axis, coords in zip("xyz", sim.mesh.flat_coords()):
        if coords.size != mask.size or not np.all(np.isfinite(coords)):
            raise ValueError("PUND mesh coordinates must be finite and match the mesh")
        if np.min(coords) == np.max(coords):
            continue
        for side, value in (("min", np.min(coords)), ("max", np.max(coords))):
            if np.array_equal(mask, coords == value):
                matches.append(f"{axis}_{side}")
    if len(matches) != 1:
        raise ValueError("PUND contact must occupy exactly one complete native boundary plane")
    return matches[0]


class PUNDTransientError(RuntimeError):
    """Incomplete pulse sequence; accepted native progress remains available."""

    def __init__(self, history, reason):
        self.history = history
        self.accepted_history = [s for s in history if s.get("valid") is True]
        self.elapsed_time_s = self.accepted_history[-1]["time_s"] if self.accepted_history else 0.
        super().__init__(f"native PUND incomplete at {self.elapsed_time_s:g} s: {reason}")


def extract_transient_pund_charge(history, pulse_windows_s, *, terminal,
                                  reference_terminal, electrode_area_m2=None):
    """Integrate P/U/N/D windows using native constant BE interval currents.

    Window boundaries must be exact accepted endpoints (normally drive knots).
    No clipping, interpolating current samples, or missing impulse correction is
    performed. Paired voltage waveforms must match at all electrodes. Matching
    windows alone cannot establish leakage cancellation or FE/material accuracy.
    """
    if (not isinstance(terminal, str) or not terminal
            or not isinstance(reference_terminal, str) or not reference_terminal
            or terminal == reference_terminal):
        raise ValueError("PUND requires distinct nonempty terminal names")
    if electrode_area_m2 is not None:
        electrode_area_m2 = _real_scalar(electrode_area_m2, "electrode_area_m2", positive=True)
    if not isinstance(pulse_windows_s, Mapping) or any(k not in pulse_windows_s for k in LABELS[1:]):
        raise ValueError("PUND requires P, U, N and D windows")
    complete = integrate_transient_terminal_history(history, voltage_quadrature="linear")
    names = tuple(history[0]["electrode_names"])
    if terminal not in names or reference_terminal not in names:
        raise ValueError("PUND terminals must be named native electrodes")
    ti, ri = names.index(terminal), names.index(reference_terminal)
    times = np.array([s["time_s"] for s in history])
    results, waves, windows = {}, {}, {}
    for label in LABELS[1:]:
        bounds = np.asarray(pulse_windows_s[label])
        if bounds.shape != (2,) or bounds.dtype.kind not in "iuf" or not np.all(np.isfinite(bounds)):
            raise ValueError("PUND window must contain two finite real times")
        start, stop = map(float, bounds)
        a, b = np.flatnonzero(times == start), np.flatnonzero(times == stop)
        if len(a) != 1 or len(b) != 1 or a[0] >= b[0]:
            raise ValueError("PUND windows must use exact increasing accepted endpoints")
        subset = [dict(s, time_s=float(s["time_s"]-start))
                  for s in history[a[0]:b[0]+1]]
        subset[0].update(initial_state=True, dt_s=0.)
        results[label] = integrate_transient_terminal_history(subset, voltage_quadrature="linear")
        voltage = np.array([s["electrode_voltages_V"] for s in subset])
        bias = voltage[:, ti]-voltage[:, ri]
        if not np.all(np.isfinite(bias)) or (label in ("P", "U") and
                (np.any(bias < 0.) or not np.any(bias > 0.))) or (label in ("N", "D") and
                (np.any(bias > 0.) or not np.any(bias < 0.))):
            raise ValueError("P/U require positive and N/D negative native pulse bias")
        waves[label] = (np.array([s["time_s"] for s in subset]), voltage)
        windows[label] = (start, stop)
    ordered = [windows[k] for k in LABELS[1:]]
    if any(first[1] > second[0] for first, second in zip(ordered, ordered[1:])):
        raise ValueError("PUND windows must be chronological and nonoverlapping")
    for first, second in (("P", "U"), ("N", "D")):
        t0, v0 = waves[first]
        t1, v1 = waves[second]
        if not np.isclose(t0[-1], t1[-1], rtol=1e-10, atol=0.):
            raise ValueError("paired PUND window durations must match")
        u0, u1 = t0/t0[-1], t1/t1[-1]
        points = np.union1d(u0, u1)
        for index in range(len(names)):
            if not np.allclose(np.interp(points, u0, v0[:, index]),
                               np.interp(points, u1, v1[:, index]), rtol=1e-10, atol=1e-12):
                raise ValueError("paired PUND voltages must match at every electrode")
    output = _pund_charge_report(results, terminal, reference_terminal, electrode_area_m2,
                                 "matched_native_backward_euler_terminal_integrals")
    output.update(pulse_windows_s=windows, sequence_integral=complete,
                  leakage_cancellation_validated=False, energy_balance_validated=False)
    return output


def audit_transient_pund_components(history, pulse_windows_s, *, terminal,
                                    reference_terminal, electrode_area_m2=None,
                                    rtol=1e-8, atol_A=0.):
    """Resolve modeled PUND charge without assuming repeated leakage cancels.

    Check total=conduction+displacement and displacement=dielectric+polarization
    at every accepted interval/electrode. Integrate each native component over
    the same windows. Removed-background quantities come directly from native
    displacement/polarization currents, preserving small signals under large
    conduction backgrounds. These are model diagnostics, not measured leakage
    corrections, proof of FE origin, or a device energy balance.
    """
    rtol = _real_scalar(rtol, "component rtol", positive=True)
    atol_A = _real_scalar(atol_A, "component atol_A")
    if rtol >= 1. or atol_A < 0.:
        raise ValueError("component audit requires 0 < rtol < 1 and nonnegative atol_A")
    output = extract_transient_pund_charge(history, pulse_windows_s, terminal=terminal,
                    reference_terminal=reference_terminal, electrode_area_m2=electrode_area_m2)
    kinds = ("total", "conduction", "displacement", "dielectric", "polarization")
    residuals, relative, accepted = [], [], True
    names = history[0]["electrode_names"]
    for state in history[1:]:
        flag = state.get("displacement_current_available")
        if not isinstance(flag, (bool, np.bool_)) or not bool(flag):
            raise ValueError("native displacement component scope is unavailable")
        fields = {kind: _real_array(state.get(f"electrode_{kind}_currents_A"),
                                   f"electrode_{kind}_currents_A") for kind in kinds}
        if any(value.shape != (len(names),) for value in fields.values()):
            raise ValueError("component audit requires one current per native electrode")
        row, errors = [], []
        for whole, first, second in (("total", "conduction", "displacement"),
                                      ("displacement", "dielectric", "polarization")):
            differences, ratios = [], []
            for a, b, c in zip(fields[whole], fields[first], fields[second]):
                residual = _finite_sum((float(a), -float(b), -float(c)))
                scale = max(abs(float(a)), abs(float(b)), abs(float(c)))
                ratio = max(abs(residual)-atol_A, 0.)/scale if scale else 0.
                accepted = accepted and ratio <= rtol
                differences.append(residual)
                ratios.append(ratio)
            row.append(differences)
            errors.append(ratios)
        residuals.append(row)
        relative.append(errors)
    times = np.array([s["time_s"] for s in history])
    components = {}
    for kind in kinds[1:]:
        reports = {}
        for label, (start, stop) in output["pulse_windows_s"].items():
            a, b = np.flatnonzero(times == start)[0], np.flatnonzero(times == stop)[0]
            subset = [dict(s, time_s=float(s["time_s"]-start)) for s in history[a:b+1]]
            subset[0].update(initial_state=True, dt_s=0.)
            reports[label] = integrate_transient_terminal_history(subset,
                                current_kind=kind, voltage_quadrature="linear")
        components[kind] = _pund_charge_report(reports, terminal, reference_terminal,
                            electrode_area_m2, f"matched_native_{kind}_current_integrals")

    def pair(report):
        return {name: report[f"switching_charge_{name}_C"]
                for name in ("positive", "negative", "magnitude")}

    output.update(valid=bool(accepted), component_balance_validated=bool(accepted),
        component_balance_scope="exported_native_terminal_current_decomposition",
        component_reports=components,
        component_pair_charge_C={"total": pair(output),
                                 **{kind: pair(report) for kind, report in components.items()}},
        modeled_conduction_removed_pair_charge_C=pair(components["displacement"]),
        modeled_conduction_and_dielectric_removed_pair_charge_C=pair(components["polarization"]),
        interval_component_residuals_A=np.array(residuals),
        interval_component_relative_residuals=np.array(relative),
        component_relations=["total=conduction+displacement", "displacement=dielectric+polarization"],
        component_electrode_names=list(names),
        max_component_relative_residual=float(np.max(relative)),
        component_rtol=rtol, component_atol_A=atol_A,
        correction_scope="native_model_current_components")
    return output


def run_transient_pund(sim, contact, reference_contact, V_pulse, *, pulse_width,
                       rise_time, fall_time, delay_time, dt, pre_pol_V=None,
                       fe_gamma=0., electrode_area_m2=None, max_iter=50, tol=1e-10,
                       audit_components=False):
    """Run one continuous preset/P/U/N/D sequence with finite linear edges.

    Extract charge over each rise and plateau; fall and delay remain in the
    continuous history and whole-sequence source-work report. Configure device
    physics beforehand. dt/final time/damping and final accepted state remain
    configured after this call; prior waveform and DC contacts are restored.
    Failed native steps retain their accepted prefix and raise PUNDTransientError.
    This opt-in driver does not change the legacy FE-state PUND protocol.
    audit_components=True also returns checked native current decomposition;
    it cannot certify experimental leakage cancellation.
    """
    for name in (contact, reference_contact):
        if not isinstance(name, str) or not name or name not in sim._contact_voltages:
            raise ValueError("PUND contacts must be configured named contacts")
    if contact == reference_contact:
        raise ValueError("PUND contacts must be distinct")
    if not isinstance(audit_components, (bool, np.bool_)):
        raise ValueError("audit_components must be boolean")
    terminal, reference = _contact_electrode(sim, contact), _contact_electrode(sim, reference_contact)
    if terminal == reference:
        raise ValueError("PUND contacts must occupy distinct native electrodes")
    values = {}
    for name, value in (("V_pulse", V_pulse), ("pulse_width", pulse_width),
                        ("rise_time", rise_time), ("fall_time", fall_time), ("dt", dt)):
        values[name] = _real_scalar(value, name, positive=True)
    delay_time = _real_scalar(delay_time, "delay_time")
    fe_gamma = _real_scalar(fe_gamma, "fe_gamma")
    if delay_time < 0. or fe_gamma < 0.:
        raise ValueError("delay_time and fe_gamma must be nonnegative")
    pre_pol_V = _real_scalar(V_pulse if pre_pol_V is None else pre_pol_V, "pre_pol_V", positive=True)
    if isinstance(max_iter, (bool, np.bool_)) or not isinstance(max_iter, (int, np.integer)) or max_iter < 1:
        raise ValueError("max_iter must be an integer >= 1")
    tol = _real_scalar(tol, "tol", positive=True)
    if electrode_area_m2 is not None:
        electrode_area_m2 = _real_scalar(electrode_area_m2, "electrode_area_m2", positive=True)
    baseline = _real_scalar(sim._contact_voltages[reference_contact], "reference voltage")
    clock, voltage, windows = [0.], [baseline], {}
    for label, amplitude in zip(LABELS, (-pre_pol_V, values["V_pulse"], values["V_pulse"],
                                        -values["V_pulse"], -values["V_pulse"])):
        if baseline+amplitude == baseline:
            raise ValueError("PUND amplitude cannot be resolved at the reference voltage")
        start = clock[-1]
        for duration, level in ((values["rise_time"], baseline+amplitude),
                                 (values["pulse_width"], baseline+amplitude),
                                 (values["fall_time"], baseline), (delay_time, baseline)):
            if duration == 0.:
                continue
            stop = clock[-1]+duration
            if not np.isfinite(stop) or stop <= clock[-1] or not np.isfinite(level):
                raise ValueError("PUND times and voltage knots must remain finite and distinct")
            clock.append(stop)
            voltage.append(level)
        # Use the stored plateau knot itself; subtraction can round differently.
        windows[label] = (start, clock[-3] if delay_time else clock[-2])
    previous = getattr(sim, "_transient_contact_waveforms", None)
    try:
        sim.set_transient_contact_waveforms(clock, {
            contact: voltage, reference_contact: np.full(len(clock), baseline)})
        sim.set_transient(dt=values["dt"], t_final=clock[-1], fe_gamma=fe_gamma)
        history = sim.run_transient(max_iter=int(max_iter), tol=tol)
        if not history or any(s.get("valid") is not True or s.get("converged") is not True for s in history):
            raise PUNDTransientError(history, "native step rejected")
        if history[-1]["time_s"] != clock[-1]:
            raise PUNDTransientError(history, "requested final time not reached")
        extractor = audit_transient_pund_components if audit_components else extract_transient_pund_charge
        output = extractor(history, windows, terminal=terminal,
                    reference_terminal=reference, electrode_area_m2=electrode_area_m2)
        output.update(history=history, waveform_times_s=np.array(clock),
                      waveform_voltages_V=np.array(voltage), pulse_labels=list(LABELS),
                      measurement_window_kind="rise_and_plateau",
                      contact_to_electrode={contact: terminal, reference_contact: reference})
        return output
    finally:
        if previous is None:
            sim.clear_transient_contact_waveforms()
        else:
            sim.set_transient_contact_waveforms(*previous)
