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
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation,
                     Overflow, ROUND_HALF_EVEN, localcontext)
import math
import sys
from typing import Optional


K_B_EV = 8.617333262e-5       # Boltzmann constant [eV/K]
RICHARDSON_M0 = 1.20173e6     # 4*pi*q*m0*kB^2/h^3 [A/(m^2 K^2)]


class _SeriesCurrentUnderflow(ValueError):
    """A nonzero series root rounds to zero at public float64 export."""


class _WindowLogRangeError(ValueError):
    """A finite-input window needs wider internal logarithms."""


def pinned_schottky_barrier_height(
    workfunction_eV: float,
    electron_affinity_eV: float,
    *,
    pinning_factor: float = 1.0,
    charge_neutrality_level_eV: Optional[float] = None,
) -> float:
    """Return an electron Schottky barrier with optional Fermi-level pinning.

    ``pinning_factor`` is the usual interface-slope parameter ``S``:

    * ``S=1`` gives the Schottky-Mott limit ``Phi_m - chi``.
    * ``S=0`` pins the electron barrier to
      ``charge_neutrality_level_eV - chi``.

    Energies are referenced to the vacuum level.  The result is clamped to the
    accumulation/ohmic limit at zero barrier, matching the existing contact
    boundary behavior.
    """
    values = (workfunction_eV, electron_affinity_eV, pinning_factor)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("workfunction, electron affinity and pinning factor must be finite")
    if not 0.0 <= pinning_factor <= 1.0:
        raise ValueError("pinning_factor must be in [0, 1]")
    if charge_neutrality_level_eV is None:
        charge_neutrality_level_eV = workfunction_eV
    if not math.isfinite(charge_neutrality_level_eV):
        raise ValueError("charge_neutrality_level_eV must be finite")
    effective_workfunction = (
        pinning_factor * workfunction_eV
        + (1.0 - pinning_factor) * charge_neutrality_level_eV
    )
    return max(effective_workfunction - electron_affinity_eV, 0.0)


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
    transport_saturation_current_A: Optional[float] = None
    tunneling_cutoff_energy_eV: Optional[float] = None
    tunneling_decay_exponent: float = 1.0

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
            self.tunneling_decay_exponent,
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
        if self.transport_saturation_current_A is not None:
            if (not math.isfinite(self.transport_saturation_current_A)
                    or self.transport_saturation_current_A <= 0.0):
                raise ValueError(
                    "transport_saturation_current_A must be finite and > 0"
                )
        if self.tunneling_cutoff_energy_eV is not None:
            if (not math.isfinite(self.tunneling_cutoff_energy_eV)
                    or self.tunneling_cutoff_energy_eV <= 0.0):
                raise ValueError(
                    "tunneling_cutoff_energy_eV must be finite and > 0"
                )
        if self.tunneling_decay_exponent <= 0.0:
            raise ValueError("tunneling_decay_exponent must be > 0")

    @property
    def richardson_constant(self) -> float:
        """Effective Richardson constant [A/(m^2 K^2)], rounded once.

        Reject nonzero values that cannot be exported. Currents still combine
        all factors independently and do not require this property to fit.
        """
        # Three finite positive binary factors form an exact integer ratio.
        # Divide once to avoid intermediate overflow and double rounding at
        # the subnormal/overflow boundaries. Logarithms lose boundary bits.
        ratios = [value.as_integer_ratio() for value in
                  (RICHARDSON_M0, self.effective_mass_ratio, self.richardson_multiplier)]
        try:
            result = math.prod(pair[0] for pair in ratios) / math.prod(pair[1] for pair in ratios)
        except OverflowError as exc:
            raise ValueError("Richardson constant is not representable in float64") from exc
        if result == 0.:
            raise ValueError("nonzero Richardson constant is not representable in float64")
        return result

    def saturation_current(self, temperature_K: float,
                           include_tunneling: bool = False) -> float:
        """Return saturation current [A], rejecting unrepresentable values."""
        if not isinstance(include_tunneling, bool):
            raise ValueError("include_tunneling must be an explicit boolean")
        barrier = self.barrier_height_eV
        if include_tunneling:
            barrier = max(
                barrier - self.tunneling_barrier_lowering_eV, 0.0
            )
        thermal = self._thermal_voltage(temperature_K)
        return self._export_current(
            self._log_prefactor(temperature_K) - barrier / thermal,
            "saturation current",
        )

    @staticmethod
    def _thermal_voltage(temperature_K: float) -> float:
        if not math.isfinite(temperature_K) or temperature_K <= 0.:
            raise ValueError("temperature_K must be finite and > 0")
        thermal = K_B_EV * temperature_K
        if not math.isfinite(thermal) or thermal <= 0.:
            raise ValueError("thermal voltage is not representable in float64")
        return thermal

    def _log_prefactor(self, temperature_K: float) -> float:
        # Each factor is positive. Do not multiply the Richardson factors or
        # T^2 before taking logs: their product can overflow or underflow even
        # when the final physical current is representable.
        return math.fsum((math.log(RICHARDSON_M0),
                          math.log(self.effective_mass_ratio),
                          math.log(self.richardson_multiplier),
                          math.log(self.area_m2),
                          2. * math.log(temperature_K)))

    @staticmethod
    def _export_current(log_value: float, label: str = "diode current") -> float:
        if not math.isfinite(log_value) or log_value > math.log(sys.float_info.max):
            raise ValueError(f"{label} is not representable in float64")
        result = math.exp(log_value)
        if result == 0.:
            raise ValueError(f"nonzero {label} is not representable in float64")
        return result

    def _branch_current(self, voltage_V: float, temperature_K: float,
                        barrier: float, *, logarithmic: bool = False) -> float:
        thermal = self._thermal_voltage(temperature_K)
        voltage_scale = thermal * self.ideality_factor
        if not math.isfinite(voltage_scale) or voltage_scale <= 0.:
            raise ValueError("thermal voltage is not representable in float64")
        if voltage_V == 0.:
            return -math.inf if logarithmic else 0.
        prefactor = self._log_prefactor(temperature_K)
        if self.series_resistance_ohm != 0.:
            return self._diode_current(voltage_V, temperature_K,
                                       prefactor - barrier / thermal,
                                       logarithmic=logarithmic)

        argument = voltage_V / voltage_scale
        if abs(argument) <= .5:
            # expm1(x)/x -> 1, including x rounded to zero. Keeping the drive
            # as logarithms also recovers large-prefactor, tiny-bias currents.
            correction = math.log(math.expm1(argument) / argument) if argument else 0.
            log_current = math.fsum((prefactor, -barrier / thermal,
                                    math.log(abs(voltage_V)),
                                    -math.log(voltage_scale), correction))
        elif argument > 0.:
            # Combine barrier and applied energy BEFORE exponentiation. Is
            # and exp(V/nVT) need not individually fit in a float64.
            activation = (voltage_V / self.ideality_factor - barrier) / thermal
            log_current = math.fsum((prefactor, activation,
                                    math.log(-math.expm1(-argument))))
        else:
            log_current = math.fsum((prefactor, -barrier / thermal,
                                    math.log(-math.expm1(argument))))
        if logarithmic:
            return log_current
        magnitude = self._export_current(log_current)
        return math.copysign(magnitude, voltage_V)

    @staticmethod
    def _log_add_positive(first: float, second: float) -> float:
        larger, smaller = max(first, second), min(first, second)
        return (larger if not math.isfinite(larger) else
                larger + math.log1p(math.exp(smaller - larger)))

    @staticmethod
    def _log_softplus(value: float) -> float:
        """log(log1p(exp(value))) without exporting a tiny inner result."""
        if value < -38.:
            return value
        return math.log(value + math.log1p(math.exp(-value)) if value > 0.
                        else math.log1p(math.exp(value)))

    def _injection_barrier(self, voltage_V: float) -> float:
        """Float-valued effective barrier, including the optional energy cutoff."""
        lowering = self.tunneling_barrier_lowering_eV
        if self.tunneling_cutoff_energy_eV is not None:
            available = max(1. - max(voltage_V, 0.) / self.tunneling_cutoff_energy_eV, 0.)
            lowering *= available ** self.tunneling_decay_exponent
        return max(self.barrier_height_eV - lowering, 0.)

    @staticmethod
    def _log_gain_fraction(reduction: float, thermal: float) -> float:
        """log(1-exp(-reduction/thermal)), retaining subnormal energy ratios."""
        gain = reduction / thermal
        if gain < .5:
            correction = math.log(-math.expm1(-gain) / gain) if gain else 0.
            return math.log(reduction) - math.log(thermal) + correction
        return math.log(-math.expm1(-gain))

    def _highfield_log_gap(self, voltage_V: float, log_scale: float,
                           log_saturation: float) -> float:
        """Resolve log(1-I/Ilimit) from the complete forward voltage law."""
        log_limit = math.log(self.transport_saturation_current_A)
        log_bulk_scale = math.log(self.series_resistance_ohm) + log_limit
        target = math.log(voltage_V)

        def required(log_gap: float) -> float:
            if log_gap == 0.:
                return -math.inf
            log_fraction = math.log(-math.expm1(log_gap))
            log_current = log_limit + log_fraction
            junction = log_scale + self._log_softplus(log_current - log_saturation)
            bulk = math.fsum((log_bulk_scale, log_fraction, -log_gap))
            return self._log_add_positive(junction, bulk)

        # The bulk-only gap gives Vbulk=V; adding the junction drop brackets
        # the full root towards a larger gap. The zero-current endpoint is 1.
        lower = math.nextafter(
            log_bulk_scale - self._log_add_positive(target, log_bulk_scale), -math.inf)
        upper = 0.
        if not math.isfinite(lower) or lower >= 0.:
            raise ValueError("high-field gap logarithm is not representable")
        for _ in range(8):
            if required(lower) >= target:
                break
            lower = math.nextafter(lower, -math.inf)
        else:
            raise ValueError("high-field gap bracket is not representable")
        for _ in range(2200):
            middle = lower + (upper - lower) * .5
            if middle == lower or middle == upper:
                return middle
            value = required(middle)
            if value == target:
                return middle
            if value > target:
                lower = middle
            else:
                upper = middle
        raise RuntimeError("Schottky high-field gap bracket did not converge")

    def _series_injection_difference(self, voltage_V: float, temperature_K: float,
                                     log_base: float, effective: float,
                                     base_current: Optional[float] = None) -> tuple:
        """Solve the positive current increment from a voltage-difference law.

        At fixed bias, J1(I0+dI)-J1(I0)+B(I0+dI)-B(I0)
        equals J0(I0)-J1(I0). No nearly equal terminal roots are subtracted.
        """
        thermal = self._thermal_voltage(temperature_K)
        scale = thermal * self.ideality_factor
        log_scale = math.log(scale)
        prefactor = self._log_prefactor(temperature_K)
        log_saturation = prefactor - self.barrier_height_eV / thermal
        forward = voltage_V > 0.
        log_gap = None
        log_gap_fraction = 0.
        if forward and self.transport_saturation_current_A is not None:
            limit = self.transport_saturation_current_A
            if base_current is not None:
                gap = limit - abs(base_current)
                if gap <= 0.:
                    raise ValueError("transport increment bracket is not representable")
                log_gap = math.log(gap)
                log_gap_fraction = log_gap - math.log(limit)
            else:
                ratio_limit = log_base - math.log(limit)
                if ratio_limit >= 0.:
                    raise ValueError("transport increment bracket is not representable")
                log_gap_fraction = math.log(-math.expm1(ratio_limit))
                log_gap = math.log(limit) + log_gap_fraction
            if log_gap_fraction < math.log(.01):
                # Export rounding in I0 is amplified by a small limit-I0.
                # Solve the physical gap before calculating the gain and both
                # high-field denominators; do not infer it from rounded I0.
                log_gap_fraction = self._highfield_log_gap(voltage_V, log_scale, log_saturation)
                log_gap = math.log(limit) + log_gap_fraction
                log_base = math.log(limit) + math.log(-math.expm1(log_gap_fraction))
        ratio = log_base - log_saturation
        saturated_reverse = not forward and ratio > -.01
        if saturated_reverse:
            # Near reverse saturation the exported current cannot resolve
            # the deficit accurately. Recover J from
            # |V|=J+Is*R*(1-exp(-J/nVT)), without subtracting I from Is.
            log_bulk_limit = log_saturation + math.log(self.series_resistance_ohm)
            lower_j, upper_j = 0., abs(voltage_V)
            for _ in range(2200):
                junction = lower_j + (upper_j - lower_j) * .5
                if junction == lower_j or junction == upper_j:
                    break
                argument = junction / scale
                fraction_log = (math.log(-math.expm1(-argument)) if argument else
                                math.log(junction) - log_scale)
                bulk_log = log_bulk_limit + fraction_log
                bulk = math.inf if bulk_log > math.log(sys.float_info.max) else math.exp(bulk_log)
                required_j = junction + bulk
                if required_j == abs(voltage_V):
                    break
                if required_j < abs(voltage_V):
                    lower_j = junction
                else:
                    upper_j = junction
            else:
                raise RuntimeError("reverse junction bracket did not converge")
        elif ratio < -38.:
            junction = math.exp(math.fsum((log_scale, log_base, -log_saturation)))
        elif forward:
            junction = scale * (ratio + math.log1p(math.exp(-ratio)) if ratio > 0.
                                else math.log1p(math.exp(ratio)))
        else:
            junction = scale * (-math.log(-math.expm1(ratio)) if ratio > -math.log(2.)
                                else -math.log1p(-math.exp(ratio)))
        junction = math.copysign(junction, voltage_V)
        reduction = self.barrier_height_eV - effective
        if reduction == 0.:
            return None, junction
        gain = reduction / thermal
        log_fraction = self._log_gain_fraction(reduction, thermal)
        log_saturation1 = prefactor - effective / thermal
        # D0=Is0+I0 forward, Is0-I0 reverse; D1=D0+(Is1-Is0).
        log_d0 = (self._log_add_positive(log_saturation, log_base) if forward else
                  log_saturation - abs(junction) / scale if saturated_reverse else
                  log_saturation + math.log(-math.expm1(ratio)))
        log_d1 = self._log_add_positive(log_d0, log_saturation1 + log_fraction)
        if forward:
            denominator = self._log_add_positive(log_saturation, log_base - gain)
            log_q = math.fsum((log_base, log_fraction, -denominator))
        else:
            log_q = math.fsum((log_base, log_fraction, -log_d0))
        if not forward and not math.isfinite(log_d0):
            voltage_gain = math.fsum((abs(junction), scale * (log_base + log_fraction - log_saturation)))
            target = math.log(voltage_gain)
        else:
            target = log_scale + self._log_softplus(log_q)
        log_resistance = math.log(self.series_resistance_ohm)

        def required(log_delta: float) -> float:
            ratio_delta = log_delta - log_d1
            if forward:
                log_junction = log_scale + self._log_softplus(ratio_delta)
            else:
                if ratio_delta >= 0.:
                    return math.inf
                if ratio_delta < -38.:
                    log_junction = log_scale + ratio_delta
                else:
                    factor = (-math.log(-math.expm1(ratio_delta)) if ratio_delta > -math.log(2.)
                              else -math.log1p(-math.exp(ratio_delta)))
                    log_junction = log_scale + math.log(factor)
            log_bulk = log_resistance + log_delta
            if log_gap is not None:
                if log_delta >= log_gap:
                    return math.inf
                # Exact B(I0+dI)-B(I0), including both high-field denominators.
                log_bulk -= 2. * log_gap_fraction + math.log(-math.expm1(log_delta - log_gap))
            return self._log_add_positive(log_junction, log_bulk)

        upper = math.nextafter(target - log_resistance, math.inf)
        if log_gap is not None:
            upper = min(upper, log_gap)
        if not forward:
            upper = min(upper, log_d1)
        if not math.isfinite(upper) or not math.isfinite(target):
            raise ValueError("series increment logarithm is not representable")
        for _ in range(8):
            if required(upper) >= target:
                break
            upper = math.nextafter(upper, math.inf)
        else:
            raise ValueError("series increment bracket is not representable")
        step = 1.
        lower = upper - step
        for _ in range(1024):
            if not math.isfinite(lower):
                raise ValueError("series increment lower bracket is not representable")
            if required(lower) <= target:
                break
            step *= 2.
            lower = upper - step
        else:
            raise ValueError("series increment lower bracket is not representable")
        for _ in range(2200):
            middle = lower + (upper - lower) * .5
            if middle == lower or middle == upper:
                return middle, junction
            value = required(middle)
            if value == target:
                return middle, junction
            if value < target:
                lower = middle
            else:
                upper = middle
        raise RuntimeError("Schottky increment bracket did not converge")

    def _window_log_currents(self, voltage_V: float, temperature_K: float) -> tuple:
        """Return branch magnitudes, window weight and total in log space."""
        junction = voltage_V
        log_delta = None
        if self.series_resistance_ohm != 0.:
            try:
                base_current = self._branch_current(voltage_V, temperature_K, self.barrier_height_eV)
            except _SeriesCurrentUnderflow:
                base_current = None
            if base_current is not None and abs(base_current) >= sys.float_info.min:
                base = math.log(abs(base_current))
            else:
                # Subnormal or unexportable roots must retain continuous
                # magnitude before deriving junction voltage and window gain.
                base = self._branch_current(voltage_V, temperature_K,
                                            self.barrier_height_eV, logarithmic=True)
                base_current = None
            log_delta, junction = self._series_injection_difference(
                voltage_V, temperature_K, base, self._injection_barrier(voltage_V), base_current)
            enhanced = base if log_delta is None else self._log_add_positive(base, log_delta)
        else:
            base = self._branch_current(voltage_V, temperature_K,
                                        self.barrier_height_eV, logarithmic=True)
            enhanced = self._branch_current(voltage_V, temperature_K,
                self._injection_barrier(voltage_V),
                logarithmic=True)
        argument = ((junction - self.tunneling_window_center_eV)
                    / self.tunneling_window_width_eV)
        # Stable log(sigmoid(-x)) and log(1-sigmoid(-x)), without a tail clip.
        correction = math.log1p(math.exp(-abs(argument)))
        log_weight = -max(argument, 0.) - correction
        log_complement = min(argument, 0.) - correction
        if self.series_resistance_ohm != 0.:
            increment = None if log_delta is None else log_delta + log_weight
            total = base if increment is None else self._log_add_positive(base, increment)
            return base, enhanced, log_weight, total, increment
        terms = (base + log_complement, enhanced + log_weight)
        if any(math.isnan(value) for value in terms):
            raise ValueError("window current combination is not representable in float64")
        larger, smaller = max(terms), min(terms)
        total = (larger if not math.isfinite(larger) else
                 larger + math.log1p(math.exp(smaller - larger)))
        return base, enhanced, log_weight, total, None

    def _bulk_voltage_drop(self, current_A: float) -> float:
        """Return the drift-region drop including velocity saturation.

        For the common first-order high-field mobility law

        ``v = mu*E / (1 + mu*E/vsat)``,

        eliminating ``E`` gives ``Vbulk = I*R0/(1-I/Isat)``.  The optional
        current limit is therefore a physical ``q*n*vsat*area`` parameter,
        not a hard numerical current clip.  Reverse bias retains the low-field
        resistance because the present calibration exercises forward
        injection only.
        """
        if current_A < 0.0 or self.transport_saturation_current_A is None:
            return current_A * self.series_resistance_ohm
        fraction = current_A / self.transport_saturation_current_A
        return (
            current_A * self.series_resistance_ohm
            / max(1.0 - fraction, 1.0e-15)
        )

    def _diode_current(self, voltage_V: float, temperature_K: float,
                       log_saturation: float, *, logarithmic: bool = False) -> float:
        """Invert the series voltage law without exporting saturation current."""
        thermal_voltage = K_B_EV * temperature_K * self.ideality_factor
        if not math.isfinite(thermal_voltage) or thermal_voltage <= 0.:
            raise ValueError("thermal voltage is not representable in float64")
        if not math.isfinite(log_saturation):
            raise ValueError("log saturation current is not representable in float64")
        if voltage_V == 0.:
            return -math.inf if logarithmic else 0.
        resistance = self.series_resistance_ohm
        transport_limit = self.transport_saturation_current_A
        if resistance == 0.:
            raise ValueError("use the combined exponential law for zero series resistance")

        forward = voltage_V > 0.
        target = abs(voltage_V)
        log_voltage_comparison = logarithmic or target < sys.float_info.min
        comparison_target = math.log(target) if log_voltage_comparison else target
        log_thermal_voltage = math.log(thermal_voltage)
        log_resistance = math.log(resistance)
        # Invert the diode law: V = VT*log1p(I/Is) + Vbulk(I).
        # Both terms have the current's sign. This avoids subtracting nearly
        # equal terminal and bulk voltages inside an exponential residual.
        lower = 0.
        # Round the ohmic bound outward; rounding V/R down must not turn a
        # representable, nearly ohmic root into a rejected bracket.
        upper = min(math.nextafter(target / resistance, math.inf), sys.float_info.max)
        if not forward:
            if log_saturation <= math.log(sys.float_info.max):
                # Round outward: the physical Is need not itself be exactly
                # representable, and may lie between subnormal currents.
                saturation_bound = math.exp(log_saturation)
                upper = min(upper, math.nextafter(saturation_bound, math.inf))
        elif transport_limit is not None:
            upper = min(upper, math.nextafter(transport_limit, 0.))

        def required_voltage(magnitude: float, log_magnitude: Optional[float] = None) -> float:
            if log_magnitude is None:
                if magnitude == 0.:
                    return -math.inf if log_voltage_comparison else 0.
                log_magnitude = math.log(magnitude)
            ratio_log = log_magnitude - log_saturation
            if not forward and ratio_log >= 0.:
                return math.inf
            fraction = 0.
            if forward and transport_limit is not None:
                fraction = (magnitude / transport_limit if magnitude != 0. else
                            math.exp(log_magnitude - math.log(transport_limit)))
                if fraction >= 1.:
                    return math.inf
            if ratio_log < -38.:
                # log1p(r)/r and -log1p(-r)/r round to 1 here. Form
                # VT*r together: r may underflow while its voltage does not.
                log_junction_voltage = math.fsum((log_thermal_voltage,
                                                  log_magnitude, -log_saturation))
                if not log_voltage_comparison:
                    junction_voltage = math.exp(log_junction_voltage)
            elif forward:
                junction = (ratio_log + math.log1p(math.exp(-ratio_log))
                            if ratio_log > 0. else math.log1p(math.exp(ratio_log)))
                junction_voltage = thermal_voltage * junction
                log_junction_voltage = log_thermal_voltage + math.log(junction)
            else:
                # expm1 preserves the small distance to the reverse Is bound.
                junction = (-math.log(-math.expm1(ratio_log)) if ratio_log > -math.log(2.)
                            else -math.log1p(-math.exp(ratio_log)))
                junction_voltage = thermal_voltage * junction
                log_junction_voltage = log_thermal_voltage + math.log(junction)
            if log_voltage_comparison:
                # Subnormal terminal voltages otherwise create wide residual
                # plateaus: both components can round before their sum.
                log_bulk = log_magnitude + log_resistance
                if forward and transport_limit is not None:
                    log_bulk -= math.log1p(-fraction)
                larger = max(log_junction_voltage, log_bulk)
                smaller = min(log_junction_voltage, log_bulk)
                return larger + math.log1p(math.exp(smaller - larger))
            bulk = magnitude * resistance
            if magnitude == 0.:
                # Used only to assess the real half-minimum current at export.
                bulk = math.exp(log_magnitude + log_resistance)
            if forward and transport_limit is not None:
                bulk /= 1. - fraction
            return junction_voltage + bulk

        if logarithmic:
            # A window can have a nonexportable thermionic root and a finite
            # total. Solve for the continuous log magnitude, without rounding
            # an intermediate current or applying a minimum-current floor.
            upper_log = math.nextafter(math.log(target) - log_resistance, math.inf)
            if not forward:
                upper_log = min(upper_log, math.nextafter(log_saturation, math.inf))
            elif transport_limit is not None:
                upper_log = min(upper_log, math.log(transport_limit))
            if not math.isfinite(upper_log):
                raise ValueError("series current logarithm is not representable")
            for _ in range(8):
                if required_voltage(0., upper_log) >= comparison_target:
                    break
                upper_log = math.nextafter(upper_log, math.inf)
            else:
                raise ValueError("logarithmic current bracket is not representable")
            step = 1.
            lower_log = upper_log - step
            for _ in range(1024):
                if not math.isfinite(lower_log):
                    raise ValueError("series current logarithm is not representable")
                if required_voltage(0., lower_log) <= comparison_target:
                    break
                step *= 2.
                lower_log = upper_log - step
            else:
                raise ValueError("logarithmic current bracket is not representable")
            for _ in range(2200):
                middle_log = lower_log + (upper_log - lower_log) * .5
                if middle_log == lower_log or middle_log == upper_log:
                    return middle_log
                value = required_voltage(0., middle_log)
                if value == comparison_target:
                    return middle_log
                if value < comparison_target:
                    lower_log = middle_log
                else:
                    upper_log = middle_log
            raise RuntimeError("Schottky logarithmic bracket did not converge")

        if required_voltage(upper) < comparison_target:
            raise ValueError("diode current is outside the representable bracket")
        # The initial interval may span the entire float64 exponent range.
        # Stop only when its endpoints are adjacent, or the voltage matches;
        # a fixed 100 iterations creates a false floor for weak injection.
        for _ in range(2200):
            middle = lower + (upper - lower) * .5
            if middle == lower or middle == upper:
                result = middle
                break
            voltage = required_voltage(middle)
            if voltage == comparison_target:
                result = middle
                break
            if voltage < comparison_target:
                lower = middle
            else:
                upper = middle
        else:
            raise RuntimeError("Schottky current bracket did not converge")
        if result == 0.:
            # A root between zero and the minimum positive float can round
            # either way. Evaluate the real midpoint without materializing it.
            half_minimum = math.log(math.ulp(0.)) - math.log(2.)
            if comparison_target > required_voltage(0., half_minimum):
                result = math.ulp(0.)
            else:
                raise _SeriesCurrentUnderflow("nonzero diode current is not representable in float64")
        return result if forward else -result

    def current(self, voltage_V: float, temperature_K: float,
                include_tunneling: bool = False) -> float:
        """Return terminal current [A], including the series resistance.

        Solves the inverse voltage law with a sign-preserving monotone current
        bracket when series resistance is nonzero. Bisection continues until
        adjacent float64 currents or an exact voltage match, with no fixed
        absolute current floor. Saturation current stays in logarithmic form
        during the series solve. With zero series resistance, the full exponential
        is evaluated together, so intermediate saturation/drive factors may
        exceed float64. Nonzero outputs that round to zero are rejected.
        Smooth-window currents combine signed branch magnitudes in log space;
        the zero-resistance branches need not individually fit in float64.
        Series windows invert the voltage-difference law for the injection
        increment and reconstruct junction voltage without V-I*R cancellation;
        the thermionic base root remains logarithmic until total export.
        If an NLM energy window is configured, the sub-barrier branch is
        smoothly removed as the thermionic junction voltage crosses its upper
        energy limit. This reproduces the physical transition from tunnelling
        to over-barrier transport instead of retaining a false high-bias NLM
        tail.
        """
        if not math.isfinite(voltage_V):
            raise ValueError("voltage_V must be finite")
        if not isinstance(include_tunneling, bool):
            raise ValueError("include_tunneling must be an explicit boolean")
        if voltage_V == 0.:
            return self._branch_current(voltage_V, temperature_K, self.barrier_height_eV)
        if not include_tunneling or self.tunneling_barrier_lowering_eV == 0.0:
            return self._branch_current(voltage_V, temperature_K,
                                        self.barrier_height_eV)
        if self.tunneling_cutoff_energy_eV is not None:
            # q*V in eV is numerically V in volts.  As the contact drive fills
            # the sub-barrier energy interval, the energy-integrated NLM
            # correction contracts continuously to the thermionic limit.
            return self._branch_current(voltage_V, temperature_K,
                                        self._injection_barrier(voltage_V))

        if self.tunneling_window_center_eV is None:
            return self._branch_current(voltage_V, temperature_K,
                                        self._injection_barrier(voltage_V))
        _, _, _, total, _ = self._window_log_currents(voltage_V, temperature_K)
        return math.copysign(self._export_current(total), voltage_V)

    def components(self, voltage_V: float, temperature_K: float) -> dict:
        """Return independently resolved thermionic, NLM increment and total [A].

        A nonzero increment can be smaller than the ULP of either branch.
        Each returned component must itself be representable in float64.
        """
        if (self.tunneling_window_center_eV is not None
                and self.tunneling_cutoff_energy_eV is None
                and self.tunneling_barrier_lowering_eV > 0. and voltage_V != 0.):
            if not math.isfinite(voltage_V):
                raise ValueError("voltage_V must be finite")
            base, enhanced, weight, total, series_increment = self._window_log_currents(voltage_V, temperature_K)
            log_increment = None
            if self.series_resistance_ohm == 0.:
                # Derive the gain from the actual float-valued barriers, not
                # from two nearly equal logarithms of terminal currents.
                effective = self._injection_barrier(voltage_V)
                reduction = self.barrier_height_eV - effective
                if reduction > 0.:
                    thermal = self._thermal_voltage(temperature_K)
                    log_increment = enhanced + self._log_gain_fraction(reduction, thermal) + weight
            else:
                log_increment = series_increment
            increment = (0. if log_increment is None else
                         self._export_current(log_increment, "tunneling increment"))
            return {
                "thermionic_A": math.copysign(self._export_current(base), voltage_V),
                "tunneling_increment_A": math.copysign(increment, voltage_V),
                "total_A": math.copysign(self._export_current(total), voltage_V),
            }
        thermionic = self.current(voltage_V, temperature_K, False)
        total = self.current(voltage_V, temperature_K, True)
        effective = self._injection_barrier(voltage_V)
        reduction = self.barrier_height_eV - effective
        increment = 0.
        if voltage_V != 0. and reduction > 0.:
            if self.series_resistance_ohm != 0.:
                log_increment, _ = self._series_injection_difference(
                    voltage_V, temperature_K, math.log(abs(thermionic)), effective, thermionic)
            else:
                enhanced = self._branch_current(voltage_V, temperature_K,
                                                effective, logarithmic=True)
                log_increment = enhanced + self._log_gain_fraction(
                    reduction, self._thermal_voltage(temperature_K))
            increment = self._export_current(log_increment, "tunneling increment")
        return {
            "thermionic_A": thermionic,
            "tunneling_increment_A": math.copysign(increment, voltage_V),
            "total_A": total,
        }


