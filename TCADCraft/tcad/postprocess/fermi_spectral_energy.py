"""Independent FD DOS, spectral flux and local device energy reconstruction."""
import math
import numpy as np
from scipy.integrate import quad,quad_vec
from scipy.optimize import brentq
from scipy.special import expit
from tcad.solver.cut_cell_transport import Q,KB,_array

H=6.62607015e-34;M0=9.1093837015e-31


def reference_reservoir(n,T,band,valleys):
    """Adaptive DOS integration, independent of production Fermi integrals."""
    edges=np.array([band+v.band_offset_owner_J for v in valleys])
    pref=np.array([2*v.degeneracy*(2*np.pi*v.dos_mass_ratio*M0*KB*T/H**2)**1.5 for v in valleys])
    origin=min(edges);offset=(edges-origin)/(KB*T)
    def integral(order,eta):
        return quad(lambda t:2*t**(2*order+1)*expit(eta-t*t),0.,math.sqrt(max(60.,eta+60.)),
            epsabs=1e-13,epsrel=5e-14,limit=250)[0]
    def residual(eta):
        return sum(c*2/math.sqrt(math.pi)*integral(.5,eta-d) for c,d in zip(pref,offset))/n-1.
    hi=max(2.,max(offset)+2.)
    for _ in range(64):
        if residual(hi)>=0:break
        hi*=2
    else:raise ValueError('reference chemical potential outside supported range')
    eta=brentq(residual,-750.,hi,xtol=1e-14,rtol=1e-15)
    populations=[c*2/math.sqrt(math.pi)*integral(.5,eta-d) for c,d in zip(pref,offset)]
    energy=math.fsum(edge*population+c*2/math.sqrt(math.pi)*KB*T*integral(1.5,eta-d)
        for edge,population,c,d in zip(edges,populations,pref,offset))
    return dict(chemical_potential_J=origin+KB*T*eta,energy_density_J_m3=energy,
        density_m3=math.fsum(populations),temperature_K=T,band_J=band)


