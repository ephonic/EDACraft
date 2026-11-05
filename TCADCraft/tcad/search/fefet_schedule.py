"""FeFET in-service refresh scheduling (M1 kinetics, TCADCraft-unique).

Problem: a FeFET memory in service suffers three M1 slow-state effects:
- wake-up: remanent polarization grows with cycling (beneficial, saturates)
- fatigue: switchable polarization decays with total stressed cycles
- imprint: internal bias accumulates during same-polarity dwell,
  shifting the memory window (rigid, output-side in our calibrated model)

Refresh (alternating the write polarity on a dummy cycle) resets the
imprint state but the realignment pulse is applied at a HIGHER field,
accelerating fatigue by (E_r/E_w)^p.

Design variable: refresh cadence C_r (cycles between refresh flips).

Objective: maximize the time-integrated usable memory window over a
device lifetime T cycles:
    U(C_r) = integral_0^T max(MW(cycles), 0) d(cycles)

Trade-off:
- Large C_r  -> imprint saturates, window collapses mid-block
- Small C_r  -> refresh stress dominates, fatigue collapses early

An interior optimum is a hypothesis to test for each configured proxy.
Ideal recovery and cycle-domain rates require independent calibration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from ..physics.ferro_kinetics import FieldHistoryCyclingState


@dataclass
class ScheduleConfig:
    """FeFET refresh-schedule design space."""
    # Device / usage
    lifetime_cycles: float = 1.0e6     # total service cycles T
    write_field: float = 3.0e8         # normal write field [V/m]
    # Refresh realignment: flip + restore = 2 switch events at higher field
    refresh_field: float = 4.5e8
    refresh_events_per_block: float = 2.0
    fatigue_field_exponent: float = 2.0
    # M1 kernel parameters
    wakeup_cycles: float = 1.0e3
    fatigue_cycles: float = 1.0e5      # at reference (= write) field
    wakeup_gain: float = 0.15
    fatigue_loss: float = 0.8
    imprint_rate: float = 1e-3         # per cycle at reference field
    imprint_field_max: float = 0.5     # max imprint bias [norm. units]
    # Fraction remaining after refresh. Zero is an ideal recovery proxy,
    # not a measured recovery law; one disables imposed recovery.
    refresh_imprint_retention: float = 0.0
    # Sweep
    cadence_lo_cycles: float = 10.0
    cadence_hi_cycles: float = 1.0e5
    n_cadence: int = 60

    def __post_init__(self) -> None:
        for name in ("lifetime_cycles", "write_field", "refresh_field",
                     "cadence_lo_cycles", "cadence_hi_cycles"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be finite and > 0")
        if self.cadence_hi_cycles < self.cadence_lo_cycles:
            raise ValueError("cadence range must be increasing")
        if (not isinstance(self.n_cadence, int) or isinstance(self.n_cadence, bool)
                or self.n_cadence < 1):
            raise ValueError("n_cadence must be a positive integer")
        if (not math.isfinite(self.refresh_events_per_block)
                or self.refresh_events_per_block < 0):
            raise ValueError("refresh_events_per_block must be finite and >= 0")
        if (not math.isfinite(self.refresh_imprint_retention)
                or not 0 <= self.refresh_imprint_retention <= 1):
            raise ValueError("refresh_imprint_retention must lie in [0, 1]")
        if not math.isfinite(self.wakeup_gain) or self.wakeup_gain < 0:
            raise ValueError("wakeup_gain must be finite and >= 0")
        self.kernel()  # Validate all kinetic parameters at configuration time.

    def kernel(self) -> FieldHistoryCyclingState:
        return FieldHistoryCyclingState(
            wakeup_cycles=self.wakeup_cycles,
            fatigue_cycles=self.fatigue_cycles,
            wakeup_gain=self.wakeup_gain,
            fatigue_loss=self.fatigue_loss,
            reference_field=self.write_field,
            fatigue_field_exponent=self.fatigue_field_exponent,
            imprint_rate=self.imprint_rate,
            imprint_field_exponent=1.0,
            imprint_field_max=self.imprint_field_max,
        )


@dataclass
class ScheduleResult:
    cadence: float                      # C_r [cycles]
    usable_window_integral: float       # summed MW*block [cycle units]
    final_fatigue: float
    max_imprint: float
    mean_window: float
    covered_cycles: float = 0.0
    refresh_count: int = 0
    final_imprint: float = 0.0
    refresh_imprint_retention: float = 0.0

    def as_dict(self) -> Dict:
        return {
            "cadence_cycles": self.cadence,
            "usable_window_integral": self.usable_window_integral,
            "final_fatigue": self.final_fatigue,
            "max_imprint": self.max_imprint,
            "mean_window": self.mean_window,
            "covered_cycles": self.covered_cycles,
            "refresh_count": self.refresh_count,
            "final_imprint": self.final_imprint,
            "refresh_imprint_retention": self.refresh_imprint_retention,
            "recovery_model": "fractional_proxy_unvalidated",
            "time_unit": "service_cycles",
        }


def _dwell_integral(amplitude: float, imprint: float, maximum: float,
                    rate: float, duration: float) -> tuple[float, float]:
    """Exact integral of max(A-B(t), 0), B'=rate*(maximum-B).

    Wake-up and fatigue stay fixed during this no-switching dwell. This
    integrates the declared cycle-domain proxy, not a device energy.
    """
    end = imprint + (maximum - imprint) * (-math.expm1(-rate * duration))
    if rate == 0.0:
        return max(amplitude - imprint, 0.0) * duration, end
    if amplitude <= imprint:
        return 0.0, end
    active_duration = duration
    if amplitude < maximum:
        crossing = math.log1p((amplitude - imprint) / (maximum - amplitude)) / rate
        active_duration = min(duration, crossing)
    integral = ((amplitude - maximum) * active_duration
                + (maximum - imprint) * (-math.expm1(-rate * active_duration)) / rate)
    return max(integral, 0.0), end


def evaluate_schedule(cadence: float,
                      config: Optional[ScheduleConfig] = None
                      ) -> ScheduleResult:
    """Simulate one refresh cadence over the service lifetime.

    Dwell in service-cycle units, then refresh only if service remains.
    Refresh stress advances the cycling kernel; recovery retains the
    configured fraction of imprint. The default ideal recovery requires
    independent calibration before making physical scheduling claims.
    """
    config = config or ScheduleConfig()
    state = config.kernel()

    if not math.isfinite(cadence) or cadence <= 0:
        raise ValueError("cadence must be finite and > 0")
    n_blocks = int(math.ceil(config.lifetime_cycles / cadence))
    integrals = []
    max_imprint = 0.0
    elapsed = 0.0
    refresh_count = 0

    for _block in range(n_blocks):
        target = min((_block + 1) * cadence, config.lifetime_cycles)
        if config.lifetime_cycles - target <= 16 * math.ulp(config.lifetime_cycles):
            target = config.lifetime_cycles
        duration = target - elapsed
        if duration <= 0.0:
            break
        amplitude = (
            (1.0 + config.wakeup_gain * state.wakeup_state)
            * (1.0 - config.fatigue_loss * state.fatigue_state)
        )
        contribution, state.imprint_state = _dwell_integral(
            amplitude, state.imprint_state, config.imprint_field_max,
            config.imprint_rate, duration)
        integrals.append(contribution)
        max_imprint = max(max_imprint, abs(state.imprint_state))
        elapsed = target
        if elapsed == config.lifetime_cycles:
            break
        if config.refresh_events_per_block > 0.0:
            retained = state.imprint_state * config.refresh_imprint_retention
            state.advance(cycles=config.refresh_events_per_block,
                          electric_field=config.refresh_field)
            # Recovery is a declared proxy, separate from cycling damage.
            state.imprint_state = retained
            refresh_count += 1

    integral = math.fsum(integrals)
    mean_window = integral / config.lifetime_cycles
    return ScheduleResult(
        cadence=cadence,
        usable_window_integral=integral,
        final_fatigue=state.fatigue_state,
        max_imprint=max_imprint,
        mean_window=mean_window,
        covered_cycles=elapsed,
        refresh_count=refresh_count,
        final_imprint=state.imprint_state,
        refresh_imprint_retention=config.refresh_imprint_retention,
    )


def sweep_cadences(config: Optional[ScheduleConfig] = None
                   ) -> List[ScheduleResult]:
    config = config or ScheduleConfig()
    cadences = np.logspace(
        math.log10(config.cadence_lo_cycles),
        math.log10(config.cadence_hi_cycles),
        config.n_cadence,
    )
    return [evaluate_schedule(c, config) for c in cadences]


def find_optimal_cadence(config: Optional[ScheduleConfig] = None
                         ) -> ScheduleResult:
    results = sweep_cadences(config)
    return max(results, key=lambda r: r.mean_window)


def scaling_signature(config: Optional[ScheduleConfig] = None) -> Dict:
    """Measure how C_r* scales with imprint rate and fatigue lifetime.

    With ideal recovery, no wake-up, small damage and small imprint:
      loss ~ fatigue_loss*T/(2*N_eff*C) + B_max*rate*C/2
      C* ~ sqrt(fatigue_loss*T/(N_eff*B_max*rate)).
    Report the assumptions separately from observed discrete sweep optima;
    this asymptotic balance is not a universal or experimentally verified law.
    """
    config = config or ScheduleConfig()
    out = {}
    base = find_optimal_cadence(config)
    out["base_cadence"] = base.cadence

    fatigue_accel = (config.refresh_field / config.write_field) \
        ** config.fatigue_field_exponent
    stress = fatigue_accel * config.refresh_events_per_block
    n_fatigue_eff = config.fatigue_cycles / stress if stress > 0 else None
    out["n_fatigue_eff"] = n_fatigue_eff
    prediction = None
    if (n_fatigue_eff is not None and config.fatigue_loss > 0
            and config.imprint_field_max > 0 and config.imprint_rate > 0):
        prediction = math.sqrt(config.fatigue_loss * config.lifetime_cycles
                               / (n_fatigue_eff * config.imprint_field_max * config.imprint_rate))
    out["asymptotic_cadence"] = prediction
    out["asymptotic_regime_satisfied"] = bool(
        prediction is not None and config.wakeup_gain == 0
        and config.refresh_imprint_retention == 0
        and config.imprint_rate * prediction < 0.1
        and config.lifetime_cycles / (n_fatigue_eff * prediction) < 0.1
        and prediction / config.lifetime_cycles < 0.01)
    out["prediction_scope"] = "ideal_recovery_no_wakeup_small_damage_small_imprint"

    cfg2 = ScheduleConfig(**{**config.__dict__, "imprint_rate":
                             config.imprint_rate / 4.0})
    r2 = find_optimal_cadence(cfg2)
    out["cadence_at_imprint_x0.25"] = r2.cadence
    out["predicted_imprint_shift"] = 2.0
    out["observed_imprint_shift"] = (r2.cadence / base.cadence
                                     if base.cadence else float("nan"))

    cfg3 = ScheduleConfig(**{**config.__dict__, "fatigue_cycles":
                             config.fatigue_cycles * 4.0})
    r3 = find_optimal_cadence(cfg3)
    out["cadence_at_fatigue_x4"] = r3.cadence
    out["predicted_fatigue_shift"] = 0.5
    out["observed_fatigue_shift"] = (r3.cadence / base.cadence
                                     if base.cadence else float("nan"))
    return out


def discover_refresh_schedule():
    print("=" * 70)
    print("TCADCRAFT-UNIQUE DISCOVERY: FeFET Refresh Scheduling (M1)")
    print("Imprint-vs-fatigue trade-off over device lifetime")
    print("=" * 70)
    config = ScheduleConfig()
    results = sweep_cadences(config)
    best = max(results, key=lambda r: r.mean_window)

    print(f"\nLifetime {config.lifetime_cycles:.0e} cycles, "
          f"imprint_rate={config.imprint_rate:.0e}/cycle, "
          f"fatigue_cycles={config.fatigue_cycles:.0e}")
    print(f"\n{'cadence':>10s} {'mean window':>12s} {'final fatigue':>14s} "
          f"{'max imprint':>12s}")
    print("-" * 55)
    for r in results[:: max(1, len(results) // 12)]:
        print(f"{r.cadence:10.0f} {r.mean_window:12.4f} "
              f"{r.final_fatigue:14.4f} {r.max_imprint:12.4f}")

    print(f"\nOPTIMAL CADENCE: {best.cadence:.0f} cycles  "
          f"(mean window {best.mean_window:.4f})")
    sig = scaling_signature(config)
    print(f"\nScaling signature:")
    print(f"  asymptotic estimate = {sig['asymptotic_cadence']} cycles; "
          f"regime satisfied = {sig['asymptotic_regime_satisfied']}")
    print(f"  imprint_rate/4 -> C_r* x{sig['observed_imprint_shift']:.2f} "
          f"(predicted x{sig['predicted_imprint_shift']:.2f})")
    print(f"  fatigue x4     -> C_r* x{sig['observed_fatigue_shift']:.2f} "
          f"(predicted x{sig['predicted_fatigue_shift']:.2f})")

    return {
        "sweep": [r.as_dict() for r in results],
        "optimal": best.as_dict(),
        "signature": sig,
    }


if __name__ == "__main__":
    discover_refresh_schedule()
