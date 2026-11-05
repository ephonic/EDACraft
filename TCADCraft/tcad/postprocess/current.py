"""Real terminal-current extraction via Scharfetter-Gummel flux integration.

This replaces the carrier-density proxy (``n.max()``) used in
``metrics.extract_transfer_characteristics`` with an actual contact current,
which is a prerequisite for credible Ion/Ioff/SS ranking in device discovery
(audit_recheck.md §3.1 #1; plan0619.md M1/B1).

The Scharfetter-Gummel edge flux here mirrors the C++ solver exactly
(``gummel_solver.cpp`` / ``newton_solver.cpp`` ``add_link``):

    Jn_edge(i->j) = q * (mu_n*VT/dx) * (n_j * B(+dphi/VT) - n_i * B(-dphi/VT))
    Jp_edge(i->j) = q * (mu_p*VT/dx) * (p_i * B(+dphi/VT) - p_j * B(-dphi/VT))

    (conventional-current sign for both, so Jn + Jp is the physical total)

with dphi = phi_j - phi_i, B(x) = x/(exp(x)-1), and harmonic edge mobility.
At steady state the total
current J = Jn + Jp is divergence-free (KCL, verified by
``TestCurrentConservation``), so the terminal current equals the flux through
any edge crossing the contact boundary.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple

import numpy as np
from math import fsum

QE = 1.602176634e-19  # SI default for standalone transport helpers [C]


def _validated_elementary_charge(value) -> float:
    """Normalize the shared finite, positive real charge contract [C]."""
    charge = np.asarray(value)
    if charge.ndim != 0 or charge.dtype.kind not in 'iuf':
        raise ValueError("elementary_charge_C must be a finite positive real scalar")
    charge = float(charge)
    if not np.isfinite(charge) or charge <= 0:
        raise ValueError("elementary_charge_C must be a finite positive real scalar")
    return charge


def _edge_lengths(spacing, count: int) -> np.ndarray:
    """Validate a positive scalar spacing or one length per edge [m]."""
    lengths = np.asarray(spacing, dtype=float)
    if lengths.ndim == 0:
        if not np.isfinite(lengths) or lengths <= 0:
            raise ValueError("edge spacing must be finite and positive")
        return np.full(count, float(lengths))
    if (lengths.shape != (count,) or not np.all(np.isfinite(lengths))
            or np.any(lengths <= 0)):
        raise ValueError("edge lengths must be finite, positive and have len(phi)-1 entries")
    return lengths


def _line_total_current(simulator, result, line, axis, lengths):
    """Prefer native quad fluxes; reconstruct legacy carrier fluxes if absent."""
    mesh = simulator.mesh
    keys = ['Jn_' + axis, 'Jp_' + axis]
    def field(key):
        values = np.asarray(result[key], dtype=float).ravel()
        if values.size != mesh.npts():
            raise ValueError(f"{key} must contain one value per mesh node")
        return values[line[:-1]]
    if all(key in result for key in keys):
        total = field(keys[0]) + field(keys[1])
    else:
        phi, n, p = [np.asarray(result[key], dtype=float)[line] for key in ['phi', 'n', 'p']]
        mu_n, mu_p = [np.asarray(mesh.fields.get(key, np.full(mesh.npts(), default)),
                                dtype=float)[line]
                      for key, default in [('mu_n', .14), ('mu_p', .045)]]
        jn, jp = sg_current_density_1d(
            phi, n, p, lengths, mu_n, mu_p, simulator.VT,
            elementary_charge_C=getattr(simulator, 'elementary_charge_C', QE))
        total = jn + jp
    if 'Jleak_' + axis in result:
        total = total + field('Jleak_' + axis)
    return total


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
    dx: float | np.ndarray,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
    VT: float,
    *,
    elementary_charge_C: float = QE,
) -> Tuple[np.ndarray, np.ndarray]:
    """Edge-centered Scharfetter-Gummel electron and hole current densities [A/m^2].

    Returns arrays of length ``len(phi)-1`` (one per edge). Sign convention:
    positive current flows in the +x direction (node i -> i+1).

    ``dx`` is a positive scalar or a vector of actual edge lengths [m].
    ``mu_n``/``mu_p`` are per-node; harmonic means are used on edges.
    Standalone calls use SI charge by default. Simulator-backed terminal
    extraction supplies the charge of its loaded native solver explicitly.
    """
    charge = _validated_elementary_charge(elementary_charge_C)
    phi = np.asarray(phi, dtype=float)
    n = np.asarray(n, dtype=float)
    p = np.asarray(p, dtype=float)
    mu_n = np.asarray(mu_n, dtype=float)
    mu_p = np.asarray(mu_p, dtype=float)
    dx = _edge_lengths(dx, len(phi) - 1)

    dphi = phi[1:] - phi[:-1]
    Bp = _bernoulli(dphi / VT)
    Bm = _bernoulli(-dphi / VT)
    # Edge mobility: harmonic mean (matches the C++ solver assembly after the
    # 2026-08 current-conservation fix; node-upwind broke div J = qR).
    mu_ne = 2.0 * mu_n[:-1] * mu_n[1:] / (mu_n[:-1] + mu_n[1:] + 1e-30)
    mu_pe = 2.0 * mu_p[:-1] * mu_p[1:] / (mu_p[:-1] + mu_p[1:] + 1e-30)
    Dn = mu_ne * VT / dx
    Dp = mu_pe * VT / dx
    # Conventional electron and hole current densities.  Their small-field
    # expansion matches the drift/diffusion split in mechanism.py.
    Jn = charge * Dn * (n[1:] * Bp - n[:-1] * Bm)
    Jp = charge * Dp * (p[:-1] * Bp - p[1:] * Bm)
    return Jn, Jp


def contact_current_1d(
    simulator,
    result: Dict,
    contact_name: str,
    direction: str = "auto",
) -> float:
    """Contact current density [A/m²] into a quasi-1-D device.

    Integrates the total current density (Jn + Jp + Jleak) on the interior edge
    adjacent to the contact. Multiply by the complete transverse area [m²]
    for absolute current [A]. Sign: positive = conventional current supplied by
    the contact into the device, matching DEVSIM/Sentaurus terminal convention.

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
    x, line = cutline_x_at_jk(mesh, j0, k0)

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

    if (direction not in ("left", "right") or len(line_contact_i) == nx
            or np.any(np.diff(line_contact_i) != 1)
            or (direction == "left" and line_contact_i[0] != 0)
            or (direction == "right" and line_contact_i[-1] != nx - 1)):
        raise ValueError("contact must be contiguous and touch the selected boundary only")
    # Validate the tensor coordinates even when native fluxes are supplied.
    mesh.axis_coordinates()
    J = _line_total_current(simulator, result, line, 'x', np.diff(x))

    if direction == "left":
        # Left contact occupies i=0..i_last; the boundary edge is
        # (i_last, i_last+1).  J[i_last] is +x, from contact into device.
        i_last = int(line_contact_i[-1])
        return float(J[i_last])
    else:  # right
        # Right contact occupies i_first..nx-1; boundary edge is
        # (i_first-1, i_first).  J[i_first-1] is +x (into the right contact).
        i_first = int(line_contact_i[0])
        return -float(J[i_first - 1])


