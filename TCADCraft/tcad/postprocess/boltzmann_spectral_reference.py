"""Independent classical reservoir and bulk spectral moments for diagnostics.

This is not a solver option or a conversion of FD trajectories. It evaluates
the MB equation of state and occupations on explicitly supplied states. Bulk
resistances match the fixed-band spectral model; thermionic interfaces and
valley offsets that differ across a face are deliberately excluded.
"""
import math
import numpy as np
from scipy.integrate import quad_vec
from scipy.special import logsumexp

KB = 1.380649e-23
Q = 1.602176634e-19
H = 6.62607015e-34
M0 = 9.1093837015e-31


def _finite(value, name, *, positive=False):
    if (isinstance(value, (bool, np.bool_)) or not np.isscalar(value)
            or not np.isrealobj(value) or not np.isfinite(value)
            or (positive and value <= 0)):
        raise ValueError('finite '+('positive ' if positive else '')+name+' required')
    return float(value)


def _valleys(values):
    values = tuple(values)
    if not values:
        raise ValueError('at least one explicit valley required')
    for v in values:
        for key in ('degeneracy', 'dos_mass_ratio'):
            _finite(getattr(v, key), key, positive=True)
        _finite(v.band_offset_owner_J, 'valley offset')
        if v.band_offset_owner_J != v.band_offset_neighbor_J:
            raise ValueError('same valley offset at both bulk endpoints required')
    return values


def boltzmann_reservoir(density_m3, temperature_K, band_J, valleys):
    """Exact parabolic-DOS MB moments, without production Fermi kernels."""
    n = _finite(density_m3, 'density', positive=True)
    t = _finite(temperature_K, 'temperature', positive=True)
    band = _finite(band_J, 'band')
    valleys = _valleys(valleys)
    edges = np.array([band+v.band_offset_owner_J for v in valleys])
    origin = min(edges)
    logpref = np.array([math.log(2*v.degeneracy)+1.5*(math.log(2*math.pi*v.dos_mass_ratio*M0*KB/H**2)+math.log(t))
                        for v in valleys])
    logs = logpref-(edges-origin)/(KB*t)
    normalization = float(logsumexp(logs))
    eta = math.log(n)-normalization
    fractions = np.exp(logs-normalization)
    energy = n*(origin+float(fractions@(edges-origin))+1.5*KB*t)
    chemical = origin+KB*t*eta
    if not all(math.isfinite(v) for v in (energy, chemical)):
        raise ValueError('representable MB reservoir moments required')
    return dict(density_m3=n, temperature_K=t, band_J=band,
                chemical_potential_J=chemical, energy_density_J_m3=energy,
                statistics='boltzmann', valley_populations_m3=(n*fractions).tolist())


def boltzmann_bulk_face(owner, neighbor, valleys, *, phi_o, phi_n, phi_f,
                        z, mu_o, mu_n, area, do, dn,
                        bulk_potential_path='linear_series'):
    """Adaptive MB particle/material-energy/entropy spectral moments.

    Each endpoint must be returned by boltzmann_reservoir with the same valley
    set. ``do`` is positive and ``dn`` may be zero at a contact. Mobilities are
    supplied independently of carrier temperature, e.g. from lattice state.
    Entropy is the integral of (f_o-f_n)*log(f_o/f_n), with no clipping.
    """
    valleys = _valleys(valleys)
    for row in (owner, neighbor):
        if row.get('statistics') != 'boltzmann':
            raise ValueError('explicit MB reservoirs required')
        for key in ('temperature_K', 'density_m3'):
            _finite(row[key], key, positive=True)
        for key in ('band_J', 'chemical_potential_J'):
            _finite(row[key], key)
    phi_o, phi_n, phi_f = [_finite(v, 'potential') for v in (phi_o, phi_n, phi_f)]
    if isinstance(z, (bool, np.bool_)) or z not in (-1, 1):
        raise ValueError('carrier charge sign -1 or +1 required')
    mu_o, mu_n, area, do = [_finite(v, 'geometry/mobility', positive=True) for v in (mu_o, mu_n, area, do)]
    dn = _finite(dn, 'neighbor distance')
    if dn < 0 or bulk_potential_path not in ('linear_series', 'endpoint_barrier'):
        raise ValueError('nonnegative neighbor distance and supported bulk path required')
    to, tn = owner['temperature_K'], neighbor['temperature_K']
    scale = KB*max(to, tn)
    chemical_o = owner['chemical_potential_J']+z*Q*phi_o
    chemical_n = neighbor['chemical_potential_J']+z*Q*phi_n
    rows = []
    for v in valleys:
        uo = owner['band_J']+v.band_offset_owner_J+z*Q*phi_o
        un = neighbor['band_J']+v.band_offset_neighbor_J+z*Q*phi_n
        high = max(uo, un)
        dos = 2*v.degeneracy*(2*math.pi*v.dos_mass_ratio*M0*KB*300/H**2)**1.5
        prefactor = area*2/(3*Q)*dos/((KB*300)**1.5*math.gamma(1.5))
        midpoint = (dn*uo+do*un)/(do+dn)

        def conductance(e):
            if bulk_potential_path == 'endpoint_barrier':
                return prefactor*(e-high)**1.5/(do/mu_o+dn/mu_n)
            def resistance(length, mobility, a, b):
                sa, sb = math.sqrt(e-a), math.sqrt(e-b)
                return 2*length/(mobility*sa*sb*(sa+sb))
            value = resistance(do, mu_o, uo, midpoint)
            if dn:
                value += resistance(dn, mu_n, midpoint, un)
            return prefactor/value

        normalizer = conductance(high+scale)
        ao0 = (chemical_o-high)/(KB*to)
        an0 = (chemical_n-high)/(KB*tn)
        log_population = max(ao0, an0)
        population = math.exp(log_population)
        if not math.isfinite(population) or population == 0:
            raise ValueError('representable nonzero MB spectral population required')

        def integrand(t):
            e = high+scale*t*t
            ao = ao0-scale/(KB*to)*t*t
            an = an0-scale/(KB*tn)*t*t
            # Stable even when both reservoirs have almost identical occupations.
            diff = (math.exp(ao-log_population)*(-math.expm1(an-ao)) if ao >= an
                    else math.exp(an-log_population)*math.expm1(ao-an))
            flow = 2*t*conductance(e)/normalizer*diff
            return flow*np.array([1., t*t, ao-an])

        moments = quad_vec(integrand, 0., math.sqrt(80.), epsabs=2e-13, epsrel=2e-12, limit=500)[0]
        rate = normalizer*scale*population*moments[0]
        total = high*rate+normalizer*scale**2*population*moments[1]
        rows.append(dict(name=v.name, particle_flux_s=float(rate), total_energy_flux_W=float(total),
                         entropy_production_W_K=float(KB*normalizer*scale*population*moments[2])))
    rate = math.fsum(r['particle_flux_s'] for r in rows)
    total = math.fsum(r['total_energy_flux_W'] for r in rows)
    entropy = math.fsum(r['entropy_production_W_K'] for r in rows)
    if not all(math.isfinite(v) for v in (rate, total, entropy)):
        raise ValueError('representable MB face moments required')
    return dict(particle_flux_s=rate, total_energy_flux_W=total,
                material_energy_flux_W=total-z*Q*phi_f*rate,
                entropy_production_W_K=entropy, valley_moments=rows, statistics='boltzmann',
                scope='independent_fixed_band_bulk_MB_diagnostic')
