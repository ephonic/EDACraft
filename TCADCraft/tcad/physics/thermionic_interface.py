"""Elastic, equal-mass Maxwell-Boltzmann interface particle and energy moments.

Two independent reservoir temperatures; no degeneracy, inelastic scattering,
DOS/valley mass discontinuity, or bulk heat equation. A common electrostatic
potential is required. A=2 corresponds to Sentaurus Thermionic A/B/C=2/4/1
in the equal-mass case. Fluxes point from owner to neighbor on BOTH sides.
"""
import numpy as np
from tcad.solver.cut_cell_transport import Q,KB

H=6.62607015e-34


def _inputs(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
            mass_kg,area_m2,potential_V,charge_sign,emission_factor):
    names=('n_owner_m3','n_neighbor_m3','T_owner_K','T_neighbor_K','band_owner_J','band_neighbor_J',
        'mass_kg','area_m2','potential_V','charge_sign','emission_factor')
    values=(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,potential_V,charge_sign,emission_factor)
    arrays=[]
    for name,value in zip(names,values):
        raw=np.asarray(value)
        if raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):raise ValueError('finite real '+name+' required')
        arrays.append(raw.astype(float))
    try:arrays=np.broadcast_arrays(*arrays)
    except ValueError:raise ValueError('interface input shapes must broadcast') from None
    for k in (0,1,2,3,6,7):
        if np.any(arrays[k]<=0):raise ValueError('positive '+names[k]+' required')
    if np.any(~np.isin(arrays[9],[-1.,1.])):raise ValueError('charge sign must be -1 or +1')
    if np.any(arrays[10]<0):raise ValueError('nonnegative emission factor required')
    return arrays


def _exp_difference(a,b):
    """Subtract positive rates accurately near equilibrium, including blockage."""
    largest=np.maximum(a,b);active=np.isfinite(largest)
    if np.any(largest[active]>np.log(np.finfo(float).max)-2):raise ValueError('interface rate dynamic range exceeded')
    out=np.zeros_like(largest)
    aa=a[active];bb=b[active];m=largest[active]
    out[active]=np.exp(m)*(-np.expm1(-abs(aa-bb)))*np.where(aa>=bb,1.,-1.)
    return out


def thermionic_interface_flux(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
                              mass_kg,area_m2,*,potential_V=0.,charge_sign=-1,emission_factor=2.):
    """Return number, kinetic/material/electrochemical energy, entropy and heat.

    Positive lattice heat is deposited locally after accounting for the change
    in carrier storage (band+3*kT/2 per particle) at prescribed temperatures.
    The forward/reverse transmitted particles carry 2*kT ABOVE the barrier;
    barrier energy is not replaced by an upwind 3*kT/2 approximation.
    """
    no,nn,To,Tn,bo,bn,m,area,phi,z,A=_inputs(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,
        band_owner_J,band_neighbor_J,mass_kg,area_m2,potential_V,charge_sign,emission_factor)
    high=np.maximum(bo,bn);active=A>0
    logA=np.full_like(A,-np.inf);np.log(A,out=logA,where=active)
    common=np.log(area)+logA+.5*(np.log(KB)-np.log(2*np.pi)-np.log(m))
    lf=common+np.log(no)+.5*np.log(To)-(high-bo)/(KB*To)
    lr=common+np.log(nn)+.5*np.log(Tn)-(high-bn)/(KB*Tn)
    number=_exp_difference(lf,lr)
    # Compute energy rates in log space, avoiding an intermediate rate*T overflow.
    kinetic_high=_exp_difference(lf+np.log(2*KB*To),lr+np.log(2*KB*Tn))
    forward=np.exp(lf);reverse=np.exp(lr)
    kinetic_owner=kinetic_high+(high-bo)*number
    kinetic_neighbor=kinetic_high+(high-bn)*number
    material=high*number+kinetic_high
    total=material+z*Q*phi*number
    heat_owner=(bo-high+1.5*KB*To)*number-kinetic_high
    heat_neighbor=(high-bn-1.5*KB*Tn)*number+kinetic_high
    # Thermodynamic DOS and chemical potentials use the SAME mass and spin=2.
    logNo=np.log(2.)+1.5*(np.log(2*np.pi*KB/H**2)+np.log(m)+np.log(To))
    logNn=np.log(2.)+1.5*(np.log(2*np.pi*KB/H**2)+np.log(m)+np.log(Tn))
    muo=(bo-high)+KB*To*(np.log(no)-logNo)
    mun=(bn-high)+KB*Tn*(np.log(nn)-logNn)
    ld=np.longdouble
    entropy=np.asarray(kinetic_high.astype(ld)*(1/Tn.astype(ld)-1/To.astype(ld))+
        number.astype(ld)*(muo.astype(ld)/To.astype(ld)-mun.astype(ld)/Tn.astype(ld)),float)
    entropy_scale=abs(kinetic_high)*(1/Tn+1/To)+abs(number)*(abs(muo)/To+abs(mun)/Tn)+KB*(forward+reverse)
    if np.any(entropy < -128*np.finfo(float).eps*entropy_scale):raise ValueError('thermionic entropy production became negative')
    result=dict(particle_flux_s=number,forward_particle_rate_s=forward,reverse_particle_rate_s=reverse,
        kinetic_owner_flux_W=kinetic_owner,kinetic_neighbor_flux_W=kinetic_neighbor,
        material_energy_flux_W=material,electrochemical_energy_flux_W=total,
        lattice_heat_owner_W=heat_owner,lattice_heat_neighbor_W=heat_neighbor,entropy_production_W_K=entropy)
    if any(not np.all(np.isfinite(v)) for v in result.values()):raise ValueError('nonfinite thermionic moment')
    return result


