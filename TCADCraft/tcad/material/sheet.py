"""Isothermal ideal 2D band statistics in SI sheet units.

Energies/quasi-Fermi levels are in eV, electrostatic potential is in V.
This module uses SI constants independently of the volume core's build profile.
No effective thickness or fitted volume DOS enters these relations.
"""
from dataclasses import dataclass
import math

import numpy as np
from scipy.special import expit, spence

Q = 1.602176634e-19
KB = 1.380649e-23
HBAR = 1.054571817e-34
M0 = 9.1093837015e-31


def _finite(value, name):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'iuf' or raw.dtype.kind == 'b':
        raise ValueError(f'{name} must contain real numbers')
    out = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(out)):
        raise ValueError(f'{name} must be finite')
    return out


def _positive_scalar(value, name):
    out = _finite(value, name)
    if out.ndim != 0 or out <= 0:
        raise ValueError(f'{name} must be a positive scalar')
    return float(out)


def fermi_one(eta):
    """F_1(eta) = integral_0^inf x/(1+exp(x-eta)) dx.

    Negative tail uses the convergent fugacity series, avoiding cancellation
    in spence(1+exp(eta)). Reflection gives the positive degenerate limit.
    """
    value = _finite(eta, 'eta')
    x = -np.abs(value)
    z = np.exp(x)
    tail = np.zeros_like(x)
    term = z.copy()
    for k in range(1, 50):
        tail += term / (k*k)
        term *= -z
    negative = np.where(x < -1, tail, -spence(1 + z))
    with np.errstate(over='ignore'):
        result = np.where(value > 0, .5*value*value + math.pi**2/6 - negative, negative)
    if not np.all(np.isfinite(result)):
        raise OverflowError('Fermi integral is not representable')
    return result


def _occupation_difference(a, b, linear_dos):
    """Stable F(a)-F(b), including nearly neutral graphene."""
    occupation = fermi_one if linear_dos else lambda x: np.logaddexp(0., x)
    derivative = lambda x: np.logaddexp(0., x) if linear_dos else expit(x)
    direct = occupation(a) - occupation(b)
    delta = a-b
    # Integrate F' over the small difference. Four-point Gauss is much more
    # accurate than subtracting two almost equal occupations near neutrality.
    close = np.abs(delta) < 1e-3
    middle = .5*a + .5*b
    average = np.zeros_like(middle)
    for node, weight in ((-.8611363115940526,.3478548451374538),
                         (-.3399810435848563,.6521451548625461),
                         (.3399810435848563,.6521451548625461),
                         (.8611363115940526,.3478548451374538)):
        average += .5*weight*derivative(middle + .5*delta*node)
    return np.where(close, delta*average, direct)


@dataclass(frozen=True)
class SheetStatistics:
    n_m2: np.ndarray
    p_m2: np.ndarray
    dn_dFn_m2_eV: np.ndarray
    minus_dp_dFp_m2_eV: np.ndarray
    charge_C_m2: np.ndarray
    quantum_capacitance_F_m2: np.ndarray


