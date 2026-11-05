"""Native FD thermodynamics/local rows; no Python numerical fallback."""
import numpy as np
from .fermi_spectral import validate_valleys


def _decimal(value):
    # str(float) supplies its shortest round-trip decimal, not its exact binary
    # value. Convert via longdouble first, then supply enough decimal digits.
    return np.format_float_scientific(np.longdouble(value),precision=35,unique=False)


def native_fermi_reservoirs(densities,temperatures,bands,valleys):
    from tcad.core._bindings import native_fermi_reservoir_raw
    valleys=validate_valleys(valleys)
    arrays=[np.asarray(a) for a in (densities,temperatures,bands)]
    if any(a.ndim!=1 or a.shape!=arrays[0].shape or a.dtype.kind not in 'iuf' or
            not np.all(np.isfinite(a)) for a in arrays) or not arrays[0].size:
        raise ValueError('matching nonempty finite reservoir arrays required')
    packed=[v for valley in valleys for v in (valley.mass_normal,valley.dos_mass_ratio,
        valley.degeneracy,valley.band_offset_owner_J)]
    values=np.asarray(native_fermi_reservoir_raw([_decimal(v) for row in zip(*arrays) for v in row],packed))
    rows=values.reshape(len(arrays[0]),3+len(valleys))
    return [dict(chemical_potential_J=row[0],energy_density_J_m3=row[1],density_m3=row[2],
        valley_densities_m3=row[3:].copy(),temperature_K=float(T),band_J=float(band),
        execution_backend='native') for row,T,band in zip(rows,arrays[1],arrays[2])]


def native_fermi_local(model,old,n,p,T,old_u,u,old_poisson,new_poisson,fn,fp,eflux,dt):
    from tcad.core._bindings import native_fermi_local_raw
    cells=zip(old.n_m3,old.p_m3,old.temperature_K,n,p,T,old_u,u,model.vol,model.capacity,
        old_poisson['cell_potential_V'],new_poisson['cell_potential_V'],model.conductivity)
    faces=[]
    for f,face in enumerate(model.mesh.faces):
        faces.extend(_decimal(v) for v in (face.owner,face.neighbor,fn[f],fp[f],eflux[f],
            old_poisson['face_potential_V'][f],new_poisson['face_potential_V'][f],
            model.area[f],model.do[f],model.dn[f],model.bath.get(f,0.),int(f in model.bath)))
    values=np.asarray(native_fermi_local_raw([_decimal(v) for row in cells for v in row],faces,float(dt)))
    result={name:values[k*model.nc:(k+1)*model.nc] for k,name in enumerate(
        ('rn','rp','delta_u','delta_t','work','energy'))}
    result['heat']=values[6*model.nc:]
    return result