def thermionic_interface_ledger(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
                                mass_kg,area_m2,dt_s,*,potential_V=0.,charge_sign=-1,emission_factor=2.):
    """Integrate one frozen interface evaluation; does not advance a device.

    Reservoir densities/temperatures remain prescribed. Reported carrier
    storage changes describe the transferred particles, not a nonlinear state
    update. Electrostatic potential is common and fixed at the interface.
    """
    a=_inputs(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,potential_V,charge_sign,emission_factor)
    raw=np.asarray(dt_s)
    if raw.dtype.kind not in 'fiu' or np.any(~np.isfinite(raw)) or np.any(raw<=0):raise ValueError('positive finite time interval required')
    try:dt=np.broadcast_to(raw,a[0].shape).astype(np.longdouble)
    except ValueError:raise ValueError('time interval must match interface shape') from None
    flux=thermionic_interface_flux(*a[:8],potential_V=a[8],charge_sign=a[9],emission_factor=a[10])
    no,nn,To,Tn,bo,bn,*_=a;ld=np.longdouble
    transfer=dt*flux['particle_flux_s'].astype(ld)
    owner=-transfer*(bo.astype(ld)+ld(1.5)*ld(KB)*To.astype(ld))
    neighbor=transfer*(bn.astype(ld)+ld(1.5)*ld(KB)*Tn.astype(ld))
    qo=dt*flux['lattice_heat_owner_W'].astype(ld);qn=dt*flux['lattice_heat_neighbor_W'].astype(ld)
    # Stable independent carrier-storage difference, rather than subtracting
    # the two possibly very large absolute band-reference contributions.
    carrier=transfer*((bn.astype(ld)-bo.astype(ld))+ld(1.5)*ld(KB)*(Tn.astype(ld)-To.astype(ld)))
    residual=carrier+qo+qn
    values=dict(transferred_particles=np.asarray(transfer,float),carrier_storage_owner_J=np.asarray(owner,float),
        carrier_storage_neighbor_J=np.asarray(neighbor,float),carrier_storage_total_J=np.asarray(carrier,float),
        lattice_heat_owner_J=np.asarray(qo,float),lattice_heat_neighbor_J=np.asarray(qn,float),
        local_energy_residual_J=np.asarray(residual,float),entropy_produced_J_K=np.asarray(dt*flux['entropy_production_W_K'],float))
    if any(not np.all(np.isfinite(v)) for v in values.values()):raise ValueError('nonfinite interface energy ledger')
    return dict(flux=flux,**values,scope='frozen_equal_mass_MB_interface_transfer_calorimetry',
        state_advanced=False,complete_device_energy=False,physical_validated=False)