def terminal_currents_1d(simulator, result: Dict, *, cross_section_m2: float) -> Dict[str, float]:
    """Integrate named 1-D contacts into signed terminal currents [A].

    The complete transverse area must be supplied explicitly. For 2-D/3-D
    meshes use the corresponding full contact-surface integration instead.
    """
    if not np.isfinite(cross_section_m2) or cross_section_m2 <= 0:
        raise ValueError("cross_section_m2 must be finite and positive")
    if simulator.mesh.ny != 1 or simulator.mesh.nz != 1:
        raise ValueError("terminal_currents_1d requires ny=nz=1")
    contacts = [name[len("contact_"):] for name in simulator.mesh.fields
                if name.startswith("contact_")]
    if len(contacts) != 2:
        raise ValueError("exactly two boundary contacts are required for a 1-D device")
    occupied = np.zeros(simulator.mesh.nx, dtype=bool)
    for name in contacts:
        mask = np.asarray(simulator.mesh.fields["contact_" + name], dtype=bool).ravel()
        nodes = np.flatnonzero(mask)
        if (mask.size != occupied.size or not nodes.size or
                mask[0] == mask[-1] or np.any(np.diff(nodes) != 1)):
            raise ValueError("1-D contacts must be contiguous and touch exactly one boundary")
        if np.any(occupied & mask):
            raise ValueError("1-D contacts must not overlap")
        occupied |= mask
    return {name: cross_section_m2 * contact_current_1d(simulator, result, name)
            for name in contacts}


