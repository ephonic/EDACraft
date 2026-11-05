"""Execute the native spectral constitutive law, with no Python fallback."""
import numpy as np
from .fermi_spectral import validate_valleys


def native_spectral_face(owner,neighbor,valleys,*,potential_owner_V,potential_neighbor_V,
        potential_face_V,charge_sign,mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,
        area_m2,distance_owner_m,distance_neighbor_m,emission_factor=None,
        bulk_potential_path='endpoint_barrier'):
    from tcad.core._bindings import native_spectral_face_raw
    valleys=validate_valleys(valleys)
    if bulk_potential_path not in ('endpoint_barrier','linear_series'):
        raise ValueError('bulk_potential_path must be endpoint_barrier or linear_series')
    parameters=[owner['temperature_K'],neighbor['temperature_K'],
        owner['chemical_potential_J'],neighbor['chemical_potential_J'],owner['band_J'],neighbor['band_J'],
        potential_owner_V,potential_neighbor_V,potential_face_V,charge_sign,
        mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,area_m2,distance_owner_m,distance_neighbor_m,
        (2. if bulk_potential_path=='linear_series' else 0.) if emission_factor is None else 1.,
        0. if emission_factor is None else emission_factor]
    if any(isinstance(v,(bool,np.bool_)) or not np.isscalar(v) or not np.isreal(v) or not np.isfinite(v)
            for v in parameters):raise ValueError('finite real native spectral scalars required')
    packed=[v for valley in valleys for v in (valley.mass_normal,valley.dos_mass_ratio,
        valley.degeneracy,valley.band_offset_owner_J)]
    values=native_spectral_face_raw([float(v) for v in parameters],packed)
    return dict(particle_flux_s=values[0],total_energy_flux_W=values[1],material_energy_flux_W=values[2],
        entropy_production_W_K=values[3],trace_occupation_min=values[4],trace_occupation_max=values[5],
        valley_moments=[dict(name=valley.name,particle_flux_s=values[6+2*i],total_energy_flux_W=values[7+2*i])
            for i,valley in enumerate(valleys)],trace_closure='energy_resolved_nonthermal_occupations',
        statistics='fermi_dirac',execution_backend='native')