def reference_face(owner,neighbor,valleys,*,phi_o,phi_n,phi_f,z,mu_o,mu_n,area,do,dn,A=None,
                   bulk_potential_path='endpoint_barrier'):
    """Adaptive integration of three physical spectral resistances in series."""
    To,Tn=owner['temperature_K'],neighbor['temperature_K'];scale=KB*max(To,Tn)
    chemical_o=owner['chemical_potential_J']+z*Q*phi_o
    chemical_n=neighbor['chemical_potential_J']+z*Q*phi_n
    result=np.zeros(3);valley_moments=[]
    for v in valleys:
        bo=owner['band_J']+v.band_offset_owner_J
        bn=neighbor['band_J']+v.band_offset_owner_J
        uo,un,fo,fn=bo+z*Q*phi_o,bn+z*Q*phi_n,bo+z*Q*phi_f,bn+z*Q*phi_f
        high=max(uo,un) if A is None else max(uo,un,fo,fn)
        dos=2*v.degeneracy*(2*np.pi*v.dos_mass_ratio*M0*KB*300/H**2)**1.5
        D0=dos/((KB*300)**1.5*math.gamma(1.5))
        def conductance(E):
            if A is None:
                if bulk_potential_path=='endpoint_barrier':return area/(do/mu_o+dn/mu_n)*2/(3*Q)*D0*(E-high)**1.5
                if bulk_potential_path!='linear_series':raise ValueError('invalid reference bulk path')
                midpoint=(dn*uo+do*un)/(do+dn)
                def integral(length,mu,a,b):
                    return 2*length/(mu*math.sqrt(E-a)*math.sqrt(E-b)*(math.sqrt(E-a)+math.sqrt(E-b)))
                resistance=integral(do,mu_o,uo,midpoint)
                if dn:resistance+=integral(dn,mu_n,midpoint,un)
                return area*2/(3*Q)*D0/resistance
            if A==0:return 0.
            one=area/do*2*mu_o/(3*Q)*D0*max(0.,E-max(uo,fo))**1.5
            two=area/dn*2*mu_n/(3*Q)*D0*max(0.,E-max(un,fn))**1.5
            interface=A*area*dos*math.sqrt(KB*300/(2*np.pi*v.mass_normal*M0))/(KB*300)**2*max(0.,E-max(fo,fn))
            return 1/(1/one+1/two+1/interface) if min(one,two,interface)>0 else 0.
        normalizer=conductance(high+scale)
        if normalizer==0:
            valley_moments.append(dict(name=v.name,particle_flux_s=0.,total_energy_flux_W=0.))
            continue
        upper=max(60.,(chemical_o-high)/scale+60.,(chemical_n-high)/scale+60.)
        # Keep the adaptive absolute norm meaningful for weak occupations.
        # Preserve the original path's arithmetic for historical raw replays.
        population_scale=(max(float(expit((chemical_o-high)/(KB*To))),
            float(expit((chemical_n-high)/(KB*Tn))),np.finfo(float).tiny)
            if A is None and bulk_potential_path=='linear_series' else 1.)
        def integrand(t):
            E=high+scale*t*t
            ao=(chemical_o-E)/(KB*To);an=(chemical_n-E)/(KB*Tn)
            flow=2*t*conductance(E)/normalizer*(expit(ao)-expit(an))/population_scale
            return flow*np.array([1.,t*t,ao-an])
        value=quad_vec(integrand,0.,math.sqrt(upper),epsabs=1e-12,epsrel=5e-13,limit=1000)[0]
        rate=normalizer*scale*population_scale*value[0]
        total=high*rate+normalizer*scale**2*population_scale*value[1]
        result+=np.array([rate,total,KB*normalizer*scale*population_scale*value[2]])
        valley_moments.append(dict(name=v.name,particle_flux_s=rate,total_energy_flux_W=total))
    return dict(particle_flux_s=result[0],total_energy_flux_W=result[1],
        material_energy_flux_W=result[1]-z*Q*phi_f*result[0],entropy_production_W_K=result[2],valley_moments=valley_moments)


