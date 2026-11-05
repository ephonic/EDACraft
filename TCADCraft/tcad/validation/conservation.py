"""Conservation-law validation with explicit failure semantics.

The validation layer accepts both dictionaries returned by the native
bindings and Python result objects. Missing fields or non-converged results
are reported as unavailable/failed instead of being replaced by zero arrays.
"""

from __future__ import annotations

import numpy as np
from typing import Callable
from collections.abc import Mapping

from .base import BaseValidationTest, ValidationResult


def _value(result, name, default=None):
    return result.get(name, default) if isinstance(result, Mapping) else getattr(result, name, default)


def _real_array(value):
    """Convert a real ledger without discarding imaginary or overflowing data."""
    try:
        if np.iscomplexobj(value):
            return None
        value = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError):
        return None
    if value.size == 0 or not np.all(np.isfinite(value)):
        return None
    return value


def _field(result, name):
    return _real_array(_value(result, name))


def _status_issues(result, require=True):
    issues = []
    found = False
    for name in ("valid", "converged"):
        absent = object()
        value = _value(result, name, absent)
        if value is not absent:
            found = True
            if not isinstance(value, (bool, np.bool_)) or not value:
                issues.append(f"result.{name} must be True")
    if require and not found:
        issues.append("result status unavailable: provide valid/converged")
    return issues


def _currents(result):
    """One signed, integrated current [A] per contact, positive into device."""
    value = _value(result, "terminal_currents_A")
    if isinstance(value, Mapping):
        value = list(value.values())
    if value is None:
        return None
    array = _real_array(value)
    if array is None or array.ndim != 1 or array.size < 2:
        return None
    return array


def _balance_error(residual, scale, absolute_tolerance):
    # Subtract the explicit SI noise budget before measuring relative error.
    if not np.isfinite(residual) or not np.isfinite(scale) or scale < 0:
        return float("inf")
    excess = max(0.0, abs(residual) - absolute_tolerance)
    if scale == 0.0:
        return 0.0 if excess == 0.0 else float("inf")
    return excess / scale


def _stored_charge(result):
    charge = _field(result, "stored_charge_C")
    if (_value(result, "stored_charge_C", _MISSING) is not _MISSING
            and (charge is None or charge.size != 1)):
        return None
    components = _component_values(result, "stored_charge_components_C")
    if (_value(result, "stored_charge_components_C", _MISSING) is not _MISSING
            and components is None):
        return None
    if charge is not None and charge.size == 1 and components is not None:
        total = float(sum(components.values()))
        scalar = float(charge.item())
        if not np.isclose(scalar, total, rtol=1e-12, atol=1e-30):
            return None
        return scalar
    if charge is not None and charge.size == 1:
        return float(charge.item())
    if components is not None:
        total = float(sum(components.values()))
        return total if np.isfinite(total) else None
    if _value(result, "stored_charge_C") is not None:
        return None
    rho = _field(result, "charge_density_C_per_m3")
    volumes = _field(result, "cell_volumes_m3")
    if rho is None or volumes is None or np.any(volumes <= 0):
        return None
    if volumes.size != 1 and rho.shape != volumes.shape:
        return None
    charge = float(np.sum(rho * volumes))
    return charge if np.isfinite(charge) else None


def _component_values(result, name):
    """Return a finite named scalar ledger, or ``None`` when absent/invalid.

    Component ledgers are deliberately explicit: silently treating a missing
    displacement, polarization, or trap term as zero would make a conservation
    check look complete while omitting a physical storage channel.
    """
    value = _value(result, name)
    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        return None
    output = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key:
            return None
        field = _field({"value": raw}, "value")
        if field is None or field.size != 1:
            return None
        output[key] = float(field.item())
    return output


_MISSING = object()


def _energy_field(result, scalar_name, component_name):
    scalar = _field(result, scalar_name)
    if (_value(result, scalar_name, _MISSING) is not _MISSING
            and scalar is None):
        return None, None
    components = _component_values(result, component_name)
    if (_value(result, component_name, _MISSING) is not _MISSING
            and components is None):
        return None, None
    if scalar is not None:
        total = float(np.sum(scalar))
        if components is not None:
            component_total = float(sum(components.values()))
            if not np.isclose(total, component_total, rtol=1e-12, atol=1e-30):
                return None, None
        return total, components
    if components is None:
        return None, None
    total = float(sum(components.values()))
    return (total, components) if np.isfinite(total) else (None, None)


