"""FD reservoirs and a positive spectral relaxation-time face model.

Diffusion has spectral conductance (area/d)*2*mobility*D0/(3*q)*epsilon^1.5.
This follows D(epsilon)*<v_normal^2>*tau with a parabolic band and
tau=mobility*m_normal/q. The thermionic conductance is proportional to
epsilon above its normal barrier. Three resistances are combined at EACH
energy, so interface trace occupations generally are not Fermi functions.
This is a separate kinetic finite-volume closure, not a Kelvin SG formula.
"""
from functools import lru_cache
import math
import numpy as np
from scipy.special import expit
from .multivalley_thermionic import ThermionicValley,_solve_mu,_fermi,Q,KB,H

M0=9.1093837015e-31


def validate_valleys(valleys):
    values=tuple(valleys)
    if not values or not all(isinstance(v,ThermionicValley) for v in values):
        raise ValueError('nonempty ThermionicValley sequence required')
    if len({v.name for v in values})!=len(values):raise ValueError('unique valley names required')
    if any(v.band_offset_owner_J!=v.band_offset_neighbor_J for v in values):
        raise ValueError('spectral bulk requires the same valley offset on both sides')
    return values


def valley_dos(T,valleys):
    return np.array([2*v.degeneracy*(2*np.pi*v.dos_mass_ratio*M0*KB*T/H**2)**1.5 for v in valleys])


def fermi_reservoir(density_m3,temperature_K,band_J,valleys):
    """FD density, chemical potential and material internal energy density."""
    for value in (density_m3,temperature_K,band_J):
        if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isreal(value) or not np.isfinite(value):
            raise ValueError('finite real reservoir scalars required')
    if density_m3<=0 or temperature_K<=0:raise ValueError('positive density and temperature required')
    valleys=validate_valleys(valleys)
    edges=np.array([band_J+v.band_offset_owner_J for v in valleys])
    mu,pref=_solve_mu(density_m3,temperature_K,valleys,edges)
    populations=[];energy=[]
    for edge,c in zip(edges,pref):
        eta=float((mu-edge)/(KB*temperature_K))
        n=c*_fermi(.5,eta)
        populations.append(n)
        energy.append(edge*n+1.5*KB*temperature_K*c*_fermi(1.5,eta))
    return dict(chemical_potential_J=mu,energy_density_J_m3=math.fsum(energy),
        density_m3=math.fsum(populations),valley_densities_m3=np.array(populations),
        temperature_K=float(temperature_K),band_J=float(band_J))


@lru_cache(maxsize=1)
def _nodes():return np.polynomial.legendre.leggauss(96)


