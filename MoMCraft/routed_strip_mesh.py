"""Polyline strip meshing and local port-group extraction for routed nets."""

from __future__ import annotations

import math
import os

import numpy as np


def _normalize(vec):
    nrm = np.linalg.norm(vec)
    if nrm < 1e-15:
        raise ValueError("degenerate vector")
    return vec / nrm


def _perp(vec):
    return np.array([-vec[1], vec[0]], dtype=float)


def _line_intersection(p0, d0, p1, d1):
    det = d0[0] * d1[1] - d0[1] * d1[0]
    if abs(det) < 1e-12:
        return None
    rhs = p1 - p0
    t = (rhs[0] * d1[1] - rhs[1] * d1[0]) / det
    return p0 + t * d0


def _simplify_short_segments(points, tol, *, allow_terminal=False):
    pts = np.asarray(points, dtype=float)
    if len(pts) <= 2 or tol <= 0.0:
        return pts

    work = pts.copy()
    changed = True
    while changed and len(work) > 2:
        changed = False
        seg = np.diff(work, axis=0)
        lens = np.linalg.norm(seg, axis=1)
        for seg_idx, seg_len in enumerate(lens):
            if seg_len >= tol:
                continue

            if seg_idx == 0:
                if not allow_terminal:
                    continue
                work = np.delete(work, 1, axis=0)
                changed = True
                break

            if seg_idx == len(lens) - 1:
                if not allow_terminal:
                    continue
                work = np.delete(work, len(work) - 2, axis=0)
                changed = True
                break

            old_local = lens[seg_idx - 1] + lens[seg_idx] + lens[seg_idx + 1]
            candidates = []
            for remove_idx in (seg_idx, seg_idx + 1):
                cand = np.delete(work, remove_idx, axis=0)
                new_local = (
                    np.linalg.norm(cand[seg_idx] - cand[seg_idx - 1])
                    + np.linalg.norm(cand[seg_idx + 1] - cand[seg_idx])
                )
                candidates.append((abs(new_local - old_local), remove_idx, cand))

            candidates.sort(key=lambda item: (item[0], item[1]))
            work = candidates[0][2]
            changed = True
            break

    return work


def _default_short_seg_tol(width, max_step):
    return min(0.95 * float(max_step), max(3.0 * float(width), 15e-6))


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _polyline_offsets(points, width):
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        raise ValueError("points must be an (N,2) array with N>=2")

    hw = 0.5 * width
    dirs = np.array([_normalize(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)])
    norms = np.array([_perp(d) for d in dirs])

    left = np.zeros_like(pts)
    right = np.zeros_like(pts)
    left[0] = pts[0] + hw * norms[0]
    right[0] = pts[0] - hw * norms[0]
    left[-1] = pts[-1] + hw * norms[-1]
    right[-1] = pts[-1] - hw * norms[-1]

    for i in range(1, len(pts) - 1):
        prev_d = dirs[i - 1]
        next_d = dirs[i]
        prev_n = norms[i - 1]
        next_n = norms[i]
        turn = prev_d[0] * next_d[1] - prev_d[1] * next_d[0]

        if abs(turn) < 1e-10 and np.dot(prev_d, next_d) > 0.0:
            avg_n = prev_n + next_n
            if np.linalg.norm(avg_n) < 1e-12:
                avg_n = prev_n
            avg_n = _normalize(avg_n)
            left[i] = pts[i] + hw * avg_n
            right[i] = pts[i] - hw * avg_n
            continue

        left_i = _line_intersection(
            pts[i] + hw * prev_n, prev_d, pts[i] + hw * next_n, next_d
        )
        right_i = _line_intersection(
            pts[i] - hw * prev_n, prev_d, pts[i] - hw * next_n, next_d
        )
        if left_i is None or right_i is None:
            avg_n = prev_n + next_n
            if np.linalg.norm(avg_n) < 1e-12:
                avg_n = prev_n
            avg_n = _normalize(avg_n)
            left_i = pts[i] + hw * avg_n
            right_i = pts[i] - hw * avg_n

        # Keep the join numerically tame at acute bends.
        if np.linalg.norm(left_i - pts[i]) > 4.0 * width:
            avg_n = prev_n + next_n
            if np.linalg.norm(avg_n) < 1e-12:
                avg_n = prev_n
            left_i = pts[i] + hw * _normalize(avg_n)
        if np.linalg.norm(right_i - pts[i]) > 4.0 * width:
            avg_n = prev_n + next_n
            if np.linalg.norm(avg_n) < 1e-12:
                avg_n = prev_n
            right_i = pts[i] - hw * _normalize(avg_n)
        left[i] = left_i
        right[i] = right_i

    return left, right, dirs