def terminal_currents_native(simulator, result: Dict) -> Dict[str, float]:
    """Integrate native tensor-grid conduction into named reservoirs [A].

    Sum exported Jn, Jp and Jleak on every edge joining a named contact to
    free volume, including lateral faces and interior contacts in 1-D/2-D/3-D.
    Positive current enters the free volume. Edges within or between contact
    reservoirs are excluded, matching the native electrode ledger. Contact
    masks must be nonempty, binary and disjoint; at least two are required.

    Geometry follows Grid3D's *full* endpoint control widths, with the full
    bounding span as extrusion on singleton axes. This differs from the
    physical half-endpoint surface quadrature in contact_current_2d. It is
    the native finite-volume convention, not a cut-cell or sub-face integral.
    Every active axis requires finite node-sized Jn/Jp/Jleak arrays in native
    x-fastest order. No classical SG reconstruction replaces missing fluxes.
    This extractor neither certifies convergence nor adds displacement current.
    """
    mesh = simulator.mesh
    axes = mesh.axis_coordinates()
    counts = (mesh.nx, mesh.ny, mesh.nz)
    size = mesh.npts()
    if sum(count > 1 for count in counts) == 0:
        raise ValueError("terminal currents require at least one active grid axis")
    names = [key[len('contact_'):] for key in mesh.fields if key.startswith('contact_')]
    if len(names) < 2 or any(not name for name in names):
        raise ValueError("at least two named contacts are required")
    owners = np.zeros(size, dtype=np.intp)
    for label, name in enumerate(names, 1):
        raw = np.asarray(mesh.fields['contact_' + name])
        if (np.iscomplexobj(raw) or raw.size != size or
                not np.all((raw == 0) | (raw == 1)) or not np.any(raw == 1)):
            raise ValueError("contact masks must be nonempty binary node arrays")
        mask = raw.ravel().astype(bool)
        if np.any(owners[mask]):
            raise ValueError("contact masks must not overlap")
        owners[mask] = label

    widths = []
    for coords, (lo, hi), count in zip(axes,
            ((mesh.xmin, mesh.xmax), (mesh.ymin, mesh.ymax), (mesh.zmin, mesh.zmax)), counts):
        if count == 1:
            width = np.array([hi - lo])
        else:
            edges = np.diff(coords)
            width = np.r_[edges[0], (edges[:-1] + edges[1:]) / 2, edges[-1]]
        if not np.all(np.isfinite(width)) or np.any(width <= 0):
            raise ValueError("native control widths must be finite and positive")
        widths.append(width)
    nodes = np.arange(size)
    strides = (1, mesh.nx, mesh.nx * mesh.ny)
    positions = [(nodes // stride) % count for stride, count in zip(strides, counts)]
    terms = [[] for _ in names]
    for axis, (stride, count) in enumerate(zip(strides, counts)):
        if count == 1:
            continue
        fields = []
        for carrier in ('Jn', 'Jp', 'Jleak'):
            key = carrier + '_' + 'xyz'[axis]
            if key not in result:
                raise ValueError(f"native terminal currents require {key}")
            raw = np.asarray(result[key])
            if np.iscomplexobj(raw):
                raise ValueError(f"{key} must be real")
            values = np.asarray(raw, dtype=float)
            if values.ndim != 1 or values.size != size or not np.all(np.isfinite(values)):
                raise ValueError(f"{key} must be a finite native node array")
            fields.append(values)
        left = nodes[positions[axis] + 1 < count]
        right = left + stride
        crossing = (owners[left] == 0) != (owners[right] == 0)
        left, right = left[crossing], right[crossing]
        labels = np.maximum(owners[left], owners[right])
        sign = np.where(owners[left] > 0, 1., -1.)
        a, b = (axis + 1) % 3, (axis + 2) % 3
        with np.errstate(over='ignore', under='ignore', invalid='ignore'):
            area = widths[a][positions[a][left]] * widths[b][positions[b][left]]
        if not np.all(np.isfinite(area)) or np.any(area <= 0):
            raise ValueError("native face areas overflowed or underflowed")
        for values in fields:
            flux = values[left]
            with np.errstate(over='ignore', under='ignore', invalid='ignore'):
                current = sign * flux * area
            if (not np.all(np.isfinite(current)) or
                    np.any((flux != 0) & (current == 0))):
                raise ValueError("native face current overflowed or underflowed")
            for label in np.unique(labels):
                terms[label - 1].extend(current[labels == label].tolist())
    try:
        currents = {name: fsum(values) for name, values in zip(names, terms)}
    except (OverflowError, ValueError) as exc:
        raise ValueError("native terminal current sum is not representable") from exc
    if not all(np.isfinite(value) for value in currents.values()):
        raise ValueError("native terminal current sum must be finite")
    return currents


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
    *,
    elementary_charge_C: float = QE,
) -> Tuple[np.ndarray, np.ndarray]:
    """Edge SG current densities along the z-axis [A/m^2].

    Identical to :func:`sg_current_density_1d` but along z (node k -> k+1).
    Returns arrays of length ``len(phi)-1``.  Positive = +z direction.
    """
    return sg_current_density_1d(phi, n, p, dz, mu_n, mu_p, VT,
                                 elementary_charge_C=elementary_charge_C)


def contact_current_2d(
    simulator,
    result: Dict,
    contact_name: str,
    width: Optional[float] = None,
    *,
    normal: Optional[str] = None,
) -> float:
    """Signed conduction current [A] supplied into an x-z tensor mesh (ny=1).

    Integrate the inner normal edge of each contact row with node dual-face
    lengths: half the adjacent interval at endpoints, half each neighboring
    interval inside. Width defaults to the full y bbox span. A partial mask
    selects complete node dual faces; sub-face electrode coverage and lateral
    faces of finite-thickness electrodes are not reconstructed here.

    ``normal`` may be left/right/bottom/top. Auto-detection rejects ambiguous
    masks except a single corner node, which retains the legacy x preference.
    Native quad SG fluxes are preferred; legacy states use actual edge lengths.
    This is conduction (including exported leakage), not displacement current.
    """
    mesh = simulator.mesh
    if mesh.ny != 1:
        raise ValueError("contact_current_2d requires ny=1")
    coordinates = mesh.axis_coordinates()
    width = mesh.ymax - mesh.ymin if width is None else width
    if not np.isfinite(width) or width <= 0:
        raise ValueError("width must be finite and positive")
    field = 'contact_' + contact_name
    if field not in mesh.fields:
        raise KeyError(f"Contact '{contact_name}' not in mesh fields")
    mask = np.asarray(mesh.fields[field], dtype=bool).ravel()
    if mask.size != mesh.npts() or not mask.any():
        raise ValueError("contact mask must have mesh.npts() entries and contain nodes")
    mask2 = mask.reshape(mesh.nz, mesh.nx)
    candidates = {}
    for side, axis, lower in [('left', 0, True), ('right', 0, False),
                              ('bottom', 2, True), ('top', 2, False)]:
        rows = mask2 if axis == 0 else mask2.T
        selected = []
        for transverse in np.flatnonzero(rows.any(axis=1)):
            occupied = np.flatnonzero(rows[transverse])
            if (len(occupied) == rows.shape[1] or np.any(np.diff(occupied) != 1)
                    or (lower and occupied[0] != 0)
                    or (not lower and occupied[-1] != rows.shape[1] - 1)):
                break
            edge = int(occupied[-1] if lower else occupied[0] - 1)
            selected.append((int(transverse), edge))
        else:
            candidates[side] = (axis, lower, selected)
    if normal is None:
        if len(candidates) == 1:
            normal = next(iter(candidates))
        elif mask.sum() == 1:
            normal = next((s for s in ['left', 'right'] if s in candidates), None)
        if normal is None:
            raise ValueError("contact normal is ambiguous or unsupported; specify normal explicitly")
    if normal not in candidates:
        raise ValueError("contact must be contiguous and touch only the selected normal boundary")
    axis, lower, selected = candidates[normal]
    transverse_axis = 2 if axis == 0 else 0
    transverse_coords = coordinates[transverse_axis]
    if len(transverse_coords) == 1:
        lo, hi = [(mesh.xmin, mesh.xmax), (mesh.ymin, mesh.ymax),
                  (mesh.zmin, mesh.zmax)][transverse_axis]
        weights = np.array([hi - lo])
    else:
        half = np.diff(transverse_coords) / 2
        weights = np.r_[half, 0.] + np.r_[0., half]
    total = 0.
    for transverse, edge in selected:
        line = (np.arange(mesh.nx) + mesh.nx * transverse if axis == 0 else
                transverse + mesh.nx * np.arange(mesh.nz))
        current = _line_total_current(simulator, result, line, 'xyz'[axis],
                                      np.diff(coordinates[axis]))
        total += (1 if lower else -1) * current[edge] * weights[transverse]
    return float(total * width)
