"""Independent infinite-tail adaptive joint-DOS reference and source audit.

The reference never imports the native integrator or production field list.
Tolerances concern numerical agreement for the declared rate law, not accuracy
of a fitted optical spectrum or measured device temperatures.
"""
import math
import numpy as np
from scipy.integrate import quad_vec
from scipy.special import log_expit
KB=1.380649e-23;Q=1.602176634e-19;M0=9.1093837015e-31;H=6.62607015e-34


def reference_radiative_source(state):
    Tn,Tp,Tg,mun,mup,Ec,Eh,mn,mp,g,rate=(float(getattr(state,n)) for n in state.__dataclass_fields__)
    if min(Tn,Tp,Tg,mn,mp,g,Ec+Eh)<=0 or g!=math.floor(g) or rate<0:
        raise ValueError('invalid radiative reference state')
    an=mp/(mn+mp);ap=mn/(mn+mp);mr=mn*mp/(mn+mp)
    # x=kB*Teff*t^2, with the dilute spontaneous kinetic temperature.
    effective=1/(an/Tn+ap/Tp);thermal=KB*effective
    pref=2*g*(2*math.pi*mr*M0*thermal/H**2)**1.5/math.gamma(1.5)*rate
    def integrand(t):
        x=t*t;en=Ec+an*thermal*x;ep=Eh+ap*thermal*x
        zn=(mun-en)/(KB*Tn);zp=(mup-ep)/(KB*Tp);y=(Ec+Eh+thermal*x)/(KB*Tg)
        log1N=-math.log(-math.expm1(-y));logN=-y+log1N
        sp=log_expit(zn)+log_expit(zp);la=sp+log1N
        lb=log_expit(-zn)+log_expit(-zp)+logN
        a=math.exp(la);b=math.exp(lb)
        d=-a*math.expm1(lb-la) if la>=lb else b*math.expm1(la-lb)
        # Dimensionless kinetic moments avoid mixing tiny joules with rates
        # in adaptive quadrature error control. Net is integrated directly.
        return 2*t*t*np.array([math.exp(sp),math.exp(sp+logN),b,
                              x*a,x*b,d,x*d,d*(la-lb)])
    points={0.,1.,2.,4.,8.}
    for temperature in (Tn/an,Tp/ap,Tg):
        for k in (1,4,16,64,80):points.add(math.sqrt(k*temperature/effective))
    for edge,mu,T,alpha in ((Ec,mun,Tn,an),(Eh,mup,Tp,ap)):
        for k in (-64,-16,0,16,64):points.add(math.sqrt(max(0.,(mu-edge+k*KB*T)/alpha/thermal)))
    points=sorted(points);total=np.zeros(8)
    for a,b in zip(points,points[1:]+[np.inf]):
        part,error=quad_vec(integrand,a,b,epsabs=2e-12,epsrel=2e-12,limit=500)
        if not np.all(np.isfinite(part)):raise ValueError('radiative reference integral range')
        total+=part
    sp,st,ab,ke,ka,net,kn,entropy=pref*total;em=sp+st
    jn=Ec*net+an*thermal*kn;jp=Eh*net+ap*thermal*kn
    return dict(spontaneous_rate_m3_s=sp,stimulated_rate_m3_s=st,absorption_rate_m3_s=ab,
        emission_rate_m3_s=em,net_recombination_rate_m3_s=net,
        emission_energy_n_W_m3=Ec*em+an*thermal*ke,
        emission_energy_p_W_m3=Eh*em+ap*thermal*ke,
        absorption_energy_n_W_m3=Ec*ab+an*thermal*ka,
        absorption_energy_p_W_m3=Eh*ab+ap*thermal*ka,
        electron_number_source_m3_s=-net,hole_number_source_m3_s=-net,photon_number_source_m3_s=net,
        electron_energy_source_W_m3=-jn,hole_energy_source_W_m3=-jp,photon_power_W_m3=jn+jp,
        lattice_heat_W_m3=0.,total_charge_source_C_m3_s=0.,total_energy_source_W_m3=0.,
        entropy_production_W_m3_K=KB*entropy)


def audit_radiative_source(state,report,*,rtol=3e-10):
    if isinstance(rtol,(bool,np.bool_)) or not np.isscalar(rtol) or not np.isreal(rtol) or not np.isfinite(rtol) or not 0<rtol<=1e-6:
        raise ValueError('finite relative moment tolerance in (0,1e-6] required')
    ref=reference_radiative_source(state);failures=[];errors={};values={}
    rate=max(ref['emission_rate_m3_s'],ref['absorption_rate_m3_s'],1e-300)
    energy=max(*(abs(ref[k]) for k in ('emission_energy_n_W_m3','emission_energy_p_W_m3',
        'absorption_energy_n_W_m3','absorption_energy_p_W_m3')),rate*KB*float(state.temperature_photon_K),1e-300)
    for name,expected in ref.items():
        value=report.get(name)
        if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isreal(value):
            failures.append(name);continue
        try:value=float(value)
        except (ValueError,TypeError,OverflowError):failures.append(name);continue
        if not math.isfinite(value):failures.append(name);continue
        values[name]=value;scale=abs(expected)
        if name.endswith('W_m3'):scale=max(scale,energy)
        elif name.endswith('C_m3_s'):scale=max(scale,Q*rate)
        elif name.endswith('W_m3_K'):scale=max(scale,KB*rate)
        elif name.startswith(('net_','electron_number','hole_number','photon_number')):scale=max(scale,rate)
        errors[name]=abs(value-expected)/max(scale,1e-300)
        if errors[name]>rtol:failures.append(name)
    if report.get('law')!='matched_direct_gap_constant_state_rate_FD_Planck_v1':failures.append('law')
    if report.get('device_coupled') is not False:failures.append('device_coupled')
    if report.get('material_calibrated') is not False:failures.append('material_calibrated')
    if not failures:
        def identity(name,value,scale):
            if abs(value)>3e-15*scale:failures.append(name)
        r=values
        identity('emission_identity',r['emission_rate_m3_s']-r['spontaneous_rate_m3_s']-r['stimulated_rate_m3_s'],rate)
        identity('particle_identity',r['electron_number_source_m3_s']+r['photon_number_source_m3_s'],rate)
        identity('charge_identity',Q*(r['hole_number_source_m3_s']-r['electron_number_source_m3_s']),Q*rate)
        identity('energy_identity',math.fsum(r[k] for k in ('electron_energy_source_W_m3',
                 'hole_energy_source_W_m3','photon_power_W_m3','lattice_heat_W_m3')),energy)
        sigma=math.fsum(((r['electron_energy_source_W_m3']-float(state.mu_n_J)*r['electron_number_source_m3_s'])/float(state.temperature_n_K),
            (r['hole_energy_source_W_m3']-float(state.mu_p_J)*r['hole_number_source_m3_s'])/float(state.temperature_p_K),
            r['photon_power_W_m3']/float(state.temperature_photon_K)))
        identity('thermodynamic_entropy',sigma-r['entropy_production_W_m3_K'],max(abs(sigma),abs(r['entropy_production_W_m3_K']),KB*rate))
        if r['entropy_production_W_m3_K'] < -1e-14*KB*rate:failures.append('negative_entropy')
    return dict(valid=not failures,failures=failures,maximum_moment_scaled_error=max(errors.values(),default=0.),
                reference=ref,relative_tolerance=float(rtol),device_coupled=False,physical_validated=False)
