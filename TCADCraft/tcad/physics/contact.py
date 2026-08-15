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
                       saturation: float) -> float:
        """Solve one thermionic diode branch with bulk transport loss."""
        thermal_voltage = K_B_EV * temperature_K * self.ideality_factor
        resistance = self.series_resistance_ohm
        transport_limit = self.transport_saturation_current_A
        if resistance == 0.0 or transport_limit is None:
            if resistance != 0.0:
                # Retain the historical constant-series-resistance path
                # bit-for-bit when high-field transport is not configured.
                lower = -saturation
                upper = max(voltage_V / resistance, 0.0)
                for _ in range(100):
                    current = 0.5 * (lower + upper)
                    argument = (
                        voltage_V - current * resistance
                    ) / thermal_voltage
                    argument = max(min(argument, 700.0), -745.0)
                    residual = saturation * math.expm1(argument) - current
                    if residual > 0.0:
                        lower = current
                    else:
                        upper = current
                return 0.5 * (lower + upper)
            argument = max(min(voltage_V / thermal_voltage, 700.0), -745.0)
            return saturation * math.expm1(argument)

        lower = -saturation
        upper = min(
            max(voltage_V / resistance, 0.0),
            transport_limit * (1.0 - 1.0e-12),
        )
        for _ in range(100):
            current = 0.5 * (lower + upper)
            argument = (
                voltage_V - self._bulk_voltage_drop(current)
            ) / thermal_voltage
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
        if self.tunneling_cutoff_energy_eV is not None:
            # q*V in eV is numerically V in volts.  As the contact drive fills
            # the sub-barrier energy interval, the energy-integrated NLM
            # correction contracts continuously to the thermionic limit.
            available = max(
                1.0 - max(voltage_V, 0.0)
                / self.tunneling_cutoff_energy_eV,
                0.0,
            )
            lowering = (
                self.tunneling_barrier_lowering_eV
                * available ** self.tunneling_decay_exponent
            )
            barrier = max(self.barrier_height_eV - lowering, 0.0)
            enhanced_saturation = (
                self.richardson_constant
                * temperature_K * temperature_K
                * self.area_m2
                * math.exp(max(-barrier / (K_B_EV * temperature_K), -745.0))
            )
            return self._diode_current(
                voltage_V, temperature_K, enhanced_saturation
            )

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
            * self.ambipolar_notch_factor(gate_voltage_V)
            * self.ambipolar_recovery_factor(gate_voltage_V)
        )
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

    def gate_weight(self, gate_voltage_V: float) -> float:
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        width = (
            self.left_width_V
            if gate_voltage_V < self.center_gate_V and self.left_width_V is not None
            else self.right_width_V
            if gate_voltage_V >= self.center_gate_V and self.right_width_V is not None
            else self.width_V
        )
        normalized = (gate_voltage_V - self.center_gate_V) / width
        skew_term = 1.0 + self.skew * normalized
        lobe = math.exp(-0.5 * normalized * normalized) * max(skew_term, 0.0)
        left_tail = self.left_tail_fraction * self._sigmoid(
            (self.center_gate_V - gate_voltage_V)
            / (self.left_tail_smoothing_V or width)
        )
        right_tail = self.right_tail_fraction * self._sigmoid(
            (gate_voltage_V - self.center_gate_V)
            / (self.right_tail_smoothing_V or width)
        )
        tail_fraction = max(left_tail, right_tail)
        weight = tail_fraction + (1.0 - tail_fraction) * lobe
        if self.notch_depth_decades == 0.0:
            return weight
        notch_x = (gate_voltage_V - self.notch_center_gate_V) / self.notch_width_V
        notch_depth = self.notch_depth_decades * math.exp(-0.5 * notch_x * notch_x)
        return weight * 10.0 ** (-notch_depth)

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 40.0:
            return 1.0
        if value <= -40.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-value))

    def temperature_factor(self, temperature_K: float) -> float:
        if not math.isfinite(temperature_K) or temperature_K <= 0.0:
            raise ValueError("temperature_K must be finite and > 0")
        if self.temperature_activation_eV == 0.0:
            return 1.0
        exponent = -self.temperature_activation_eV / K_B_EV * (
            1.0 / temperature_K - 1.0 / self.temperature_reference_K
        )
        return math.exp(max(min(exponent, 700.0), -745.0))

    def drain_factor(self, drain_voltage_V: float) -> float:
        if not math.isfinite(drain_voltage_V):
            raise ValueError("drain_voltage_V must be finite")
        if self.drain_exponent == 0.0:
            return 1.0
        drive = max(abs(drain_voltage_V), 1.0e-30) / self.drain_reference_V
        return drive ** self.drain_exponent

    def current_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> float:
        peak = (
            self.peak_current_A_per_um
            * self.temperature_factor(temperature_K)
            * self.drain_factor(drain_voltage_V)
        )
        signal = peak * self.gate_weight(gate_voltage_V)
        return max(self.floor_current_A_per_um, signal)


@dataclass(frozen=True)
class WSe2TwoWindowTransferModel:
    """Two-window WSe2 transfer model with explicit electron/hole components."""

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
    def _log_sum_currents(currents: tuple[float, ...]) -> float:
        logs = [math.log(max(current, 1.0e-300)) for current in currents]
        base = max(logs)
        return math.exp(base) * sum(math.exp(value - base) for value in logs)

    def components_A_per_um(
        self,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
    ) -> dict[str, float]:
        electron = self.electron_window.current_A_per_um(
            gate_voltage_V, drain_voltage_V, temperature_K
        )
        hole = self.hole_window.current_A_per_um(
            gate_voltage_V, drain_voltage_V, temperature_K
        )
        coupled = self.component_coupling * math.sqrt(electron * hole)
        total = self._log_sum_currents(
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
        return self.components_A_per_um(
            gate_voltage_V, drain_voltage_V, temperature_K
        )["total_A_per_um"]