@dataclass(frozen=True)
class WSe2CompactContactModel:
    """Gate-controlled WSe2 Schottky/NLM compact contact proxy.

    This model couples a pinned electron Schottky barrier to a smooth
    gate-controlled channel term.  It is intended as an intermediate
    calibration object between a pure contact law and a full drift-diffusion
    WSe2 Schottky FET solve.
    """

    workfunction_eV: float = 4.6
    electron_affinity_eV: float = 3.9
    pinning_factor: float = 0.55
    charge_neutrality_level_eV: float = 4.35
    gate_barrier_coupling: float = 0.30
    channel_turn_on_V: float = 0.20
    channel_smoothing_V: float = 0.08
    channel_gain: float = 0.30
    bandgap_eV: float = 1.65
    effective_mass_ratio: float = 0.36
    hole_effective_mass_ratio: float = 0.45
    area_m2: float = 20.0e-9 * 1.0e-6
    tunneling_barrier_lowering_eV: float = 0.06
    hole_tunneling_barrier_lowering_eV: float = 0.0
    hole_gate_barrier_coupling: float = 0.0
    hole_drain_barrier_coupling: float = 0.0
    hole_current_scale: float = 0.0
    tunneling_decay_exponent: float = 0.5
    high_gate_rolloff_start_V: float = 1.0e9
    high_gate_rolloff_smoothing_V: float = 0.10
    high_gate_rolloff_decades_per_V: float = 0.0
    source_drain_electron_barrier_asymmetry_eV: float = 0.0
    electron_barrier_asymmetry_coupling: float = 0.0
    electron_barrier_asymmetry_start_V: float = 1.2
    electron_barrier_asymmetry_smoothing_V: float = 0.20
    electron_barrier_asymmetry_max_decades: float = 12.0
    electron_contact_bottleneck_center_V: float = 1.0e9
    electron_contact_bottleneck_width_V: float = 0.20
    electron_contact_bottleneck_depth_decades: float = 0.0
    electron_contact_bottleneck_recovery_center_V: float = 1.0e9
    electron_contact_bottleneck_recovery_width_V: float = 0.12
    electron_contact_bottleneck_recovery_gain_decades: float = 0.0
    electron_contact_bottleneck2_center_V: float = 1.0e9
    electron_contact_bottleneck2_width_V: float = 0.20
    electron_contact_bottleneck2_depth_decades: float = 0.0
    electron_contact_bottleneck2_recovery_center_V: float = 1.0e9
    electron_contact_bottleneck2_recovery_width_V: float = 0.12
    electron_contact_bottleneck2_recovery_gain_decades: float = 0.0
    electron_current_limit_A_per_um: float = 1.0e300
    ambipolar_notch_center_V: float = 1.0e9
    ambipolar_notch_width_V: float = 0.25
    ambipolar_notch_depth_decades: float = 0.0
    ambipolar_recovery_center_V: float = 1.0e9
    ambipolar_recovery_width_V: float = 0.25
    ambipolar_recovery_gain_decades: float = 0.0
    log_residual_lut: tuple[tuple[float, float], ...] = ()
    current_scale_A_per_um: float = 0.3120162936636294

    def __post_init__(self) -> None:
        finite = (
            self.workfunction_eV,
            self.electron_affinity_eV,
            self.pinning_factor,
            self.charge_neutrality_level_eV,
            self.gate_barrier_coupling,
            self.channel_turn_on_V,
            self.channel_smoothing_V,
            self.channel_gain,
            self.bandgap_eV,
            self.effective_mass_ratio,
            self.hole_effective_mass_ratio,
            self.area_m2,
            self.tunneling_barrier_lowering_eV,
            self.hole_tunneling_barrier_lowering_eV,
            self.hole_gate_barrier_coupling,
            self.hole_drain_barrier_coupling,
            self.hole_current_scale,
            self.tunneling_decay_exponent,
            self.high_gate_rolloff_start_V,
            self.high_gate_rolloff_smoothing_V,
            self.high_gate_rolloff_decades_per_V,
            self.source_drain_electron_barrier_asymmetry_eV,
            self.electron_barrier_asymmetry_coupling,
            self.electron_barrier_asymmetry_start_V,
            self.electron_barrier_asymmetry_smoothing_V,
            self.electron_barrier_asymmetry_max_decades,
            self.electron_contact_bottleneck_center_V,
            self.electron_contact_bottleneck_width_V,
            self.electron_contact_bottleneck_depth_decades,
            self.electron_contact_bottleneck_recovery_center_V,
            self.electron_contact_bottleneck_recovery_width_V,
            self.electron_contact_bottleneck_recovery_gain_decades,
            self.electron_contact_bottleneck2_center_V,
            self.electron_contact_bottleneck2_width_V,
            self.electron_contact_bottleneck2_depth_decades,
            self.electron_contact_bottleneck2_recovery_center_V,
            self.electron_contact_bottleneck2_recovery_width_V,
            self.electron_contact_bottleneck2_recovery_gain_decades,
            self.electron_current_limit_A_per_um,
            self.ambipolar_notch_center_V,
            self.ambipolar_notch_width_V,
            self.ambipolar_notch_depth_decades,
            self.ambipolar_recovery_center_V,
            self.ambipolar_recovery_width_V,
            self.ambipolar_recovery_gain_decades,
            self.current_scale_A_per_um,
        )
        if not all(math.isfinite(value) for value in finite):
            raise ValueError("WSe2 compact contact parameters must be finite")
        if self.channel_smoothing_V <= 0.0:
            raise ValueError("channel_smoothing_V must be > 0")
        if self.effective_mass_ratio <= 0.0:
            raise ValueError("effective_mass_ratio must be > 0")
        if self.hole_effective_mass_ratio <= 0.0:
            raise ValueError("hole_effective_mass_ratio must be > 0")
        if self.bandgap_eV <= 0.0:
            raise ValueError("bandgap_eV must be > 0")
        if self.area_m2 <= 0.0:
            raise ValueError("area_m2 must be > 0")
        if self.tunneling_barrier_lowering_eV < 0.0:
            raise ValueError("tunneling_barrier_lowering_eV must be >= 0")
        if self.hole_tunneling_barrier_lowering_eV < 0.0:
            raise ValueError("hole_tunneling_barrier_lowering_eV must be >= 0")
        if self.hole_gate_barrier_coupling < 0.0:
            raise ValueError("hole_gate_barrier_coupling must be >= 0")
        if self.hole_drain_barrier_coupling < 0.0:
            raise ValueError("hole_drain_barrier_coupling must be >= 0")
        if self.hole_current_scale < 0.0:
            raise ValueError("hole_current_scale must be >= 0")
        if self.tunneling_decay_exponent <= 0.0:
            raise ValueError("tunneling_decay_exponent must be > 0")
        if self.high_gate_rolloff_smoothing_V <= 0.0:
            raise ValueError("high_gate_rolloff_smoothing_V must be > 0")
        if self.high_gate_rolloff_decades_per_V < 0.0:
            raise ValueError("high_gate_rolloff_decades_per_V must be >= 0")
        if self.source_drain_electron_barrier_asymmetry_eV < 0.0:
            raise ValueError("source_drain_electron_barrier_asymmetry_eV must be >= 0")
        if self.electron_barrier_asymmetry_coupling < 0.0:
            raise ValueError("electron_barrier_asymmetry_coupling must be >= 0")
        if self.electron_barrier_asymmetry_smoothing_V <= 0.0:
            raise ValueError("electron_barrier_asymmetry_smoothing_V must be > 0")
        if self.electron_barrier_asymmetry_max_decades < 0.0:
            raise ValueError("electron_barrier_asymmetry_max_decades must be >= 0")
        if self.electron_contact_bottleneck_width_V <= 0.0:
            raise ValueError("electron_contact_bottleneck_width_V must be > 0")
        if self.electron_contact_bottleneck_depth_decades < 0.0:
            raise ValueError("electron_contact_bottleneck_depth_decades must be >= 0")
        if self.electron_contact_bottleneck_depth_decades > 12.0:
            raise ValueError("electron_contact_bottleneck_depth_decades must be <= 12")
        if self.electron_contact_bottleneck_recovery_width_V <= 0.0:
            raise ValueError("electron_contact_bottleneck_recovery_width_V must be > 0")
        if self.electron_contact_bottleneck_recovery_gain_decades < 0.0:
            raise ValueError("electron_contact_bottleneck_recovery_gain_decades must be >= 0")
        if self.electron_contact_bottleneck_recovery_gain_decades > 12.0:
            raise ValueError("electron_contact_bottleneck_recovery_gain_decades must be <= 12")
        if self.electron_contact_bottleneck2_width_V <= 0.0:
            raise ValueError("electron_contact_bottleneck2_width_V must be > 0")
        if self.electron_contact_bottleneck2_depth_decades < 0.0:
            raise ValueError("electron_contact_bottleneck2_depth_decades must be >= 0")
        if self.electron_contact_bottleneck2_depth_decades > 12.0:
            raise ValueError("electron_contact_bottleneck2_depth_decades must be <= 12")
        if self.electron_contact_bottleneck2_recovery_width_V <= 0.0:
            raise ValueError("electron_contact_bottleneck2_recovery_width_V must be > 0")
        if self.electron_contact_bottleneck2_recovery_gain_decades < 0.0:
            raise ValueError("electron_contact_bottleneck2_recovery_gain_decades must be >= 0")
        if self.electron_contact_bottleneck2_recovery_gain_decades > 12.0:
            raise ValueError("electron_contact_bottleneck2_recovery_gain_decades must be <= 12")
        if self.electron_current_limit_A_per_um <= 0.0:
            raise ValueError("electron_current_limit_A_per_um must be > 0")
        if self.ambipolar_notch_width_V <= 0.0:
            raise ValueError("ambipolar_notch_width_V must be > 0")
        if self.ambipolar_notch_depth_decades < 0.0:
            raise ValueError("ambipolar_notch_depth_decades must be >= 0")
        if self.ambipolar_recovery_width_V <= 0.0:
            raise ValueError("ambipolar_recovery_width_V must be > 0")
        if self.ambipolar_recovery_gain_decades < 0.0:
            raise ValueError("ambipolar_recovery_gain_decades must be >= 0")
        if self.current_scale_A_per_um <= 0.0:
            raise ValueError("current_scale_A_per_um must be > 0")
        previous_gate = -math.inf
        for gate_voltage, correction_decades in self.log_residual_lut:
            if not (
                math.isfinite(gate_voltage)
                and math.isfinite(correction_decades)
            ):
                raise ValueError("log_residual_lut entries must be finite")
            if gate_voltage <= previous_gate:
                raise ValueError("log_residual_lut gate voltages must be strictly increasing")
            if abs(correction_decades) > 12.0:
                raise ValueError("log_residual_lut corrections must be within +/-12 decades")
            previous_gate = gate_voltage

    @staticmethod
    def _softplus(value: float) -> float:
        if value > 40.0:
            return value
        if value < -40.0:
            return math.exp(value)
        return math.log1p(math.exp(value))

    @property
    def nominal_barrier_height_eV(self) -> float:
        return pinned_schottky_barrier_height(
            self.workfunction_eV,
            self.electron_affinity_eV,
            pinning_factor=self.pinning_factor,
            charge_neutrality_level_eV=self.charge_neutrality_level_eV,
        )

    def effective_barrier_height_eV(self, gate_voltage_V: float) -> float:
        """Return the gate-controlled electron injection barrier."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        gate = max(gate_voltage_V, 0.0)
        channel_lowering = (
            self.channel_gain
            * self.channel_smoothing_V
            * self._softplus((gate - self.channel_turn_on_V) / self.channel_smoothing_V)
        )
        return max(
            self.nominal_barrier_height_eV
            - self.gate_barrier_coupling * gate
            + channel_lowering,
            0.0,
        )

    def contact_model(self, gate_voltage_V: float) -> SchottkyContactModel:
        barrier = self.effective_barrier_height_eV(gate_voltage_V)
        return SchottkyContactModel(
            barrier_height_eV=barrier,
            effective_mass_ratio=self.effective_mass_ratio,
            area_m2=self.area_m2,
            tunneling_barrier_lowering_eV=min(
                self.tunneling_barrier_lowering_eV, barrier
            ),
            tunneling_cutoff_energy_eV=max(barrier, 1.0e-6),
            tunneling_decay_exponent=self.tunneling_decay_exponent,
        )

    @property
    def nominal_hole_barrier_height_eV(self) -> float:
        return max(self.bandgap_eV - self.nominal_barrier_height_eV, 0.0)

    def effective_hole_barrier_height_eV(
        self, gate_voltage_V: float, drain_voltage_V: float
    ) -> float:
        """Return the compact hole-injection barrier."""
        if not math.isfinite(gate_voltage_V) or not math.isfinite(drain_voltage_V):
            raise ValueError("gate_voltage_V and drain_voltage_V must be finite")
        gate_drive = max(-gate_voltage_V, 0.0)
        drain_drive = max(abs(drain_voltage_V), 0.0)
        return max(
            self.nominal_hole_barrier_height_eV
            - self.hole_gate_barrier_coupling * gate_drive
            - self.hole_drain_barrier_coupling * drain_drive,
            0.0,
        )

    def hole_contact_model(
        self, gate_voltage_V: float, drain_voltage_V: float
    ) -> SchottkyContactModel:
        barrier = self.effective_hole_barrier_height_eV(
            gate_voltage_V, drain_voltage_V
        )
        return SchottkyContactModel(
            barrier_height_eV=barrier,
            effective_mass_ratio=self.hole_effective_mass_ratio,
            area_m2=self.area_m2,
            tunneling_barrier_lowering_eV=min(
                self.hole_tunneling_barrier_lowering_eV, barrier
            ),
            tunneling_cutoff_energy_eV=max(barrier, 1.0e-6),
            tunneling_decay_exponent=self.tunneling_decay_exponent,
        )

    def high_gate_rolloff_factor(self, gate_voltage_V: float) -> float:
        """Return optional high-gate current suppression factor."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if self.high_gate_rolloff_decades_per_V == 0.0:
            return 1.0
        excess = (
            self.high_gate_rolloff_smoothing_V
            * self._softplus(
                (gate_voltage_V - self.high_gate_rolloff_start_V)
                / self.high_gate_rolloff_smoothing_V
            )
        )
        return 10.0 ** (-self.high_gate_rolloff_decades_per_V * excess)

    def electron_barrier_asymmetry_factor(
        self,
        gate_voltage_V: float,
        temperature_K: float,
    ) -> float:
        """Return source/drain electron-barrier asymmetry suppression.

        Sentaurus WSe2 local profiles show that the hardest high-workfunction
        branches are electron-current dominated at both contacts, but with a
        large source/drain electron-barrier asymmetry.  This opt-in factor
        converts that local barrier mismatch into a high-gate transport
        bottleneck without using a branch-local residual LUT.
        """
        if not math.isfinite(gate_voltage_V) or not math.isfinite(temperature_K):
            raise ValueError("gate_voltage_V and temperature_K must be finite")
        if temperature_K <= 0.0:
            raise ValueError("temperature_K must be > 0")
        if (
            self.source_drain_electron_barrier_asymmetry_eV == 0.0
            or self.electron_barrier_asymmetry_coupling == 0.0
            or self.electron_barrier_asymmetry_max_decades == 0.0
        ):
            return 1.0
        arg = (
            (gate_voltage_V - self.electron_barrier_asymmetry_start_V)
            / self.electron_barrier_asymmetry_smoothing_V
        )
        arg = max(min(arg, 80.0), -80.0)
        high_gate_weight = 1.0 / (1.0 + math.exp(-arg))
        barrier_eV = (
            self.source_drain_electron_barrier_asymmetry_eV
            * self.electron_barrier_asymmetry_coupling
            * high_gate_weight
        )
        suppression_decades = barrier_eV / (K_B_EV * temperature_K * math.log(10.0))
        suppression_decades = min(
            max(suppression_decades, 0.0),
            self.electron_barrier_asymmetry_max_decades,
        )
        return 10.0 ** (-suppression_decades)

    def electron_contact_bottleneck_factor(self, gate_voltage_V: float) -> float:
        """Return optional local electron contact-window bottleneck factor.

        This second, opt-in gate window is separate from the ambipolar notch.
        Sentaurus WSe2 profiles show hard high-workfunction branches with a
        mid/high-gate electron contact valley followed by recovery.  The
        Gaussian bottleneck plus logistic recovery captures that local contact
        window without requiring a branch-local residual LUT.
        """
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        correction_decades = self._contact_bottleneck_correction_decades(
            gate_voltage_V,
            center_V=self.electron_contact_bottleneck_center_V,
            width_V=self.electron_contact_bottleneck_width_V,
            depth_decades=self.electron_contact_bottleneck_depth_decades,
            recovery_center_V=self.electron_contact_bottleneck_recovery_center_V,
            recovery_width_V=self.electron_contact_bottleneck_recovery_width_V,
            recovery_gain_decades=self.electron_contact_bottleneck_recovery_gain_decades,
        )
        correction_decades += self._contact_bottleneck_correction_decades(
            gate_voltage_V,
            center_V=self.electron_contact_bottleneck2_center_V,
            width_V=self.electron_contact_bottleneck2_width_V,
            depth_decades=self.electron_contact_bottleneck2_depth_decades,
            recovery_center_V=self.electron_contact_bottleneck2_recovery_center_V,
            recovery_width_V=self.electron_contact_bottleneck2_recovery_width_V,
            recovery_gain_decades=self.electron_contact_bottleneck2_recovery_gain_decades,
        )
        return 10.0 ** correction_decades

    def _contact_bottleneck_correction_decades(
        self,
        gate_voltage_V: float,
        *,
        center_V: float,
        width_V: float,
        depth_decades: float,
        recovery_center_V: float,
        recovery_width_V: float,
        recovery_gain_decades: float,
    ) -> float:
        correction_decades = 0.0
        if depth_decades != 0.0:
            normalized = (
                (gate_voltage_V - center_V)
                / width_V
            )
            correction_decades -= (
                depth_decades
                * math.exp(-0.5 * normalized * normalized)
            )
        if recovery_gain_decades != 0.0:
            arg = (
                (
                    gate_voltage_V
                    - recovery_center_V
                )
                / recovery_width_V
            )
            arg = max(min(arg, 80.0), -80.0)
            correction_decades += (
                recovery_gain_decades
                / (1.0 + math.exp(-arg))
            )
        return correction_decades

    def electron_current_limit(self, electron_current_A_per_um: float) -> float:
        """Apply the optional limit, rejecting nonfinite and unexportable output."""
        if not math.isfinite(electron_current_A_per_um) or electron_current_A_per_um < 0.0:
            raise ValueError("electron_current_A_per_um must be finite and >= 0")
        if self.electron_current_limit_A_per_um >= 1.0e299:
            return electron_current_A_per_um
        if electron_current_A_per_um == 0.:
            return 0.
        smaller = min(electron_current_A_per_um, self.electron_current_limit_A_per_um)
        larger = max(electron_current_A_per_um, self.electron_current_limit_A_per_um)
        result = smaller / (1. + smaller / larger)
        if result == 0.:
            raise ValueError("nonzero limited current is not representable in float64")
        return result

    def ambipolar_notch_factor(self, gate_voltage_V: float) -> float:
        """Return optional valley/filter suppression around an ambipolar crossover."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if self.ambipolar_notch_depth_decades == 0.0:
            return 1.0
        normalized = (
            (gate_voltage_V - self.ambipolar_notch_center_V)
            / self.ambipolar_notch_width_V
        )
        depth = self.ambipolar_notch_depth_decades * math.exp(
            -0.5 * normalized * normalized
        )
        return 10.0 ** (-depth)

    def ambipolar_recovery_factor(self, gate_voltage_V: float) -> float:
        """Return optional post-valley recovery/lobe gain."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if self.ambipolar_recovery_gain_decades == 0.0:
            return 1.0
        arg = (
            (gate_voltage_V - self.ambipolar_recovery_center_V)
            / self.ambipolar_recovery_width_V
        )
        arg = max(min(arg, 80.0), -80.0)
        recovery = 1.0 / (1.0 + math.exp(-arg))
        return 10.0 ** (self.ambipolar_recovery_gain_decades * recovery)

    def residual_lut_correction_decades(self, gate_voltage_V: float) -> float:
        """Return branch-local Sentaurus residual correction in log-current space.

        The LUT is intentionally explicit and opt-in.  It is useful for
        profile-calibrated WSe2 deck replay, but it should not be interpreted
        as a transferable physics model outside the calibrated branch grid.
        """
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if not self.log_residual_lut:
            return 0.0
        points = self.log_residual_lut
        if gate_voltage_V <= points[0][0]:
            return points[0][1]
        if gate_voltage_V >= points[-1][0]:
            return points[-1][1]
        lo = 0
        hi = len(points) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if points[mid][0] <= gate_voltage_V:
                lo = mid
            else:
                hi = mid
        x0, y0 = points[lo]
        x1, y1 = points[hi]
        if x1 <= x0:
            return 0.5 * (y0 + y1)
        fraction = (gate_voltage_V - x0) / (x1 - x0)
        return y0 + fraction * (y1 - y0)

    def residual_lut_factor(self, gate_voltage_V: float) -> float:
        """Return the multiplicative factor from the log residual LUT."""
        correction = self.residual_lut_correction_decades(gate_voltage_V)
        return 10.0 ** correction

    def abs_current_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
        *,
        include_tunneling: bool = True,
    ) -> float:
        """Return the calibrated compact contact/channel current in A/um."""
        model = self.contact_model(gate_voltage_V)
        current_A = abs(
            model.current(drain_voltage_V, temperature_K, include_tunneling)
        )
        electron_current = (
            current_A
            / 1.0e6
            * self.current_scale_A_per_um
            * self.high_gate_rolloff_factor(gate_voltage_V)
            * self.electron_barrier_asymmetry_factor(gate_voltage_V, temperature_K)
            * self.electron_contact_bottleneck_factor(gate_voltage_V)
            * self.ambipolar_notch_factor(gate_voltage_V)
            * self.ambipolar_recovery_factor(gate_voltage_V)
        )
        electron_current = self.electron_current_limit(electron_current)
        if self.hole_current_scale == 0.0:
            return electron_current * self.residual_lut_factor(gate_voltage_V)
        hole_A = abs(
            self.hole_contact_model(gate_voltage_V, drain_voltage_V).current(
                abs(drain_voltage_V), temperature_K, include_tunneling
            )
        )
        total = electron_current + hole_A / 1.0e6 * self.hole_current_scale
        return total * self.residual_lut_factor(gate_voltage_V)