def build_routed_strip_mesh(
    points,
    width,
    z,
    max_step=16e-6,
    n_w=4,
    *,
    short_seg_tol=None,
    simplify_terminals=None,
):
    """Build a triangle strip mesh that follows a routed centerline polyline.

    The sweep keeps a constant section normal within each straight routed
    segment and only changes section orientation at the explicit polyline
    vertices. This avoids shearing short jog segments into twisted quads,
    which was the main failure mode of the older endpoint-interpolation sweep.
    """
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        raise ValueError("need at least two route points")

    if short_seg_tol is None:
        short_seg_tol_um = os.environ.get("MOM_ROUTE_SHORT_SEG_TOL_UM")
        if short_seg_tol_um is not None and short_seg_tol_um.strip():
            short_seg_tol = max(0.0, float(short_seg_tol_um)) * 1e-6
        else:
            short_seg_tol = _default_short_seg_tol(width, max_step)
    else:
        short_seg_tol = max(0.0, float(short_seg_tol))

    if simplify_terminals is None:
        simplify_terminals = _env_bool("MOM_ROUTE_SIMPLIFY_TERMINALS", False)

    pts = _simplify_short_segments(
        pts,
        short_seg_tol,
        allow_terminal=bool(simplify_terminals),
    )

    left, right, dirs = _polyline_offsets(pts, width)
    seg_lens = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    seg_counts = [max(1, int(math.ceil(seg_len / max_step))) for seg_len in seg_lens]

    cross_sections = [
        (pts[0] + 0.5 * width * _perp(dirs[0]), pts[0] - 0.5 * width * _perp(dirs[0]))
    ]
    for i, seg_len in enumerate(seg_lens):
        n_seg = seg_counts[i]
        seg_norm = _perp(dirs[i])
        for k in range(1, n_seg + 1):
            u = k / n_seg
            center = (1.0 - u) * pts[i] + u * pts[i + 1]
            if k == n_seg and i + 1 < len(pts) - 1:
                li = left[i + 1]
                ri = right[i + 1]
            else:
                li = center + 0.5 * width * seg_norm
                ri = center - 0.5 * width * seg_norm
            cross_sections.append((li, ri))

    # Very short jog segments can place two consecutive sections almost on top
    # of each other while rotating their orientation sharply. Those near-zero
    # quads were the main trigger behind full-route lines collapsing to |S21|~0.
    step_scale = float(os.environ.get("MOM_MIN_SECTION_STEP_SCALE", "0.2"))
    min_section_step = max(0.0, step_scale) * float(max_step)
    compact_sections = [cross_sections[0]]
    for li, ri in cross_sections[1:]:
        prev_li, prev_ri = compact_sections[-1]
        prev_c = 0.5 * (prev_li + prev_ri)
        curr_c = 0.5 * (li + ri)
        if np.linalg.norm(curr_c - prev_c) < min_section_step:
            compact_sections[-1] = (li, ri)
            continue
        compact_sections.append((li, ri))
    cross_sections = compact_sections

    verts = []
    for li, ri in cross_sections:
        for wi in range(n_w + 1):
            u = wi / n_w
            pi = (1.0 - u) * ri + u * li
            verts.append([pi[0], pi[1], z])
    verts = np.asarray(verts, dtype=float)

    def idx(si, wi):
        return si * (n_w + 1) + wi

    tris = []
    for si in range(len(cross_sections) - 1):
        for wi in range(n_w):
            a = idx(si, wi)
            b = idx(si, wi + 1)
            c = idx(si + 1, wi)
            e = idx(si + 1, wi + 1)
            tris.append([a, c, b])
            tris.append([b, c, e])
    tris = np.asarray(tris, dtype=np.int32)

    meta = {
        "n_sections": len(cross_sections),
        "mesh_step_start": float(seg_lens[0] / seg_counts[0]) if len(seg_lens) else 0.0,
        "mesh_step_end": float(seg_lens[-1] / seg_counts[-1]) if len(seg_lens) else 0.0,
        "axis_start": dirs[0],
        "axis_end_in": -dirs[-1],
        "short_seg_tol": float(short_seg_tol),
        "simplify_terminals": bool(simplify_terminals),
    }
    return verts, tris, meta


