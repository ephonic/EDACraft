#!/usr/bin/env python3
"""Simple 2D Delaunay triangular mesh generator for MOSFET structures.
Creates a mesh with:
- Fine triangles near the Si/SiO2 interface and S/D-channel junction
- Coarse triangles in the bulk
- Contact definitions on geometric edges

Output: UnstructuredMesh compatible node/edge/face data.
This is a SIMPLIFIED mesh generator — not a full Delaunay mesher.
It creates a structured grid of triangles with non-uniform spacing."""
import numpy as np
from scipy.spatial import Delaunay
import json

def generate_mosfet_mesh(
    # Geometry
    LSD=500e-9, LG=1000e-9, TOX=10e-9, TSI=1000e-9,
    # Mesh spacing
    dx_fine=5e-9,   # fine spacing near gate edges
    dx_coarse=50e-9, # coarse spacing in S/D bulk
    dz_fine=2e-9,    # fine spacing near Si surface
    dz_coarse=100e-9, # coarse spacing deep in substrate
    # Refinement zones
    dx_refine=200e-9, # x-range for fine mesh near gate edges
    dz_refine=100e-9, # z-range for fine mesh near surface
):
    """Generate a 2D non-uniform triangular mesh for an nMOS cross-section."""
    x_total = 2 * LSD + LG
    z_top = -TOX
    z_bot = TSI

    # Generate non-uniform x positions
    x_nodes = []
    x = 0.0
    while x <= x_total + 1e-12:
        x_nodes.append(x)
        # Determine spacing
        dist_to_gate_s = abs(x - LSD)
        dist_to_gate_d = abs(x - (LSD + LG))
        dist_to_gate = min(dist_to_gate_s, dist_to_gate_d)
        if dist_to_gate < dx_refine:
            dx = dx_fine
        else:
            dx = dx_coarse
        x += dx
    x_arr = np.array(x_nodes)

    # Generate non-uniform z positions
    z_nodes = []
    z = z_top
    while z <= z_bot + 1e-12:
        z_nodes.append(z)
        if abs(z) < dz_refine:
            dz = dz_fine
        else:
            dz = dz_coarse
        z += dz
    z_arr = np.array(z_nodes)

    # Create grid of points
    X, Z = np.meshgrid(x_arr, z_arr, indexing="ij")
    points_2d = np.column_stack([X.ravel(), Z.ravel()])
    nx = len(x_arr)
    nz = len(z_arr)
    N = nx * nz

    # Triangulate with Delaunay
    tri = Delaunay(points_2d)

    # Identify regions and contacts
    def get_region(x, z):
        if z < 0:
            return 1  # oxide
        return 0  # Si

    def get_contact(x, z):
        # Source: x < LSD, z = 0 (surface)
        if z < 1e-12 and z > -1e-12 and x < LSD:
            return 0  # source
        # Drain: x > LSD+LG, z = 0
        if z < 1e-12 and z > -1e-12 and x > LSD + LG:
            return 1  # drain
        # Gate: oxide top (z = -TOX)
        if z < -TOX + 1e-12 and z > -TOX - 1e-12:
            if LSD < x < LSD + LG:
                return 2  # gate
        # Substrate: z = TSI
        if z > TSI - 1e-12 and z < TSI + 1e-12:
            return 3  # substrate
        return -1  # interior

    regions = np.array([get_region(points_2d[i, 0], points_2d[i, 1]) for i in range(N)])
    contacts = np.array([get_contact(points_2d[i, 0], points_2d[i, 1]) for i in range(N)])

    return {
        "points": points_2d,          # (N, 2) array of [x, z]
        "triangles": tri.simplices,   # (M, 3) array of node indices
        "regions": regions,           # (N,) array of region IDs
        "contacts": contacts,         # (N,) array of contact IDs
        "nx": nx, "nz": nz,
        "x_arr": x_arr, "z_arr": z_arr,
    }


def mesh_to_tcadcraft(mesh_data, sim, VT, ni, NSD, NA, NSD_CM3, NA_CM3,
                      WF, PHI_G, EG, Nc, Nv, EPS_SI, EPS_OX):
    """Convert mesh data to TCADCraft DeviceSimulator setup.
    Uses structured grid API (set_z_positions + set_x_positions) with
    non-uniform spacing to approximate the unstructured mesh."""
    x_arr = mesh_data["x_arr"]
    z_arr = mesh_data["z_arr"]
    nx = len(x_arr)
    nz = len(z_arr)
    N = nx * nz

    DX0 = x_arr[1] - x_arr[0]
    DZ0 = z_arr[1] - z_arr[0]

    # Build 2D arrays
    X, Z = np.meshgrid(x_arr, z_arr, indexing="ij")
    is_ox = Z < 0
    in_sd = (Z >= 0) & (((X < 500e-9) & (Z < 300e-9)) |
                         ((X > 1500e-9) & (Z < 300e-9)))

    doping_cm3 = np.where(is_ox, 0.0, np.where(in_sd, NSD_CM3, -NA_CM3))
    doping = doping_cm3 * 1e6
    eps = np.where(is_ox, EPS_OX, EPS_SI)
    Eg_a = np.where(is_ox, 9.0, EG)
    Nca = np.where(is_ox, 1e25, Nc)
    Nva = np.where(is_ox, 1e25, Nv)

    from philips_mobility import mu_n, mu_p
    mun = np.where(is_ox, 0.0, mu_n(np.abs(doping)))
    mup = np.where(is_ox, 0.0, mu_p(np.abs(doping)))

    # Create simulator with non-uniform grid
    sim_obj = sim(nx, 1, nz, DX0, DX0, DZ0)
    sim_obj.set_x_positions(np.array(x_arr, dtype=float))
    sim_obj.set_z_positions(np.array(z_arr, dtype=float))
    sim_obj.set_doping(np.ascontiguousarray(doping))
    sim_obj.set_permittivity(np.ascontiguousarray(eps))
    sim_obj.set_mobility(np.ascontiguousarray(mun), np.ascontiguousarray(mup))
    sim_obj.set_recombination(np.full(N, 1e-6), np.full(N, 1e-6))
    sim_obj.set_effective_dos(np.ascontiguousarray(Nca), np.ascontiguousarray(Nva))
    sim_obj.set_bandgap(np.ascontiguousarray(Eg_a))
    sim_obj.set_thermal_voltage(VT)
    return sim_obj, X, Z, is_ox, in_sd, x_arr, z_arr, nx, nz


if __name__ == "__main__":
    mesh = generate_mosfet_mesh()
    print("Mesh: %d nodes, %d triangles" % (len(mesh["points"]), len(mesh["triangles"])))
    print("x: %d nodes (%.1f-%.1f nm, dx=%.1f-%.1f nm)" % (
        len(mesh["x_arr"]),
        mesh["x_arr"][0]*1e9, mesh["x_arr"][-1]*1e9,
        np.diff(mesh["x_arr"]).min()*1e9, np.diff(mesh["x_arr"]).max()*1e9))
    print("z: %d nodes (%.1f-%.1f nm, dz=%.1f-%.1f nm)" % (
        len(mesh["z_arr"]),
        mesh["z_arr"][0]*1e9, mesh["z_arr"][-1]*1e9,
        np.diff(mesh["z_arr"]).min()*1e9, np.diff(mesh["z_arr"]).max()*1e9))
    print("Contacts: source=%d drain=%d gate=%d substrate=%d" % (
        np.sum(mesh["contacts"] == 0),
        np.sum(mesh["contacts"] == 1),
        np.sum(mesh["contacts"] == 2),
        np.sum(mesh["contacts"] == 3)))
