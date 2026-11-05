"""Independent adaptive DOS audit of the standalone trap source operator.

No production integrator, native source function, or reported deposit is used
to construct the reference. Net moments are integrated before subtraction.
The tolerance bounds numerical moment agreement, not material-model error.
"""
import math
import numpy as np
from scipy.integrate import quad_vec
from scipy.special import expit,log_expit

KB=1.380649e-23;Q=1.602176634e-19
M0=9.1093837015e-31;H=6.62607015e-34


def reference_trap_capture(state,valleys_n,valleys_p):
    """Independently integrate a supplied state using adaptive infinite tails."""
    f=float(state.occupancy);Nt=float(state.trap_density_m3)
    Tl=float(state.temperature_l_K);Et=float(state.trap_level_J)
    if not 0<f<1 or Tl<=0 or Nt<0:raise ValueError('invalid reference trap state')
    channels=[]
    for holes,valleys in ((False,valleys_n),(True,valleys_p)):
        T=float(state.temperature_p_K if holes else state.temperature_n_K)
        mu=float(state.mu_p_J if holes else state.mu_n_J)
        band=float(state.Eh_J if holes else state.Ec_J)
        coefficient=float(state.capture_p_m3_s if holes else state.capture_n_m3_s)
        if T<=0 or coefficient<0:raise ValueError('invalid reference carrier state')
        cp=f if holes else 1-f;ep=1-f if holes else f
        c=e=uc=ue=net=un=entropy=density=0.
        for v in valleys:
            edge=band+v.band_offset_owner_J;gap=edge+Et if holes else edge-Et
            if gap<0:raise ValueError('reference trap must lie in gap')
            # epsilon = kBT * t^2. The dimensionless integral uses a new
            # adaptive Gauss-Kronrod rule and an actual infinite upper tail.
            pref=2*v.degeneracy*(2*math.pi*v.dos_mass_ratio*M0*KB*T/H**2)**1.5/math.gamma(1.5)
            eta=(mu-edge)/(KB*T)
            def integrand(t):
                x=t*t;z=eta-x
                la=math.log(cp)+log_expit(z)
                lb=math.log(ep)+log_expit(-z)-(gap+KB*T*x)/(KB*Tl)
                a=math.exp(la);b=math.exp(lb)
                d=-a*math.expm1(lb-la) if la>=lb else b*math.expm1(la-lb)
                measure=2*t*t
                return measure*np.array([a,b,x*a,x*b,d,x*d,d*(la-lb),expit(z)])
            points={0.,1.,2.,4.,8.}
            for sign in (-16.,0.,16.):points.add(math.sqrt(max(0.,eta+sign)))
            for x in (1.,4.,16.,64.):points.add(math.sqrt(x*Tl/T))
            points=sorted(points);total=np.zeros(8)
            for a,b in zip(points,points[1:]+[np.inf]):
                part,error=quad_vec(integrand,a,b,epsabs=2e-12,epsrel=2e-12,limit=500)
                if not np.all(np.isfinite(part)):raise ValueError('reference trap integral range')
                total+=part
            factor=pref*Nt*coefficient
            c+=factor*total[0];e+=factor*total[1]
            uc+=factor*(edge*total[0]+KB*T*total[2])
            ue+=factor*(edge*total[1]+KB*T*total[3])
            net+=factor*total[4];un+=factor*(edge*total[4]+KB*T*total[5])
            entropy+=KB*factor*total[6];density+=pref*total[7]
        channels.append((c,e,uc,ue,net,un,entropy,density))
    a,b=channels;trapped=a[4]-b[4];trapenergy=Et*trapped
    return dict(capture_n_m3_s=a[0],emission_n_m3_s=a[1],capture_p_m3_s=b[0],emission_p_m3_s=b[1],
        capture_energy_n_W_m3=a[2],emission_energy_n_W_m3=a[3],
        capture_energy_p_W_m3=b[2],emission_energy_p_W_m3=b[3],
        net_capture_n_m3_s=a[4],net_capture_p_m3_s=b[4],
        electron_number_source_m3_s=-a[4],hole_number_source_m3_s=-b[4],
        occupancy_source_s=trapped/Nt if Nt else 0.,
        electron_energy_source_W_m3=-a[5],hole_energy_source_W_m3=-b[5],
        trap_energy_source_W_m3=trapenergy,lattice_heat_W_m3=a[5]+b[5]-trapenergy,
        trap_charge_source_C_m3_s=-Q*trapped,total_charge_source_C_m3_s=0.,
        total_energy_source_W_m3=0.,entropy_production_W_m3_K=a[6]+b[6],
        density_n_m3=a[7],density_p_m3=b[7])


