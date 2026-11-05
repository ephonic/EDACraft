"""Validate the deliberately narrow native reconstruction scope."""
import numpy as np

MODE = 'quadratic_entropy_limited_1d'


def validate_reconstruction(model):
    mode = model.transport_reconstruction
    if mode not in ('cell_mean', MODE):
        raise ValueError('unknown three-temperature transport reconstruction')
    if mode == 'cell_mean':
        return
    if (model.residual_orchestration != 'native' or model.nc < 3 or
        model.bulk_potential_path != 'linear_series' or model.temperature_dependent_bands or
        model.trap_capture_law is not None or model.radiative_law is not None or
        model.auger_events is not None or np.any(model.Nt != 0) or
        np.any(model.intercarrier_conductance_W_m3_K != 0) or
        np.any(model.pair_generation_rate_m3_s != 0) or model.thermionic_faces or
        np.any(model.capacity != model.capacity[0]) or
        np.any(model.Ec != model.Ec[0]) or np.any(model.Eh != model.Eh[0])):
        raise ValueError('quadratic reconstruction requires native >=3 fixed-band source-free 1d cells')
    for valleys in model.valleys.values():
        if len(valleys) != 1 or valleys[0].band_offset_owner_J != 0 or valleys[0].band_offset_neighbor_J != 0:
            raise ValueError('quadratic reconstruction requires one zero-offset valley per carrier')
    edges = sorted(f.centroid_m[0] for f in model.mesh.faces if f.area_vector_m2[0] != 0)
    if len(edges) != model.nc+1 or np.any(np.diff(edges) <= 0):
        raise ValueError('quadratic reconstruction requires one ordered axial chain')
    widths = np.diff(np.asarray(edges, np.longdouble))
    x = np.asarray(model.mesh.centroids_m[:, 0], np.longdouble)
    if np.any(abs((x-edges[:-1])/widths-np.longdouble('.5')) > 1e-12):
        raise ValueError('quadratic reconstruction requires ordered midpoint centers')
