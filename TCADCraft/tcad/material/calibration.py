"""Traceable, static two-observable calibration of a reduced quartic FE law.

The inferred spinodal law matches measured Pr/Ec by construction. It does not
identify domain kinetics, viscosity, leakage, permittivity, or a device model.
"""
from dataclasses import dataclass, asdict
import math


def _positive(value, name):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be a finite positive scalar')
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f'{name} must be a finite positive scalar') from error
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f'{name} must be a finite positive scalar')
    return result


@dataclass(frozen=True)
class StaticLandauCalibration:
    remanence_C_m2: float
    coercive_field_V_m: float
    alpha: float
    beta: float
    source: str
    specimen: str

    def report(self):
        return dict(**asdict(self), model='E=alpha*P+beta*P^3',
            scope='Reduced static fit to published approximate Pr and Ec',
            dynamic_viscosity=None, experimental_uncertainty=None,
            independent_validation=False, physical_validated=False,
            unidentified=['viscosity', 'switching-time distribution',
                'permittivity', 'leakage', 'transport', 'temperature dependence'])

    def configure_lk(self, simulator, mask, *, viscosity):
        """Apply the fitted static law; the caller must supply dynamic viscosity."""
        gamma = _positive(viscosity, 'viscosity')
        simulator.set_ferroelectric_params(mask, self.alpha, self.beta)
        simulator.set_ferroelectric_gamma(gamma)


def fit_static_landau(remanence_C_m2, coercive_field_V_m, *, source, specimen):
    """Fit alpha/beta using Pr=sqrt(-alpha/beta) and the cubic spinodal Ec.

    Inputs are SI. 1 uC/cm^2=0.01 C/m^2; 1 MV/cm=1e8 V/m.
    Source/specimen are required to prevent unlabelled process extrapolation.
    """
    pr = _positive(remanence_C_m2, 'remanence_C_m2')
    ec = _positive(coercive_field_V_m, 'coercive_field_V_m')
    if not isinstance(source, str) or not source.strip():
        raise ValueError('source must identify the measurement provenance')
    if not isinstance(specimen, str) or not specimen.strip():
        raise ValueError('specimen must identify the measured film or stack')
    try:
        alpha = -(3*math.sqrt(3)/2)*ec/pr
        beta = -alpha/pr**2
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError('Landau coefficients exceed the finite numeric range') from error
    if not math.isfinite(alpha) or not math.isfinite(beta) or alpha >= 0 or beta <= 0:
        raise ValueError('Landau coefficients exceed the finite numeric range')
    return StaticLandauCalibration(pr, ec, alpha, beta, source.strip(), specimen.strip())


def published_alscn_2025_static():
    """40 nm Al0.8Sc0.2N single layer, room temperature; Fig. 1e/f and text.

    DOI 10.1038/s41467-025-62904-6 reports approximately Pr=105 uC/cm^2
    and Ec=7.0 MV/cm. These observables use distinct PUND protocols (1 us
    square and 50 kHz triangular pulses). Raw data are restricted. Consequently
    this is a process-specific static surrogate, with no dynamic validation.
    """
    return fit_static_landau(105*.01, 7.0e8,
        source='https://www.nature.com/articles/s41467-025-62904-6',
        specimen='40 nm Al0.8Sc0.2N; HfN0.4 bottom/TiN top; room temperature; AlN insert=0 nm')
