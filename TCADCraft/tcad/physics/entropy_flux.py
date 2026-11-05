"""Conservative face-flux blending against supplied thermodynamic forces.

This algebraic utility does not reconstruct states, evaluate an EOS or prove a
fully discrete entropy inequality. A caller must supply forces from the stored
thermodynamic states and the potential used by its electrical-work ledger.
"""
from dataclasses import dataclass
import numpy as np


def _finite(value):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'fiu':
        raise ValueError('real finite numeric data required')
    result = np.asarray(raw, dtype=np.longdouble)
    if not np.all(np.isfinite(result)):
        raise ValueError('real finite numeric data required')
    return result


def _owned(value):
    result = np.array(value, dtype=np.longdouble, copy=True)
    result.flags.writeable = False
    return result


def carrier_entropy_forces(temperature_owner_K, temperature_neighbor_K,
                           chemical_owner_J, chemical_neighbor_J, *, charge_C,
                           potential_owner_V, potential_neighbor_V,
                           potential_face_V):
    """Return (..., 2) forces conjugate to particle and material-energy flux.

    chemical_* are material chemical potentials, excluding electrostatic
    potential. Potentials must match the electrical-work discretization; for a
    midpoint-work ledger these are midpoint potentials. Positive flux leaves
    the owner. The paired value is face entropy production in W/K.
    """
    t_o, t_n, m_o, m_n, charge, p_o, p_n, p_f = np.broadcast_arrays(*map(_finite,
        (temperature_owner_K, temperature_neighbor_K, chemical_owner_J,
         chemical_neighbor_J, charge_C, potential_owner_V,
         potential_neighbor_V, potential_face_V)))
    if np.any(t_o <= 0) or np.any(t_n <= 0):
        raise ValueError('strictly positive temperatures required')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        particle = (m_o+charge*(p_o-p_f))/t_o-(m_n+charge*(p_n-p_f))/t_n
        energy = 1/t_n-1/t_o
    return _owned(_finite(np.stack((particle, energy), axis=-1)))


def _pairs(*values):
    rows = [_finite(value) for value in values]
    if any(row.ndim == 0 or row.shape[-1] != 2 for row in rows):
        raise ValueError('last dimension must contain particle and energy components')
    return np.broadcast_arrays(*rows)


def entropy_flux_pairing(flux, forces):
    """Pair (..., 2) particle/material-energy flux with its supplied forces."""
    flux, forces = _pairs(flux, forces)
    with np.errstate(over='ignore', invalid='ignore'):
        value = np.sum(flux*forces, axis=-1, dtype=np.longdouble)
    return _owned(_finite(value))


@dataclass(frozen=True)
class EntropyLimitedFlux:
    flux: np.ndarray
    high_order_fraction: np.ndarray
    entropy_production: np.ndarray


def limit_entropy_flux(low_order_flux, high_order_flux, forces):
    """Use one convex weight for both conserved flux components per face.

    The baseline must have nonnegative pairing under the supplied forces;
    otherwise reject, without a sign tolerance or silent baseline repair.
    Keep an admissible candidate exactly. For a negative candidate, contract
    its weight slightly inside the nonnegative affine half-space. Roundoff
    may require reverting an affected face to the already checked baseline.
    Returned arrays own their storage and are read-only.

    This guarantees the returned floating-point pairing, not occupation bounds,
    density positivity, FD admissibility or a complete time-step entropy law.
    """
    low, high, forces = _pairs(low_order_flux, high_order_flux, forces)
    sigma_low = entropy_flux_pairing(low, forces)
    sigma_high = entropy_flux_pairing(high, forces)
    if np.any(sigma_low < 0):
        raise ValueError('baseline entropy pairing must be nonnegative')
    limited = sigma_high < 0
    theta = np.ones(sigma_low.shape, dtype=np.longdouble)
    # sigma_low/(sigma_low-sigma_high), evaluated without an overflowing sum.
    scale = np.maximum(sigma_low, -sigma_high)
    a = np.zeros_like(theta); b = np.zeros_like(theta)
    np.divide(sigma_low, scale, out=a, where=limited)
    np.divide(-sigma_high, scale, out=b, where=limited)
    np.divide(a, a+b, out=theta, where=limited)
    theta = np.where(limited, theta*(1-16*np.finfo(np.longdouble).eps), theta)
    with np.errstate(over='ignore', invalid='ignore'):
        # Weighted sum avoids overflow in high-low for opposite large values.
        flux = (1-theta[..., None])*low+theta[..., None]*high
    # Preserve exact endpoints, including signed zeros.
    flux = np.where((theta == 1)[..., None], high, flux)
    flux = np.where((theta == 0)[..., None], low, flux)
    _finite(flux)
    sigma = entropy_flux_pairing(flux, forces)
    fallback = sigma < 0
    flux = np.where(fallback[..., None], low, flux)
    theta = np.where(fallback, np.longdouble(0), theta)
    sigma = entropy_flux_pairing(flux, forces)
    return EntropyLimitedFlux(_owned(flux), _owned(theta), sigma)
