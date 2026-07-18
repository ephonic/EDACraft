"""Helpers for extracting routed geometry directly from testcase assets."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np


_NET_RE = re.compile(r"^-\s+(\S+)")
_ROUTE_RE = re.compile(r"^(?:\+\s+ROUTED|NEW)\s+([A-Za-z0-9_]+)")
_POINT_RE = re.compile(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)")
_LAYER_ONLY_RE = re.compile(r"^([A-Za-z0-9_]+)")


def load_txt_endpoints(txt_path):
    """Return {net_name: {'layer': str, 'p1_um': array, 'p2_um': array}}."""
    nets = {}
    with open(txt_path) as f:
        next(f, None)
        for line in f:
            parts = line.split()
            if len(parts) < 6:
                continue
            nets[parts[0]] = {
                "layer": parts[1],
                "p1_um": np.array([float(parts[2]), float(parts[3])], dtype=float),
                "p2_um": np.array([float(parts[4]), float(parts[5])], dtype=float),
            }
    return nets


def poly_points_um(poly):
    """Convert a GDS polygon to an (N, 2) array in microns."""
    pts = []
    for p in poly:
        x = p[0][0] if isinstance(p[0], tuple) else p[0]
        y = p[1][0] if isinstance(p[1], tuple) else p[1]
        pts.append((x / 1000.0, y / 1000.0))
    return np.asarray(pts, dtype=float)


def projected_width_um(poly, p1_um, p2_um):
    """Project polygon points onto the endpoint-normal direction.

    This is only reliable for a straight route polygon. For routed polylines with
    bends it overestimates width by folding route excursion into the width axis.
    """
    pts = poly_points_um(poly)
    axis = np.asarray(p2_um, dtype=float) - np.asarray(p1_um, dtype=float)
    norm = np.linalg.norm(axis)
    if norm < 1e-12:
        raise ValueError("degenerate route endpoints")
    axis /= norm
    perp = np.array([-axis[1], axis[0]], dtype=float)
    proj = pts @ perp
    return float(proj.max() - proj.min())


def endpoint_width_geometry(poly, p1_um, p2_um, width_um=None):
    """Return endpoints in meters plus an explicit or projected width.

    Pass ``width_um`` for routed nets. Falling back to projected polygon width is
    meant for straight strips only.
    """
    if width_um is None:
        width_um = projected_width_um(poly, p1_um, p2_um)
    return (
        np.asarray(p1_um, dtype=float) * 1e-6,
        np.asarray(p2_um, dtype=float) * 1e-6,
        float(width_um) * 1e-6,
    )


def _as_path(path_like) -> Path:
    return path_like if isinstance(path_like, Path) else Path(path_like)


@lru_cache(maxsize=16)
def load_cases_manifest(manifest_path):
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    return {entry["case_name"]: entry for entry in data}


def infer_case_name(case_path):
    path = _as_path(case_path)
    stem = path.stem
    if stem.endswith("__gr"):
        return stem[:-4]
    return stem


def find_manifest_near(case_path):
    path = _as_path(case_path).resolve()
    for parent in [path.parent] + list(path.parents):
        candidate = parent / "cases_manifest.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"could not find cases_manifest.json near {path}")


def routing_width_um(case_name, layer_name=None, manifest_path=None, case_path=None):
    """Return the routing width in microns from testcase metadata."""
    if manifest_path is None:
        if case_path is None:
            raise ValueError("manifest_path or case_path is required")
        manifest_path = find_manifest_near(case_path)
    cases = load_cases_manifest(str(manifest_path))
    meta = cases[case_name]["tech_metadata"]
    widths = meta.get("routing_widths_um", {})
    if layer_name and layer_name in widths:
        return float(widths[layer_name])
    if "routing_width_um" in meta:
        return float(meta["routing_width_um"])
    if "width" in meta:
        return float(meta["width"])
    raise KeyError(f"routing width missing for case={case_name} layer={layer_name}")


@lru_cache(maxsize=16)
def parse_def_routes(def_path):
    """Parse routed centerlines from DEF.

    Returns:
      {net_name: [{'layer': 'M2', 'points_um': ndarray(N, 2)}, ...], ...}
    """
    routes = {}
    current_net = None
    current_entries = None
    pending_routed = False
    with open(def_path, encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if current_net is None:
                m_net = _NET_RE.match(line)
                if m_net:
                    current_net = m_net.group(1)
                    current_entries = []
                continue

            route_payload = None
            if line.startswith("+ ROUTED"):
                pending_routed = True
                tail = line[len("+ ROUTED"):].strip()
                if tail:
                    route_payload = tail
                    pending_routed = False
            elif pending_routed:
                route_payload = line
                pending_routed = False
            elif line.startswith("NEW "):
                route_payload = line[len("NEW "):].strip()

            if route_payload:
                m_layer = _LAYER_ONLY_RE.match(route_payload)
                if m_layer:
                    layer = m_layer.group(1)
                    pts = _POINT_RE.findall(route_payload)
                    if pts:
                        arr = np.array(
                            [[int(x) / 4000.0, int(y) / 4000.0] for x, y in pts],
                            dtype=float,
                        )
                        current_entries.append({"layer": layer, "points_um": arr})

            if line.endswith(";"):
                routes[current_net] = current_entries
                current_net = None
                current_entries = None
                pending_routed = False
    return routes


def _append_chain(chain, points_um, tol_um=1e-3):
    pts = np.asarray(points_um, dtype=float)
    if len(pts) < 2:
        return chain
    if not chain:
        chain.extend(pts.tolist())
        return chain

    head = np.asarray(chain[-1], dtype=float)
    if np.linalg.norm(head - pts[0]) <= tol_um:
        chain.extend(pts[1:].tolist())
        return chain
    if np.linalg.norm(head - pts[-1]) <= tol_um:
        chain.extend(pts[-2::-1].tolist())
        return chain
    return chain


def orient_route_points(points_um, p1_um=None, p2_um=None, snap_tol_um=5.0):
    pts = np.asarray(points_um, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        raise ValueError("route polyline must be an (N,2) array with N>=2")

    if p1_um is None or p2_um is None:
        return pts

    p1_um = np.asarray(p1_um, dtype=float)
    p2_um = np.asarray(p2_um, dtype=float)
    err_fwd = np.linalg.norm(pts[0] - p1_um) + np.linalg.norm(pts[-1] - p2_um)
    err_rev = np.linalg.norm(pts[-1] - p1_um) + np.linalg.norm(pts[0] - p2_um)
    if err_rev < err_fwd:
        pts = pts[::-1].copy()

    if np.linalg.norm(pts[0] - p1_um) <= snap_tol_um:
        pts[0] = p1_um
    if np.linalg.norm(pts[-1] - p2_um) <= snap_tol_um:
        pts[-1] = p2_um
    return pts


def route_length_um(points_um):
    pts = np.asarray(points_um, dtype=float)
    if len(pts) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def load_def_route_polyline(def_path, net_name, layer_name, p1_um=None, p2_um=None):
    """Load one routed centerline polyline for a net/layer from the DEF."""
    routes = parse_def_routes(str(def_path))
    entries = routes.get(net_name)
    if not entries:
        raise KeyError(f"net {net_name} not found in {def_path}")

    chain = []
    for entry in entries:
        if entry["layer"] != layer_name:
            continue
        _append_chain(chain, entry["points_um"])

    if len(chain) < 2:
        raise KeyError(f"net {net_name} has no routed points on {layer_name}")

    return orient_route_points(np.asarray(chain, dtype=float), p1_um, p2_um)
