"""Displacement quadrature on explicitly meshed tetrahedral contact surfaces."""
import numpy as np

from tcad.postprocess.terminal_trace import _real_array
from .electrode_charge import integrate_electrode_surface_charge


def _indices(values, width, count, name):
    a = np.asarray(values)
    if (a.ndim != 2 or a.shape[1] != width or not len(a)
            or a.dtype.kind not in 'iu' or np.any(a < 0) or np.any(a >= count)):
        raise ValueError(f'{name} must contain nonempty integer vertex indices (N,{width})')
    a = a.astype(np.intp)
    ordered = np.sort(a, axis=1)
    if np.any(np.diff(ordered, axis=1) == 0):
        raise ValueError(name + ' contains repeated vertices')
    if len(np.unique(ordered, axis=0)) != len(a):
        raise ValueError(name + ' contains duplicate cells/faces')
    return a


def tetrahedral_surface_quadrature(vertices_m, tetrahedra, potential_V,
        permittivity_F_m, polarization_C_m2, contact_triangles):
    """Reconstruct interface-side D samples from a conforming linear tetra mesh.

    Coordinates/potential are (V,3)/(V,), connectivity is (T,4), absolute
    permittivity is piecewise constant (T,). Polarization is either constant
    (T,3), or linear with *cell-local*, potentially discontinuous values (T,4,3).
    The selected contact triangles (K,3) must each have exactly one volume owner.
    Face orientation is inferred from that owner, independently of vertex order.
    The potential gradient is reconstructed inside each owner; no nodal field,
    polarization or permittivity averaging across material interfaces occurs.

    All arguments are SI. Geometry must be a conforming nonoverlapping mesh;
    duplicate cells, nonmanifold faces, coplanar/ill-conditioned tetrahedra and
    adjacent cells on the same side of a shared face are rejected. Intersections
    between unrelated cells and hanging nodes are not detected. Selected surface
    coverage, the PDE solution and mesh convergence remain the caller's concern.
    This supplies quadrature, not a tetrahedral PDE solver or cut-cell mesher.
    """
    x = _real_array(vertices_m, 'vertices_m')
    phi = _real_array(potential_V, 'potential_V')
    eps = _real_array(permittivity_F_m, 'permittivity_F_m')
    p = _real_array(polarization_C_m2, 'polarization_C_m2')
    if x.ndim != 2 or x.shape[1] != 3 or len(x) < 4 or phi.shape != (len(x),):
        raise ValueError('require finite vertices (V,3) and potential (V,)')
    tet = _indices(tetrahedra, 4, len(x), 'tetrahedra')
    contact = _indices(contact_triangles, 3, len(x), 'contact_triangles')
    if (eps.shape != (len(tet),) or np.any(eps <= 0)
            or p.shape not in ((len(tet),3), (len(tet),4,3))):
        raise ValueError('require positive cell permittivity (T,) and polarization (T,3) or (T,4,3)')
    local_faces = np.array([[1,2,3], [0,2,3], [0,1,3], [0,1,2]])
    with np.errstate(over='ignore', invalid='ignore', divide='ignore', under='ignore'):
        points = x[tet]
        edges = points[:,1:] - points[:,:1]
        scale = np.max(np.abs(edges), axis=(1,2))
        scaled = edges / scale[:,None,None]
    if np.any(~np.isfinite(scaled)):
        raise ValueError('tetrahedral geometry has zero or unrepresentable extent')
    if np.any(np.linalg.cond(scaled) > 1e14):
        raise ValueError('tetrahedral geometry is degenerate or ill-conditioned')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore', under='ignore'):
        volume = np.abs(np.linalg.det(scaled)) * scale**3 / 6
        electric = -np.linalg.solve(scaled, (phi[tet[:,1:]]-phi[tet[:,:1]])[...,None])[...,0] / scale[:,None]
        shifted = (points - points[:,:1]) / scale[:,None,None]
        fp = shifted[:,local_faces]
        area_vectors = np.cross(fp[:,:,1]-fp[:,:,0], fp[:,:,2]-fp[:,:,0]) / 2
        inward = np.sum(area_vectors * (shifted-fp[:,:,0]), axis=2)
        area_vectors *= np.where(inward > 0, -1., 1.)[:,:,None]
        area_vectors *= scale[:,None,None]**2
        areas = np.linalg.norm(area_vectors / scale[:,None,None]**2, axis=2) * scale[:,None]**2
        normals = area_vectors / areas[:,:,None]
    if (np.any(volume <= 0) or np.any(areas <= 0)
            or any(np.any(~np.isfinite(a)) for a in (volume,electric,areas,normals))):
        raise ValueError('tetrahedral geometry/field exceeds float64 quadrature range')

    face_vertices = tet[:,local_faces].reshape(-1,3)
    canonical = np.sort(face_vertices, axis=1)
    unique, inverse, counts = np.unique(canonical, axis=0, return_inverse=True, return_counts=True)
    if np.any(counts > 2):
        raise ValueError('nonmanifold tetrahedral face')
    order = np.argsort(inverse, kind='stable')
    offsets = np.r_[0, np.cumsum(counts)]
    shared = np.flatnonzero(counts == 2)
    first, second = order[offsets[shared]], order[offsets[shared]+1]
    normal_flat = normals.reshape(-1,3)
    if np.any(np.sum(normal_flat[first]*normal_flat[second], axis=1) > -1.+1e-10):
        raise ValueError('adjacent tetrahedra lie on the same side of a shared face')
    lookup = {tuple(face):i for i,face in enumerate(unique)}
    selected = []
    for face in np.sort(contact, axis=1):
        index = lookup.get(tuple(face))
        if index is None or counts[index] != 1:
            raise ValueError('contact triangle must be an exterior face with exactly one volume owner')
        selected.append(order[offsets[index]])
    selected = np.asarray(selected, dtype=np.intp)
    owners = selected // 4
    sides = selected % 4
    surface_p = p[owners] if p.ndim == 2 else p[owners[:,None],local_faces[sides]].mean(axis=1)
    return dict(electric_field_V_m=electric[owners], polarization_C_m2=surface_p,
        permittivity_F_m=eps[owners], outward_dielectric_normals=normal_flat[selected],
        surface_weights_m2=areas.reshape(-1)[selected], owner_cells=owners,
        cell_volumes_m3=volume)


def integrate_tetrahedral_electrode_charge(vertices_m, tetrahedra, potential_V,
        permittivity_F_m, polarization_C_m2, contact_triangles):
    """Integrate -D.n using owner-side linear-tetrahedral surface quadrature."""
    q = tetrahedral_surface_quadrature(vertices_m, tetrahedra, potential_V,
        permittivity_F_m, polarization_C_m2, contact_triangles)
    result = integrate_electrode_surface_charge(*(q[key] for key in (
        'electric_field_V_m', 'polarization_C_m2', 'permittivity_F_m',
        'outward_dielectric_normals', 'surface_weights_m2')))
    result.update(surface_area_m2=float(np.sum(q['surface_weights_m2'])),
        scope='selected conforming tetrahedral exterior faces; cell-side E, epsilon and P',
        boundary_coverage_verified=False, trajectory_validated=False)
    return result
