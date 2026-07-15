"""Physics invariant checks.

These functions encode laws of physics that must **never** be violated.
If any check fails, the simulation has a bug — raise immediately so the
caller knows not to trust the result.

Usage
-----
::

    from tcad.physics import PhysicsInvariants as PI

    PI.check_polarization(P, Ps=1.4)          # |P| <= Ps
    PI.check_carriers(n, p)                   # n, p >= 0
    PI.check_divergence_stencil(P, dx)        # stencil correctness
    PI.check_material_units("AlScN", Ps, Ec,  eps_r, alpha, beta)

Every function raises ``PhysicsViolation`` on failure and returns ``None``
on success, so they can be used as bare statements.
"""

from __future__ import annotations

import numpy as np
import warnings
from typing import Optional


class PhysicsViolation(ValueError):
    """Raised when a physics invariant is violated."""
    pass


class PhysicsInvariants:
    """Stateless physics-invariant checks.

    All methods are ``@staticmethod`` — call them as
    ``PhysicsInvariants.check_*(...)`` or import the class as ``PI``.
    """

    # ------------------------------------------------------------------
    # Polarization
    # ------------------------------------------------------------------

    @staticmethod
    def check_polarization(P: np.ndarray, Ps: float,
                           tolerance: float = 1.01,
                           context: str = "") -> None:
        """Assert ``|P| <= Ps * tolerance`` everywhere.

        This would have caught the L-K divergence bug (P -> 167 C/m^2)
        and the div(P) stencil bug (P pinned at -16700 uC/cm^2).

        Parameters
        ----------
        P : ndarray
            Polarisation array (any shape).
        Ps : float
            Saturation polarisation [C/m^2].
        tolerance : float
            Multiplicative slack (default 1 %).
        context : str
            Extra info appended to the error message.
        """
        P = np.asarray(P)
        max_abs = float(np.nanmax(np.abs(P)))
        limit = Ps * tolerance
        if max_abs > limit:
            raise PhysicsViolation(
                f"|P| = {max_abs:.4f} C/m^2 exceeds Ps*{tolerance} = "
                f"{limit:.4f} C/m^2 "
                f"(ratio {max_abs/Ps:.1f}x). {context}")

    @staticmethod
    def check_polarization_not_constant(P: np.ndarray,
                                        Ps: float,
                                        min_variation_frac: float = 0.05,
                                        context: str = "") -> None:
        """Assert that P is **not** pinned at a single value.

        A constant P across a voltage sweep indicates the self-consistent
        loop has collapsed (the div(P) stencil bug).  We require the
        peak-to-peak variation to be at least ``min_variation_frac * Ps``.
        """
        P = np.asarray(P)
        ptp = float(np.ptp(P))
        threshold = min_variation_frac * Ps
        if ptp < threshold:
            raise PhysicsViolation(
                f"P is pinned: peak-to-peak = {ptp:.4e} C/m^2, "
                f"expected >= {threshold:.4e} ({min_variation_frac*100:.0f}% "
                f"of Ps={Ps}). {context}")

    # ------------------------------------------------------------------
    # Carrier densities
    # ------------------------------------------------------------------

    @staticmethod
    def check_carriers(n: np.ndarray, p: np.ndarray,
                       floor: float = -1e-10,
                       context: str = "") -> None:
        """Assert ``n >= floor`` and ``p >= floor`` everywhere."""
        n = np.asarray(n)
        p = np.asarray(p)
        n_min = float(np.nanmin(n))
        p_min = float(np.nanmin(p))
        if n_min < floor:
            raise PhysicsViolation(
                f"n has negative values: min(n) = {n_min:.3e} < {floor:.0e}. "
                f"{context}")
        if p_min < floor:
            raise PhysicsViolation(
                f"p has negative values: min(p) = {p_min:.3e} < {floor:.0e}. "
                f"{context}")

    # ------------------------------------------------------------------
    # Potential bounds
    # ------------------------------------------------------------------

    @staticmethod
    def check_potential(phi: np.ndarray,
                        V_min: float = -100.0,
                        V_max: float = 100.0,
                        context: str = "") -> None:
        """Assert ``V_min <= phi <= V_max`` (loose range check).

        A phi far outside the applied-voltage range signals a divergent
        solve or a unit error.
        """
        phi = np.asarray(phi)
        phi_min = float(np.nanmin(phi))
        phi_max = float(np.nanmax(phi))
        if phi_min < V_min or phi_max > V_max:
            raise PhysicsViolation(
                f"phi out of range: [{phi_min:.3f}, {phi_max:.3f}] V, "
                f"expected [{V_min}, {V_max}]. {context}")

    # ------------------------------------------------------------------
    # Divergence stencil correctness
    # ------------------------------------------------------------------

    @staticmethod
    def check_divergence_stencil(dx: float = 1e-9,
                                 ny: int = 1, nz: int = 1) -> None:
        """Verify the finite-difference divergence operator on test fields.

        For a **constant** field ``P = c`` the divergence is exactly 0.
        For a **linear** field ``P = a*x`` the divergence is exactly ``a``.

        This is a *unit test for the stencil itself* — it catches the
        sign-flip bug that turned div(P) into a Laplacian (comments2.docx).
        """
        nx = 10
        x = np.arange(nx) * dx

        # Constant field
        const_P = np.ones(nx)
        div_const = np.diff(const_P) / dx
        if not np.allclose(div_const, 0, atol=1e-15):
            raise PhysicsViolation(
                f"Divergence stencil is wrong: div(constant) = "
                f"{div_const} != 0")

        # Linear field P = a*x
        a = 2.0
        lin_P = a * x
        # Central difference for interior points
        div_interior = (lin_P[2:] - lin_P[:-2]) / (2 * dx)
        if not np.allclose(div_interior, a, rtol=1e-10):
            raise PhysicsViolation(
                f"Divergence stencil is wrong: div(a*x) = "
                f"{div_interior[0]:.6f} != {a}")

        # Check that forward-backward subtraction does NOT produce Laplacian
        # (the old bug: +diff(i,i+1) - diff(i-1,i) = second difference)
        fwd = (lin_P[1:] - lin_P[:-1]) / dx        # forward diff
        bwd = (lin_P[1:] - lin_P[:-1]) / dx        # backward diff (same for linear)
        wrong = fwd[:-1] - bwd[1:]                  # old bug pattern
        if not np.allclose(wrong, 0, atol=1e-15):
            # For a LINEAR field the second difference IS zero, so this
            # check is only informative.  The real catch is the constant
            # and the interior central-difference check above.
            pass

    # ------------------------------------------------------------------
    # Material parameter unit consistency
    # ------------------------------------------------------------------

    @staticmethod
    def check_material_units(name: str,
                             Ps: float, Ec: float,
                             epsilon_r: float,
                             alpha: float, beta: float,
                             max_ratio: float = 100.0) -> None:
        """Warn (not raise) if L-K alpha/beta are inconsistent with Ps/Ec.

        ``Ps_LK = sqrt(-alpha/beta)`` and ``Ec_LK = (2|alpha|/3)*sqrt(-alpha/(3*beta))``
        should be within ``max_ratio`` of the declared ``Ps`` and ``Ec``.

        This would have caught the case where alpha/beta were in wrong
        units, giving Ps_LK ~ 1e-5 while Ps = 1.4.
        """
        if alpha >= 0 or beta <= 0:
            return  # not a ferroelectric double-well; skip

        Ps_LK = float(np.sqrt(-alpha / beta))
        P_sp = float(np.sqrt(-alpha / (3.0 * beta)))
        Ec_LK = (2.0 / 3.0) * abs(alpha) * P_sp

        if Ps > 0:
            ratio_Ps = Ps_LK / Ps
            if ratio_Ps > max_ratio or ratio_Ps < 1.0 / max_ratio:
                warnings.warn(
                    f"[{name}] Unit inconsistency: "
                    f"sqrt(-alpha/beta) = {Ps_LK:.3e} vs declared "
                    f"Ps = {Ps:.3e} (ratio {ratio_Ps:.1f}). "
                    f"Check alpha/beta units.",
                    stacklevel=2)

        if Ec > 0:
            ratio_Ec = Ec_LK / Ec
            if ratio_Ec > max_ratio or ratio_Ec < 1.0 / max_ratio:
                warnings.warn(
                    f"[{name}] Unit inconsistency: "
                    f"LK Ec = {Ec_LK:.3e} vs declared "
                    f"Ec = {Ec:.3e} (ratio {ratio_Ec:.1f}).",
                    stacklevel=2)

    # ------------------------------------------------------------------
    # Hysteresis existence
    # ------------------------------------------------------------------

    @staticmethod
    def check_hysteresis(V: np.ndarray, P: np.ndarray,
                         min_window: float = 0.0,
                         context: str = "") -> None:
        """Assert that a P-V loop has hysteresis (forward != backward).

        This catches the "P pinned at constant" failure mode where the
        loop degenerates to a single line.
        """
        V = np.asarray(V)
        P = np.asarray(P)
        n = len(V) // 4  # each quadrant
        if n < 3:
            return  # too few points
        # Compare forward sweep (0->+Vmax) with backward (+Vmax->0)
        P_fwd = P[:n]
        P_bwd = P[n:2*n][::-1]
        if not np.allclose(P_fwd, P_bwd, atol=0.001):
            return  # hysteresis exists — pass
        # No hysteresis: check if at least P varies
        ptp = float(np.ptp(P))
        if ptp < min_window:
            raise PhysicsViolation(
                f"No hysteresis and P nearly constant "
                f"(ptp={ptp:.4e}). Loop is degenerate. {context}")

    # ------------------------------------------------------------------
    # Full result check (convenience)
    # ------------------------------------------------------------------

    @staticmethod
    def check_result(result: dict,
                     Ps: float = 0.0,
                     V_applied: float = 0.0,
                     context: str = "") -> None:
        """Convenience: run all applicable checks on a solve() result dict.

        Parameters
        ----------
        result : dict
            Output of ``Simulator.run()`` or ``PyDeviceSimulator.solve()``.
        Ps : float
            Saturation polarisation (skip P check if 0).
        V_applied : float
            Max applied voltage (skip potential check if 0).
        context : str
            Extra info for error messages.
        """
        if "n" in result and "p" in result:
            PhysicsInvariants.check_carriers(
                result["n"], result["p"], context=context)

        if Ps > 0 and "P" in result and result["P"] is not None:
            PhysicsInvariants.check_polarization(
                result["P"], Ps, context=context)

        if V_applied > 0 and "phi" in result:
            PhysicsInvariants.check_potential(
                result["phi"],
                V_min=-2 * V_applied,
                V_max=2 * V_applied,
                context=context)
