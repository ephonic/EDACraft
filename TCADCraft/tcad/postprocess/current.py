"""Real terminal-current extraction via Scharfetter-Gummel flux integration.

This replaces the carrier-density proxy (``n.max()``) used in
``metrics.extract_transfer_characteristics`` with an actual contact current,
which is a prerequisite for credible Ion/Ioff/SS ranking in device discovery
(audit_recheck.md §3.1 #1; plan0619.md M1/B1).

The Scharfetter-Gummel edge flux here mirrors the C++ solver exactly
(``gummel_solver.cpp`` / ``newton_solver.cpp`` ``add_link``):

    Jn_edge(i->j) = q * (mu_n*VT/dx) * (n_i * B(-dphi/VT) - n_j * B(+dphi/VT))
    Jp_edge(i->j) = q * (mu_p*VT/dx) * (p_i * B(+dphi/VT) - p_j * B(-dphi/VT))

with dphi = phi_j - phi_i, B(x) = x/(exp(x)-1), and node-upwind mobility
mu[i] (matching ``mu_n_[idx]`` in the C++ stencil). At steady state the total
current J = Jn + Jp is divergence-free (KCL, verified by
``TestCurrentConservation``), so the terminal current equals the flux through
any edge crossing the contact boundary.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple

import numpy as np

QE = 1.602176634e-19  # elementary charge [C]


def _bernoulli(x: np.ndarray) -> np.ndarray:
    """Vectorized Bernoulli function B(x) = x / (exp(x) - 1).

    Uses the Newton-solver small-x branch (1 - x/2) to match
    ``newton_solver.cpp:111``; for |x| > 100 the asymptotes B->0 (x->+inf) and
    B->-x (x->-inf) are used. Under real contact bias |dphi/VT| >> 1e-12 so the
    small-x branch is moot in practice.
    """
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    small = np.abs(x) < 1e-12
    out[small] = 1.0 - x[small] / 2.0
    big_pos = x > 100.0
    out[big_pos] = 0.0
    big_neg = x < -100.0
    out[big_neg] = -x[big_neg]
    rest = ~(small | big_pos | big_neg)
    out[rest] = x[rest] / np.expm1(x[rest])
    return out


def sg_current_density_1d(
    phi: np.ndarray,
    n: np.ndarray,
    p: np.ndarray,
    dx: float,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
    VT: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Edge-centered Scharfetter-Gummel electron and hole current densities [A/m^2].

    Returns arrays of length ``len(phi)-1`` (one per edge). Sign convention:
    positive current flows in the +x direction (node i -> i+1).

    Parameters mirror the C++ solver; ``mu_n``/``mu_p`` are per-node and the
    node-upwind value ``mu[i]`` is used on edge (i, i+1) (matching ``mu_n_[idx]``).
    """
    phi = np.asarray(phi, dtype=float)
    n = np.asarray(n, dtype=float)
    p = np.asarray(p, dtype=float)
    mu_n = np.asarray(mu_n, dtype=float)
    mu_p = np.asarray(mu_p, dtype=float)

    dphi = phi[1:] - phi[:-1]
    Bp = _bernoulli(dphi / VT)
    Bm = _bernoulli(-dphi / VT)
    Dn = mu_n[:-1] * VT / dx   # node-upwind mobility
    Dp = mu_p[:-1] * VT / dx
    Jn = QE * Dn * (n[:-1] * Bm - n[1:] * Bp)
    Jp = QE * Dp * (p[:-1] * Bp - p[1:] * Bm)
    return Jn, Jp


