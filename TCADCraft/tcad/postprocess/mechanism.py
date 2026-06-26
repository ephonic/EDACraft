"""D2 mechanism attribution (plan0619.md §D2).

Decomposes the total current into drift / diffusion / BTBT / FE-polarization
components and labels the *dominant* transport mechanism for a candidate.
This answers "why is this candidate good" and feeds the B4 novelty metric
(the mechanism-fraction vector is a structural+physics signature, more
informative than the bag-of-kinds histogram alone — plan §64).

Components
----------
1. **Drift / diffusion split** of the Scharfetter-Gummel edge flux.  The
   solver stores only the combined Bernoulli flux (``current.sg_current_density_1d``
   returns Jn, Jp totals); here we re-derive the classical split
   ``Jn_drift = -q*mu_n*n_avg*d(phi)/dx``, ``Jn_diff = q*mu_n*VT*d(n)/dx``
   which sums (in magnitude) to the SG total on each edge.

2. **BTBT generation** (local Kane model, recomputed from the E-field because
   ``simulate_sweep`` does not expose the solver's internal G_btbt and does
   not auto-enable BTBT).  Uses the corrected ``B_kane=2.0e9`` V/m (the
   ``tfet.py`` default ``2.0e7`` is a known stale V/cm-convention value).

3. **FE polarization charge** magnitude from ``result["P"][:,0]`` (the
   in-plane Px component; FE nodes identified by ``|Px|>1e-30``, matching
   ``discovery._px_at_vg0``).

The four magnitudes are normalized into a **mechanism-fraction vector**
``[drift, diffusion, btbt, fe]`` (sums to 1); the argmax is the dominant
label.  ``mechanism_feature_vector`` returns this 4-D vector for B4 novelty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from .bands import cutline_x_at_jk
from .current import sg_current_density_1d, QE

# Corrected Kane B coefficient [V/m] (audit §12.4; tfet.py still carries the
# stale 2.0e7 V/cm value — mechanism.py uses the SI-correct 2.0e9).
B_KANE_SI = 2.0e9
A_KANE = 3.1e21   # [cm^-3 s^-1 V^-D]
KANE_D = 2
BTBT_FIELD_FLOOR = 1e4   # |E| below this -> G_btbt = 0 (V/m)


# ---------------------------------------------------------------------------
# 1. Drift / diffusion split (1-D, on the x cutline)
# ---------------------------------------------------------------------------

def drift_diffusion_split_1d(
    phi: np.ndarray,
    n: np.ndarray,
    p: np.ndarray,
    dx: float,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
    VT: float,
) -> Dict[str, np.ndarray]:
    """Split the SG electron/hole flux into drift and diffusion parts [A/m^2].

    Classical decomposition (valid away from degenerate limits):
        Jn_drift = -q * mu_n * n_avg * d(phi)/dx
        Jn_diff  =  q * mu_n * VT * d(n)/dx
    with ``n_avg = (n[i]+n[i+1])/2`` and node-upwind mobility ``mu_n[i]``
    (matching ``sg_current_density_1d``).  ``|Jn_drift| + |Jn_diff|`` agrees
    with ``|Jn_total|`` from the Bernoulli form in the drift-diffusion limit.

    Returns per-edge arrays of length ``len(phi)-1``:
    ``Jn_drift, Jn_diff, Jp_drift, Jp_diff``.
    """
    phi = np.asarray(phi, dtype=float)
    n = np.asarray(n, dtype=float)
    p = np.asarray(p, dtype=float)
    mu_n = np.asarray(mu_n, dtype=float)
    mu_p = np.asarray(mu_p, dtype=float)

    dphi = (phi[1:] - phi[:-1]) / dx
    dn = (n[1:] - n[:-1]) / dx
    dp = (p[1:] - p[:-1]) / dx
    n_avg = 0.5 * (n[:-1] + n[1:])
    p_avg = 0.5 * (p[:-1] + p[1:])
    mu_n_e = mu_n[:-1]   # node-upwind
    mu_p_e = mu_p[:-1]

    Jn_drift = -QE * mu_n_e * n_avg * dphi
    Jn_diff = QE * mu_n_e * VT * dn
    Jp_drift = -QE * mu_p_e * p_avg * dphi
    Jp_diff = -QE * mu_p_e * VT * dp   # hole diffusion opposes dn sign convention
    return {"Jn_drift": Jn_drift, "Jn_diff": Jn_diff,
            "Jp_drift": Jp_drift, "Jp_diff": Jp_diff}


# ---------------------------------------------------------------------------
# 2. BTBT generation (local Kane, recomputed from E-field)
# ---------------------------------------------------------------------------

def btbt_generation(
    result: Dict,
    mesh,
    A_kane: float = A_KANE,
    B_kane: float = B_KANE_SI,
    D: int = KANE_D,
) -> Tuple[np.ndarray, float]:
    """Per-node BTBT generation rate [m^-3 s^-1] and total BTBT current [A].

    Local Kane model: ``G = A*|E|^D*exp(-B/|E|)`` (A in cm^-3 s^-1 V^-D,
    converted to m^-3; B in V/m).  Fields below ``BTBT_FIELD_FLOOR`` are zeroed
    (no tunneling at negligible field).  ``I_btbt = q * sum(G * dV)``.
    """
    Ex = np.asarray(result.get("Ex", np.zeros(mesh.npts())), dtype=float)
    Ey = np.asarray(result.get("Ey", np.zeros(mesh.npts())), dtype=float)
    Ez = np.asarray(result.get("Ez", np.zeros(mesh.npts())), dtype=float)
    E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)
    E_safe = np.maximum(E_mag, BTBT_FIELD_FLOOR)
    # A in cm^-3 -> m^-3 via *1e6
    G = (A_kane * 1e6) * E_safe**D * np.exp(-B_kane / E_safe)  # m^-3 s^-1
    G[E_mag < BTBT_FIELD_FLOOR] = 0.0
    g = mesh.to_cxx_grid()
    dV = g["dx"] * g["dy"] * g["dz"]
    I_btbt = float(QE * G.sum() * dV)
    return G, I_btbt


# ---------------------------------------------------------------------------
# 3. FE polarization charge magnitude
# ---------------------------------------------------------------------------

def fe_polarization_charge(result: Dict) -> Tuple[float, np.ndarray]:
    """Representative FE polarization magnitude and the FE-node mask.

    Reads ``result["P"][:,0]`` (Px).  FE nodes are those with ``|Px|>1e-30``
    (matching ``discovery._px_at_vg0``).  Returns
    ``(P_mag, fe_mask)`` where ``P_mag`` is the mean ``|Px|`` over FE nodes
    (0.0 if no FE nodes).
    """
    P = np.asarray(result.get("P", np.zeros((0, 3))), dtype=float)
    if P.size == 0:
        return 0.0, np.zeros(0, dtype=bool)
    Px = P[:, 0]
    fe_mask = np.abs(Px) > 1e-30
    if not fe_mask.any():
        return 0.0, fe_mask
    P_mag = float(np.mean(np.abs(Px[fe_mask])))
    return P_mag, fe_mask


# ---------------------------------------------------------------------------
# 4. Mechanism report
# ---------------------------------------------------------------------------

#: The four mechanism labels, in feature-vector order.
MECHANISM_LABELS = ("drift", "diffusion", "btbt", "fe_polarization")


@dataclass
class MechanismReport:
    """Dominant transport mechanism + per-mechanism fractions for a candidate."""
    dominant: str                          # one of MECHANISM_LABELS
    fractions: Dict[str, float]            # label -> normalized weight (sum 1)
    J_drift: float                         # |drift| magnitude on cutline [A/m^2]
    J_diff: float                          # |diffusion| magnitude [A/m^2]
    I_btbt: float                          # total BTBT current [A]
    fe_charge: float                       # mean |Px| over FE nodes [C/m^2]
    cutline_x: Optional[np.ndarray] = None  # x coords of the cutline [m]

    def feature_vector(self) -> np.ndarray:
        """4-D normalized mechanism-fraction vector (B4 novelty input)."""
        return np.array([self.fractions[l] for l in MECHANISM_LABELS], dtype=float)


def attribute_mechanism(
    simulator,
    result: Dict,
    *,
    j: int = 0,
    k: int = 0,
    A_kane: float = A_KANE,
    B_kane: float = B_KANE_SI,
    D: int = KANE_D,
) -> MechanismReport:
    """Attribute the dominant current mechanism on a 1-D x cutline.

    The four candidate magnitudes (drift, diffusion, BTBT, FE) are normalized
    to a probability vector; the argmax is the dominant label.  Drift and
    diffusion are the mean absolute edge flux on the cutline; BTBT is the total
    generation current; FE is the polarization charge magnitude (scaled by a
    typical FE-field product to be commensurate with a current density).
    """
    mesh = simulator.mesh
    VT = simulator.VT
    x, line = cutline_x_at_jk(mesh, j, k)

    phi = np.asarray(result["phi"], dtype=float)[line]
    n = np.asarray(result["n"], dtype=float)[line]
    p = np.asarray(result["p"], dtype=float)[line]
    mu_n = np.asarray(mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)),
                      dtype=float)[line]
    mu_p = np.asarray(mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)),
                      dtype=float)[line]

    split = drift_diffusion_split_1d(phi, n, p, mesh.dx, mu_n, mu_p, VT)
    J_drift = float(np.mean(np.abs(split["Jn_drift"] + split["Jp_drift"])))
    J_diff = float(np.mean(np.abs(split["Jn_diff"] + split["Jp_diff"])))

    _, I_btbt = btbt_generation(result, mesh, A_kane=A_kane, B_kane=B_kane, D=D)
    P_mag, _ = fe_polarization_charge(result)

    # Scale FE polarization to a current-density-like magnitude: a polarization
    # charge |P| at a typical interface field drives a displacement-current-
    # equivalent ~ |P| * mu_n * E_typical.  We use a representative E_typical
    # of 1e7 V/m (~the BTBT floor order) so FE contributes only when P is
    # non-negligible, and is otherwise ~0.
    E_typical = 1e7
    J_fe = P_mag * 1400e-4 * E_typical  # mu_n(Si) * E_typical * |P|

    mags = np.array([J_drift, J_diff, I_btbt, J_fe], dtype=float)
    total = mags.sum()
    if total <= 0 or not np.isfinite(total):
        fracs = np.zeros(4, dtype=float)
        dominant = "drift"
    else:
        fracs = mags / total
        dominant = MECHANISM_LABELS[int(np.argmax(fracs))]

    fractions = {label: float(fracs[i]) for i, label in enumerate(MECHANISM_LABELS)}
    return MechanismReport(
        dominant=dominant, fractions=fractions,
        J_drift=J_drift, J_diff=J_diff, I_btbt=I_btbt, fe_charge=P_mag,
        cutline_x=x,
    )


def mechanism_feature_vector(report: MechanismReport) -> np.ndarray:
    """4-D mechanism-fraction vector for B4 novelty (plan §64)."""
    return report.feature_vector()
