"""Explicit native MB thermodynamics and bulk spectral moments, no fallback.

These primitives do not select statistics in a device solver. A face accepts
two physical (density_m3,temperature_K,band_J) triples and derives its own MB
chemical potentials inside C++, preserving the native scalar precision.
"""
from decimal import Decimal
import numpy as np
from .fermi_spectral import validate_valleys
from .native_fermi_local import _decimal


def _numbers(values, shape):
    a=np.asarray(values)
    if (a.shape!=shape or a.dtype.kind not in 'iuf' or
            any(isinstance(v,(bool,np.bool_)) for v in np.asarray(values,dtype=object).flat)
            or np.any(~np.isfinite(a))):
        raise ValueError('finite real MB physical inputs of the required shape expected')
    return a


def _valleys(values):
    vs=validate_valleys(values)
    return vs,[_decimal(v) for valley in vs for v in
              (valley.mass_normal,valley.dos_mass_ratio,valley.degeneracy,valley.band_offset_owner_J)]


def _view(values):
    numbers=np.array(values,dtype=float)
    if (np.any(~np.isfinite(numbers)) or
            any(x==0 and not Decimal(raw).is_zero() for x,raw in zip(numbers,values))):
        raise ValueError('native MB result does not fit nonzero finite float64 view; use the raw decimal API')
    return numbers


def native_boltzmann_reservoirs(densities,temperatures,bands,valleys):
    from tcad.core._bindings import native_boltzmann_reservoir_raw
    vs,packed=_valleys(valleys)
    arrays=[np.asarray(v) for v in (densities,temperatures,bands)]
    if arrays[0].ndim!=1 or not arrays[0].size:raise ValueError('nonempty reservoir vectors required')
    arrays=[_numbers(v,arrays[0].shape) for v in (densities,temperatures,bands)]
    raw=native_boltzmann_reservoir_raw([_decimal(v) for row in zip(*arrays) for v in row],packed)
    width=3+len(vs)
    if len(raw)!=width*len(arrays[0]):raise ValueError('native MB reservoir output coverage mismatch')
    result=[]
    for i,(T,band) in enumerate(zip(arrays[1],arrays[2])):
        text=tuple(raw[width*i:width*(i+1)]);row=_view(text)
        result.append(dict(chemical_potential_J=row[0],energy_density_J_m3=row[1],density_m3=row[2],
            valley_densities_m3=row[3:].copy(),temperature_K=float(T),band_J=float(band),
            native_decimal=text,statistics='boltzmann',execution_backend='native'))
    return result


def native_boltzmann_bulk_face(owner,neighbor,valleys,*,potential_owner_V,potential_neighbor_V,
        potential_face_V,charge_sign,mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,
        area_m2,distance_owner_m,distance_neighbor_m,bulk_potential_path='linear_series'):
    from tcad.core._bindings import native_boltzmann_bulk_face_raw
    vs,packed=_valleys(valleys)
    if bulk_potential_path not in ('linear_series','endpoint_barrier'):raise ValueError('explicit MB bulk path required')
    one,two=_numbers(owner,(3,)),_numbers(neighbor,(3,))
    geometry=_numbers([potential_owner_V,potential_neighbor_V,potential_face_V,charge_sign,
        mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,area_m2,distance_owner_m,distance_neighbor_m,
        2 if bulk_potential_path=='linear_series' else 0],(10,))
    raw=native_boltzmann_bulk_face_raw([_decimal(v) for row in (one,two) for v in row],
        [_decimal(v) for v in geometry],packed)
    if len(raw)!=6+2*len(vs):raise ValueError('native MB face output coverage mismatch')
    row=_view(raw)
    return dict(particle_flux_s=row[0],total_energy_flux_W=row[1],material_energy_flux_W=row[2],
        entropy_production_W_K=row[3],trace_occupation_min=row[4],trace_occupation_max=row[5],
        valley_moments=[dict(name=v.name,particle_flux_s=row[6+2*i],total_energy_flux_W=row[7+2*i]) for i,v in enumerate(vs)],
        native_decimal=tuple(raw),statistics='boltzmann',execution_backend='native',
        trace_closure='energy_resolved_MB_bulk',device_statistics_selected=False)