def spectral_face(owner,neighbor,valleys,*,potential_owner_V,potential_neighbor_V,
        potential_face_V,charge_sign,mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,
        area_m2,distance_owner_m,distance_neighbor_m,emission_factor=None,
        bulk_potential_path='endpoint_barrier'):
    """Integrate particle, material-energy and entropy fluxes, owner to neighbor.

    emission_factor=None selects a bulk diffusion edge. A nonnegative value
    selects two diffusive half cells and an elastic thermionic barrier in
    series. Both moments use the same nonthermal spectral trace occupations.
    """
    valleys=validate_valleys(valleys)
    if bulk_potential_path not in ('endpoint_barrier','linear_series'):
        raise ValueError('bulk_potential_path must be endpoint_barrier or linear_series')
    values=(potential_owner_V,potential_neighbor_V,potential_face_V,
        mobility_owner_m2_Vs,mobility_neighbor_m2_Vs,area_m2,distance_owner_m,distance_neighbor_m)
    if any(not np.isscalar(v) or not np.isreal(v) or not np.isfinite(v) for v in values):
        raise ValueError('finite real spectral geometry and transport inputs required')
    if charge_sign not in (-1,1) or min(values[3:7])<=0 or distance_neighbor_m<0:
        raise ValueError('positive face metric and mobility required')
    if emission_factor is not None and (not np.isscalar(emission_factor) or not np.isreal(emission_factor)
            or not np.isfinite(emission_factor) or emission_factor<0):
        raise ValueError('nonnegative finite emission factor required')
    if emission_factor is not None and distance_neighbor_m<=0:
        raise ValueError('positive neighbor half distance required at an interface')
    To,Tn=owner['temperature_K'],neighbor['temperature_K']
    muo=owner['chemical_potential_J']+charge_sign*Q*potential_owner_V
    mun=neighbor['chemical_potential_J']+charge_sign*Q*potential_neighbor_V
    bo=owner['band_J']+charge_sign*Q*potential_owner_V
    bn=neighbor['band_J']+charge_sign*Q*potential_neighbor_V
    bfo=owner['band_J']+charge_sign*Q*potential_face_V
    bfn=neighbor['band_J']+charge_sign*Q*potential_face_V
    nodes,weights=_nodes();scale=KB*max(To,Tn)
    particles=[];energies=[];entropies=[];records=[];trace_min=1.;trace_max=0.
    for valley in valleys:
        offset=valley.band_offset_owner_J
        uo,un,fo,fn=(v+offset for v in (bo,bn,bfo,bfn))
        high=max(uo,un) if emission_factor is None else max(uo,un,fo,fn)
        eta_o=(muo-high)/scale;eta_n=(mun-high)/scale
        upper=max(60.,eta_o+60.,eta_n+60.)
        breaks=sorted({0.,upper,*[min(upper,max(0.,v)) for eta in (eta_o,eta_n) for v in (eta-16,eta+16)]})
        if emission_factor is None and bulk_potential_path=='linear_series':
            breaks=sorted(set(breaks)|{min(upper,abs(un-uo)/scale)})
        # D(epsilon)=D0*sqrt(epsilon), including spin and valley degeneracy.
        dos300=valley_dos(300.,(valley,))[0]
        D0=dos300/((KB*300.)**1.5*math.gamma(1.5))
        particle=energy=entropy=0.
        for lower,limit in zip(breaks,breaks[1:]):
            a,b=math.sqrt(lower),math.sqrt(limit)
            t=a+.5*(b-a)*(nodes+1)
            E=high+scale*t*t;measure=scale*(b-a)*t*weights
            left=expit((muo-E)/(KB*To));right=expit((mun-E)/(KB*Tn))
            trace_min=min(trace_min,float(min(min(left),min(right))))
            trace_max=max(trace_max,float(max(max(left),max(right))))
            if emission_factor is None:
                if bulk_potential_path=='endpoint_barrier':
                    resistance=distance_owner_m/mobility_owner_m2_Vs+distance_neighbor_m/mobility_neighbor_m2_Vs
                    g=area_m2/resistance*2/(3*Q)*D0*(E-high)**1.5
                else:
                    middle=uo+(un-uo)*distance_owner_m/(distance_owner_m+distance_neighbor_m)
                    def mean(a,b):
                        x=np.sqrt(a);y=np.sqrt(b)
                        return x*y*(x+y)/2
                    resistance=distance_owner_m/mobility_owner_m2_Vs/mean(E-uo,E-middle)
                    if distance_neighbor_m>0:
                        resistance+=distance_neighbor_m/mobility_neighbor_m2_Vs/mean(E-middle,E-un)
                    g=area_m2*2/(3*Q)*D0/resistance
            elif emission_factor==0:
                g=np.zeros_like(E)
            else:
                go=area_m2/distance_owner_m*2*mobility_owner_m2_Vs/(3*Q)*D0*(E-max(uo,fo))**1.5
                gn=area_m2/distance_neighbor_m*2*mobility_neighbor_m2_Vs/(3*Q)*D0*(E-max(un,fn))**1.5
                gt=(emission_factor*area_m2*dos300*math.sqrt(KB*300./(2*np.pi*valley.mass_normal*M0))
                    /(KB*300.)**2*(E-max(fo,fn)))
                g=1/(1/go+1/gt+1/gn)
                occupation_o=left-g*(left-right)/go
                occupation_n=right+g*(left-right)/gn
                trace_min=min(trace_min,float(min(min(occupation_o),min(occupation_n))))
                trace_max=max(trace_max,float(max(max(occupation_o),max(occupation_n))))
            flow=measure*g*(left-right)
            particle+=float(np.sum(flow,dtype=np.longdouble))
            energy+=float(np.sum(flow*E,dtype=np.longdouble))
            affinity=(muo-E)/To-(mun-E)/Tn
            entropy+=float(np.sum(flow*affinity,dtype=np.longdouble))
        particles.append(particle);energies.append(energy);entropies.append(entropy)
        records.append(dict(name=valley.name,particle_flux_s=particle,total_energy_flux_W=energy))
    number=math.fsum(particles);total=math.fsum(energies)
    result=dict(particle_flux_s=number,total_energy_flux_W=total,
        material_energy_flux_W=total-charge_sign*Q*potential_face_V*number,
        entropy_production_W_K=math.fsum(entropies),valley_moments=records,
        trace_occupation_min=trace_min,trace_occupation_max=trace_max,
        trace_closure='energy_resolved_nonthermal_occupations',statistics='fermi_dirac')
    if not all(np.isfinite(result[k]) for k in ('particle_flux_s','total_energy_flux_W','material_energy_flux_W','entropy_production_W_K')):
        raise ValueError('spectral moment dynamic range exceeded')
    return result
