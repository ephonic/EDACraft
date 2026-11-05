"""Independent adaptive-quadrature audit of matched-valley reservoir moments."""
import math
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import expit

from tcad.physics.multivalley_thermionic import ThermionicValley


def audit_multivalley_interface(report, no, nn, To, Tn, bo, bn, valleys, area, *,
        potential_V=0., charge_sign=-1, emission_factor=2., statistics='fermi_dirac',
        particle_flux_atol_s, energy_flux_atol_W, entropy_atol_W_K):
    """Integrate occupied energy states without calling the production kernel.

    Reservoir density uses the 3-D DOS; transmission integrates the normal
    threshold and transverse kinetic states. Budgets have explicit SI units.
    This checks frozen reservoirs, not a degenerate bulk device model.
    """
    budgets=(particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K)
    if any(not np.isscalar(b) or not np.isreal(b) or not np.isfinite(b) or b<=0 for b in budgets):
        raise ValueError('finite positive moment budgets required')
    scalars=(no,nn,To,Tn,bo,bn,area,potential_V,emission_factor)
    if any(isinstance(v,(bool,np.bool_)) or not np.isscalar(v) or not np.isreal(v) or not np.isfinite(v) for v in scalars):
        raise ValueError('finite real reservoir scalars required')
    if min(no,nn,To,Tn,area)<=0 or emission_factor<0 or charge_sign not in (-1,1):
        raise ValueError('invalid reservoir domain')
    valleys=tuple(valleys)
    if not valleys or not all(isinstance(v,ThermionicValley) for v in valleys):
        raise ValueError('valley definitions required')
    if statistics not in ('boltzmann','fermi_dirac'):
        raise ValueError('invalid statistics')
    k=1.380649e-23; h=6.62607015e-34; m0=9.1093837015e-31; q=1.602176634e-19

    def integral(order,eta):
        # A separate adaptive integral; x=t^2 regularizes the DOS endpoint.
        limit=math.sqrt(max(60.,eta+60.))
        return quad(lambda t:2*t**(2*order+1)*expit(eta-t*t),0.,limit,
                    epsabs=1e-13,epsrel=5e-14,limit=250)[0]

    def reservoir(density,T,band,side):
        edges=np.array([band+getattr(v,'band_offset_'+side+'_J') for v in valleys])
        dos=np.array([2*v.degeneracy*(2*math.pi*v.dos_mass_ratio*m0*k*T/h**2)**1.5 for v in valleys])
        origin=min(edges);offsets=(edges-origin)/(k*T)
        if statistics=='boltzmann':
            reduced=math.log(density/sum(dos*np.exp(-offsets)))
            populations=dos*np.exp(reduced-offsets)
            energy=populations*(edges+1.5*k*T)
        else:
            def residual(eta):
                return sum(c*2/math.sqrt(math.pi)*integral(.5,eta-d) for c,d in zip(dos,offsets))/density-1
            upper=max(2.,max(offsets)+2.)
            while residual(upper)<0: upper*=2
            reduced=brentq(residual,-750.,upper,xtol=1e-14,rtol=1e-15)
            populations=np.array([c*2/math.sqrt(math.pi)*integral(.5,reduced-d) for c,d in zip(dos,offsets)])
            energy=populations*edges+np.array([c*2/math.sqrt(math.pi)*k*T*integral(1.5,reduced-d) for c,d in zip(dos,offsets)])
        return origin+k*T*reduced,edges,dos,float(sum(energy)/density)

    muo,eo,co,uo=reservoir(no,To,bo,'owner')
    mun,en,cn,un=reservoir(nn,Tn,bn,'neighbor')
    fr=[];rr=[];ko=[];kn=[];material=[]
    for v,a,b,c,d in zip(valleys,eo,en,co,cn):
        high=max(a,b)
        eta_o=(muo-high)/(k*To);eta_n=(mun-high)/(k*Tn)
        rate=[];excess=[]
        for eta,T,dos in ((eta_o,To,c),(eta_n,Tn,d)):
            scale=emission_factor*area*dos*math.sqrt(k*T/(2*math.pi*v.mass_normal*m0))
            # The triangular normal/transverse energy domain has measure x.
            rate.append(scale*(math.exp(eta) if statistics=='boltzmann' else integral(1.,eta)))
            excess.append(scale*k*T*(2*math.exp(eta) if statistics=='boltzmann' else integral(2.,eta)))
        particle=rate[0]-rate[1];ex=excess[0]-excess[1]
        fr.append(rate[0]);rr.append(rate[1]);ko.append((high-a)*particle+ex)
        kn.append((high-b)*particle+ex);material.append(high*particle+ex)
    forward=math.fsum(fr);reverse=math.fsum(rr);number=forward-reverse;energy=math.fsum(material)
    expected=dict(particle_flux_s=number,forward_particle_rate_s=forward,reverse_particle_rate_s=reverse,
        kinetic_owner_flux_W=math.fsum(ko),kinetic_neighbor_flux_W=math.fsum(kn),material_energy_flux_W=energy,
        electrochemical_energy_flux_W=energy+charge_sign*q*potential_V*number,
        lattice_heat_owner_W=uo*number-energy,lattice_heat_neighbor_W=energy-un*number,
        entropy_production_W_K=(energy-mun*number)/Tn-(energy-muo*number)/To)
    errors={};valid=True
    for name,target in expected.items():
        given=report[name]
        if not np.isscalar(given) or not np.isreal(given) or not np.isfinite(given):
            raise ValueError('finite scalar reported '+name+' required')
        errors[name]=abs(float(given)-target)
        budget=budgets[0] if name.endswith('_s') else budgets[2] if name.endswith('_W_K') else budgets[1]
        valid=valid and errors[name]<=budget
    valid=valid and expected['entropy_production_W_K']>=-entropy_atol_W_K
    valid=valid and report.get('statistics')==statistics and report.get('valley_count')==len(valleys)
    valid=valid and report.get('complete_device_energy') is False and report.get('physical_validated') is False
    return dict(valid=bool(valid),max_errors=errors,expected=expected,
        scope='independent_matched_valley_reservoir_quadrature',complete_device_energy=False)
