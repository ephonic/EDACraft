"""Independent photon counts and energy for the rounded FD transport view.

Reintegrate the joint DOS with adaptive infinite-tail quadrature. No native
constitutive function or production model source packer is used. This is a
maintained Planck bath, not a transported photon population or a measured
optical spectrum. The signed carrier excess remains authoritative storage.
"""
import numpy as np
from .fermi_spectral_energy import reference_reservoir
from .spectral_radiative import reference_radiative_source, audit_radiative_source
from tcad.physics.spectral_radiative import SpectralRadiativeState, FIELDS, LAW
from tcad.solver.cut_cell_transport import _array


def radiative_increments(model,state,dt,moments=None):
    ld=np.longdouble;nc=model.nc
    pairs=np.zeros(nc,ld);photons=np.zeros(nc,ld);entropy=np.zeros(nc,ld)
    energy=[np.zeros(nc,ld),np.zeros(nc,ld)]
    rate=_array(model.radiative_transition_rate_s,nc,'radiative rate',nonnegative=True)
    bath=_array(model.photon_bath_temperature_K,nc,'photon bath',positive=True)
    if model.radiative_law is None:
        if np.any(rate!=0) or moments is not None:raise ValueError('unconfigured radiative channel')
        return pairs,energy,photons,entropy
    if model.radiative_law!='matched_direct_gap_FD_Planck':raise ValueError('explicit radiative law required')
    valleys=[]
    for label in ('electrons','holes'):
        row=model.valleys[label]
        if len(row)!=1:raise ValueError('one radiative valley per carrier required')
        v=row[0]
        if (v.mass_normal!=v.mass_tangent_1 or v.mass_normal!=v.mass_tangent_2 or
            v.band_offset_owner_J!=0 or v.band_offset_neighbor_J!=0 or
            v.degeneracy!=np.floor(v.degeneracy)):
            raise ValueError('matched isotropic zero-offset radiative valleys required')
        valleys.append(v)
    if valleys[0].degeneracy!=valleys[1].degeneracy or np.any(model.Ec.astype(ld)+model.Eh<=0):
        raise ValueError('matched degeneracy and positive direct gap required')
    if moments is not None and (len(moments)!=nc or any(len(row)!=len(FIELDS) for row in moments)):
        raise ValueError('complete per-cell radiative moment coverage required')
    for i in range(nc):
        mu=[]
        for label,n,T,band in (('electrons',state.n_m3,state.electron_temperature_K,model.Ec),
                               ('holes',state.p_m3,state.hole_temperature_K,model.Eh)):
            mu.append(reference_reservoir(n[i],T[i],band[i],model.valleys[label])['chemical_potential_J'])
        source=SpectralRadiativeState(state.electron_temperature_K[i],state.hole_temperature_K[i],bath[i],
            *mu,model.Ec[i],model.Eh[i],valleys[0].mass_normal,valleys[1].mass_normal,
            valleys[0].degeneracy,rate[i])
        if moments is None:ref=reference_radiative_source(source)
        else:
            report=dict(zip(FIELDS,moments[i]),law=LAW,device_coupled=False,material_calibrated=False)
            checked=audit_radiative_source(source,report)
            if not checked['valid']:raise ValueError('independent radiative moment audit failed: '+str(checked['failures']))
            ref=checked['reference']
        factor=ld(dt)*ld(model.vol[i])
        pairs[i]=factor*ld(ref['net_recombination_rate_m3_s'])
        photons[i]=factor*ld(ref['photon_power_W_m3'])
        entropy[i]=factor*ld(ref['entropy_production_W_m3_K'])
        for s,key in enumerate(('electron_energy_source_W_m3','hole_energy_source_W_m3')):
            energy[s][i]=factor*ld(ref[key])
    if not all(np.all(np.isfinite(v)) for v in (pairs,*energy,photons,entropy)):
        raise ValueError('finite independently reconstructed radiative increments required')
    return pairs,energy,photons,entropy
