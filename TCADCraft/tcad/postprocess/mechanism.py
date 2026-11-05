"""D2 mechanism attribution (plan0619.md §D2).

Compares drift / diffusion / BTBT / FE-polarization magnitudes and labels
the *dominant* feature for a candidate; this is not a current partition.
This answers "why is this candidate good" and feeds the B4 novelty metric
(the mechanism-fraction vector is a structural+physics signature, more
informative than the bag-of-kinds histogram alone — plan §64).

Components
----------
1. **Drift / diffusion split** of the Scharfetter-Gummel edge flux.  The
   solver stores only the combined Bernoulli flux (``current.sg_current_density_1d``
   returns Jn, Jp totals); here we re-derive the classical split
   ``Jn_drift = -q*mu_n*n_avg*d(phi)/dx``, ``Jn_diff = q*mu_n*VT*d(n)/dx``
   whose signed sum approaches the conventional SG total on each edge.

2. **BTBT generation** from the solver's explicit ``G_btbt`` source when
   available, with an SI-correct local Kane fallback for legacy results.

3. **FE polarization charge** magnitude along the dominant polar axis, so
   x-, y-, and z-stacked ferroelectric devices share the same truth chain.

The default retains legacy mixed-unit heuristic weights. Explicit
``normalization="current_density"`` compares all four magnitudes in A/m^2
using a supplied cross-section and FE timescale. Neither mode represents
a conserved terminal-current decomposition. The four weights sum to one
when available, or are all zero for a zero signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from .bands import cutline_x_at_jk
from .current import sg_current_density_1d, QE, _edge_lengths, _validated_elementary_charge

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
    dx: float | np.ndarray,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
    VT: float,
    *,
    elementary_charge_C: float = QE,
) -> Dict[str, np.ndarray]:
    """Split the SG electron/hole flux into drift and diffusion parts [A/m^2].

    Classical decomposition (valid away from degenerate limits):
        Jn_drift = -q * mu_n * n_avg * d(phi)/dx
        Jn_diff  =  q * mu_n * VT * d(n)/dx
    with ``n_avg = (n[i]+n[i+1])/2`` and harmonic edge mobility (matching
    ``sg_current_density_1d`` and the C++ solver).  The signed component sum
    agrees with the SG current in the drift-diffusion limit.

    Returns per-edge arrays of length ``len(phi)-1``:
    ``Jn_drift, Jn_diff, Jp_drift, Jp_diff``.
    Standalone calls default to SI charge; bound attribution supplies the
    loaded solver's shared charge explicitly.
    """
    charge = _validated_elementary_charge(elementary_charge_C)
    phi = np.asarray(phi, dtype=float)
    n = np.asarray(n, dtype=float)
    p = np.asarray(p, dtype=float)
    mu_n = np.asarray(mu_n, dtype=float)
    mu_p = np.asarray(mu_p, dtype=float)

    dx = _edge_lengths(dx, len(phi) - 1)
    dphi = (phi[1:] - phi[:-1]) / dx
    dn = (n[1:] - n[:-1]) / dx
    dp = (p[1:] - p[:-1]) / dx
    n_avg = 0.5 * (n[:-1] + n[1:])
    p_avg = 0.5 * (p[:-1] + p[1:])
    mu_n_e = 2.0 * mu_n[:-1] * mu_n[1:] / (mu_n[:-1] + mu_n[1:] + 1e-30)
    mu_p_e = 2.0 * mu_p[:-1] * mu_p[1:] / (mu_p[:-1] + mu_p[1:] + 1e-30)

    Jn_drift = -charge * mu_n_e * n_avg * dphi
    Jn_diff = charge * mu_n_e * VT * dn
    Jp_drift = -charge * mu_p_e * p_avg * dphi
    Jp_diff = -charge * mu_p_e * VT * dp   # hole diffusion opposes dn sign convention
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
    D: float = KANE_D,
    *,
    elementary_charge_C: float = QE,
) -> Tuple[np.ndarray, float]:
    """Per-node BTBT generation rate [m^-3 s^-1] and total BTBT current [A].

    Local Kane model: ``G = A*|E|^D*exp(-B/|E|)`` (A in cm^-3 s^-1 V^-D,
    converted to m^-3; B in V/m).  Fields below ``BTBT_FIELD_FLOOR`` are zeroed
    (no tunneling at negligible field).  ``I_btbt = q * sum(G * dV)``.
    Charge defaults to SI and affects only conversion to amperes, not G or
    the local Kane coefficients, field floor or generation-rate units.
    """
    charge = _validated_elementary_charge(elementary_charge_C)
    if "G_btbt" in result:
        G = np.asarray(result["G_btbt"], dtype=float).ravel()
        if G.size != mesh.npts():
            raise ValueError(
                f"G_btbt size {G.size} does not match mesh npts={mesh.npts()}"
            )
    else:
        Ex = np.asarray(result.get("Ex", np.zeros(mesh.npts())), dtype=float)
        Ey = np.asarray(result.get("Ey", np.zeros(mesh.npts())), dtype=float)
        Ez = np.asarray(result.get("Ez", np.zeros(mesh.npts())), dtype=float)
        E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)
        E_safe = np.maximum(E_mag, BTBT_FIELD_FLOOR)
        # A in cm^-3 -> m^-3 via *1e6
        G = (A_kane * 1e6) * E_safe**D * np.exp(-B_kane / E_safe)
        G[E_mag < BTBT_FIELD_FLOOR] = 0.0
    I_btbt = float(charge * np.dot(G, mesh.control_volumes()))
    return G, I_btbt


# ---------------------------------------------------------------------------
# 3. FE polarization charge magnitude
# ---------------------------------------------------------------------------

def fe_polarization_charge(result: Dict) -> Tuple[float, np.ndarray]:
    """Representative FE polarization magnitude and the FE-node mask.

    Selects the component with the largest mean magnitude. FE nodes are those
    with nonzero polarization on that component. Returns
    ``(P_mag, fe_mask)`` where ``P_mag`` is the mean magnitude over FE nodes
    (0.0 if no FE nodes).
    """
    P = np.asarray(result.get("P", np.zeros((0, 3))), dtype=float)
    if P.size == 0:
        return 0.0, np.zeros(0, dtype=bool)
    axis = int(np.argmax(np.mean(np.abs(P), axis=0)))
    P_axis = P[:, axis]
    fe_mask = np.abs(P_axis) > 1e-30
    if not fe_mask.any():
        return 0.0, fe_mask
    P_mag = float(np.mean(np.abs(P_axis[fe_mask])))
    return P_mag, fe_mask


# ---------------------------------------------------------------------------
# 4. Mechanism report
# ---------------------------------------------------------------------------

#: The four mechanism labels, in feature-vector order.
MECHANISM_LABELS = ("drift", "diffusion", "btbt", "fe_polarization")


@dataclass
class MechanismReport:
    """Legacy heuristic feature report (mixed units, not current fractions)."""
    dominant: str                          # one of MECHANISM_LABELS
    fractions: Dict[str, float]            # label -> normalized weight (sum 1)
    J_drift: float                         # |drift| magnitude on cutline [A/m^2]
    J_diff: float                          # |diffusion| magnitude [A/m^2]
    I_btbt: float                          # total BTBT current [A]
    fe_charge: float                       # mean dominant-axis |P| [C/m^2]
    cutline_x: Optional[np.ndarray] = None  # x coords of the cutline [m]

    def feature_vector(self) -> np.ndarray:
        """Four feature weights in MECHANISM_LABELS order (B4 novelty input)."""
        return np.array([self.fractions[l] for l in MECHANISM_LABELS], dtype=float)

    @property
    def normalization(self) -> str:
        return "legacy_mixed"

    @property
    def component_unit(self) -> str:
        return "mixed"


@dataclass(kw_only=True)
class CurrentDensityMechanismReport(MechanismReport):
    """Comparable A/m^2 feature magnitudes, not conserved current fractions.

    J_btbt is integrated generation current divided by the supplied area;
    J_fe is |P| divided by a characteristic time, not measured dP/dt.
    Carrier flow can already contain BTBT-generated carriers. Feature weights
    therefore overlap and must not be interpreted as terminal-current shares.
    """
    J_btbt: float
    J_fe: float
    cross_section_m2: float
    fe_timescale_s: Optional[float]
    weights_available: bool

    @property
    def normalization(self) -> str:
        return "current_density"

    @property
    def component_unit(self) -> str:
        return "A/m^2"


def _positive_scale(value, name: str) -> float:
    """Require an explicit finite positive real scalar, without coercing strings."""
    a = np.asarray(value)
    if a.ndim != 0 or a.dtype.kind not in "iuf":
        raise ValueError(f"{name} must be a finite positive real scalar")
    scale = float(a)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f"{name} must be a finite positive real scalar")
    return scale


def attribute_mechanism(
    simulator,
    result: Dict,
    *,
    j: int = 0,
    k: int = 0,
    A_kane: float = A_KANE,
    B_kane: float = B_KANE_SI,
    D: float = KANE_D,
    normalization: str = "legacy_mixed",
    cross_section_m2: Optional[float] = None,
    fe_timescale_s: Optional[float] = None,
) -> MechanismReport:
    """Attribute the dominant current mechanism on a 1-D x cutline.

    Default ``legacy_mixed`` preserves the existing heuristic feature vector.
    Drift/diffusion use A/m^2, BTBT uses A, and FE uses a legacy scale factor.
    ``current_density`` requires an explicit positive ``cross_section_m2``:
    BTBT becomes I_btbt/area [A/m^2]. Nonzero FE additionally requires a positive
    ``fe_timescale_s``: FE becomes |P|/time [A/m^2]. The area must correspond to
    the integrated generation volume and representative carrier cutline; it
    is never inferred from padded mesh dimensions. For zero FE the time may
    be omitted. All supplied scales are validated, including for zero signal.

    Neither mode is a conserved terminal-current decomposition. Carrier and BTBT conversion
    use the simulator's shared charge, or SI for facades without metadata.
    """
    if not isinstance(normalization, str) or normalization not in ("legacy_mixed", "current_density"):
        raise ValueError("normalization must be 'legacy_mixed' or 'current_density'")
    if normalization == "legacy_mixed":
        if cross_section_m2 is not None or fe_timescale_s is not None:
            raise ValueError("scales require normalization='current_density'")
    else:
        cross_section_m2 = _positive_scale(cross_section_m2, "cross_section_m2")
        if fe_timescale_s is not None:
            fe_timescale_s = _positive_scale(fe_timescale_s, "fe_timescale_s")
        if not np.all(np.isfinite(np.asarray(result.get("P", []), dtype=float))):
            raise ValueError("current_density requires finite polarization")
    mesh = simulator.mesh
    VT = simulator.VT
    charge = getattr(simulator, 'elementary_charge_C', QE)
    x, line = cutline_x_at_jk(mesh, j, k)

    phi = np.asarray(result["phi"], dtype=float)[line]
    n = np.asarray(result["n"], dtype=float)[line]
    p = np.asarray(result["p"], dtype=float)[line]
    mu_n = np.asarray(mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)),
                      dtype=float)[line]
    mu_p = np.asarray(mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)),
                      dtype=float)[line]

    split = drift_diffusion_split_1d(
        phi, n, p, np.diff(mesh.axis_coordinates()[0]), mu_n, mu_p, VT,
        elementary_charge_C=charge)
    J_drift = float(np.mean(np.abs(split["Jn_drift"] + split["Jp_drift"])))
    J_diff = float(np.mean(np.abs(split["Jn_diff"] + split["Jp_diff"])))

    G, I_btbt = btbt_generation(result, mesh, A_kane=A_kane, B_kane=B_kane, D=D,
                                elementary_charge_C=charge)
    P_mag, _ = fe_polarization_charge(result)

    if normalization == "current_density":
        if np.any(~np.isfinite(G)) or np.any(G < 0):
            raise ValueError("current_density requires finite nonnegative BTBT generation")
        if P_mag > 0 and fe_timescale_s is None:
            raise ValueError("fe_timescale_s is required for nonzero FE polarization")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            J_btbt = float(np.divide(I_btbt, cross_section_m2))
            J_fe = float(np.divide(P_mag, fe_timescale_s)) if fe_timescale_s is not None else 0.
        mags = np.array([J_drift, J_diff, J_btbt, J_fe], dtype=float)
        if np.any(~np.isfinite(mags)) or np.any(mags < 0):
            raise ValueError("current_density requires finite nonnegative component magnitudes")
        largest = float(mags.max())
        available = largest > 0
        scaled = mags / largest if available else np.zeros(4, dtype=float)
        fracs = scaled / scaled.sum() if available else scaled
        return CurrentDensityMechanismReport(
            dominant=MECHANISM_LABELS[int(np.argmax(fracs))],
            fractions={label: float(fracs[i]) for i, label in enumerate(MECHANISM_LABELS)},
            J_drift=J_drift, J_diff=J_diff, I_btbt=I_btbt, fe_charge=P_mag,
            cutline_x=x, J_btbt=J_btbt, J_fe=J_fe,
            cross_section_m2=cross_section_m2, fe_timescale_s=fe_timescale_s,
            weights_available=available,
        )

    # Historical mixed-unit heuristic retained for existing search features.
    E_typical = 1e7
    J_fe = P_mag * 1400e-4 * E_typical

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