def rwg_current_direction(mesh, bi):
    info = mesh.get_rwg_info(bi)
    cp_plus = np.array(mesh.get_triangle_centroid(info["t_plus"]))
    cp_minus = (
        np.array(mesh.get_triangle_centroid(info["t_minus"]))
        if info["t_minus"] >= 0
        else cp_plus
    )
    flow = cp_plus - cp_minus
    flow[2] = 0.0
    nrm = np.linalg.norm(flow)
    return (flow / nrm, nrm) if nrm > 1e-15 else (np.zeros(3), 0.0)


def find_anchor_bases(mesh, p1, p2, z, radius_um=30.0):
    """Find RWG bases nearest each end of the trace."""
    nb = mesh.n_rwg()
    ends = [[], []]
    radius = radius_um * 1e-6
    for bi in range(nb):
        info = mesh.get_rwg_info(bi)
        if not info["is_interior"]:
            continue
        cp = np.array(mesh.get_triangle_centroid(info["t_plus"]))
        if abs(cp[2] - z) > 1e-6:
            continue
        for ei, ep in enumerate([p1, p2]):
            if np.linalg.norm(cp[:2] - ep) < radius:
                ends[ei].append(bi)

    def closest(target, bases):
        if not bases:
            return None
        return min(
            bases,
            key=lambda b: np.linalg.norm(
                np.array(mesh.get_triangle_centroid(mesh.get_rwg_info(b)["t_plus"]))[:2]
                - target
            ),
        )

    return closest(p1, ends[0]), closest(p2, ends[1])


def build_port_group(mesh, anchor, axis2d, z_layer, tol_um=15.0, cos_min=0.2):
    """Sign-aware port edge set near the anchor basis."""
    info = mesh.get_rwg_info(anchor)
    cp = np.array(mesh.get_triangle_centroid(info["t_plus"]))
    s_anchor = np.dot(cp[:2], axis2d)
    nb = mesh.n_rwg()
    group = []
    for bi in range(nb):
        info_i = mesh.get_rwg_info(bi)
        if not info_i["is_interior"]:
            continue
        cp_i = np.array(mesh.get_triangle_centroid(info_i["t_plus"]))
        if abs(cp_i[2] - z_layer) > 1e-6:
            continue
        s_i = np.dot(cp_i[:2], axis2d)
        if abs(s_i - s_anchor) > tol_um * 1e-6:
            continue
        fd, fm = rwg_current_direction(mesh, bi)
        if fm < 1e-15:
            continue
        ca = np.dot(fd[:2], axis2d)
        if abs(ca) < cos_min:
            continue
        group.append((bi, 1 if ca > 0 else -1))
    return group


def build_local_port_group(mesh, anchor_xy, axis_in, width, z, s_max, cos_min=0.35):
    """Collect longitudinal RWG bases near a route endpoint.

    `axis_in` must point from the port into the routed net.
    """
    axis_in = _normalize(np.asarray(axis_in, dtype=float))
    anchor_xy = np.asarray(anchor_xy, dtype=float)
    perp = _perp(axis_in)
    group = []
    for bi in range(mesh.n_rwg()):
        info = mesh.get_rwg_info(bi)
        if not info["is_interior"]:
            continue
        cp = np.array(mesh.get_triangle_centroid(info["t_plus"]))
        if abs(cp[2] - z) > 1e-6:
            continue
        rel = cp[:2] - anchor_xy
        s = np.dot(rel, axis_in)
        p = np.dot(rel, perp)
        if s < -1e-9 or s > s_max:
            continue
        if abs(p) > 0.6 * width:
            continue
        flow_dir, flow_mag = rwg_current_direction(mesh, bi)
        if flow_mag < 1e-15:
            continue
        cos_a = np.dot(flow_dir[:2], axis_in)
        if abs(cos_a) < cos_min:
            continue
        group.append((bi, 1 if cos_a > 0 else -1))
    group.sort(key=lambda item: item[0])
    return group