def contact_current_1d(
    simulator,
    result: Dict,
    contact_name: str,
    direction: str = "auto",
) -> float:
    """Terminal current [A] into a named contact of a quasi-1-D device.

    Integrates the total SG current density (Jn + Jp) on the interior edge
    adjacent to the contact, times a unit cross-section (1 m^2). For a true 1-D
    sheet the result is current density [A/m^2]; multiply by the device width
    for absolute current. Sign: positive = current flowing *into* the contact
    from the interior (i.e. conventional current entering the terminal).

    The simulator mesh may be 1-D, 2-D or 3-D; this routine extracts the
    x-axis line (fixed j,k) that passes through the requested contact and
    applies the 1-D SG stencil along it. For a quasi-1-D device (uniform in y,
    z) every line is equivalent, so the choice of (j,k) does not affect the
    result. The representative (j,k) is taken from the first node of the
    contact mask.

    Parameters
    ----------
    simulator : Simulator
        Holds the mesh (for contact mask, mobility fields, grid spacing) and VT.
    result : dict
        A single solve() result dict (phi/n/p/...).
    contact_name : str
        Contact whose terminal current is requested.
    direction : str
        ``"auto"`` (detect from contact position: left contact -> edge 0,
        right contact -> edge N-2), ``"left"``, or ``"right"``.
    """
    mesh = simulator.mesh
    field = f"contact_{contact_name}"
    if field not in mesh.fields:
        raise KeyError(f"Contact '{contact_name}' not in mesh fields: {list(mesh.fields.keys())}")
    contact_mask = mesh.fields[field].astype(bool).ravel()
    nodes = np.nonzero(contact_mask)[0]
    if len(nodes) == 0:
        raise ValueError(f"Contact '{contact_name}' has no nodes")

    nx = mesh.nx
    # Representative (j, k) from the first contact node (1-D extraction line).
    n0 = int(nodes[0])
    i0 = n0 % nx
    j0 = (n0 // nx) % mesh.ny
    k0 = n0 // (nx * mesh.ny)
    from .bands import cutline_x_at_jk
    _, line = cutline_x_at_jk(mesh, j0, k0)

    # Find the contact's extent along the extraction line.  A contact may span
    # several nodes (a finite-thickness electrode); the terminal current is the
    # flux through the cross-section at the *inner* boundary of the contact —
    # the edge connecting the last contact node to the first free node (left
    # contact) or the first contact node to its lower-index free neighbour
    # (right contact).  Using an edge with both endpoints pinned by the Dirichlet
    # BC would give zero flux (n[i]==n[i+1] for two BC nodes).
    line_mask = contact_mask[line]
    line_contact_i = np.nonzero(line_mask)[0]  # i-indices on this line in contact
    if direction == "auto":
        # A contact touching i=0 is a left-boundary contact; one touching
        # i=nx-1 is a right-boundary contact.  Use the contact's full extent
        # (not just the first node) so finite-thickness electrodes are detected.
        if line_contact_i[-1] == nx - 1:
            direction = "right"
        else:
            direction = "left"

    # Prefer solver-output edge fluxes (Audit §20): computed in __float128
    # from the converged state, avoiding the catastrophic cancellation of
    # double-precision re-derivation when carrier densities are large.
    # result["Jn_x"][idx] is the +x edge leaving node idx (idx -> idx+1);
    # the last node on the line has no +x neighbor so its entry is 0.
    if "Jn_x" in result and "Jp_x" in result and len(result["Jn_x"]) == mesh.npts():
        Jn_edge = np.asarray(result["Jn_x"], dtype=float)[line]   # Jn on edge i
        Jp_edge = np.asarray(result["Jp_x"], dtype=float)[line]
        J = (Jn_edge + Jp_edge)[:nx - 1]  # length nx-1, J[i] = edge (i, i+1)
    else:
        phi = np.asarray(result["phi"], dtype=float)[line]
        n = np.asarray(result["n"], dtype=float)[line]
        p = np.asarray(result["p"], dtype=float)[line]
        mu_n = np.asarray(
            mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)), dtype=float
        )[line]
        mu_p = np.asarray(
            mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)), dtype=float
        )[line]
        VT = simulator.VT
        Jn, Jp = sg_current_density_1d(phi, n, p, mesh.dx, mu_n, mu_p, VT)
        J = Jn + Jp  # total current density per edge [A/m^2]

    if direction == "left":
        # Left contact occupies i=0..i_last; the boundary edge is
        # (i_last, i_last+1).  J[i_last] is +x (into interior).  Current *into*
        # the left terminal = -J[i_last] (conventional current leaving the
        # interior toward the left contact).
        i_last = int(line_contact_i[-1])
        return -float(J[i_last])
    else:  # right
        # Right contact occupies i_first..nx-1; boundary edge is
        # (i_first-1, i_first).  J[i_first-1] is +x (into the right contact).
        i_first = int(line_contact_i[0])
        return float(J[i_first - 1])


# ---------------------------------------------------------------------------
# 2-D terminal-current extraction (M6c)
# ---------------------------------------------------------------------------

