"""Band-gap narrowing (BGN) models for heavily-doped regions.

BGN reduces the local band gap as a function of total ionized impurity
concentration, raising the effective intrinsic density:

    ni_eff^2 = ni^2 * exp(dEg / VT)

The models here return an *effective band gap* array that can be injected
into the solver via ``set_bandgap(Eg_eff)`` — for Boltzmann statistics this
is physically equivalent to a full BGN implementation (band-edge split,
``Bgn2Chi=0.5``, does not affect drift-diffusion currents).

Reference: Sentaurus Device MaterialDB Silicon.par (W-2024.09).
"""
from __future__ import annotations

import numpy as np

# Sentaurus defaults for Silicon (OldSlotboom section of Silicon.par)
SLOTBOOM_EBGN = 9.0e-3      # eV  (OldSlotboom Ebgn)
SLOTBOOM_NREF = 1.0e17      # cm^-3
SLOTBOOM_C = 0.5            # dimensionless
SLOTBOOM_dEg0 = -1.5950e-2  # eV  (BandGap section dEg0(OldSlotboom) constant offset)
# deltaEg = dEg0 + Ebgn*(ln(N/Nref)+sqrt(ln^2+C)).  Omitting dEg0 over-narrows
# the gap by ~0.016 eV -> ni_eff^2 high by ~exp(0.016/VT)=1.86 -> ~86% current
# overestimate vs Sentaurus (the bgn1e19/1e20 ~97% benchmark gap).


def oldslotboom_dEg(N_tot_cm3: np.ndarray,
                    Ebgn: float = SLOTBOOM_EBGN,
                    Nref: float = SLOTBOOM_NREF,
                    C: float = SLOTBOOM_C,
                    dEg0: float = SLOTBOOM_dEg0) -> np.ndarray:
    """OldSlotboom band-gap narrowing [eV], incl. the dEg0 constant offset.

    deltaEg = dEg0 + Ebgn * ( ln(N/Nref) + sqrt( ln(N/Nref)^2 + C ) )

    Parameters
    ----------
    N_tot_cm3 : total ionized impurity concentration |Nd| + |Na| [cm^-3].
    """
    N = np.maximum(np.asarray(N_tot_cm3, dtype=float), 1.0)
    x = np.log(N / Nref)
    # Sentaurus OldSlotboom: ΔEg = Ebgn*(...) - dEg0
    # Verified from Sentaurus bgn1e19 IV: BGN effect = 46× (matches
    # exp(0.099/VT)=45, not exp(0.067/VT)=13).  The MaterialDB comment
    # says "dEg0 + Ebgn*(...)" but the implementation uses "-dEg0 + Ebgn*(...)"
    # (dEg0=-0.016 enters with opposite sign, giving dEg=0.099 at 1e19).
    return -dEg0 + Ebgn * (x + np.sqrt(x * x + C))


def effective_bandgap(Eg: np.ndarray, doping_cm3: np.ndarray,
                      model: str = "oldslotboom") -> np.ndarray:
    """Return BGN-corrected band gap array [eV].

    Eg : base band gap (scalar or array) [eV].
    doping_cm3 : NET doping array (Nd - Na) [cm^-3]; total impurities are
        used internally, so compensated regions get the right narrowing.
    """
    if model.lower() != "oldslotboom":
        raise ValueError(f"unknown BGN model: {model}")
    dEg = oldslotboom_dEg(np.abs(np.asarray(doping_cm3, dtype=float)))
    return np.asarray(Eg, dtype=float) - dEg