@dataclass(frozen=True)
class WSe2TransportWindow:
    """One calibrated WSe2 electron/hole transfer window.

    The window is a smooth log-current lobe in gate voltage.  It is designed to
    be fitted against Sentaurus local band/quasi-Fermi/current profiles:
    ``center_gate_V`` identifies the transport window, ``width_V`` sets the
    gate-bias energy spread, and ``temperature_activation_eV`` represents the
    effective thermal barrier of that window.  The object is not a replacement
    for a full 2-D drift-diffusion solve; it is the next calibration layer
    between pure response replay and full-device physics.

    Gate, thermal and drain scaling are combined before current export. Individual
    factor accessors reject nonzero values outside float64; the current can
    still fit when those factors do not. The configured current floor applies
    at zero drain for a positive drain exponent. Internal float64 log overflow
    and opposing finite logs use a Decimal fallback. Working precision does not certify
    correct rounding or arbitrary cancellation of very large logarithms.
    """

    center_gate_V: float
    width_V: float
    peak_current_A_per_um: float
    floor_current_A_per_um: float = 1.0e-30
    left_width_V: Optional[float] = None
    right_width_V: Optional[float] = None
    left_tail_fraction: float = 0.0
    right_tail_fraction: float = 0.0
    left_tail_smoothing_V: Optional[float] = None
    right_tail_smoothing_V: Optional[float] = None
    skew: float = 0.0
    notch_center_gate_V: float = 1.0e9
    notch_width_V: float = 0.25
    notch_depth_decades: float = 0.0
    temperature_reference_K: float = 300.0
    temperature_activation_eV: float = 0.0
    drain_exponent: float = 1.0
    drain_reference_V: float = 0.5
    polarity: int = 1

    def __post_init__(self) -> None:
        values = (
            self.center_gate_V,
            self.width_V,
            self.peak_current_A_per_um,
            self.floor_current_A_per_um,
            self.left_tail_fraction,
            self.right_tail_fraction,
            self.skew,
            self.notch_center_gate_V,
            self.notch_width_V,
            self.notch_depth_decades,
            self.temperature_reference_K,
            self.temperature_activation_eV,
            self.drain_exponent,
            self.drain_reference_V,
        )
        optional_values = (
            self.left_width_V,
            self.right_width_V,
            self.left_tail_smoothing_V,
            self.right_tail_smoothing_V,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("WSe2 transport window parameters must be finite")
        if not all(value is None or math.isfinite(value) for value in optional_values):
            raise ValueError("optional WSe2 window widths must be finite")
        if self.width_V <= 0.0:
            raise ValueError("width_V must be > 0")
        if self.left_width_V is not None and self.left_width_V <= 0.0:
            raise ValueError("left_width_V must be > 0")
        if self.right_width_V is not None and self.right_width_V <= 0.0:
            raise ValueError("right_width_V must be > 0")
        if not 0.0 <= self.left_tail_fraction <= 1.0:
            raise ValueError("left_tail_fraction must be in [0, 1]")
        if not 0.0 <= self.right_tail_fraction <= 1.0:
            raise ValueError("right_tail_fraction must be in [0, 1]")
        if self.left_tail_smoothing_V is not None and self.left_tail_smoothing_V <= 0.0:
            raise ValueError("left_tail_smoothing_V must be > 0")
        if self.right_tail_smoothing_V is not None and self.right_tail_smoothing_V <= 0.0:
            raise ValueError("right_tail_smoothing_V must be > 0")
        if self.peak_current_A_per_um <= 0.0:
            raise ValueError("peak_current_A_per_um must be > 0")
        if self.floor_current_A_per_um <= 0.0:
            raise ValueError("floor_current_A_per_um must be > 0")
        if self.floor_current_A_per_um > self.peak_current_A_per_um:
            raise ValueError("floor_current_A_per_um must be <= peak_current_A_per_um")
        if self.notch_width_V <= 0.0:
            raise ValueError("notch_width_V must be > 0")
        if self.notch_depth_decades < 0.0:
            raise ValueError("notch_depth_decades must be >= 0")
        if self.temperature_reference_K <= 0.0:
            raise ValueError("temperature_reference_K must be > 0")
        if self.temperature_activation_eV < 0.0:
            raise ValueError("temperature_activation_eV must be >= 0")
        if self.drain_exponent < 0.0:
            raise ValueError("drain_exponent must be >= 0")
        if self.drain_reference_V <= 0.0:
            raise ValueError("drain_reference_V must be > 0")
        if self.polarity not in (-1, 1):
            raise ValueError("polarity must be -1 or 1")

    @staticmethod
    def _coordinate_ratio(voltage: float, center: float, width: float) -> tuple[int, int]:
        # Form the difference before division without overflowing voltage-center.
        vn, vd = voltage.as_integer_ratio()
        cn, cd = center.as_integer_ratio()
        wn, wd = width.as_integer_ratio()
        return (vn * cd - cn * vd) * wd, vd * cd * wn

    @staticmethod
    def _coordinate_value(numerator: int, denominator: int) -> float:
        try:
            return numerator / denominator
        except OverflowError as exc:
            raise _WindowLogRangeError("gate coordinate is not representable in float64") from exc

    @staticmethod
    def _log_positive_ratio(numerator: int, denominator: int) -> float:
        try:
            ratio = numerator / denominator
        except OverflowError:
            ratio = math.inf
        if math.isfinite(ratio) and ratio >= sys.float_info.min:
            return math.log(ratio)
        return math.log(numerator) - math.log(denominator)

    @staticmethod
    def _log_add(first: float, second: float) -> float:
        if first == -math.inf:
            return second
        if second == -math.inf:
            return first
        larger, smaller = max(first, second), min(first, second)
        return larger + math.log1p(math.exp(smaller - larger))

    @staticmethod
    def _log_sigmoid(value: float) -> float:
        return (-math.log1p(math.exp(-value)) if value >= 0.0
                else value - math.log1p(math.exp(value)))

    @staticmethod
    def _log_gaussian(coordinate: float) -> float:
        result = -0.5 * coordinate * coordinate
        if not math.isfinite(result):
            raise _WindowLogRangeError("gate Gaussian logarithm is not representable in float64")
        return result

    def _log_gate_weight(self, gate_voltage_V: float) -> float:
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        width = (
            self.left_width_V
            if gate_voltage_V < self.center_gate_V and self.left_width_V is not None
            else self.right_width_V
            if gate_voltage_V >= self.center_gate_V and self.right_width_V is not None
            else self.width_V
        )
        numerator, denominator = self._coordinate_ratio(gate_voltage_V, self.center_gate_V, width)
        normalized = self._coordinate_value(numerator, denominator)
        sn, sd = self.skew.as_integer_ratio()
        skew_numerator = sd * denominator + sn * numerator
        if skew_numerator <= 0:
            log_lobe = -math.inf  # Exact clipping, distinct from underflow.
        else:
            log_lobe = math.fsum((self._log_gaussian(normalized),
                self._log_positive_ratio(skew_numerator, sd * denominator)))

        def tail(fraction: float, smoothing: Optional[float], sign: int) -> tuple[float, float]:
            if fraction == 0.0:
                return -math.inf, 0.0
            coordinate = (normalized if smoothing is None or smoothing == width else
                self._coordinate_value(*self._coordinate_ratio(
                    gate_voltage_V, self.center_gate_V, smoothing)))
            coordinate *= sign
            log_fraction = math.log(fraction)
            log_tail = log_fraction + self._log_sigmoid(coordinate)
            # 1 - f*sigmoid(z) = (1-f) + f*sigmoid(-z). Preserve the
            # complement even if the tail itself rounds to exactly one.
            log_complement = self._log_add(
                math.log1p(-fraction) if fraction < 1.0 else -math.inf,
                log_fraction + self._log_sigmoid(-coordinate))
            return log_tail, log_complement

        log_tail, log_complement = max(
            tail(self.left_tail_fraction, self.left_tail_smoothing_V, -1),
            tail(self.right_tail_fraction, self.right_tail_smoothing_V, 1),
            key=lambda pair: (pair[0], -pair[1]))
        log_weight = self._log_add(log_tail, log_complement + log_lobe)
        if self.notch_depth_decades == 0.0 or log_weight == -math.inf:
            return log_weight
        notch_x = self._coordinate_value(*self._coordinate_ratio(
            gate_voltage_V, self.notch_center_gate_V, self.notch_width_V))
        log_penalty = math.fsum((math.log(self.notch_depth_decades),
            math.log(math.log(10.0)), self._log_gaussian(notch_x)))
        try:
            penalty = math.exp(log_penalty)
        except OverflowError as exc:
            raise _WindowLogRangeError("gate notch logarithm is not representable in float64") from exc
        result = log_weight - penalty
        if not math.isfinite(result):
            raise _WindowLogRangeError("gate weight logarithm is not representable in float64")
        return result

    def gate_weight(self, gate_voltage_V: float) -> float:
        """Return the weight, rejecting nonzero loss at float64 export."""
        try:
            log_weight = self._log_gate_weight(gate_voltage_V)
        except _WindowLogRangeError:
            return self._wide_window_value(gate_voltage_V)
        if log_weight != -math.inf and self._near_export_boundary(log_weight):
            return self._wide_window_value(gate_voltage_V, precision=1200)
        return (0.0 if log_weight == -math.inf
                else self._export_factor(log_weight, "gate weight"))

    def _log_temperature_factor(self, temperature_K: float) -> float:
        if not math.isfinite(temperature_K) or temperature_K <= 0.0:
            raise ValueError("temperature_K must be finite and > 0")
        if (self.temperature_activation_eV == 0.0
                or temperature_K == self.temperature_reference_K):
            return 0.0
        # Evaluate Ea/k * (1/Tref - 1/T) as one exact rational expression
        # before rounding. Neither reciprocals nor Ea/k have to fit, and
        # adjacent temperatures retain their actual difference.
        en, ed = self.temperature_activation_eV.as_integer_ratio()
        kn, kd = K_B_EV.as_integer_ratio()
        tn, td = temperature_K.as_integer_ratio()
        rn, rd = self.temperature_reference_K.as_integer_ratio()
        try:
            return (en * kd * (tn * rd - rn * td)) / (ed * kn * rn * tn)
        except OverflowError as exc:
            raise _WindowLogRangeError("temperature factor logarithm is not representable in float64") from exc

    def _log_drain_factor(self, drain_voltage_V: float) -> float:
        if not math.isfinite(drain_voltage_V):
            raise ValueError("drain_voltage_V must be finite")
        if self.drain_exponent == 0.0:
            return 0.0
        drive = abs(drain_voltage_V)
        if drive == 0.0:
            return -math.inf  # Exact zero, distinct from nonzero underflow.
        reference = self.drain_reference_V
        if drive >= reference:
            fraction = (drive - reference) / drive
            log_ratio = (-math.log1p(-fraction) if fraction <= 0.5
                         else math.log(drive) - math.log(reference))
        else:
            fraction = (reference - drive) / reference
            log_ratio = (math.log1p(-fraction) if fraction <= 0.5
                         else math.log(drive) - math.log(reference))
        result = self.drain_exponent * log_ratio
        if not math.isfinite(result):
            raise _WindowLogRangeError("drain factor logarithm is not representable in float64")
        return result

    @staticmethod
    def _export_factor(log_value: float, label: str) -> float:
        try:
            result = math.exp(log_value)
        except OverflowError as exc:
            raise ValueError(f"{label} is not representable in float64") from exc
        if not math.isfinite(result) or result == 0.0:
            raise ValueError(f"nonzero {label} is not representable in float64")
        return result

    def temperature_factor(self, temperature_K: float) -> float:
        """Return the actual thermal factor, rejecting nonzero export loss."""
        log_factor = self._log_temperature_factor(temperature_K)
        if self._near_export_boundary(log_factor):
            return self._wide_factor_value(temperature_K, thermal=True)
        return self._export_factor(log_factor, "temperature factor")

    def drain_factor(self, drain_voltage_V: float) -> float:
        """Return |Vd/Vref|**p, including exact zero for p > 0."""
        log_factor = self._log_drain_factor(drain_voltage_V)
        if log_factor == -math.inf:
            return 0.0
        if self.drain_exponent == 1.0:
            return self._linear_drain_value(drain_voltage_V)
        if self._near_export_boundary(log_factor):
            return self._wide_factor_value(drain_voltage_V)
        return self._export_factor(log_factor, "drain factor")

    @staticmethod
    def _near_export_boundary(log_value: float) -> bool:
        # Rounded logarithms cannot decide overflow or subnormal rounding.
        # Include a margin on either side; ordinary windows stay on the fast path.
        return log_value > 700.0 or log_value < -700.0

    def _linear_drain_value(self, drain: float, *, current: bool = False) -> float:
        numerator, denominator = self._coordinate_ratio(abs(drain), 0., self.drain_reference_V)
        label = 'window current' if current else 'drain factor'
        if current:
            pn, pd = self.peak_current_A_per_um.as_integer_ratio()
            numerator *= pn
            denominator *= pd
        try:
            value = numerator / denominator
        except OverflowError as exc:
            raise ValueError(f"{label} is not representable in float64") from exc
        if current:
            return max(self.floor_current_A_per_um, value)
        if value == 0.0:
            raise ValueError(f"nonzero {label} is not representable in float64")
        return value

    def _wide_factor_value(self, value: float, *, thermal: bool = False,
                           current: bool = False) -> float:
        # Direct powers preserve exact dyadic underflow ties that exp(log(x))
        # can move across a rounding boundary, even at high precision. 1200
        # digits include the decimal expansion of float64 subnormal midpoints.
        # This working precision is not a global correct-rounding proof.
        with localcontext(Context(prec=1200, rounding=ROUND_HALF_EVEN,
                                Emax=999999, Emin=-999999,
                                traps=[InvalidOperation, DivisionByZero, Overflow])) as ctx:
            d = Decimal.from_float
            if thermal:
                t, ref = d(value), d(self.temperature_reference_K)
                exponent = d(self.temperature_activation_eV)/d(K_B_EV)*(t-ref)/(ref*t)
                if exponent > 711 or exponent < -800:
                    raise ValueError('nonzero temperature factor is not representable in float64')
                result = exponent.exp()
                label = 'temperature factor'
            else:
                log_factor = self._log_drain_factor(value)
                log_result = log_factor + (math.log(self.peak_current_A_per_um) if current else 0.)
                if log_result > 711 or log_result < -800:
                    if current and log_result < -800:
                        return self.floor_current_A_per_um
                    raise ValueError('nonzero drain factor is not representable in float64')
                result = ctx.power(abs(d(value))/d(self.drain_reference_V), d(self.drain_exponent))
                if current:
                    result *= d(self.peak_current_A_per_um)
                    if result <= d(self.floor_current_A_per_um):
                        return self.floor_current_A_per_um
                label = 'window current' if current else 'drain factor'
            exported = float(result)
            if not math.isfinite(exported) or exported == 0.0:
                raise ValueError(f"nonzero {label} is not representable in float64")
            return max(self.floor_current_A_per_um, exported) if current else exported

    def current_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> float:
        """Combine all factors, widening range or strong finite cancellation."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if not math.isfinite(drain_voltage_V):
            raise ValueError("drain_voltage_V must be finite")
        if not math.isfinite(temperature_K) or temperature_K <= 0.0:
            raise ValueError("temperature_K must be finite and > 0")
        if drain_voltage_V == 0.0 and self.drain_exponent > 0.0:
            return self.floor_current_A_per_um
        try:
            return self._current_from_float_logs(gate_voltage_V, drain_voltage_V, temperature_K)
        except _WindowLogRangeError:
            return self._wide_window_value(gate_voltage_V, drain_voltage_V, temperature_K)

    def _wide_window_value(self, gate: float, drain: Optional[float] = None,
                           temperature: Optional[float] = None, *, precision: int = 2400) -> float:
        """Recompute the formula; public outputs still have float64 limits.

        Working precision is intentionally not a correct-rounding proof.
        The float-log path handles normal inputs without this extra cost.
        """
        # Do not inherit a caller's rounding mode, precision or Inexact trap.
        with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN,
                                Emax=999999, Emin=-999999,
                                traps=[InvalidOperation, DivisionByZero, Overflow])) as ctx:
            d = Decimal.from_float
            zero, one = Decimal(0), Decimal(1)
            neg_inf = Decimal('-Infinity')
            # Terms smaller than working precision do not change a rounded
            # log-sum. Avoid exp of astronomically negative arguments; keep
            # sigmoid complements independently, rather than subtracting.
            negligible = -Decimal(ctx.prec + 10) * Decimal(10).ln()

            def small_exp(value):
                return zero if value < negligible else value.exp()

            def add(first, second):
                if first == neg_inf:
                    return second
                if second == neg_inf:
                    return first
                larger, smaller = max(first, second), min(first, second)
                return larger + (one + small_exp(smaller-larger)).ln()

            def sigmoid_log(value):
                correction = (one + small_exp(-abs(value))).ln()
                return -correction if value >= 0 else value-correction

            width = (self.left_width_V if gate < self.center_gate_V and self.left_width_V is not None
                     else self.right_width_V if gate >= self.center_gate_V and self.right_width_V is not None
                     else self.width_V)
            offset = d(gate)-d(self.center_gate_V)
            x = offset/d(width)
            # Use the exact skew sign even at a cancellation boundary.
            xn, xd = self._coordinate_ratio(gate, self.center_gate_V, width)
            sn, sd = self.skew.as_integer_ratio()
            skew_n = sd*xd + sn*xn
            log_lobe = (neg_inf if skew_n <= 0 else
                        -x*x/2 + (Decimal(skew_n)/Decimal(sd*xd)).ln())

            def tail(fraction, smoothing, sign):
                if fraction == 0.0:
                    return neg_inf, zero
                z = sign*offset/d(smoothing or width)
                lf = d(fraction).ln()
                return (lf+sigmoid_log(z),
                        add((one-d(fraction)).ln() if fraction < 1.0 else neg_inf,
                            lf+sigmoid_log(-z)))

            lt, lc = max(tail(self.left_tail_fraction, self.left_tail_smoothing_V, -1),
                         tail(self.right_tail_fraction, self.right_tail_smoothing_V, 1),
                         key=lambda pair: (pair[0], -pair[1]))
            result = add(lt, lc+log_lobe)
            if result == neg_inf:
                return 0.0 if drain is None else self.floor_current_A_per_um
            if self.notch_depth_decades:
                nx = (d(gate)-d(self.notch_center_gate_V))/d(self.notch_width_V)
                # Combine depth before dropping a negligible Gaussian: a
                # large depth can restore a Gaussian below working precision.
                ln10 = Decimal(10).ln()
                log_penalty = d(self.notch_depth_decades).ln()-nx*nx/2+ln10.ln()
                result -= small_exp(log_penalty)
            label = 'gate weight'
            if drain is not None:
                thermal = d(self.temperature_activation_eV)/d(K_B_EV)*(
                    one/d(self.temperature_reference_K)-one/d(temperature))
                drive = (zero if self.drain_exponent == 0.0 else
                         d(self.drain_exponent)*(abs(d(drain))/d(self.drain_reference_V)).ln())
                result += d(self.peak_current_A_per_um).ln()+thermal+drive
                if result <= d(self.floor_current_A_per_um).ln():
                    return self.floor_current_A_per_um
                label = 'window current'
            if result > d(sys.float_info.max).ln()+one or result < -800:
                raise ValueError(f"nonzero {label} is not representable in float64")
            value = float(result.exp())
            if not math.isfinite(value) or value == 0.0:
                raise ValueError(f"nonzero {label} is not representable in float64")
            return value if drain is None else max(self.floor_current_A_per_um, value)

    def _current_from_float_logs(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> float:
        """Combine scaling before export, retaining the configured current floor."""
        thermal = self._log_temperature_factor(temperature_K)
        drain = self._log_drain_factor(drain_voltage_V)
        log_weight = self._log_gate_weight(gate_voltage_V)
        if drain == -math.inf or log_weight == -math.inf:
            return self.floor_current_A_per_um
        if thermal == 0.0 and drain == 0.0 and log_weight == 0.0:
            return self.peak_current_A_per_um
        try:
            log_signal = math.fsum((math.log(self.peak_current_A_per_um),
                                   thermal, drain, log_weight))
        except OverflowError as exc:
            raise _WindowLogRangeError("window current logarithm is not representable in float64") from exc
        largest = max(abs(thermal), abs(drain), abs(log_weight))
        # fsum preserves the sum of rounded inputs, but cannot restore a
        # small contribution already lost inside a log. Check cancellation
        # of the modulation itself: the peak must not hide it. This trigger
        # and the precision margin are not global error bounds.
        if (largest >= 32.0 and min(thermal, drain, log_weight) < 0.0
                and max(thermal, drain, log_weight) > 0.0):
            modulation = math.fsum((thermal, drain, log_weight))
            if abs(modulation) <= largest / 2.0:
                precision = 96 + math.ceil(math.log10(largest))
                return self._wide_window_value(gate_voltage_V, drain_voltage_V,
                                              temperature_K, precision=precision)
        if self._near_export_boundary(log_signal):
            # A neutral gate/temperature leaves a literal scaled power. Avoid
            # introducing log/exp error at exact subnormal rounding ties.
            neutral_gate = (gate_voltage_V == self.center_gate_V
                            and self.notch_depth_decades == 0.0)
            neutral_temperature = (self.temperature_activation_eV == 0.0
                                   or temperature_K == self.temperature_reference_K)
            if neutral_gate and neutral_temperature:
                if self.drain_exponent == 1.0:
                    return self._linear_drain_value(drain_voltage_V, current=True)
                return self._wide_factor_value(drain_voltage_V, current=True)
            return self._wide_window_value(gate_voltage_V, drain_voltage_V,
                                          temperature_K, precision=1200)
        if log_signal <= math.log(self.floor_current_A_per_um):
            return self.floor_current_A_per_um
        return max(self.floor_current_A_per_um,
                   self._export_factor(log_signal, "window current"))


@dataclass(frozen=True)
class WSe2TwoWindowTransferModel:
    """Two-window model; each reported component must fit in float64."""

    electron_window: WSe2TransportWindow
    hole_window: WSe2TransportWindow
    valley_floor_A_per_um: float = 1.0e-30
    component_coupling: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.valley_floor_A_per_um) or self.valley_floor_A_per_um <= 0.0:
            raise ValueError("valley_floor_A_per_um must be finite and > 0")
        if not math.isfinite(self.component_coupling) or self.component_coupling < 0.0:
            raise ValueError("component_coupling must be finite and >= 0")

    @staticmethod
    def _sum_currents(currents: tuple[float, ...]) -> float:
        if any(not math.isfinite(current) or current < 0. for current in currents):
            raise ValueError("current components must be finite and >= 0")
        try:
            return math.fsum(currents)
        except OverflowError as exc:
            raise ValueError("total current is not representable in float64") from exc

    def _coupled_current(self, electron: float, hole: float, *, require_export: bool) -> float:
        if not all(math.isfinite(value) and value > 0. for value in (electron, hole)):
            raise ValueError("window currents must be finite and > 0")
        if self.component_coupling == 0.:
            return 0.
        # Keep all three factors scaled until the final export. Forming e*h
        # first can overflow or erase a small geometric mean before a large
        # coupling factor restores a representable component.
        em, ee = math.frexp(electron)
        hm, he = math.frexp(hole)
        cm, ce = math.frexp(self.component_coupling)
        exponent, odd = divmod(ee + he, 2)
        mantissa = cm * math.sqrt(em * hm * (2. if odd else 1.))
        try:
            result = math.ldexp(mantissa, ce + exponent)
        except OverflowError as exc:
            raise ValueError("coupled current is not representable in float64") from exc
        if result == 0. and require_export:
            raise ValueError("nonzero coupled current is not representable in float64")
        return result

    def components_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> dict[str, float]:
        """Return finite components, rejecting nonzero component underflow."""
        return self._current_components(gate_voltage_V, drain_voltage_V, temperature_K,
                                        require_components=True)

    def _current_components(
        self, gate_voltage_V: float, drain_voltage_V: float, temperature_K: float,
        *, require_components: bool,
    ) -> dict[str, float]:
        electron = self.electron_window.current_A_per_um(
            gate_voltage_V, drain_voltage_V, temperature_K
        )
        hole = self.hole_window.current_A_per_um(
            gate_voltage_V, drain_voltage_V, temperature_K
        )
        coupled = self._coupled_current(electron, hole, require_export=require_components)
        total = self._sum_currents(
            (electron, hole, coupled, self.valley_floor_A_per_um)
        )
        return {
            "electron_A_per_um": electron,
            "hole_A_per_um": hole,
            "coupled_A_per_um": coupled,
            "floor_A_per_um": self.valley_floor_A_per_um,
            "total_A_per_um": total,
        }

    def abs_current_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> float:
        # Total-only evaluation permits coupling export underflow; the public
        # component interface reports that loss of range explicitly.
        return self._current_components(
            gate_voltage_V, drain_voltage_V, temperature_K, require_components=False
        )["total_A_per_um"]