@dataclass(frozen=True)
class SheetMaterial:
    """A single ideal parabolic subband pair or an ideal Dirac cone pair.

    Degeneracies include spin and valley exactly once. Parameters describe
    an ideal band model and are not experimental material calibration.
    Mobilities belong to the separate DD device configuration.
    """
    name: str
    dispersion: str
    gap_eV: float = 0.
    reference_eV: float = 0.  # midgap or Dirac energy at phi=0
    mass_n_m0: float = .5
    mass_p_m0: float = .6
    degeneracy_n: float = 4.
    degeneracy_p: float = 2.
    fermi_velocity_m_s: float = 1e6

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError('sheet material requires a name')
        if self.dispersion not in ('parabolic', 'dirac'):
            raise ValueError('dispersion must be parabolic or dirac')
        gap = _finite(self.gap_eV, 'gap_eV')
        reference = _finite(self.reference_eV, 'reference_eV')
        if gap.ndim or reference.ndim or gap < 0:
            raise ValueError('gap must be nonnegative and energies scalar')
        if self.dispersion == 'dirac' and (gap != 0 or self.degeneracy_n != self.degeneracy_p):
            raise ValueError('ideal Dirac sheets require zero gap and equal degeneracies')
        for name in ('mass_n_m0', 'mass_p_m0', 'degeneracy_n', 'degeneracy_p', 'fermi_velocity_m_s'):
            _positive_scalar(getattr(self, name), name)

    def statistics(self, phi_V=0., Fn_eV=0., Fp_eV=None, temperature_K=300.):
        """Return sheet carriers, charge and analytic charge susceptibility.

        Band edges shift by -phi_V in eV. Both quasi-Fermi levels use the
        electron-energy convention; at equilibrium Fn=Fp. Charge is q(p-n).
        Cq = -d(charge)/d(phi) at fixed Fn/Fp = q(dn/dFn-dp/dFp).
        No extra quantum-capacitance element should duplicate this derivative.
        """
        temperature = _positive_scalar(temperature_K, 'temperature_K')
        phi, fn, fp = np.broadcast_arrays(_finite(phi_V, 'phi_V'),
            _finite(Fn_eV, 'Fn_eV'), _finite(Fn_eV if Fp_eV is None else Fp_eV, 'Fp_eV'))
        vt = KB*temperature/Q
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            a = (fn + phi - self.reference_eV - self.gap_eV/2)/vt
            b = (self.reference_eV - self.gap_eV/2 - phi - fp)/vt
            if self.dispersion == 'parabolic':
                pref_n = self.degeneracy_n*self.mass_n_m0*M0*KB*temperature/(2*math.pi*HBAR**2)
                pref_p = self.degeneracy_p*self.mass_p_m0*M0*KB*temperature/(2*math.pi*HBAR**2)
                n, p = pref_n*np.logaddexp(0., a), pref_p*np.logaddexp(0., b)
                an, ap = pref_n/vt*expit(a), pref_p/vt*expit(b)
                # Use the cancellation-safe identity when the DOS are equal.
                net = pref_n*_occupation_difference(b, a, False) if pref_n == pref_p else p-n
            else:
                pref = self.degeneracy_n/(2*math.pi)*(KB*temperature/(HBAR*self.fermi_velocity_m_s))**2
                n, p = pref*fermi_one(a), pref*fermi_one(b)
                an, ap = pref/vt*np.logaddexp(0., a), pref/vt*np.logaddexp(0., b)
                net = pref*_occupation_difference(b, a, True)
            values = (n, p, an, ap, Q*net, Q*(an+ap))
        output = []
        for value in values:
            copy = np.array(value, dtype=float, copy=True)
            if not np.all(np.isfinite(copy)):
                raise OverflowError('sheet statistics are not representable')
            copy.setflags(write=False)
            output.append(copy)
        return SheetStatistics(*output)


def mos2_sheet(*, gap_eV=1.8, mass_n_m0=.5, mass_p_m0=.6,
               degeneracy_n=4., degeneracy_p=2., reference_eV=0.):
    """Representative single-subband MoS2 model; override for a calibrated sample."""
    return SheetMaterial('MoS2 sheet', 'parabolic', gap_eV, reference_eV,
                         mass_n_m0, mass_p_m0, degeneracy_n, degeneracy_p)


def graphene_sheet(*, fermi_velocity_m_s=1e6, degeneracy=4., reference_eV=0.):
    """Ideal graphene sheet; excludes puddles, gaps, ribbons and interaction corrections."""
    return SheetMaterial('Graphene sheet', 'dirac', reference_eV=reference_eV,
                         degeneracy_n=degeneracy, degeneracy_p=degeneracy,
                         fermi_velocity_m_s=fermi_velocity_m_s)
