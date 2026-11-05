"""Monolithic FD particle/lattice energy solve with spectral face resistances.

One local temperature; elastic matched valleys, fixed bands and geometry.
This is not hydrodynamic transport with independent carrier temperatures.
"""
import numpy as np
from scipy.optimize import least_squares
from .cut_cell_transport import CutCellState,Q,KB,_array,_immutable_state_array
from .electrothermal_cut_cell import ElectrothermalCutCellTransport
from tcad.physics.fermi_spectral import validate_valleys,valley_dos,fermi_reservoir,spectral_face
from tcad.postprocess.cut_cell_terminals import validate_terminal_groups,integrate_cut_cell_terminals


class FermiSpectralState(CutCellState):
    """Immutable FD state retaining density precision through Poisson coupling.

    Densities use platform np.longdouble; temperatures/traps stay float64.
    This is not a claim of binary128: inspect finfo(dtype).nmant + 1.
    Converting to CutCellState explicitly rounds densities back to float64.
    """
    def __post_init__(self):
        for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
            dtype=np.longdouble if name in ('n_m3','p_m3') else float
            object.__setattr__(self,name,_immutable_state_array(getattr(self,name),dtype))


class FermiSpectralElectrothermal(ElectrothermalCutCellTransport):
    """FD bulk/energy and optional spectral thermionic series on orthogonal cells.

    Matched valley offsets may be nonzero but must be the same on both sides.
    Mobilities are prescribed per carrier, with the inherited temperature law.
    No traps, quantum or FE are accepted by this deliberately limited model.
    """
    def __init__(self,*args,valleys_n,valleys_p,thermionic_faces=(),
            emission_factor_n=2.,emission_factor_p=2.,terminal_groups=None,spectral_backend='python',
            local_backend='python',poisson_backend='python',nonlinear_backend='python',residual_backend='python',**kwargs):
        if spectral_backend not in ('python','native'):raise ValueError('spectral_backend must be python or native')
        if spectral_backend=='native':
            from tcad.core._bindings import native_spectral_face_raw
        if local_backend not in ('python','native'):raise ValueError('local_backend must be python or native')
        if local_backend=='native':
            if spectral_backend!='native':raise ValueError('native local_backend requires native spectral_backend')
            from tcad.core._bindings import native_fermi_reservoir_raw,native_fermi_local_raw
        self.local_backend=local_backend
        self.spectral_backend=spectral_backend
        if poisson_backend not in ('python','native'):raise ValueError('poisson_backend must be python or native')
        if poisson_backend=='native':
            from tcad.core._bindings import native_hybrid_poisson_raw
        self.poisson_backend=poisson_backend
        if nonlinear_backend not in ('python','native'):
            raise ValueError('nonlinear_backend must be python or native')
        if nonlinear_backend=='native':
            if (spectral_backend,local_backend,poisson_backend)!=('native','native','native'):
                raise ValueError('native nonlinear_backend requires native spectral, local and Poisson backends')
            from tcad.core._bindings import native_fermi_newton_raw
        self.nonlinear_backend=nonlinear_backend
        if residual_backend not in ('python','native'):
            raise ValueError('residual_backend must be python or native')
        if residual_backend=='native':
            if (spectral_backend,local_backend,poisson_backend,nonlinear_backend)!=('native',)*4:
                raise ValueError('native residual_backend requires all physics and nonlinear backends native')
            from tcad.core._bindings import native_fermi_dispatch_raw
        self.residual_backend=residual_backend
        self.valleys={'electrons':validate_valleys(valleys_n),'holes':validate_valleys(valleys_p)}
        T=float(kwargs.get('temperature_K',300.))
        for label,key in (('electrons','Nc_m3'),('holes','Nv_m3')):
            dos=sum(valley_dos(T,self.valleys[label])*np.exp(
                -np.array([v.band_offset_owner_J for v in self.valleys[label]])/(KB*T)))
            if key in kwargs and not np.allclose(kwargs[key],dos,rtol=2e-12,atol=0):
                raise ValueError('reference MB DOS must match spectral valleys')
            kwargs[key]=dos
        super().__init__(*args,**kwargs)
        if any(np.any(a!=0) for a in (self.Nt,self.cn,self.cp)) or self.kn!=0 or self.kp!=0:
            raise ValueError('FD spectral solver does not implement traps or quantum energy')
        if max(self.skew,self.contact_skew)>1e-10:raise ValueError('orthogonal geometry required')
        if min(min(self.mn),min(self.mp))<=0:raise ValueError('positive mobilities required')
        faces=list(thermionic_faces);nf=len(self.mesh.faces)
        if any(isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer)) or
                not 0<=f<nf or self.mesh.faces[f].neighbor<0 for f in faces):
            raise ValueError('internal thermionic face indices required')
        if len(faces)!=len(set(faces)):raise ValueError('duplicate thermionic faces')
        self.thermionic_faces=tuple(sorted(map(int,faces)))
        self.An=_array(emission_factor_n,len(faces),'electron emission',nonnegative=True)
        self.Ap=_array(emission_factor_p,len(faces),'hole emission',nonnegative=True)
        self.emission={label:{int(f):float(a) for f,a in zip(faces,A)}
            for label,A in (('electrons',self.An),('holes',self.Ap))}
        for f,i,j in zip(self.internal,self.i,self.j):
            if (self.Ec[i]!=self.Ec[j] or self.Eh[i]!=self.Eh[j]) and int(f) not in self.thermionic_faces:
                raise ValueError('band jumps require explicit thermionic faces')
        self.groups=None if terminal_groups is None else validate_terminal_groups(self.mesh,self.bc,terminal_groups)
        self.area=np.array([np.linalg.norm(f.area_vector_m2) for f in self.mesh.faces])
        if self.thermionic_faces and any(v.mass_normal!=v.mass_tangent_1 or v.mass_normal!=v.mass_tangent_2
                for values in self.valleys.values() for v in values):
            normals=[self.mesh.faces[f].area_vector_m2/self.area[f] for f in self.thermionic_faces]
            if any(abs(normal@normals[0])<1-1e-10 for normal in normals[1:]):
                raise ValueError('anisotropic thermionic masses require parallel emitting faces')
        self.do=np.zeros(nf);self.dn=np.zeros(nf)
        for f,face in enumerate(self.mesh.faces):
            normal=face.area_vector_m2/self.area[f]
            delta=face.centroid_m-self.mesh.centroids_m[face.owner]
            self.do[f]=delta@normal
            if self.do[f]<=0 or np.linalg.norm(delta-self.do[f]*normal)>1e-10*self.do[f]:
                raise ValueError('orthogonal positive owner half distance required')
            if face.neighbor>=0:
                delta=self.mesh.centroids_m[face.neighbor]-face.centroid_m
                self.dn[f]=delta@normal
                if self.dn[f]<=0 or np.linalg.norm(delta-self.dn[f]*normal)>1e-10*self.dn[f]:
                    raise ValueError('orthogonal positive neighbor half distance required')

    def _poisson(self,n,p,f,atol):
        if self.poisson_backend=='native':
            from .native_poisson import solve_native_state_poisson
            return solve_native_state_poisson(self.mesh,self.eps,self.rhofix,n,p,self.Nt,f,
                dirichlet_V=self.bc,charge_atol_C=atol)
        if self.poisson_backend!='python':raise ValueError('poisson_backend must be python or native')
        return super()._poisson(n,p,f,atol)

    def reservoirs(self,n,p,T):
        if self.local_backend=='native':
            from tcad.physics.native_fermi_local import native_fermi_reservoirs
            return {label:native_fermi_reservoirs(density,T,band,self.valleys[label])
                for label,density,band in (('electrons',n,self.Ec),('holes',p,self.Eh))}
        if self.local_backend!='python':raise ValueError('local_backend must be python or native')
        return {label:[fermi_reservoir(density[c],T[c],band[c],self.valleys[label]) for c in range(self.nc)]
            for label,density,band in (('electrons',n,self.Ec),('holes',p,self.Eh))}

    def face_transport(self,n,p,T,poisson):
        if self.spectral_backend=='native':
            from tcad.physics.native_spectral import native_spectral_face as face_law
        elif self.spectral_backend=='python':face_law=spectral_face
        else:raise ValueError('spectral_backend must be python or native')
        reservoirs=self.reservoirs(n,p,T);nf=len(self.mesh.faces)
        rates={};energy=np.zeros(nf);records={}
        for label,density,band,base,exponent,z in (
                ('electrons',n,self.Ec,self.mn,self.mn_exponent,-1),
                ('holes',p,self.Eh,self.mp,self.mp_exponent,1)):
            mu=base*(self.T/T)**exponent;flux=np.zeros(nf);rows={}
            for f in list(self.internal)+list(self.contact_faces):
                f=int(f);face=self.mesh.faces[f];i,j=face.owner,face.neighbor
                one=reservoirs[label][i]
                if j>=0:
                    two=reservoirs[label][j];potential=poisson['cell_potential_V'][j]
                    mobility=mu[j];dn=self.dn[f]
                else:
                    r=self.contacts[f];value=r.n_m3 if label=='electrons' else r.p_m3
                    if self.local_backend=='native':
                        from tcad.physics.native_fermi_local import native_fermi_reservoirs
                        two=native_fermi_reservoirs([value],[r.temperature_K],[band[i]],self.valleys[label])[0]
                    else:two=fermi_reservoir(value,r.temperature_K,band[i],self.valleys[label])
                    potential=self.bc[f];mobility=base[i]*(self.T/r.temperature_K)**exponent;dn=0.
                moment=face_law(one,two,self.valleys[label],potential_owner_V=poisson['cell_potential_V'][i],
                    potential_neighbor_V=potential,potential_face_V=poisson['face_potential_V'][f],charge_sign=z,
                    mobility_owner_m2_Vs=mu[i],mobility_neighbor_m2_Vs=mobility,area_m2=self.area[f],
                    distance_owner_m=self.do[f],distance_neighbor_m=dn,
                    emission_factor=self.emission[label].get(f))
                moment['execution_backend']=self.spectral_backend
                flux[f]=moment['particle_flux_s'];energy[f]+=moment['material_energy_flux_W'];rows[f]=moment
            rates[label]=flux;records[label]=rows
        return rates['electrons'],rates['holes'],energy,records,reservoirs

    def carrier_density_energy(self,n,p,T):
        values=self.reservoirs(n,p,T)
        return np.array([values['electrons'][c]['energy_density_J_m3']+
            values['holes'][c]['energy_density_J_m3'] for c in range(self.nc)])

    def transport(self,n,p,f,temperature,poisson):
        """Generic particle API also returns the FD spectral constitutive law."""
        fn,fp,_,_,_=self.face_transport(n,p,temperature,poisson)
        zero=np.zeros(self.nc)
        return fn,fp,zero.copy(),zero.copy(),zero.copy(),zero.copy()

    def heat_terms(self,*args,**kwargs):
        raise ValueError('FD spectral transport uses a combined local energy equation, not MB heat splitting')

    def energies(self,state,*,charge_atol_C):
        self._validate_state(state)
        poisson=self._poisson(state.n_m3,state.p_m3,state.trap_fraction,charge_atol_C)
        carrier=self.carrier_density_energy(state.n_m3,state.p_m3,state.temperature_K)
        return dict(carrier_J=float(np.sum(self.vol.astype(np.longdouble)*carrier)),
            thermal_J=float(np.sum(self.vol.astype(np.longdouble)*self.capacity*state.temperature_K)),
            electrostatic_J=poisson['electrostatic_energy_J']),poisson

    def energy_increments(self,old,new,old_poisson,new_poisson):
        ld=np.longdouble
        before=self.carrier_density_energy(old.n_m3,old.p_m3,old.temperature_K)
        after=self.carrier_density_energy(new.n_m3,new.p_m3,new.temperature_K)
        return dict(carrier_J=float(np.sum(self.vol.astype(ld)*(after.astype(ld)-before.astype(ld)))),
            thermal_J=float(np.sum(self.vol.astype(ld)*self.capacity*(new.temperature_K.astype(ld)-old.temperature_K))),
            electrostatic_J=float(ld(new_poisson['electrostatic_energy_J'])-ld(old_poisson['electrostatic_energy_J'])))

    def step(self,state,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=400):
        self._validate_state(state)
        if any(np.any(a!=0) for a in (self.Nt,self.cn,self.cp)) or self.kn!=0 or self.kp!=0:
            raise ValueError('FD spectral solver does not implement traps or quantum energy')
        for name,value in dict(dt=dt_s,charge=charge_atol_C,particle=particle_atol,energy=energy_atol_J).items():
            _array(value,1,name,positive=True)
        dt=float(dt_s);nc=self.nc;vol=self.vol;ld=np.longdouble
        if self.residual_backend=='native':
            from .native_fd_dispatch import native_fd_step
            cache,before,a,after,b,fit,native_stats,native_history=native_fd_step(
                self,state,dt,charge_atol_C,particle_atol,energy_atol_J,max_nfev)
            polish_iterations=0
        else:
            before,a=self.energies(state,charge_atol_C=charge_atol_C)
            if not a['valid']:raise ValueError('initial FD Poisson budget failed')
            old_u=self.carrier_density_energy(state.n_m3,state.p_m3,state.temperature_K)
            scale=vol*(self.capacity*state.temperature_K+abs(old_u))
            cache={}
            def evaluate(x):
                # Relative logarithms avoid large absolute log(n) steps and their
                # spurious Poisson perturbation near dense neutral states.
                # Subtracting dense n and p in float64 quantizes Poisson charge
                # enough to defeat absolute continuity budgets under bias. Keep
                # extra density bits in both residual evaluation and returned state.
                n=state.n_m3.astype(ld)*np.exp(x[:nc].astype(ld))
                p=state.p_m3.astype(ld)*np.exp(x[nc:2*nc].astype(ld))
                T=state.temperature_K*np.exp(x[2*nc:])
                b=self._poisson(n,p,state.trap_fraction,charge_atol_C)
                fn,fp,eflux,records,reservoirs=self.face_transport(n,p,T,b)
                u=np.array([reservoirs['electrons'][c]['energy_density_J_m3']+
                    reservoirs['holes'][c]['energy_density_J_m3'] for c in range(nc)])
                if self.local_backend=='native':
                    from tcad.physics.native_fermi_local import native_fermi_local
                    local=native_fermi_local(self,state,n,p,T,old_u,u,a,b,fn,fp,eflux,dt)
                    delta_u,delta_t,heat,work,energy,rn,rp=(local[key] for key in
                        ('delta_u','delta_t','heat','work','energy','rn','rp'))
                elif self.local_backend=='python':
                    delta_u=np.asarray(vol.astype(ld)*(u.astype(ld)-old_u.astype(ld)),float)
                    delta_t=vol*self.capacity*(T-state.temperature_K)
                    heat=self.conduction(T);qflux=Q*(fp-fn)
                    midphi=(a['cell_potential_V']+b['cell_potential_V'])/2
                    midface=(a['face_potential_V']+b['face_potential_V'])/2
                    work=dt*(midphi*self.mesh.divergence_integrals(qflux)-self.mesh.divergence_integrals(midface*qflux))
                    energy=delta_u+delta_t+dt*self.mesh.divergence_integrals(eflux+heat)-work
                    rn=vol*(n-state.n_m3)+dt*self.mesh.divergence_integrals(fn)
                    rp=vol*(p-state.p_m3)+dt*self.mesh.divergence_integrals(fp)
                else:raise ValueError('local_backend must be python or native')
                cache.update(n=n,p=p,T=T,b=b,fn=fn,fp=fp,eflux=eflux,heat=heat,records=records,
                    delta_u=delta_u,delta_t=delta_t,energy=energy,rn=rn,rp=rp,work=work)
                return np.asarray(np.r_[rn/(vol*state.n_m3),rp/(vol*state.p_m3),energy/scale],float)
            def jacobian(x):
                # A central derivative preserves the electron/hole symmetry at a
                # spectral threshold tie; one-sided differences break neutrality.
                h=1e-7;matrix=np.empty((3*nc,3*nc))
                for column in range(3*nc):
                    plus=x.copy();minus=x.copy();plus[column]+=h;minus[column]-=h
                    matrix[:,column]=(evaluate(plus)-evaluate(minus))/(2*h)
                return matrix
            x0=np.zeros(3*nc)
            origin=np.r_[np.log(state.n_m3),np.log(state.p_m3),np.log(state.temperature_K)]
            lower=np.r_[np.full(2*nc,-600.),np.full(nc,0.)]-origin
            upper=np.r_[np.full(2*nc,600.),np.full(nc,np.log(1e5))]-origin
            def physical_merit():
                return max(max(abs(cache['rn']))/particle_atol,max(abs(cache['rp']))/particle_atol,
                    max(abs(cache['energy']))/energy_atol_J,
                    abs(Q*np.sum(cache['rp'].astype(ld)-cache['rn'].astype(ld)))/charge_atol_C)
            # Relative optimizer gradients can be tiny while absolute particle
            # or charge budgets still fail at high density. Stop on the step;
            # acceptance remains governed by the physical budgets below.
            native_stats=None;native_history=[]
            if self.nonlinear_backend=='native':
                from tcad.core._bindings import native_fermi_newton_raw
                from types import SimpleNamespace
                def native_residual(x):
                    residual=evaluate(np.asarray(x,float))
                    return residual,physical_merit()
                solution,native_stats,native_history=native_fermi_newton_raw(
                    native_residual,x0,np.asarray(lower,float),np.asarray(upper,float),max_nfev)
                fit=SimpleNamespace(x=np.asarray(solution,float),nfev=int(native_stats[0]),success=True)
            else:
                fit=least_squares(evaluate,x0,xtol=1e-15,ftol=None,gtol=None,max_nfev=max_nfev,
                    jac=jacobian,bounds=(lower,upper))
            x=fit.x.copy();polish_iterations=0
            if self.nonlinear_backend=='python':evaluate(x)
            # Float64 optimizer stopping is relative. Polish against the actual
            # absolute conservation budgets, including summed charge cancellation.
            for _ in range(8 if self.nonlinear_backend=='python' else 0):
                residual_vector=evaluate(x);merit=physical_merit()
                if merit<=.25:break
                try:direction=np.linalg.solve(jacobian(x),-residual_vector)
                except np.linalg.LinAlgError:break
                accepted=False
                for fraction in (1.,.5,.25,.125,.0625):
                    trial=x+fraction*direction
                    if np.any(origin+trial<=np.r_[np.full(2*nc,-600.),np.full(nc,0.)]) or np.any(
                            origin+trial>=np.r_[np.full(2*nc,600.),np.full(nc,np.log(1e5))]):continue
                    evaluate(trial)
                    if physical_merit()<merit:
                        x=trial;polish_iterations+=1;accepted=True;break
                if not accepted:break
            if self.nonlinear_backend=='python':evaluate(x)
        if not fit.success or max(max(abs(cache['rn'])),max(abs(cache['rp'])))>particle_atol:
            raise ValueError('FD spectral particle conservation budget failed')
        if not cache['b']['valid'] or max(abs(cache['energy']))>energy_atol_J:
            raise ValueError('FD spectral local energy or Poisson budget failed')
        new=FermiSpectralState(cache['n'],cache['p'],state.trap_fraction,cache['T'],state.time_s+dt)
        if self.residual_backend!='native':after,b=self.energies(new,charge_atol_C=charge_atol_C)
        increments=dict(carrier_J=float(np.sum(cache['delta_u'],dtype=ld)),
            thermal_J=float(np.sum(cache['delta_t'],dtype=ld)),
            electrostatic_J=float(ld(b['electrostatic_energy_J'])-ld(a['electrostatic_energy_J'])))
        boundary=np.array([f for f,v in enumerate(self.mesh.faces) if v.neighbor<0],int)
        dq=b['integrated_D_flux_C']-a['integrated_D_flux_C'];qflux=Q*(cache['fp']-cache['fn'])
        terminals={f:float(-dq[f]/dt-qflux[f]) for f in self.bc}
        displacement=-sum(value*dq[f] for f,value in self.bc.items())
        conduction=-dt*sum(value*qflux[f] for f,value in self.bc.items());source=displacement+conduction
        carrier_out=dt*float(np.sum(cache['eflux'][boundary],dtype=ld))
        heat_out=dt*float(np.sum(cache['heat'][boundary],dtype=ld))
        residual=float(ld(source)-sum(map(ld,increments.values()))-ld(carrier_out)-ld(heat_out))
        charge=float(Q*np.sum(vol.astype(ld)*(new.p_m3.astype(ld)-state.p_m3-new.n_m3.astype(ld)+state.n_m3))+
            dt*np.sum(qflux[boundary],dtype=ld))
        if abs(residual)>energy_atol_J or max(abs(charge),abs(dt*sum(terminals.values())))>charge_atol_C:
            raise ValueError('FD spectral global energy or terminal charge budget failed')
        report=dict(valid=True,scope='monolithic_FD_spectral_matched_valley_shared_temperature',nfev=fit.nfev,
            spectral_backend=self.spectral_backend,native_nonlinear_driver=self.nonlinear_backend=='native',
            nonlinear_backend=self.nonlinear_backend,residual_dispatch_backend=self.residual_backend,
            nonlinear_statistics=None if native_stats is None else dict(
                residual_evaluations=int(native_stats[0]),iterations=int(native_stats[1]),
                backtracks=int(native_stats[2]),physical_budget_ratio=float(native_stats[3]),
                evaluation_budget=int(max_nfev),jacobian_probe_calls_included=True),
            nonlinear_history=np.asarray(native_history,float).reshape(-1,3),
            local_backend=self.local_backend,thermodynamic_backend=self.local_backend,
            poisson_backend=self.poisson_backend,
            density_precision=dict(dtype=str(new.n_m3.dtype),mantissa_bits=np.finfo(new.n_m3.dtype).nmant+1),
            conservation_polish_iterations=polish_iterations,
            state_advanced=True,temperature_feedback=True,complete_device_energy=False,physical_validated=False,
            energy_before_J=before,energy_after_J=after,energy_increments_J=increments,energy_residual_J=residual,
            source_work_J=float(source),displacement_work_J=float(displacement),conduction_work_J=float(conduction),
            outward_carrier_energy_J=carrier_out,outward_heat_J=heat_out,cell_energy_residuals_J=cache['energy'],
            cell_electrical_work_J=cache['work'],particle_residuals=np.r_[cache['rn'],cache['rp']],
            integrated_electron_particle_flux_s=cache['fn'],integrated_hole_particle_flux_s=cache['fp'],
            integrated_carrier_energy_flux_W=cache['eflux'],integrated_heat_flux_W=cache['heat'],
            terminal_currents_A=terminals,charge_balance_residual_C=charge,thermionic_faces=list(self.thermionic_faces),
            face_moments=cache['records'],trace_closure='energy_resolved_nonthermal_occupations',
            missing_physics=['native_backend','independent_carrier_temperatures','traps_quantum_FE',
                'mass_discontinuity','commercial_and_experimental_validation'])
        if self.groups is not None:
            report['terminal_groups']={name:list(faces) for name,faces in self.groups.items()}
            report['terminals']=integrate_cut_cell_terminals(self.mesh,self.bc,self.groups,a,b,
                cache['fn'],cache['fp'],cache['eflux'],cache['heat'],dt)
        return new,report