def build_local_port_cluster_group(
    mesh,
    anchor_xy,
    axis_in,
    width,
    z,
    *,
    max_clusters=2,
    gap_um=2.0,
    p_scale=0.6,
    cos_min=0.35,
):
    """Collect the first few longitudinal RWG clusters near a route endpoint.

    A fixed longitudinal window can split one discrete cross-section cluster
    from the next when the routed endpoint lands near the middle of a cell.
    This helper groups candidate RWGs by their longitudinal centroid location
    and returns the first `max_clusters` layers into the routed net.

    `axis_in` must point from the port into the routed net.
    """

    axis_in = _normalize(np.asarray(axis_in, dtype=float))
    anchor_xy = np.asarray(anchor_xy, dtype=float)
    perp = _perp(axis_in)
    candidates = []
    gap_m = float(gap_um) * 1e-6
    p_max = float(p_scale) * float(width)

    for bi in range(mesh.n_rwg()):
        info = mesh.get_rwg_info(bi)
        if not info["is_interior"]:
            continue
        cp = np.array(mesh.get_triangle_centroid(info["t_plus"]))
        if abs(cp[2] - z) > 1e-6:
            continue
        rel = cp[:2] - anchor_xy
        s = float(np.dot(rel, axis_in))
        p = float(np.dot(rel, perp))
        if s < -1e-9:
            continue
        if abs(p) > p_max:
            continue
        flow_dir, flow_mag = rwg_current_direction(mesh, bi)
        if flow_mag < 1e-15:
            continue
        cos_a = float(np.dot(flow_dir[:2], axis_in))
        if abs(cos_a) < cos_min:
            continue
        candidates.append((s, bi, 1 if cos_a > 0.0 else -1))

    if not candidates:
        return []

    candidates.sort(key=lambda item: item[0])
    groups = [[candidates[0]]]
    for item in candidates[1:]:
        if item[0] - groups[-1][-1][0] <= gap_m:
            groups[-1].append(item)
        else:
            groups.append([item])

    out = []
    for group in groups[: int(max_clusters)]:
        for _, bi, sign in group:
            out.append((bi, sign))
    out.sort(key=lambda item: item[0])
    return out


def build_cell_port_group(mesh, n_sections, n_w, axis_in, *, at_end=False, cos_min=0.35):
    """Collect longitudinal RWGs supported entirely on the first/last mesh cell.

    For the structured routed-strip mesh this gives a topology-stable port
    aperture: every selected RWG lives on the first (or last) section cell and
    carries substantial current along the route axis.
    """

    axis_in = _normalize(np.asarray(axis_in, dtype=float))
    perp = _perp(axis_in)
    if at_end:
        cell_sections = {int(n_sections) - 2, int(n_sections) - 1}
    else:
        cell_sections = {0, 1}

    out = []
    for bi in range(mesh.n_rwg()):
        info = mesh.get_rwg_info(bi)
        if not info["is_interior"]:
            continue
        verts = [
            int(info["v_edge"][0]),
            int(info["v_edge"][1]),
            int(info["v_free_plus"]),
        ]
        if int(info["t_minus"]) >= 0:
            verts.append(int(info["v_free_minus"]))
        sec_ids = {v // (int(n_w) + 1) for v in verts}
        if not sec_ids.issubset(cell_sections):
            continue

        flow_dir, flow_mag = rwg_current_direction(mesh, bi)
        if flow_mag < 1e-15:
            continue
        cos_a = float(np.dot(flow_dir[:2], axis_in))
        if abs(cos_a) < cos_min:
            continue

        v0 = np.array(mesh.get_vertex(int(info["v_edge"][0])))
        v1 = np.array(mesh.get_vertex(int(info["v_edge"][1])))
        edge_mid = 0.5 * (v0 + v1)
        p = float(np.dot(edge_mid[:2], perp))
        out.append((bi, p, 1 if cos_a > 0.0 else -1))

    out.sort(key=lambda item: item[1])
    return out
