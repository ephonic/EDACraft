"""IGZO tail-state transport calibration models.

The models in this module are calibrated transport modifiers for amorphous
oxide semiconductors.  They are opt-in: creating an a-IGZO material does not
silently enable them.  The first implementation is a compact occupancy kernel
that represents trap-limited percolation recovery as gate bias fills the
subgap tail manifold.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class IgzoTailOccupancyTransport:
    """Gate-controlled tail-state transport recovery factor.

    Parameters
    ----------
    minimum_factor:
        Low-gate transport multiplier.  Must be strictly positive.
    high_gate_factor:
        High-gate transport multiplier.  Defaults to ``1.0`` for the original
        recovery-to-baseline model, but can be fitted as a selector when a
        Sentaurus branch has temperature- or field-dependent mobility scaling.
    center_voltage_V:
        Gate voltage where tail-limited transport is half recovered.
    width_V:
        Logistic smoothing width.  Must be positive.

    Notes
    -----
    This compact model is a software-calibration proxy for tail-state /
    trap-limited percolation.  It intentionally returns a multiplicative
    current/mobility factor rather than changing material truth.
    """

    minimum_factor: float = 0.15
    center_voltage_V: float = 1.35
    width_V: float = 0.15
    high_gate_factor: float = 1.0

    def __post_init__(self) -> None:
        values = (
            self.minimum_factor,
            self.center_voltage_V,
            self.width_V,
            self.high_gate_factor,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("IGZO tail transport parameters must be finite")
        if self.minimum_factor <= 0.0:
            raise ValueError("minimum_factor must be > 0")
        if self.high_gate_factor <= 0.0:
            raise ValueError("high_gate_factor must be > 0")
        if self.width_V <= 0.0:
            raise ValueError("width_V must be > 0")

    def factor(self, gate_voltage_V: float) -> float:
        """Return the transport multiplier at gate bias ``gate_voltage_V``."""
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        arg = (float(gate_voltage_V) - self.center_voltage_V) / self.width_V
        arg = max(min(arg, 80.0), -80.0)
        recovery = 1.0 / (1.0 + math.exp(-arg))
        return float(
            self.minimum_factor
            + (self.high_gate_factor - self.minimum_factor) * recovery
        )

    def corrected_current_A_per_um(
        self, raw_current_A_per_um: float, gate_voltage_V: float
    ) -> float:
        """Apply the calibrated transport multiplier to a terminal current."""
        if not math.isfinite(raw_current_A_per_um):
            raise ValueError("raw_current_A_per_um must be finite")
        return float(raw_current_A_per_um) * self.factor(gate_voltage_V)


@dataclass(frozen=True)
class IgzoTailCalibration:
    """Named Sentaurus calibration for the IGZO tail transport kernel."""

    name: str
    branch: str
    minimum_factor: float
    center_voltage_V: float
    width_V: float
    high_gate_factor: float = 1.0
    log_current_floor_A_per_um: float = 0.0
    accepted: bool = False
    acceptance_mode: str = "direct_log_current"
    rmse_log_current_decades: float | None = None
    max_abs_log_current_error_decades: float | None = None
    raw_rmse_log_current_decades: float | None = None
    raw_max_abs_log_current_error_decades: float | None = None
    source: str = "sentaurus_material_deck_v1"

    def transport(self) -> IgzoTailOccupancyTransport:
        """Return the transport model represented by this calibration."""
        return IgzoTailOccupancyTransport(
            minimum_factor=self.minimum_factor,
            center_voltage_V=self.center_voltage_V,
            width_V=self.width_V,
            high_gate_factor=self.high_gate_factor,
        )


_SENTAURUS_V1_IGZO_TAIL_CALIBRATIONS = {
    "igzo_t10_T300_vd0p1": IgzoTailCalibration(
        name="igzo_t10_T300_vd0p1_tail_kernel_v1",
        branch="igzo_t10_T300_vd0p1",
        minimum_factor=0.15,
        center_voltage_V=1.35,
        width_V=0.15,
        high_gate_factor=1.0,
        accepted=True,
        rmse_log_current_decades=0.1154189516,
        max_abs_log_current_error_decades=0.2022216648,
        raw_rmse_log_current_decades=0.1154189516,
        raw_max_abs_log_current_error_decades=0.2022216648,
    ),
    "igzo_t10_T400_vd0p1": IgzoTailCalibration(
        name="igzo_t10_T400_vd0p1_tail_kernel_v1",
        branch="igzo_t10_T400_vd0p1",
        minimum_factor=0.05,
        center_voltage_V=1.5,
        width_V=0.08,
        high_gate_factor=0.25,
        accepted=True,
        rmse_log_current_decades=0.0527970082,
        max_abs_log_current_error_decades=0.0899497112,
        raw_rmse_log_current_decades=0.0527970082,
        raw_max_abs_log_current_error_decades=0.0899497112,
    ),
    "igzo_t5_T300_vd0p1": IgzoTailCalibration(
        name="igzo_t5_T300_vd0p1_tail_kernel_v1",
        branch="igzo_t5_T300_vd0p1",
        minimum_factor=0.15,
        center_voltage_V=1.2,
        width_V=0.05,
        high_gate_factor=1.0,
        accepted=True,
        rmse_log_current_decades=0.0176132172,
        max_abs_log_current_error_decades=0.0224585594,
        raw_rmse_log_current_decades=0.0176132172,
        raw_max_abs_log_current_error_decades=0.0224585594,
    ),
    "igzo_t20_T300_vd0p1": IgzoTailCalibration(
        name="igzo_t20_T300_vd0p1_tail_kernel_v1",
        branch="igzo_t20_T300_vd0p1",
        minimum_factor=0.15,
        center_voltage_V=1.0,
        width_V=0.05,
        high_gate_factor=1.0,
        accepted=True,
        rmse_log_current_decades=0.0113268981,
        max_abs_log_current_error_decades=0.0167287089,
        raw_rmse_log_current_decades=0.0113268981,
        raw_max_abs_log_current_error_decades=0.0167287089,
    ),
    "igzo_t10_T300_vd5p0": IgzoTailCalibration(
        name="igzo_t10_T300_vd5p0_tail_kernel_v1",
        branch="igzo_t10_T300_vd5p0",
        minimum_factor=0.15,
        center_voltage_V=1.5,
        width_V=0.12,
        high_gate_factor=1.0,
        accepted=True,
        rmse_log_current_decades=0.0234048905,
        max_abs_log_current_error_decades=0.0338311131,
        raw_rmse_log_current_decades=0.0234048905,
        raw_max_abs_log_current_error_decades=0.0338311131,
    ),
    "igzo_t10_T250_vd0p1": IgzoTailCalibration(
        name="igzo_t10_T250_vd0p1_tail_kernel_v1_candidate",
        branch="igzo_t10_T250_vd0p1",
        minimum_factor=0.3,
        center_voltage_V=0.8,
        width_V=0.08,
        high_gate_factor=2.8,
        log_current_floor_A_per_um=1.0e-36,
        accepted=True,
        acceptance_mode="floor_aware_log_current",
        rmse_log_current_decades=0.0337893986,
        max_abs_log_current_error_decades=0.0743968432,
        raw_rmse_log_current_decades=0.3495686606,
        raw_max_abs_log_current_error_decades=0.7105561319,
    ),
}


def igzo_tail_calibration(
    branch: str = "igzo_t10_T300_vd0p1",
    *,
    profile: str = "sentaurus_v1",
    require_accepted: bool = False,
) -> IgzoTailCalibration:
    """Return a named IGZO tail calibration.

    The selector is intentionally exact-branch based.  It avoids silent
    interpolation across temperature, thickness, or drain-bias branches until
    those branches have independent Sentaurus acceptance data.
    """
    if profile != "sentaurus_v1":
        raise KeyError(f"unknown IGZO tail calibration profile: {profile!r}")
    try:
        calibration = _SENTAURUS_V1_IGZO_TAIL_CALIBRATIONS[branch]
    except KeyError as exc:
        raise KeyError(f"no IGZO tail calibration for branch: {branch!r}") from exc
    if require_accepted and not calibration.accepted:
        raise ValueError(f"IGZO tail calibration is not accepted: {branch!r}")
    return calibration


def igzo_tail_calibrations(
    *,
    profile: str = "sentaurus_v1",
    accepted_only: bool = False,
) -> tuple[IgzoTailCalibration, ...]:
    """Return all named IGZO tail calibrations for a profile."""
    if profile != "sentaurus_v1":
        raise KeyError(f"unknown IGZO tail calibration profile: {profile!r}")
    calibrations = tuple(
        _SENTAURUS_V1_IGZO_TAIL_CALIBRATIONS[branch]
        for branch in sorted(_SENTAURUS_V1_IGZO_TAIL_CALIBRATIONS)
    )
    if accepted_only:
        return tuple(calibration for calibration in calibrations if calibration.accepted)
    return calibrations


def igzo_tail_transport(
    branch: str = "igzo_t10_T300_vd0p1",
    *,
    profile: str = "sentaurus_v1",
    require_accepted: bool = False,
) -> IgzoTailOccupancyTransport:
    """Return an IGZO tail transport model selected from Sentaurus calibration."""
    return igzo_tail_calibration(
        branch,
        profile=profile,
        require_accepted=require_accepted,
    ).transport()
