"""Degenerate, anisotropic multi-valley thermionic interface moments.

This module is deliberately independent of the equal-mass Maxwell interface.
Each valley has its own density-of-states and normal transport mass, while a
common electrochemical potential is reconstructed from the total reservoir
density.  The Fermi supply correction reduces exactly to the Maxwell limit at
low occupancy and is retained in the energy and entropy ledger.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit, logsumexp

Q = 1.602176634e-19
KB = 1.380649e-23
H = 6.62607015e-34


@dataclass(frozen=True)
class ThermionicValley:
    """One anisotropic valley, with masses expressed as multiples of ``m0``."""

    name: str
    degeneracy: float
    mass_normal: float
    mass_tangent_1: float
    mass_tangent_2: float
    band_offset_owner_J: float = 0.0
    band_offset_neighbor_J: float = 0.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("valley name must be nonempty")
        for name in ("degeneracy", "mass_normal", "mass_tangent_1", "mass_tangent_2"):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("band_offset_owner_J", "band_offset_neighbor_J"):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or not np.isfinite(value):
                raise ValueError(f"{name} must be finite")

    @property
    def dos_mass_ratio(self):
        return (self.mass_normal * self.mass_tangent_1 * self.mass_tangent_2) ** (1.0 / 3.0)


@lru_cache(maxsize=1)
def _quadrature():
    return np.polynomial.legendre.leggauss(128)


@lru_cache(maxsize=8192)
def _fermi(order, eta):
    """Normalized complete Fermi integral with ``F_j -> exp(eta)``."""
    eta = float(eta)
    if not math.isfinite(eta):
        raise ValueError("finite reduced chemical potential required")
    if order not in (0., .5, 1., 1.5, 2.):
        raise ValueError('supported Fermi orders are 0, 1/2, 1, 3/2 and 2')
    if order == 0.0:
        return float(np.logaddexp(0.0, eta))
    if eta < -16.:
        fugacity = math.exp(eta)
        return fugacity * (1. - fugacity / 2.**(order+1) + fugacity**2 / 3.**(order+1))
    if eta > 100.:
        # Sommerfeld expansion through eta^-6, normalized by Gamma(j+1).
        j = order
        terms = (eta**(j+1)/(j+1) + math.pi**2/6*j*eta**(j-1)
            + 7*math.pi**4/360*j*(j-1)*(j-2)*eta**(j-3)
            + 31*math.pi**6/15120*j*(j-1)*(j-2)*(j-3)*(j-4)*eta**(j-5))
        return terms / math.gamma(j+1)
    nodes, weights = _quadrature()
    # x=t^2 removes the square-root endpoint singularity for half orders.
    breaks=sorted({0., max(0.,eta-16.), max(0.,eta+16.), max(48.,eta+48.)})
    total=0.
    for lower,upper in zip(breaks,breaks[1:]):
        left,right=math.sqrt(lower),math.sqrt(upper)
        t=left+.5*(right-left)*(nodes+1.)
        total+=(right-left)*float(np.sum(weights*t**(2*order+1)*expit(eta-t*t)))
    return total / math.gamma(order+1)


def _solve_mu(density, temperature, valleys, edges, statistics='fermi_dirac'):
    if density <= 0 or temperature <= 0:
        raise ValueError("density and temperature must be positive")
    m0 = 9.1093837015e-31
    pref = []
    for valley in valleys:
        md = valley.dos_mass_ratio * m0
        nc = 2.0 * (2.0 * math.pi * md * KB * temperature / H ** 2) ** 1.5
        pref.append(valley.degeneracy * nc)
    origin = min(edges)
    offsets = (np.asarray(edges)-origin)/(KB*temperature)
    eta_mb = math.log(density)-float(logsumexp(np.log(pref)-offsets))
    if statistics == 'boltzmann':
        return origin+KB*temperature*eta_mb, tuple(pref)
    def residual(eta):
        return sum(c*_fermi(.5, float(eta-d)) for c,d in zip(pref,offsets))/density-1.
    lo = eta_mb-2.
    hi = max(eta_mb+2., 2.)
    for _ in range(64):
        if residual(hi) >= 0:
            break
        hi *= 2.
    else:
        raise ValueError('density exceeds supported chemical-potential range')
    eta = brentq(residual, lo, hi, xtol=1e-14, rtol=1e-15)
    return origin+KB*temperature*eta, tuple(pref)


def multivalley_thermionic_interface_flux(
    density_owner_m3, density_neighbor_m3, temperature_owner_K, temperature_neighbor_K,
    band_owner_J, band_neighbor_J, valleys, area_m2, *, potential_V=0.0,
    charge_sign=-1, statistics="fermi_dirac", emission_factor=2.0,
):
    """Return particle/energy/entropy moments for a valley-resolved interface.

    ``band_owner_J`` and ``band_neighbor_J`` are common reference band edges;
    each valley's offsets form the actual matched valley edge.  The returned
    moments use the same owner-to-neighbor sign convention as the legacy
    interface.  ``statistics='boltzmann'`` is available as a low-density
    reference and converges to the Fermi result as occupancy vanishes.
    """
    values = (density_owner_m3, density_neighbor_m3, temperature_owner_K, temperature_neighbor_K,
              band_owner_J, band_neighbor_J, area_m2, potential_V, emission_factor)
    if any(isinstance(v, (bool, np.bool_)) or not np.isscalar(v) or not np.isfinite(v) for v in values):
        raise ValueError("all interface scalars must be finite real values")
    if density_owner_m3 <= 0 or density_neighbor_m3 <= 0 or temperature_owner_K <= 0 or temperature_neighbor_K <= 0 or area_m2 <= 0:
        raise ValueError("densities, temperatures and area must be positive")
    if statistics not in ("boltzmann", "fermi_dirac"):
        raise ValueError("statistics must be boltzmann or fermi_dirac")
    valleys = tuple(valleys)
    if not valleys or not all(isinstance(v, ThermionicValley) for v in valleys):
        raise ValueError("at least one ThermionicValley is required")
    names = [v.name for v in valleys]
    if len(set(names)) != len(names):
        raise ValueError("valley names must be unique")
    owner_edges = [band_owner_J + v.band_offset_owner_J for v in valleys]
    neighbor_edges = [band_neighbor_J + v.band_offset_neighbor_J for v in valleys]
    if isinstance(charge_sign,(bool,np.bool_)) or charge_sign not in (-1,1) or emission_factor < 0:
        raise ValueError('charge sign must be -1 or +1 and emission factor nonnegative')
    mu_o, pref_o = _solve_mu(density_owner_m3, temperature_owner_K, valleys, owner_edges, statistics)
    mu_n, pref_n = _solve_mu(density_neighbor_m3, temperature_neighbor_K, valleys, neighbor_edges, statistics)
    m0 = 9.1093837015e-31
    forward = reverse = material = 0.0
    kinetic_o = kinetic_n = 0.0
    storage_o = storage_n = 0.0
    per_valley = []
    for valley, eo, en, co, cn in zip(valleys, owner_edges, neighbor_edges, pref_o, pref_n):
        eta_o = (mu_o - eo) / (KB * temperature_owner_K)
        eta_n = (mu_n - en) / (KB * temperature_neighbor_K)
        barrier = max(eo, en)
        delta_o = (barrier - eo) / (KB * temperature_owner_K)
        delta_n = (barrier - en) / (KB * temperature_neighbor_K)
        fo = math.exp(eta_o) if statistics == 'boltzmann' else _fermi(.5, eta_o)
        fn = math.exp(eta_n) if statistics == 'boltzmann' else _fermi(.5, eta_n)
        no = co * fo
        nn = cn * fn
        uo = 1.5*KB*temperature_owner_K*(1. if statistics=='boltzmann' else _fermi(1.5,eta_o)/fo)
        un = 1.5*KB*temperature_neighbor_K*(1. if statistics=='boltzmann' else _fermi(1.5,eta_n)/fn)
        storage_o += no*(eo+uo)
        storage_n += nn*(en+un)
        vn_o = math.sqrt(KB * temperature_owner_K / (2.0 * math.pi * valley.mass_normal * m0))
        vn_n = math.sqrt(KB * temperature_neighbor_K / (2.0 * math.pi * valley.mass_normal * m0))
        if statistics == "boltzmann":
            supply_o = math.exp(eta_o-delta_o)
            supply_n = math.exp(eta_n-delta_n)
            energy_o = 2*KB*temperature_owner_K*supply_o
            energy_n = 2*KB*temperature_neighbor_K*supply_n
        else:
            supply_o = _fermi(1., eta_o-delta_o)
            supply_n = _fermi(1., eta_n-delta_n)
            energy_o = 2*KB*temperature_owner_K*_fermi(2., eta_o-delta_o)
            energy_n = 2*KB*temperature_neighbor_K*_fermi(2., eta_n-delta_n)
        scale_o = emission_factor*area_m2*co*vn_o
        scale_n = emission_factor*area_m2*cn*vn_n
        fo_rate = scale_o*supply_o
        fn_rate = scale_n*supply_n
        number = fo_rate-fn_rate
        excess = scale_o*energy_o-scale_n*energy_n
        forward += fo_rate
        reverse += fn_rate
        kinetic_o += (barrier-eo)*number+excess
        kinetic_n += (barrier-en)*number+excess
        material += barrier*number+excess
        per_valley.append(dict(name=valley.name, forward_particle_rate_s=fo_rate,
            reverse_particle_rate_s=fn_rate, barrier_J=barrier, owner_eta=eta_o, neighbor_eta=eta_n,
            dos_mass_ratio=valley.dos_mass_ratio, normal_mass_ratio=valley.mass_normal))
    particle = forward - reverse
    electrochemical = material + charge_sign * Q * potential_V * particle
    entropy = (material - mu_n * particle) / temperature_neighbor_K - (material - mu_o * particle) / temperature_owner_K
    if not all(np.isfinite(x) for x in (particle, forward, reverse, material, electrochemical, entropy)):
        raise ValueError("nonfinite multi-valley interface moment")
    return dict(particle_flux_s=particle, forward_particle_rate_s=forward, reverse_particle_rate_s=reverse,
        kinetic_owner_flux_W=kinetic_o, kinetic_neighbor_flux_W=kinetic_n,
        material_energy_flux_W=material, electrochemical_energy_flux_W=electrochemical,
        lattice_heat_owner_W=storage_o/density_owner_m3*particle-material,
        lattice_heat_neighbor_W=material-storage_n/density_neighbor_m3*particle,
        entropy_production_W_K=entropy, chemical_potential_owner_J=mu_o,
        chemical_potential_neighbor_J=mu_n, statistics=statistics, valley_count=len(valleys),
        valley_moments=per_valley, complete_device_energy=False, physical_validated=False)