class ConservationTest(BaseValidationTest):
    """Check steady terminal KCL and an explicit energy ledger.

    ``terminal_currents_A`` contains signed currents into the device, one per
    contact. Carrier neutrality is neither required nor a conservation test.
    An optional extractor receives (simulation, result) and returns these
    currents. Energy fields are integrated joules: initial + supplied equals
    final + dissipated. Missing optional terms mean zero; malformed terms fail.
    """

    def __init__(self, check_charge: bool = True, check_energy: bool = True,
                 check_entropy: bool = False, tolerance: float = 1e-6,
                 *, current_atol_A: float = 1e-15, current_extractor: Callable = None):
        super().__init__("Conservation Laws Test")
        self.check_charge = check_charge
        self.check_energy = check_energy
        self.check_entropy = check_entropy
        self.tolerance = tolerance
        if not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("tolerance must be finite and positive")
        if not np.isfinite(current_atol_A) or current_atol_A < 0:
            raise ValueError("current_atol_A must be finite and nonnegative")
        self.current_atol_A = current_atol_A
        self.current_extractor = current_extractor

    def run(self, device_builder: Callable) -> ValidationResult:
        try:
            simulation = device_builder()
            result = simulation.run() if hasattr(simulation, "run") else simulation
            currents = self.current_extractor(simulation, result) if (
                self.check_charge and self.current_extractor is not None) else _value(result, "terminal_currents_A")
        except Exception as exc:
            return ValidationResult(self.name, False, f"simulation failed: {exc}")

        violations = _status_issues(result)
        details = {}
        if self.check_charge:
            value = self._check_charge_conservation({"terminal_currents_A": currents})
            details["charge_violation"] = value
            if not np.isfinite(value):
                violations.append("charge conservation unavailable: provide at least two finite signed terminal_currents_A")
            elif value > self.tolerance:
                violations.append(f"charge conservation violation: {value:.2e}")
        if self.check_energy:
            value = self._check_energy_conservation(result)
            details["energy_violation"] = value
            if not np.isfinite(value):
                violations.append(
                    "energy conservation unavailable: provide energy_initial/energy_final "
                    "or explicit initial/final energy components in joules"
                )
            elif value > self.tolerance:
                violations.append(f"energy conservation violation: {value:.2e}")
        if self.check_entropy:
            value = self._check_entropy_production(result)
            details["entropy_violation"] = value
            if not np.isfinite(value) or value < -self.tolerance:
                violations.append("entropy production unavailable or negative")
        details["status"] = "failed" if violations else "ok"
        return ValidationResult(
            self.name, not violations,
            "all requested conservation checks passed" if not violations else "; ".join(violations),
            details,
        )

    def _check_charge_conservation(self, result) -> float:
        currents = _currents(result)
        if currents is None:
            return float("nan")
        return _balance_error(float(np.sum(currents)), float(np.sum(np.abs(currents))), self.current_atol_A)

    def _check_energy_conservation(self, result) -> float:
        initial, initial_components = _energy_field(
            result, "energy_initial", "energy_components_initial_J")
        final, final_components = _energy_field(
            result, "energy_final", "energy_components_final_J")
        if initial is None or final is None:
            return float("nan")
        if ((initial_components is None) != (final_components is None)
                or (initial_components is not None
                    and set(initial_components) != set(final_components))):
            return float("nan")
        lhs = initial
        rhs = final
        # Scale by the energy terms before signed source work cancels stored
        # energy. A complete discharge may have lhs ~= rhs ~= 0, despite
        # finite initial/returned energy and only floating-point roundoff.
        lhs_scale = float(np.sum(np.abs(initial)))
        rhs_scale = float(np.sum(np.abs(final)))
        for name in ("energy_supplied", "energy_dissipated"):
            absent = object()
            component_name = "energy_components_" + name[7:] + "_J"
            if (_value(result, name, absent) is not absent
                    or _value(result, component_name, absent) is not absent):
                term, _ = _energy_field(result, name, component_name)
                if term is None:
                    return float("nan")
                if name == "energy_supplied":
                    lhs += term
                    lhs_scale += abs(term)
                else:
                    rhs += term
                    rhs_scale += abs(term)
        return _balance_error(lhs - rhs, max(lhs_scale, rhs_scale), 0.0)

    def _check_entropy_production(self, result) -> float:
        value = _field(result, "entropy_production")
        return float(np.sum(value)) if value is not None else float("nan")