def audit_spectral_trap_capture(state,valleys_n,valleys_p,report,*,rtol=3e-10):
    """Check every moment and number, charge, energy, entropy identities.

    Net cancellation uses independent gross activity as its absolute scale;
    no relative accuracy is asserted for an exactly vanishing equilibrium net.
    """
    if isinstance(rtol,bool) or not np.isscalar(rtol) or not np.isfinite(rtol) or not 0<rtol<=1e-6:
        raise ValueError('finite moment relative tolerance in (0,1e-6] required')
    ref=reference_trap_capture(state,valleys_n,valleys_p)
    failures=[];fractions={}
    rate=max(*(abs(ref[k]) for k in ('capture_n_m3_s','emission_n_m3_s','capture_p_m3_s','emission_p_m3_s')),1e-300)
    energy=max(*(abs(ref[k]) for k in ('capture_energy_n_W_m3','emission_energy_n_W_m3',
                                      'capture_energy_p_W_m3','emission_energy_p_W_m3')),
               rate*KB*float(state.temperature_l_K),1e-300)
    def number(name):
        value=report.get(name)
        if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isreal(value):return None
        try:value=float(value)
        except (ValueError,TypeError,OverflowError):return None
        return value if math.isfinite(value) else None
    for name,expected in ref.items():
        value=number(name)
        if value is None:failures.append(name);continue
        scale=abs(expected)
        if name.startswith(('net_capture','electron_number','hole_number')):scale=max(scale,rate)
        elif name=='occupancy_source_s':scale=max(scale,rate/max(float(state.trap_density_m3),1e-300))
        elif name.endswith('W_m3'):scale=max(scale,energy)
        elif name.endswith('C_m3_s'):scale=max(scale,Q*rate)
        elif name=='entropy_production_W_m3_K':scale=max(scale,KB*rate)
        fractions[name]=abs(value-expected)/max(scale,1e-300)
        if fractions[name]>rtol:failures.append(name)
    expected_law='constant_capture_coefficient_FD_DOS_local_detailed_balance_v1'
    if report.get('law')!=expected_law:failures.append('law')
    if report.get('device_coupled') is not False:failures.append('device_coupled')
    if report.get('material_calibrated') is not False:failures.append('material_calibrated')
    if not failures:
        # Check exported sources themselves, not only the claimed zero totals.
        charge=Q*(report['hole_number_source_m3_s']-report['electron_number_source_m3_s'])+report['trap_charge_source_C_m3_s']
        power=math.fsum(report[k] for k in ('electron_energy_source_W_m3','hole_energy_source_W_m3',
                                          'trap_energy_source_W_m3','lattice_heat_W_m3'))
        occupied=float(state.trap_density_m3)*report['occupancy_source_s']
        if abs(charge)>3e-15*Q*rate:failures.append('exported_charge_identity')
        if abs(power)>3e-15*energy:failures.append('exported_energy_identity')
        if abs(occupied-report['net_capture_n_m3_s']+report['net_capture_p_m3_s'])>3e-15*rate:
            failures.append('exported_occupancy_identity')
        if report['entropy_production_W_m3_K'] < -1e-14*KB*rate:failures.append('negative_entropy')
    return dict(valid=not failures,failures=failures,maximum_moment_scaled_error=max(fractions.values(),default=0.),
                relative_tolerance=float(rtol),reference=ref,device_coupled=False,physical_validated=False)
