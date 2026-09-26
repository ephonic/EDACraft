"""M5 negative-capacitance dual-verdict model (plan0918 direction-1).

Comment7 5.6 controversy 1: is negative capacitance a material property or a
measurement artifact?  The artifact camp (Alexe 2025) shows that a source
impedance as small as 50 Ohm can produce the voltage dip that gets reported
as NC, removable with a low-impedance buffer.  This module makes both sides
of the argument computable on the SAME ferroelectric film:

Circuit model
-------------
A triangular voltage ramp ``V_a(t)`` drives the FE capacitor ``C``
(area A, thickness d, permittivity eps) through a series resistance ``Rs``
(the 50-Ohm measurement source).  The film follows Landau-Khalatnikov
dynamics::

    gamma * dP/dt = E - alpha*P - beta*P^3        (LK switching)
    V_a = Rs*A*(eps0*epsr*dE/dt + dP/dt) + E*d    (KCL at the device)

``Rs -> 0`` degenerates to the ideal voltage drive ``E = V_a/d`` (the
buffered measurement).  Discretization is implicit in ``E`` (linear solve)
with an iterated LK update, stable for arbitrary ``dt``.

Dual verdict
------------
Two distinct non-monotonicity probes:

* **Terminal dip** - non-monotone excursion of the film voltage
  ``V_fe = E*d`` measured through the source while ``V_a`` is monotone.
  Under the ideal drive (``Rs = 0``) ``V_fe`` is *identically* ``V_a`` and
  cannot dip, so any terminal dip observed in a real measurement is by
  construction the series-impedance drop during the switching-current
  transient (the Alexe 2025 mechanism, here reproduced computationally).
* **Branch dip** - non-monotone excursion of the internal branch voltage
  ``d*(alpha*P + beta*P^3)`` along the trajectory.  This is the
  Landau-Devonshire S-branch traverse and exists whenever the film switches
  (dynamically, both drives): the intrinsic NC signature, visible only in
  the internal coordinate.

``nc_verdict`` runs the loop at the measurement impedance and reports both
probes with the label ``no_dip`` / ``intrinsic_only`` (low-impedance
regime: internal traverse, no terminal artifact) / ``artifact`` (terminal
dip present - the source impedance is manufacturin the apparent NC).
The sweep defaults to the P-E measurement convention ``p0 = -Ps`` so the
upward branch carries the switching transient.

Analytic anchors (tests/test_nc_verdict.py): the linear-dielectric RC
transient closed form, the static S-curve ``E(P) = alpha*P + beta*P^3``
(negative-slope region = the static NC branch), quasi-static branch
reproduction under slow ideal ramps, and the energy identity (source work =
Rs Joule heat + LK dissipation + Landau storage + dielectric storage).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

EPS0 = 8.854187817e-12


@dataclass
class LKCircuitModel:
    """Landau-Khalatnikov film driven through a series resistance."""

    alpha: float = -5.0e8        # Landau alpha [m/F]
    beta: float = 1.5e9          # Landau beta [m^5/(F C^2)]
    gamma: float = 1.0e3         # LK damping [Ohm m]
    epsilon_r: float = 20.0
    thickness: float = 10.0e-9   # film thickness [m]
    area: float = 1.0e-12        # device area [m^2]
    rs: float = 50.0             # series/source resistance [Ohm]

    def __post_init__(self) -> None:
        for name, value in (
            ("gamma", self.gamma), ("epsilon_r", self.epsilon_r),
            ("thickness", self.thickness), ("area", self.area),
        ):
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if not np.isfinite(self.alpha) or not np.isfinite(self.beta):
            raise ValueError("alpha/beta must be finite")
        if self.beta < 0.0:
            raise ValueError("beta must be >= 0")
        if self.beta == 0.0 and self.alpha < 0.0:
            raise ValueError(
                "beta = 0 requires alpha >= 0 (bounded linear/paraelectric limit)"
            )
        if not np.isfinite(self.rs) or self.rs < 0.0:
            raise ValueError("rs must be finite and >= 0")

    @property
    def capacitance(self) -> float:
        return EPS0 * self.epsilon_r * self.area / self.thickness

    def static_field(self, p: float) -> float:
        """Static S-curve branch E(P) = alpha*P + beta*P^3."""
        return self.alpha * p + self.beta * p ** 3

    def ps(self) -> float:
        """Spontaneous polarization sqrt(-alpha/beta) (alpha < 0)."""
        if self.alpha >= 0.0:
            return 0.0
        return float(np.sqrt(-self.alpha / self.beta))

    def ec_static(self) -> float:
        """Spinodal coercive field (2/3)|alpha| sqrt(-alpha/(3 beta))."""
        if self.alpha >= 0.0:
            return 0.0
        return (2.0 / 3.0) * abs(self.alpha) * float(
            np.sqrt(-self.alpha / (3.0 * self.beta))
        )

    def landau_energy(self, p: float) -> float:
        return 0.5 * self.alpha * p ** 2 + 0.25 * self.beta * p ** 4


def _triangular_ramp(t: float, v_max: float, period: float) -> float:
    """0 -> +Vmax -> -Vmax -> 0 triangular ramp over ``period``."""
    quarter = period / 4.0
    half = period / 2.0
    if t <= quarter:
        return v_max * t / quarter
    if t <= half:
        return v_max - v_max * (t - quarter) / quarter
    if t <= period - quarter:
        return -v_max * (t - half) / quarter
    return -v_max + v_max * (t - (period - quarter)) / quarter


def run_triangular_sweep(
    model: LKCircuitModel,
    v_max: float,
    period: float,
    n_steps: int,
    p0: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """Drive one triangular period and record waveforms + energy ledger."""
    if not np.isfinite(v_max) or v_max <= 0.0:
        raise ValueError("v_max must be finite and > 0")
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and > 0")
    if n_steps < 4:
        raise ValueError("n_steps must be >= 4")
    dt = period / n_steps

    p = -model.ps() if p0 is None else float(p0)
    e_field = model.static_field(p)

    t_arr = np.empty(n_steps + 1)
    v_a_arr = np.empty(n_steps + 1)
    v_fe_arr = np.empty(n_steps + 1)
    p_arr = np.empty(n_steps + 1)
    i_arr = np.empty(n_steps + 1)

    e_source = 0.0
    e_joule = 0.0
    e_lk = 0.0
    volume = model.area * model.thickness
    e_landau_0 = volume * model.landau_energy(p)
    e_cap_0 = 0.5 * volume * EPS0 * model.epsilon_r * e_field ** 2
    prev_i = 0.0

    g = model.rs * model.area * EPS0 * model.epsilon_r / dt

    for k in range(n_steps + 1):
        t = k * dt
        v_a = _triangular_ramp(t, v_max, period)
        t_arr[k] = t
        v_a_arr[k] = v_a
        v_fe_arr[k] = e_field * model.thickness
        p_arr[k] = p
        if k == n_steps:
            i_arr[k] = prev_i
            break
        v_next = _triangular_ramp((k + 1) * dt, v_max, period)
        p_new, e_new = p, e_field
        for _ in range(4):
            dpdt = (e_new - model.alpha * p_new - model.beta * p_new ** 3) / model.gamma
            if model.rs <= 0.0:
                e_new = 0.5 * (v_a + v_next) / model.thickness
            else:
                e_new = (
                    0.5 * (v_a + v_next)
                    - model.rs * model.area * dpdt
                    + g * e_field
                ) / (g + model.thickness)
            p_new = p + dt * (
                e_new - model.alpha * p - model.beta * p ** 3
            ) / model.gamma

        dpdt_final = (p_new - p) / dt
        i_new = model.area * (
            EPS0 * model.epsilon_r * (e_new - e_field) / dt + dpdt_final
        )
        i_avg = 0.5 * (prev_i + i_new)
        e_source += 0.5 * (v_a + v_next) * i_avg * dt
        e_joule += model.rs * i_avg ** 2 * dt
        e_lk += volume * model.gamma * dpdt_final ** 2 * dt
        e_field = e_new
        p = p_new
        prev_i = i_new
        i_arr[k + 1] = i_new

    e_landau_change = volume * model.landau_energy(p) - e_landau_0
    e_cap_change = (
        0.5 * volume * EPS0 * model.epsilon_r * e_field ** 2 - e_cap_0
    )
    return {
        "t": t_arr,
        "V_a": v_a_arr,
        "V_fe": v_fe_arr,
        "P": p_arr,
        "I": i_arr,
        "E_source": e_source,
        "E_joule": e_joule,
        "E_lk": e_lk,
        "E_landau_change": e_landau_change,
        "E_cap_change": e_cap_change,
        "energy_residual": (
            e_source - e_joule - e_lk - e_landau_change - e_cap_change
        ),
    }


def run_pulse_protocol(
    model: LKCircuitModel,
    v_step: float,
    hold_time: float,
    n_steps: int,
    p0: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """Voltage-step (pulsed) measurement through the source impedance.

    ``V_a`` steps from 0 to ``v_step`` at t=0 and holds.  With a finite
    source resistance the film voltage ``V_fe`` first charges toward the
    step, then SAGS when the switching-current transient flows (the
    apparent-NC mechanism of Alexe 2025: "even a 50-Ohm pulse-source
    impedance produces the voltage dip"), then recovers.  Under the ideal
    drive (``Rs = 0``) ``V_fe`` is the step itself and cannot dip.

    The LK/circuit discretization is shared with the triangular sweep.
    """
    if not np.isfinite(v_step) or v_step <= 0.0:
        raise ValueError("v_step must be finite and > 0")
    if not np.isfinite(hold_time) or hold_time <= 0.0:
        raise ValueError("hold_time must be finite and > 0")
    if n_steps < 4:
        raise ValueError("n_steps must be >= 4")

    # Sub-step the earliest decade so the RC charge transient (the fastest
    # scale when Rs is small) is resolved without paying for it globally.
    dt_min = hold_time / n_steps
    g = model.rs * model.area * EPS0 * model.epsilon_r / dt_min

    p = -model.ps() if p0 is None else float(p0)
    e_field = model.static_field(p)
    volume = model.area * model.thickness

    t_arr = [0.0]
    v_fe_arr = [e_field * model.thickness]
    p_arr = [p]
    i_arr = [0.0]
    e_source = 0.0
    e_joule = 0.0
    e_lk = 0.0
    e_landau_0 = volume * model.landau_energy(p)
    e_cap_0 = 0.5 * volume * EPS0 * model.epsilon_r * e_field ** 2
    prev_i = 0.0
    t = 0.0

    while t < hold_time:
        dt = dt_min
        p_new, e_new = p, e_field
        for _ in range(4):
            dpdt = (e_new - model.alpha * p_new - model.beta * p_new ** 3) / model.gamma
            if model.rs <= 0.0:
                e_new = v_step / model.thickness
            else:
                e_new = (
                    v_step - model.rs * model.area * dpdt + g * e_field
                ) / (g + model.thickness)
            p_new = p + dt * (
                e_new - model.alpha * p - model.beta * p ** 3
            ) / model.gamma
        dpdt_final = (p_new - p) / dt
        i_new = model.area * (
            EPS0 * model.epsilon_r * (e_new - e_field) / dt + dpdt_final
        )
        i_avg = 0.5 * (prev_i + i_new)
        e_source += v_step * i_avg * dt
        e_joule += model.rs * i_avg ** 2 * dt
        e_lk += volume * model.gamma * dpdt_final ** 2 * dt
        e_field = e_new
        p = p_new
        prev_i = i_new
        t += dt
        t_arr.append(t)
        v_fe_arr.append(e_field * model.thickness)
        p_arr.append(p)
        i_arr.append(i_new)

    e_landau_change = volume * model.landau_energy(p) - e_landau_0
    e_cap_change = (
        0.5 * volume * EPS0 * model.epsilon_r * e_field ** 2 - e_cap_0
    )
    return {
        "t": np.asarray(t_arr),
        "V_a": np.full(len(t_arr), v_step),
        "V_fe": np.asarray(v_fe_arr),
        "P": np.asarray(p_arr),
        "I": np.asarray(i_arr),
        "E_source": e_source,
        "E_joule": e_joule,
        "E_lk": e_lk,
        "E_landau_change": e_landau_change,
        "E_cap_change": e_cap_change,
        "energy_residual": (
            e_source - e_joule - e_lk - e_landau_change - e_cap_change
        ),
    }


def measure_dip(
    sweep: Dict[str, np.ndarray], phase: str = "rise",
) -> float:
    """Depth [V] of the non-monotone V_fe excursion on a monotone V_a phase.

    ``rise`` covers the 0 -> +Vmax quarter, where the NC dip is
    conventionally reported (the sweep defaults to ``p0 = -Ps`` so this
    quarter carries the switching transient).
    """
    v_a = sweep["V_a"]
    v_fe = sweep["V_fe"]
    n = len(v_a)
    quarter = n // 4
    if phase == "rise":
        segment = v_fe[: quarter + 1]
    elif phase == "fall":
        segment = v_fe[quarter: 2 * quarter + 1]
    else:
        raise ValueError("phase must be 'rise' or 'fall'")
    if len(segment) < 3:
        return 0.0
    running_max = np.maximum.accumulate(segment)
    return float(np.max(running_max - segment))


def measure_branch_dip(
    model: LKCircuitModel,
    sweep: Dict[str, np.ndarray],
    phase: str = "rise",
) -> float:
    """Depth [V] of the non-monotone internal branch-voltage excursion.

    The branch voltage ``d*(alpha*P + beta*P^3)`` traverses the negative
    differential capacitance region while the film switches; its
    non-monotonicity is the intrinsic (Landau) NC signature.
    """
    v_a = sweep["V_a"]
    n = len(v_a)
    quarter = n // 4
    if phase == "rise":
        segment = (model.thickness * model.static_field(sweep["P"]))[: quarter + 1]
    elif phase == "fall":
        segment = (model.thickness * model.static_field(sweep["P"]))[
            quarter: 2 * quarter + 1
        ]
    else:
        raise ValueError("phase must be 'rise' or 'fall'")
    if len(segment) < 3:
        return 0.0
    running_max = np.maximum.accumulate(segment)
    running_min = np.minimum.accumulate(segment)
    return float(max(
        np.max(running_max - segment),
        np.max(segment - running_min),
    ))


def measure_pulse_dip(sweep: Dict[str, np.ndarray]) -> float:
    """Sag depth [V] of V_fe below its running maximum during a pulse hold.

    Skips the initial charge transient (the first 10% of the hold) so only
    the switching-induced sag - the apparent-NC signature - is counted.
    """
    v_fe = np.asarray(sweep["V_fe"], dtype=float)
    if len(v_fe) < 10:
        return 0.0
    start = len(v_fe) // 10
    segment = v_fe[start:]
    running_max = np.maximum.accumulate(segment)
    return float(np.max(running_max - segment))


def nc_verdict(
    model: LKCircuitModel,
    v_step: float,
    hold_time: float,
    n_steps: int = 4000,
    dip_floor: float = 1.0e-3,
) -> Dict[str, object]:
    """Dual-verdict pulsed run at the measurement source impedance.

    Reports the terminal sag (apparent NC measured through Rs; identically
    zero under the ideal drive, so its presence IS the source-impedance
    artifact signature - Alexe 2025), the internal branch traverse, and the
    verdict label.  ``dip_floor`` [V] is the resolution below which a
    terminal sag is not counted as an artifact (a 50-Ohm source on a
    micron-scale device manufactures only a microvolt-level sag - the
    physically honest verdict there is ``intrinsic_only``).
    """
    if not np.isfinite(dip_floor) or dip_floor < 0.0:
        raise ValueError("dip_floor must be finite and >= 0")
    measured = LKCircuitModel(**{**model.__dict__})
    ideal = LKCircuitModel(**{**model.__dict__, "rs": 0.0})
    sweep_m = run_pulse_protocol(measured, v_step, hold_time, n_steps)
    sweep_i = run_pulse_protocol(ideal, v_step, hold_time, n_steps)
    dip_terminal = measure_pulse_dip(sweep_m)
    dip_terminal_ideal = measure_pulse_dip(sweep_i)
    branch = measured.thickness * measured.static_field(sweep_m["P"])
    running_max = np.maximum.accumulate(branch)
    dip_branch = float(np.max(running_max - branch))
    artifact = dip_terminal > dip_floor
    if artifact:
        verdict = "artifact"
    elif dip_branch > dip_floor:
        verdict = "intrinsic_only"
    else:
        verdict = "no_dip"
    return {
        "dip_terminal_measurement_V": dip_terminal,
        "dip_terminal_ideal_V": dip_terminal_ideal,
        "dip_branch_intrinsic_V": dip_branch,
        "dip_floor_V": dip_floor,
        "verdict": verdict,
        "energy_residual": sweep_m["energy_residual"],
        "sweep_measurement": sweep_m,
        "sweep_ideal": sweep_i,
    }