class TransientConservationTest(BaseValidationTest):
    """Check delta Q = integral(sum I_into) dt for each sampled interval.

    Each snapshot must provide ``time_s``, converged/valid status, signed
    ``terminal_currents_A`` and ``stored_charge_C`` (or named
    ``stored_charge_components_C`` / charge density times positive cell
    volumes). Currents transport the charge in this ledger;
    do not include displacement current already counted as stored charge.
    Both endpoint samples, including the initial state, are required.
    """

    def __init__(self, dt: float = 1e-9, t_final: float = 1e-7,
                 tolerance: float = 1e-3, *, charge_atol_C: float = 1e-24,
                 integration: str = "trapezoid"):
        super().__init__("Transient Conservation Test")
        self.dt = dt
        self.t_final = t_final
        self.tolerance = tolerance
        if not all(np.isfinite(x) and x > 0 for x in (dt, t_final, tolerance)):
            raise ValueError("dt, t_final and tolerance must be finite and positive")
        if not np.isfinite(charge_atol_C) or charge_atol_C < 0:
            raise ValueError("charge_atol_C must be finite and nonnegative")
        if integration not in ("trapezoid", "backward_euler"):
            raise ValueError("integration must be trapezoid or backward_euler")
        self.charge_atol_C = charge_atol_C
        self.integration = integration

    def run(self, device_builder: Callable) -> ValidationResult:
        try:
            simulation = device_builder()
            if hasattr(simulation, "run_transient"):
                # The public Simulator configures time separately from its run
                # method. Keep legacy adapters that accept dt/t_final working.
                if hasattr(simulation, "set_transient"):
                    simulation.set_transient(self.dt, self.t_final)
                    result = simulation.run_transient()
                else:
                    result = simulation.run_transient(dt=self.dt, t_final=self.t_final)
            else:
                result = simulation
        except Exception as exc:
            return ValidationResult(self.name, False, f"transient simulation failed: {exc}")
        if not isinstance(result, (list, tuple)) and _status_issues(result, require=False):
            return ValidationResult(self.name, False, "; ".join(_status_issues(result, require=False)))
        snapshots = result if isinstance(result, (list, tuple)) else _value(result, "snapshots")
        if not isinstance(snapshots, (list, tuple)) or len(snapshots) < 2:
            return ValidationResult(self.name, False, "transient conservation unavailable: at least two snapshots required")
        times, charges, currents, current_scales = [], [], [], []
        charge_components = []
        for snapshot in snapshots:
            issues = _status_issues(snapshot)
            if issues:
                return ValidationResult(self.name, False, "transient snapshot: " + "; ".join(issues))
            time = _field(snapshot, "time_s")
            charge = _stored_charge(snapshot)
            components = _component_values(snapshot, "stored_charge_components_C")
            if _value(snapshot, "stored_charge_components_C") is not None and components is None:
                return ValidationResult(self.name, False,
                    "transient charge components must be a finite named scalar mapping")
            terminal = _currents(snapshot)
            if time is None or time.size != 1 or charge is None or terminal is None:
                return ValidationResult(self.name, False,
                    "transient conservation unavailable: finite time_s, stored_charge_C "
                    "(or charge density/cell volumes), and signed terminal_currents_A required")
            times.append(float(time.item()))
            charges.append(charge)
            currents.append(float(np.sum(terminal)))
            current_scales.append(float(np.sum(np.abs(terminal))))
            charge_components.append(components)
        if any(item is not None for item in charge_components):
            if any(item is None for item in charge_components):
                return ValidationResult(self.name, False,
                    "stored_charge_components_C must be present at every snapshot")
            keys = set(charge_components[0])
            if not keys or any(set(item) != keys for item in charge_components[1:]):
                return ValidationResult(self.name, False,
                    "stored_charge_components_C names must remain constant")
        intervals = np.diff(times)
        if np.any(intervals <= 0):
            return ValidationResult(self.name, False, "snapshot time_s must strictly increase")
        net = np.asarray(currents)
        scale = np.asarray(current_scales)
        if self.integration == "trapezoid":
            transported = intervals * (net[:-1] + net[1:]) / 2
            throughput = intervals * (scale[:-1] + scale[1:]) / 2
        else:
            transported = intervals * net[1:]
            throughput = intervals * scale[1:]
        changes = np.diff(charges)
        residuals = changes - transported
        errors = [_balance_error(r, max(abs(q), s), self.charge_atol_C)
                  for r, q, s in zip(residuals, changes, throughput)]
        max_error = float(max(errors))
        passed = max_error <= self.tolerance
        component_deltas = None
        if charge_components and charge_components[0] is not None:
            component_deltas = {
                key: [charge_components[i + 1][key] - charge_components[i][key]
                      for i in range(len(intervals))]
                for key in charge_components[0]
            }
        return ValidationResult(
            self.name, passed,
            "transient charge conservation passed" if passed else f"transient charge balance violation: {max_error:.2e}",
            {"charge_violation": max_error,
             "max_charge_residual_C": float(np.max(np.abs(residuals))),
             "charge_component_deltas_C": component_deltas,
             "intervals": len(intervals), "time_start_s": times[0],
             "time_end_s": times[-1], "integration": self.integration},
        )
