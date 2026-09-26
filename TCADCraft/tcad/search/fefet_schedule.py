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
    U(C_r) = sum over blocks of MW(cycles) * block_length

Trade-off:
- Large C_r  -> imprint saturates, window collapses mid-block
- Small C_r  -> refresh stress dominates, fatigue collapses early

Discovery target: an interior optimum C_r* and its scaling law with
imprint rate and fatigue lifetime (signature: C_r* ~ sqrt of the
imprint x fatigue lifetime product).
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
    # Sweep
    cadence_lo_cycles: float = 10.0
    cadence_hi_cycles: float = 1.0e5
    n_cadence: int = 60

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

    def as_dict(self) -> Dict:
        return {
            "cadence_cycles": self.cadence,
            "usable_window_integral": self.usable_window_integral,
            "final_fatigue": self.final_fatigue,
            "max_imprint": self.max_imprint,
            "mean_window": self.mean_window,
        }


def evaluate_schedule(cadence: float,
                      config: Optional[ScheduleConfig] = None
                      ) -> ScheduleResult:
    """Simulate one refresh cadence over the service lifetime.

    Protocol per block of C_r cycles:
      - C_r - 1 write cycles at write_field alternating polarity each cycle
        (so imprint does NOT accumulate from repeated same-polarity writes;
        in real arrays, adjacent blocks store opposite data, and the worst
        case is a long same-value dwell -- modeled as write_field hold)
      - 1 refresh flip at refresh_field (opposite polarity) that erases
        imprint and pays accelerated fatigue
    """
    config = config or ScheduleConfig()
    state = config.kernel()

    cadence = max(cadence, 1.0)
    n_blocks = int(math.ceil(config.lifetime_cycles / cadence))
    integral = 0.0
    max_imprint = 0.0

    for _block in range(n_blocks):
        # Same-polarity dwell for the block duration (worst-case storage):
        # imprint advances under the held field; no switching occurs, so
        # wake-up/fatigue do not advance during the dwell.
        dwell_gain = 1.0 - math.exp(-config.imprint_rate * cadence)
        state.imprint_state = (
            config.imprint_field_max
            + (state.imprint_state - config.imprint_field_max)
            * (1.0 - dwell_gain)
        )
        max_imprint = max(max_imprint, abs(state.imprint_state))

        # Usable window in this block: pristine window with wake-up boost,
        # degraded by fatigue loss and the current imprint bias.
        window = (
            (1.0 + config.wakeup_gain * state.wakeup_state)
            * (1.0 - config.fatigue_loss * state.fatigue_state)
            - abs(state.imprint_state)
        )
        integral += max(window, 0.0) * cadence

        # Refresh: flip + restore at the higher field erases imprint and
        # pays accelerated fatigue (2 stressed events per refresh).
        state.imprint_state = 0.0
        state.advance(cycles=config.refresh_events_per_block,
                      electric_field=config.refresh_field)

    mean_window = integral / config.lifetime_cycles
    return ScheduleResult(
        cadence=cadence,
        usable_window_integral=integral,
        final_fatigue=state.fatigue_state,
        max_imprint=max_imprint,
        mean_window=mean_window,
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


def scaling_signature(config: Optional[ScheduleConfig] = None) -> Dict[str, float]:
    """Measure how C_r* scales with imprint rate and fatigue lifetime.

    Balance analysis (small-rC, linearized imprint): the mean-window loss is
        L(C) ~ K/C + 0.25*r*C,  K ~ fatigue cost per refresh * T
    giving C* = sqrt(K / (0.25 r)) ~ sqrt(T * r / N_fatigue_eff / r)
    = sqrt(T / N_fatigue_eff) -- INDEPENDENT of r to first order, with
    imprint-rate entering only through higher-order terms. Signature
    checks below probe the leading responses:
      - imprint_rate /4  -> C* x ~2 (from the 0.25*r*C linear term)
      - fatigue x4 (N_fatigue_eff x4) -> C* x ~1/2 (refresh gets cheaper)
    """
    config = config or ScheduleConfig()
    out = {}
    base = find_optimal_cadence(config)
    out["base_cadence"] = base.cadence

    fatigue_accel = (config.refresh_field / config.write_field) \
        ** config.fatigue_field_exponent
    n_fatigue_eff = config.fatigue_cycles / fatigue_accel \
        * config.refresh_events_per_block
    out["n_fatigue_eff"] = n_fatigue_eff
    out["sqrt_t_over_nf"] = math.sqrt(config.lifetime_cycles / n_fatigue_eff)

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
    print(f"  sqrt(T / N_fatigue_eff) = {sig['sqrt_t_over_nf']:.0f} cycles")
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