def sg_current_density_1d_z(
    phi: np.ndarray,
    n: np.ndarray,
    p: np.ndarray,
    dz: float,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
    VT: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Edge SG current densities along the z-axis [A/m^2].

    Identical to :func:`sg_current_density_1d` but along z (node k -> k+1).
    Returns arrays of length ``len(phi)-1``.  Positive = +z direction.
    """
    phi = np.asarray(phi, dtype=float)
    n = np.asarray(n, dtype=float)
    p = np.asarray(p, dtype=float)
    mu_n = np.asarray(mu_n, dtype=float)
    mu_p = np.asarray(mu_p, dtype=float)
    dphi = phi[1:] - phi[:-1]
    Bp = _bernoulli(dphi / VT)
    Bm = _bernoulli(-dphi / VT)
    Dn = mu_n[:-1] * VT / dz
    Dp = mu_p[:-1] * VT / dz
    Jn = QE * Dn * (n[:-1] * Bm - n[1:] * Bp)
    Jp = QE * Dp * (p[:-1] * Bp - p[1:] * Bm)
    return Jn, Jp


def contact_current_2d(
    simulator,
    result: Dict,
    contact_name: str,
    width: Optional[float] = None,
) -> float:
    """Terminal current [A] into a named contact of a 2-D cross-section device.

    The device is meshed as a 2-D x-z cross-section (``ny=1``, single y-layer).
    Unlike :func:`contact_current_1d` (which takes a single cutline and returns a
    per-edge density), this integrates the total SG current over the *full*
    contact face:

    - **x-normal contact** (source/drain on the left or right boundary): sum the
      x-directed SG flux over every z-row that touches the contact, multiply by
      ``dz * W``.
    - **z-normal contact** (gate on top, body on bottom): sum the z-directed SG
      flux over every x-column that touches the contact, multiply by ``dx * W``.

    Solver-output edge fluxes (``result["Jn_x"]`` etc., computed in
    ``__float128``) are preferred over the double-precision Python re-derivation
    to avoid the catastrophic cancellation documented in Audit §20.  The flux is
    taken at the *inner* boundary of the contact (the edge connecting the last
    contact node to the first free node), not at an edge between two Dirichlet
    BC nodes (which would be zero).

    ``W`` defaults to the device width ``mesh.dy * mesh.ny`` (the y-extent).
    Sign convention: positive = conventional current flowing *into* the contact
    from the interior.

    Parameters
    ----------
    simulator : Simulator
        Holds the mesh (contact mask, mobility fields, grid spacing) and VT.
    result : dict
        A single solve() result dict (phi/n/p/...).
    contact_name : str
        Contact whose terminal current is requested.
    width : float, optional
        Device width [m] for the out-of-plane integration.  Defaults to
        ``mesh.dy * mesh.ny``.
    """
    mesh = simulator.mesh
    nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
    field = f"contact_{contact_name}"
    if field not in mesh.fields:
        raise KeyError(f"Contact '{contact_name}' not in mesh fields")
    contact_mask = mesh.fields[field].astype(bool).ravel()
    nodes = np.nonzero(contact_mask)[0]
    if len(nodes) == 0:
        raise ValueError(f"Contact '{contact_name}' has no nodes")

    if width is None:
        width = mesh.dy * mesh.ny

    # Decode contact node positions.
    i_arr = nodes % nx
    j_arr = (nodes // nx) % ny
    k_arr = nodes // (nx * ny)

    VT = simulator.VT
    has_solver_flux = (
        "Jn_x" in result and "Jp_x" in result
        and "Jn_z" in result and "Jp_z" in result
        and len(result["Jn_x"]) == mesh.npts()
    )

    # Determine contact orientation: x-normal (left/right) or z-normal (top/bot).
    # Use the contact's full extent: a left contact touches i=0, a right contact
    # touches i=nx-1, a bottom contact touches k=0, a top contact touches k=nz-1.
    is_left = (i_arr.min() == 0) and (i_arr.max() < nx - 1 or i_arr.min() == 0)
    # More robust: classify by which boundary face the contact touches.
    touches_left = bool(np.any(i_arr == 0))
    touches_right = bool(np.any(i_arr == nx - 1))
    touches_bot = bool(np.any(k_arr == 0))
    touches_top = bool(np.any(k_arr == nz - 1))
    # x-normal contacts touch left or right but not top/bottom (unless the
    # contact is a single corner node — prefer x for left/right, z for top/bot).
    is_x_normal = touches_left or touches_right
    is_z_normal = (touches_top or touches_bot) and not is_x_normal

    j0 = int(j_arr[0])  # 2-D device: single y-layer

    if is_x_normal:
        is_left = touches_left and not touches_right
        is_right = touches_right and not touches_left
        # If contact touches both left and right (spans full width), treat as
        # left (pick the left boundary edge).
        if not is_left and not is_right:
            is_left = True

        k_unique = sorted(set(int(k) for k in k_arr))
        total = 0.0
        for k_row in k_unique:
            # x-line at (j0, k_row): indices i + nx*(j0 + ny*k_row)
            line = np.array([i + nx * (j0 + ny * k_row) for i in range(nx)],
                            dtype=np.int64)
            line_mask = contact_mask[line]
            line_contact_i = np.nonzero(line_mask)[0]

            if has_solver_flux:
                Jn_edge = np.asarray(result["Jn_x"], dtype=float)[line]
                Jp_edge = np.asarray(result["Jp_x"], dtype=float)[line]
                J = (Jn_edge + Jp_edge)[:nx - 1]
            else:
                phi_l = np.asarray(result["phi"], dtype=float)[line]
                n_l = np.asarray(result["n"], dtype=float)[line]
                p_l = np.asarray(result["p"], dtype=float)[line]
                mu_n_l = np.asarray(
                    mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)),
                    dtype=float,
                )[line]
                mu_p_l = np.asarray(
                    mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)),
                    dtype=float,
                )[line]
                Jn, Jp = sg_current_density_1d(phi_l, n_l, p_l, mesh.dx,
                                               mu_n_l, mu_p_l, VT)
                J = Jn + Jp  # [A/m^2] per x-edge

            if is_left:
                # Inner boundary edge = (i_last, i_last+1); +x into interior.
                # Into left terminal = -J[i_last].
                i_last = int(line_contact_i[-1])
                total += -J[i_last]
            else:  # right
                # Inner boundary edge = (i_first-1, i_first); +x into contact.
                i_first = int(line_contact_i[0])
                total += J[i_first - 1]
        # Integrate over z-extent: each z-row contributes over dz, times width W.
        return float(total * mesh.dz * width)

    else:  # z-normal (top or bottom)
        is_bot = touches_bot and not touches_top
        is_top = touches_top and not touches_bot
        if not is_bot and not is_top:
            is_bot = True

        i_unique = sorted(set(int(i) for i in i_arr))
        total = 0.0
        for i_col in i_unique:
            # z-line at (i_col, j0): indices i_col + nx*(j0 + ny*k) for k in range(nz)
            line = np.array([i_col + nx * (j0 + ny * k) for k in range(nz)],
                            dtype=np.int64)
            line_mask = contact_mask[line]
            line_contact_k = np.nonzero(line_mask)[0]

            if has_solver_flux:
                Jn_edge = np.asarray(result["Jn_z"], dtype=float)[line]
                Jp_edge = np.asarray(result["Jp_z"], dtype=float)[line]
                J = (Jn_edge + Jp_edge)[:nz - 1]
            else:
                phi_l = np.asarray(result["phi"], dtype=float)[line]
                n_l = np.asarray(result["n"], dtype=float)[line]
                p_l = np.asarray(result["p"], dtype=float)[line]
                mu_n_l = np.asarray(
                    mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)),
                    dtype=float,
                )[line]
                mu_p_l = np.asarray(
                    mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)),
                    dtype=float,
                )[line]
                Jn, Jp = sg_current_density_1d_z(phi_l, n_l, p_l, mesh.dz,
                                                  mu_n_l, mu_p_l, VT)
                J = Jn + Jp  # [A/m^2] per z-edge

            if is_bot:
                # Inner boundary edge = (k_last, k_last+1); +z into interior.
                # Into bottom terminal = -J[k_last].
                k_last = int(line_contact_k[-1])
                total += -J[k_last]
            else:  # top
                # Inner boundary edge = (k_first-1, k_first); +z into contact.
                k_first = int(line_contact_k[0])
                total += J[k_first - 1]
        return float(total * mesh.dx * width)