def audit_fermi_spectral_energy(model,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J,
        particle_flux_atol_s=1e4,energy_flux_atol_W=1e-17,entropy_atol_W_K=1e-19):
    """Reconstruct FD storage, constitutive fluxes and each local energy row.

    Calls neither production reservoir/face kernels nor model.energies,
    model.face_transport or model._poisson. Electrostatics is reconstructed
    with the Python HMM assembly/solve, independently of native Poisson.
    """
    from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal
    if not isinstance(model,FermiSpectralElectrothermal):raise ValueError('FD spectral device required')
    for value in (charge_atol_C,particle_atol,energy_atol_J,particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K):
        _array(value,1,'audit budget',positive=True)
    model._validate_state(old);model._validate_state(new);dt=new.time_s-old.time_s
    if not np.isfinite(dt) or dt<=0:raise ValueError('increasing physical time required')
    if not np.array_equal(new.trap_fraction,old.trap_fraction):raise ValueError('unmodeled trap state changed')
    nc=model.nc;nf=len(model.mesh.faces);ld=np.longdouble
    from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
    electrostatic=lambda state:solve_cut_cell_poisson(model.mesh,model.eps,
        model.rhofix+Q*(state.p_m3-state.n_m3-model.Nt*state.trap_fraction),
        dirichlet_V=model.bc,charge_atol_C=charge_atol_C)
    a=electrostatic(old);b=electrostatic(new)
    u=[];states=[]
    for state in (old,new):
        r={label:[reference_reservoir(density[c],state.temperature_K[c],band[c],model.valleys[label]) for c in range(nc)]
            for label,density,band in (('electrons',state.n_m3,model.Ec),('holes',state.p_m3,model.Eh))}
        states.append(r);u.append(np.array([r['electrons'][c]['energy_density_J_m3']+r['holes'][c]['energy_density_J_m3'] for c in range(nc)]))
    given_n=_array(report['integrated_electron_particle_flux_s'],nf,'electron flux')
    given_p=_array(report['integrated_hole_particle_flux_s'],nf,'hole flux')
    given_e=_array(report['integrated_carrier_energy_flux_W'],nf,'material energy flux')
    given_h=_array(report['integrated_heat_flux_W'],nf,'heat flux')
    expected_e=np.zeros(nf);expected_h=np.zeros(nf);flux_errors=[];moment_energy_errors=[];moment_particle_errors=[]
    entropy_errors=[];min_entropy=float('inf');occupation_valid=True;coverage=True
    for label,density,band,base,exponent,z,given in (
            ('electrons',new.n_m3,model.Ec,model.mn,model.mn_exponent,-1,given_n),
            ('holes',new.p_m3,model.Eh,model.mp,model.mp_exponent,1,given_p)):
        expected=np.zeros(nf);wanted=set(map(int,model.internal))|set(map(int,model.contact_faces))
        rows=report['face_moments'][label];coverage=coverage and set(rows)==wanted
        for f in wanted:
            face=model.mesh.faces[f];i,j=face.owner,face.neighbor
            area=np.linalg.norm(face.area_vector_m2);normal=face.area_vector_m2/area
            do=(face.centroid_m-model.mesh.centroids_m[i])@normal
            if j>=0:
                two=states[1][label][j];phi_n=b['cell_potential_V'][j]
                dn=(model.mesh.centroids_m[j]-face.centroid_m)@normal
                mobility=base[j]*(model.T/new.temperature_K[j])**exponent
            else:
                contact=model.contacts[f];value=contact.n_m3 if label=='electrons' else contact.p_m3
                two=reference_reservoir(value,contact.temperature_K,band[i],model.valleys[label])
                phi_n=model.bc[f];dn=0.;mobility=base[i]*(model.T/contact.temperature_K)**exponent
            target=reference_face(states[1][label][i],two,model.valleys[label],phi_o=b['cell_potential_V'][i],
                phi_n=phi_n,phi_f=b['face_potential_V'][f],z=z,
                mu_o=base[i]*(model.T/new.temperature_K[i])**exponent,mu_n=mobility,
                area=area,do=do,dn=dn,A=model.emission[label].get(f))
            expected[f]=target['particle_flux_s'];expected_e[f]+=target['material_energy_flux_W']
            min_entropy=min(min_entropy,target['entropy_production_W_K'])
            row=rows[f]
            if len(row['valley_moments'])!=len(target['valley_moments']):raise ValueError('valley moment coverage mismatch')
            for given_valley,expected_valley in zip(row['valley_moments'],target['valley_moments']):
                coverage=coverage and given_valley['name']==expected_valley['name']
                moment_particle_errors.append(float(given_valley['particle_flux_s'])-expected_valley['particle_flux_s'])
                moment_energy_errors.append(float(given_valley['total_energy_flux_W'])-expected_valley['total_energy_flux_W'])
            for key in ('total_energy_flux_W','material_energy_flux_W'):
                moment_energy_errors.append(float(row[key])-target[key])
            moment_particle_errors.append(float(row['particle_flux_s'])-target['particle_flux_s'])
            entropy_errors.append(float(row['entropy_production_W_K'])-target['entropy_production_W_K'])
            occupation_valid=occupation_valid and (0<=float(row['trace_occupation_min'])<=float(row['trace_occupation_max'])<=1)
            occupation_valid=occupation_valid and row.get('trace_closure')=='energy_resolved_nonthermal_occupations'
            occupation_valid=occupation_valid and row.get('statistics')=='fermi_dirac'
            occupation_valid=occupation_valid and row.get('execution_backend')==model.spectral_backend
        flux_errors.extend(expected-given)
    # Independent Fourier flux from actual geometry, not model.conduction.
    for f,face in enumerate(model.mesh.faces):
        i,j=face.owner,face.neighbor;area=np.linalg.norm(face.area_vector_m2);normal=face.area_vector_m2/area
        if j>=0:
            distance=(model.mesh.centroids_m[j]-model.mesh.centroids_m[i])@normal
            expected_h[f]=2/(1/model.conductivity[i]+1/model.conductivity[j])*area/distance*(new.temperature_K[i]-new.temperature_K[j])
        elif f in model.bath:
            distance=(face.centroid_m-model.mesh.centroids_m[i])@normal
            expected_h[f]=model.conductivity[i]*area/distance*(new.temperature_K[i]-model.bath[f])
    vol=model.vol;delta_u=vol.astype(ld)*(u[1].astype(ld)-u[0].astype(ld))
    delta_t=vol.astype(ld)*model.capacity*(new.temperature_K.astype(ld)-old.temperature_K)
    qflux=Q*(given_p-given_n);midphi=(a['cell_potential_V']+b['cell_potential_V'])/2
    midface=(a['face_potential_V']+b['face_potential_V'])/2
    work=dt*(midphi*model.mesh.divergence_integrals(qflux)-model.mesh.divergence_integrals(midface*qflux))
    local=np.asarray(delta_u+delta_t+dt*model.mesh.divergence_integrals(given_e+given_h)-work,float)
    particles=np.r_[vol*(new.n_m3-old.n_m3)+dt*model.mesh.divergence_integrals(given_n),
        vol*(new.p_m3-old.p_m3)+dt*model.mesh.divergence_integrals(given_p)]
    boundary=np.array([f for f,face in enumerate(model.mesh.faces) if face.neighbor<0],int)
    dq=b['integrated_D_flux_C']-a['integrated_D_flux_C']
    terminals={f:float(-dq[f]/dt-qflux[f]) for f in model.bc}
    if set(report['terminal_currents_A'])!=set(terminals):raise ValueError('terminal coverage mismatch')
    current_errors=[dt*(float(report['terminal_currents_A'][f])-value) for f,value in terminals.items()]
    displacement=-sum(v*dq[f] for f,v in model.bc.items())
    conduction=-dt*sum(v*qflux[f] for f,v in model.bc.items());source=displacement+conduction
    charge=float(Q*np.sum(vol.astype(ld)*(new.p_m3.astype(ld)-old.p_m3-new.n_m3.astype(ld)+old.n_m3))+
        dt*np.sum(qflux[boundary],dtype=ld))
    current_errors.append(float(report['charge_balance_residual_C'])-charge)
    increments=dict(carrier_J=float(sum(delta_u)),thermal_J=float(sum(delta_t)),
        electrostatic_J=float(ld(b['electrostatic_energy_J'])-ld(a['electrostatic_energy_J'])))
    carrier_out=dt*float(np.sum(given_e[boundary],dtype=ld));heat_out=dt*float(np.sum(given_h[boundary],dtype=ld))
    residual=float(ld(source)-sum(map(ld,increments.values()))-ld(carrier_out)-ld(heat_out))
    errors=[float(report['energy_increments_J'][key])-value for key,value in increments.items()]
    for state_index,name in ((0,'energy_before_J'),(1,'energy_after_J')):
        state=(old,new)[state_index];poisson=(a,b)[state_index]
        expected=dict(carrier_J=float(np.sum(vol.astype(ld)*u[state_index])),
            thermal_J=float(np.sum(vol.astype(ld)*model.capacity*state.temperature_K)),
            electrostatic_J=poisson['electrostatic_energy_J'])
        errors.extend(float(report[name][key])-float(value) for key,value in expected.items())
    errors.extend(float(report[key])-value for key,value in dict(source_work_J=source,
        displacement_work_J=displacement,conduction_work_J=conduction,
        outward_carrier_energy_J=carrier_out,outward_heat_J=heat_out,energy_residual_J=residual).items())
    errors.extend(_array(report['cell_energy_residuals_J'],nc,'local energy')-local)
    errors.extend(_array(report['cell_electrical_work_J'],nc,'local work')-work)
    worst=lambda values:float(np.max(np.abs(values),initial=0.))
    reported_particles=_array(report['particle_residuals'],2*nc,'particle residuals')
    named_valid=True
    if model.groups is not None:
        from .cut_cell_terminals import integrate_cut_cell_terminals,audit_named_terminals
        expected_named=integrate_cut_cell_terminals(model.mesh,model.bc,model.groups,a,b,given_n,given_p,given_e,given_h,dt)
        named_valid=report.get('terminal_groups')=={name:list(faces) for name,faces in model.groups.items()}
        named_valid=named_valid and audit_named_terminals(expected_named,report.get('terminals'),
            dt_s=dt,charge_atol_C=charge_atol_C,energy_atol_J=energy_atol_J)['valid']
    elif 'terminals' in report or 'terminal_groups' in report:named_valid=False
    if not np.isfinite(min_entropy):min_entropy=0.
    finite=all(np.all(np.isfinite(v)) for v in (local,particles,errors,flux_errors,moment_particle_errors,moment_energy_errors,entropy_errors,current_errors))
    valid=(finite and a['valid'] and b['valid'] and coverage and occupation_valid and named_valid and
        worst(particles)<=particle_atol and worst(flux_errors)*dt<=particle_atol and worst(flux_errors)<=particle_flux_atol_s and
        worst(reported_particles-particles)<=particle_atol and
        worst(moment_particle_errors)<=particle_flux_atol_s and worst(moment_energy_errors)<=energy_flux_atol_W and
        worst(entropy_errors)<=entropy_atol_W_K and min_entropy>=-entropy_atol_W_K and
        max(worst(expected_e-given_e),worst(expected_h-given_h))<=energy_flux_atol_W and
        max(worst(local),worst(errors),abs(residual))<=energy_atol_J and
        max(worst(current_errors),abs(charge),abs(dt*sum(terminals.values())))<=charge_atol_C and
        report.get('density_precision')==dict(dtype=str(new.n_m3.dtype),mantissa_bits=np.finfo(new.n_m3.dtype).nmant+1) and
        report.get('spectral_backend')==model.spectral_backend and
        report.get('native_nonlinear_driver') is (model.nonlinear_backend=='native') and
        report.get('nonlinear_backend')==model.nonlinear_backend and report.get('residual_dispatch_backend')==model.residual_backend and
        report.get('local_backend')==model.local_backend and report.get('thermodynamic_backend')==model.local_backend and
        report.get('poisson_backend')==model.poisson_backend and
        report.get('state_advanced') is True and report.get('temperature_feedback') is True and
        report.get('thermionic_faces')==list(model.thermionic_faces) and
        report.get('trace_closure')=='energy_resolved_nonthermal_occupations' and
        report.get('complete_device_energy') is False and report.get('physical_validated') is False)
    return dict(valid=bool(valid),scope='independent_FD_spectral_local_energy_audit',complete_device_energy=False,
        max_cell_energy_residual_J=worst(local),max_particle_residual=worst(particles),
        max_constitutive_particle_error_s=worst(flux_errors),max_constitutive_energy_error_W=worst(expected_e-given_e),
        max_report_energy_error_J=worst(errors),energy_residual_J=residual,min_face_entropy_W_K=min_entropy,
        terminal_KCL_residual_C=float(dt*sum(terminals.values())),charge_balance_residual_C=charge,
        density_mantissa_bits=np.finfo(new.n_m3.dtype).nmant+1,occupation_bounds_valid=bool(occupation_valid))
