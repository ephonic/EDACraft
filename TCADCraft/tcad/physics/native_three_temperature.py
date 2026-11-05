"""Native five conservation rows; decimal boundaries preserve density precision."""
import numpy as np
from .native_fermi_local import _decimal


def native_three_temperature_local(model, old, n, p, Tl, old_u, u, equilibrium_u,
                                   old_poisson, poisson, rates, energies, dt, *, Tn=None, Tp=None):
    """Assemble storage, FD relaxation, electrical work and Fourier transport.

    FD energies and oriented spectral fluxes come from the existing native
    primitives. This adapter packs inputs and splits outputs; it never forms
    conservation rows or supplies a Python numerical fallback.
    """
    from tcad.core._bindings import native_three_temperature_local_raw
    if any(law is not None for law in model.relaxation_laws) and (Tn is None or Tp is None):
        raise ValueError('explicit carrier temperatures required for relaxation law')
    tau=model.relaxation_times(n,p,Tn,Tp,Tl)
    cells=zip(old.n_m3,old.p_m3,old.temperature_K,n,p,Tl,
        old_u['electrons'],u['electrons'],equilibrium_u['electrons'],
        old_u['holes'],u['holes'],equilibrium_u['holes'],model.vol,model.capacity,
        old_poisson['cell_potential_V'],poisson['cell_potential_V'],model.conductivity,
        tau['electrons'],tau['holes'])
    faces=[]
    for f,face in enumerate(model.mesh.faces):
        faces.extend(_decimal(v) for v in (face.owner,face.neighbor,
            rates['electrons'][f],rates['holes'][f],energies['electrons'][f],energies['holes'][f],
            old_poisson['face_potential_V'][f],poisson['face_potential_V'][f],
            model.area[f],model.do[f],model.dn[f],model.bath.get(f,0.),int(f in model.bath)))
    packed = [_decimal(v) for row in cells for v in row]
    coupled = np.any(model.intercarrier_conductance_W_m3_K != 0)
    generated = np.any(model.pair_generation_rate_m3_s != 0)
    if coupled or generated:
        if Tn is None or Tp is None:
            raise ValueError('explicit carrier temperatures required for intercarrier exchange')
        from tcad.core._bindings import native_three_temperature_exchange_local_raw
        exchange = [_decimal(v) for row in zip(Tn,Tp,model.intercarrier_conductance_W_m3_K) for v in row]
        if generated:
            from tcad.core._bindings import native_three_temperature_generation_local_raw
            generation=[_decimal(v) for row in zip(*model.pair_generation_parameters()) for v in row]
            values=np.asarray(native_three_temperature_generation_local_raw(packed,faces,float(dt),exchange,generation))
        else:
            values=np.asarray(native_three_temperature_exchange_local_raw(packed,faces,float(dt),exchange))
    else:
        values=np.asarray(native_three_temperature_local_raw(packed,faces,float(dt)))
    names=('rn','rp','du_n','du_p','dl','exchange_n','exchange_p','work_n','work_p',
           'energy_n','energy_p','energy_l')
    result={name:values[k*model.nc:(k+1)*model.nc] for k,name in enumerate(names)}
    offset=12*model.nc+len(model.mesh.faces)
    result['heat']=values[12*model.nc:offset]
    nc=model.nc
    result['intercarrier_exchange_J']=values[offset:offset+nc] if coupled or generated else np.zeros(nc)
    result['generated_pairs']=values[offset+nc:offset+2*nc] if generated else np.zeros(nc)
    result['generation_energy_J']=dict(
        electrons=values[offset+2*nc:offset+3*nc] if generated else np.zeros(nc),
        holes=values[offset+3*nc:offset+4*nc] if generated else np.zeros(nc))
    result['tau']=tau
    return result
