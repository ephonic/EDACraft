"""Calibratable metal--semiconductor contact injection models.

The drift--diffusion solver uses an ideal Schottky-Mott carrier boundary.  This
module supplies the corresponding terminal injection law, including an
effective non-local tunnelling (NLM) correction.  The correction is expressed
as a barrier reduction, rather than a curve multiplier, so its temperature
dependence remains explicit and parameters can be calibrated against a
Sentaurus ``eBarrierTunneling`` deck or measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


K_B_EV = 8.617333262e-5       # Boltzmann constant [eV/K]
RICHARDSON_M0 = 1.20173e6     # 4*pi*q*m0*kB^2/h^3 [A/(m^2 K^2)]


@dataclass(frozen=True)
class SchottkyContactModel:
    """Thermionic/NLM-equivalent Schottky terminal-current model.

    Parameters are SI except energies, which are in eV. ``area_m2`` is the
    physical contact area represented by the reported current.  For a 2-D
    simulation normalized to 1 um depth, multiply the contact edge length by
    ``1e-6``. ``series_resistance_ohm`` is the resistance for that same area.

    ``tunneling_barrier_lowering_eV`` is an effective representation of the
    energy-integrated WKB/non-local transmission.  Zero exactly recovers the
    thermionic-only limit.  It must be calibrated for the barrier mass,
    doping, mesh/path length and interface stack; it is not material truth.
    """

    barrier_height_eV: float
    effective_mass_ratio: float
    area_m2: float = 1.0
    series_resistance_ohm: float = 0.0
    ideality_factor: float = 1.0
    richardson_multiplier: float = 1.0
    tunneling_barrier_lowering_eV: float = 0.0
    tunneling_window_center_eV: Optional[float] = None
    tunneling_window_width_eV: float = 0.025

    def __post_init__(self) -> None:
        finite = (
            self.barrier_height_eV,
            self.effective_mass_ratio,
            self.area_m2,
            self.series_resistance_ohm,
            self.ideality_factor,
            self.richardson_multiplier,
            self.tunneling_barrier_lowering_eV,
            self.tunneling_window_width_eV,
        )
        if not all(math.isfinite(value) for value in finite):
            raise ValueError("Schottky contact parameters must be finite")
        if self.barrier_height_eV < 0.0:
            raise ValueError("barrier_height_eV must be >= 0")
        if self.effective_mass_ratio <= 0.0:
            raise ValueError("effective_mass_ratio must be > 0")
        if self.area_m2 <= 0.0:
            raise ValueError("area_m2 must be > 0")
        if self.series_resistance_ohm < 0.0:
            raise ValueError("series_resistance_ohm must be >= 0")
        if self.ideality_factor <= 0.0:
            raise ValueError("ideality_factor must be > 0")
        if self.richardson_multiplier <= 0.0:
            raise ValueError("richardson_multiplier must be > 0")
        if self.tunneling_barrier_lowering_eV < 0.0:
            raise ValueError("tunneling_barrier_lowering_eV must be >= 0")
        if self.tunneling_window_center_eV is not None:
            if (not math.isfinite(self.tunneling_window_center_eV)
                    or self.tunneling_window_center_eV < 0.0):
                raise ValueError(
                    "tunneling_window_center_eV must be finite and >= 0"
                )
        if self.tunneling_window_width_eV <= 0.0:
            raise ValueError("tunneling_window_width_eV must be > 0")

    @property
    def richardson_constant(self) -> float:
        """Effective Richardson constant [A/(m^2 K^2)]."""
        return (
            RICHARDSON_M0
            * self.effective_mass_ratio
            * self.richardson_multiplier
        )

    def saturation_current(self, temperature_K: float,
                           include_tunneling: bool = False) -> float:
        """Return the thermionic saturation current [A]."""
        if not math.isfinite(temperature_K) or temperature_K <= 0.0:
            raise ValueError("temperature_K must be finite and > 0")
        barrier = self.barrier_height_eV
        if include_tunneling:
            barrier = max(
                barrier - self.tunneling_barrier_lowering_eV, 0.0
            )
        exponent = -barrier / (K_B_EV * temperature_K)
        return (
            self.richardson_constant
            * temperature_K * temperature_K
            * self.area_m2
            * math.exp(max(exponent, -745.0))
        )

    def _diode_current(self, voltage_V: float, temperature_K: float,
                       saturation: float) -> float:
        """Solve one thermionic diode branch with series resistance."""
        thermal_voltage = K_B_EV * temperature_K * self.ideality_factor
        resistance = self.series_resistance_ohm
        if resistance == 0.0:
            argument = max(min(voltage_V / thermal_voltage, 700.0), -745.0)
            return saturation * math.expm1(argument)

        lower = -saturation
        upper = max(voltage_V / resistance, 0.0)
        for _ in range(100):
            current = 0.5 * (lower + upper)
            argument = (voltage_V - current * resistance) / thermal_voltage
            argument = max(min(argument, 700.0), -745.0)
            residual = saturation * math.expm1(argument) - current
            if residual > 0.0:
                lower = current
            else:
                upper = current
        return 0.5 * (lower + upper)

    def current(self, voltage_V: float, temperature_K: float,
                include_tunneling: bool = False) -> float:
        """Return terminal current [A], including the series resistance.

        Solves ``I = Is*(exp((V-I*Rs)/(n*VT))-1)`` by monotone bisection.
        The bounded solve avoids overflow and remains stable at large forward
        bias. If an NLM energy window is configured, the sub-barrier branch is
        smoothly removed as the thermionic junction voltage crosses its upper
        energy limit. This reproduces the physical transition from tunnelling
        to over-barrier transport instead of retaining a false high-bias NLM
        tail.
        """
        if not math.isfinite(voltage_V):
            raise ValueError("voltage_V must be finite")
        thermionic = self._diode_current(
            voltage_V, temperature_K,
            self.saturation_current(temperature_K, False),
        )
        if not include_tunneling or self.tunneling_barrier_lowering_eV == 0.0:
            return thermionic
        enhanced = self._diode_current(
            voltage_V, temperature_K,
            self.saturation_current(temperature_K, True),
        )
        if self.tunneling_window_center_eV is None:
            return enhanced

        # q*Vj in eV is numerically Vj in volts.  The base (thermionic) branch
        # gives a stable estimate of junction voltage independent of the NLM
        # interpolation itself.
        junction_energy_eV = (
            voltage_V - thermionic * self.series_resistance_ohm
        )
        argument = (
            (junction_energy_eV - self.tunneling_window_center_eV)
            / self.tunneling_window_width_eV
        )
        argument = max(min(argument, 700.0), -700.0)
        subbarrier_weight = 1.0 / (1.0 + math.exp(argument))
        return thermionic + (enhanced - thermionic) * subbarrier_weight

    def components(self, voltage_V: float, temperature_K: float) -> dict:
        """Return thermionic, NLM increment, and total currents [A]."""
        thermionic = self.current(voltage_V, temperature_K, False)
        total = self.current(voltage_V, temperature_K, True)
        return {
            "thermionic_A": thermionic,
            "tunneling_increment_A": total - thermionic,
            "total_A": total,
        }
