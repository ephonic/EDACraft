"""Open-contact, monolithic Maxwell-Boltzmann electrothermal cut-cell model.

Non-isothermal SG uses logarithmic mean temperature (Kelvin model, WIAS
preprint 2664, Eq. 16, Boltzmann limit). Carrier kinetic storage and transported
internal energy are 3 k_B T / 2 per particle. Conservative face energy fluxes
and discrete gradients close the first law with SRH and graph quantum energy.
This does not establish a second-law proof for the combined graph DG scheme.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from scipy.special import expit
from .cut_cell_transport import CutCellTransport,CutCellState,Q,KB,_array,_bernoulli


def logarithmic_mean_temperature(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,dtype=float),np.asarray(b,dtype=float))
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)) or np.any(a<=0) or np.any(b<=0):
        raise ValueError('positive finite temperatures required')
    # Symmetric, stable even when temperatures coincide to machine precision.
    mean=(a+b)/2;r=(b-a)/(a+b);small=abs(r)<1e-4
    factor=np.empty_like(mean);factor[small]=1-r[small]**2/3-4*r[small]**4/45
    factor[~small]=r[~small]/np.arctanh(r[~small])
    return mean*factor


@dataclass(frozen=True)
class CarrierReservoir:
    n_m3: float
    p_m3: float
    temperature_K: float=300.

    def __post_init__(self):
        for name in ('n_m3','p_m3','temperature_K'):
            value=getattr(self,name)
            if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isreal(value) or not np.isfinite(value) or value<=0:
                raise ValueError('reservoir requires finite positive real '+name)
            object.__setattr__(self,name,float(value))


class ElectrothermalCutCellTransport(CutCellTransport):
    """One carrier/lattice temperature, fixed voltages and static reservoirs.

    Mobilities scale as (T_ref/T)**exponent; DOS scales as T**1.5 in SRH
    emission. Band edges, permittivity, thermal properties and quantum kappa
    are fixed. Material jumps use reference-DOS activity corrections; a full
    heterojunction thermionic or degenerate model is not supplied.
    """
    def __init__(self,*args,particle_contacts=None,mobility_temperature_exponent_n=1.5,
                 mobility_temperature_exponent_p=1.5,**kwargs):
        super().__init__(*args,**kwargs)
        self.mn_exponent=float(_array(mobility_temperature_exponent_n,1,'electron mobility exponent')[0])
        self.mp_exponent=float(_array(mobility_temperature_exponent_p,1,'hole mobility exponent')[0])
        contacts={} if particle_contacts is None else particle_contacts
        if not isinstance(contacts,dict):raise ValueError('particle contacts must map boundary face indices to reservoirs')
        self.contacts={}
        for f,value in contacts.items():
            if (isinstance(f,bool) or not isinstance(f,(int,np.integer)) or f not in self.bc):
                raise ValueError('particle reservoir requires a Dirichlet potential boundary face')
            if isinstance(value,dict):value=CarrierReservoir(**value)
            if not isinstance(value,CarrierReservoir):raise ValueError('CarrierReservoir required')
            self.contacts[int(f)]=value
        self.contact_faces=np.array(sorted(self.contacts),int)
        self.contact_cells=np.array([self.mesh.faces[f].owner for f in self.contact_faces],int)
        self.contact_metric=np.empty(len(self.contacts));skews=[]
        for k,f in enumerate(self.contact_faces):
            face=self.mesh.faces[f];area=np.linalg.norm(face.area_vector_m2);normal=face.area_vector_m2/area
            delta=face.centroid_m-self.mesh.centroids_m[face.owner];distance=delta@normal
            if distance<=0:raise ValueError('positive contact distance required')
            self.contact_metric[k]=area/distance
            skews.append(np.linalg.norm(delta-distance*normal)/np.linalg.norm(delta))
        self.contact_skew=max(skews,default=0.)
        self.res_n=np.array([self.contacts[f].n_m3 for f in self.contact_faces])
        self.res_p=np.array([self.contacts[f].p_m3 for f in self.contact_faces])
        self.res_T=np.array([self.contacts[f].temperature_K for f in self.contact_faces])

    def _boundary_quantum(self,n,kappa,old,reservoir):
        # Fixed reservoir density contributes boundary quantum storage, not
        # unrecorded work from time-varying boundary parameters.
        root=np.sqrt(n);previous=root if old is None else np.sqrt(old);c=self.contact_cells
        force=kappa*self.contact_metric*(root[c]+previous[c]-2*np.sqrt(reservoir))
        return np.bincount(c,force,minlength=self.nc)/(self.vol*(root+previous))

    def quantum_potentials(self,n,p,old_n=None,old_p=None):
        qn=CutCellTransport._quantum(self,n,self.kn,old_n)
        qp=CutCellTransport._quantum(self,p,self.kp,old_p)
        if len(self.contacts):
            qn+=self._boundary_quantum(n,self.kn,old_n,self.res_n)
            qp+=self._boundary_quantum(p,self.kp,old_p,self.res_p)
        return qn,qp

    def _edge_flux(self,ni,nj,Ti,Tj,Ui,Uj,dosi,dosj,mui,muj,metric):
        temp=logarithmic_mean_temperature(Ti,Tj)
        d=(Uj-Ui)/(KB*temp)-np.log(dosj/dosi)
        mu=np.divide(2*mui*muj,mui+muj,out=np.zeros_like(mui),where=(mui+muj)>0)
        return mu*KB*temp/Q*metric*(_bernoulli(d)*ni-_bernoulli(-d)*nj)

    def transport(self,n,p,f,temperature,poisson):
        """Owner-oriented number fluxes, SRH rates and quantum potentials."""
        i,j=self.i,self.j;c=self.contact_cells;phi=poisson['cell_potential_V']
        qn,qp=self.quantum_potentials(n,p)
        mn=self.mn*(self.T/temperature)**self.mn_exponent
        mp=self.mp*(self.T/temperature)**self.mp_exponent
        fn=np.zeros(len(self.mesh.faces));fp=fn.copy()
        for density,band,dos,mu,sign,quantum,flux,res_density,exponent,base_mu in (
                (n,self.Ec,self.Nc,mn,-1,qn,fn,self.res_n,self.mn_exponent,self.mn),
                (p,self.Eh,self.Nv,mp,1,qp,fp,self.res_p,self.mp_exponent,self.mp)):
            U=band+quantum+sign*Q*phi
            flux[self.internal]=self._edge_flux(density[i],density[j],temperature[i],temperature[j],
                U[i],U[j],dos[i],dos[j],mu[i],mu[j],self.metric)
            if len(c):
                reservoir_U=band[c]+sign*Q*np.array([self.bc[f] for f in self.contact_faces])
                reservoir_mu=base_mu[c]*(self.T/self.res_T)**exponent
                flux[self.contact_faces]=self._edge_flux(density[c],res_density,temperature[c],self.res_T,
                    U[c],reservoir_U,dos[c],dos[c],mu[c],reservoir_mu,self.contact_metric)
        Nc=self.Nc*(temperature/self.T)**1.5;Nv=self.Nv*(temperature/self.T)**1.5
        n1=Nc*np.exp(np.clip((self.Et-self.Ec-qn)/(KB*temperature),-690,690))
        p1=Nv*np.exp(np.clip((-self.Et-self.Eh-qp)/(KB*temperature),-690,690))
        rn=self.cn*(n*(1-f)-n1*f);rp=self.cp*(p*f-p1*(1-f))
        return fn,fp,rn,rp,qn,qp

    def heat_terms(self,old,n,p,temperature,old_poisson,new_poisson,fn,fp,rn,rp,dt):
        """Construct local heat from face energy flux and capture reactions."""
        nc=self.nc;i,j=self.i,self.j;c=self.contact_cells
        midT=(old.temperature_K+temperature)/2
        midphi=(old_poisson['cell_potential_V']+new_poisson['cell_potential_V'])/2
        facephi=(old_poisson['face_potential_V']+new_poisson['face_potential_V'])/2
        qn,qp=self.quantum_potentials(n,p,old.n_m3,old.p_m3)
        heat=np.zeros(nc);transport_heat=np.longdouble(0);carrier_out=np.longdouble(0)
        particle_energy_flux=np.zeros(len(self.mesh.faces))
        for flux,band,sign,quantum in ((fn,self.Ec,-1,qn),(fp,self.Eh,1,qp)):
            energy=band+1.5*KB*midT+quantum+sign*Q*midphi
            number=flux[self.internal]
            upwind=np.where(number>=0,temperature[i],temperature[j])
            # Kelvin transported internal energy, not an independently added
            # ideal-gas pressure-work enthalpy. Quantum face term is symmetric.
            carried=(band[i]+band[j]+quantum[i]+quantum[j])/2+1.5*KB*upwind+sign*Q*facephi[self.internal]
            left=dt*number*(energy[i]-carried);right=dt*number*(carried-energy[j])
            heat+=np.bincount(i,left,minlength=nc)+np.bincount(j,right,minlength=nc)
            transport_heat+=np.sum(left.astype(np.longdouble))+np.sum(right.astype(np.longdouble))
            particle_energy_flux[self.internal]+=number*(carried-sign*Q*facephi[self.internal])
            if len(c):
                number=flux[self.contact_faces];upwind=np.where(number>=0,temperature[c],self.res_T)
                carried=band[c]+1.5*KB*upwind
                reservoir_phi=np.array([self.bc[f] for f in self.contact_faces])
                local=dt*number*(energy[c]-carried-sign*Q*reservoir_phi)
                heat+=np.bincount(c,local,minlength=nc);transport_heat+=np.sum(local.astype(np.longdouble))
                carrier_out+=np.sum((dt*number*carried).astype(np.longdouble))
                particle_energy_flux[self.contact_faces]+=number*carried
        capture=dt*self.vol*self.Nt*(rn*(self.Ec+1.5*KB*midT+qn-self.Et)+
            rp*(self.Eh+1.5*KB*midT+qp+self.Et))
        return heat+capture,float(transport_heat),float(np.sum(capture,dtype=np.longdouble)),float(carrier_out),particle_energy_flux

    def conduction(self,temperature):
        a,b=self.conductivity[self.i],self.conductivity[self.j]
        flux=np.zeros(len(self.mesh.faces))
        flux[self.internal]=2*a*b/(a+b)*self.metric*(temperature[self.i]-temperature[self.j])
        for f,temp in self.bath.items():
            face=self.mesh.faces[f];c=face.owner;area=np.linalg.norm(face.area_vector_m2)
            distance=face.area_vector_m2@(face.centroid_m-self.mesh.centroids_m[c])/area
            flux[f]=self.conductivity[c]*area/distance*(temperature[c]-temp)
        return flux

    def energies(self,state,*,charge_atol_C):
        energies,poisson=super().energies(state,charge_atol_C=charge_atol_C)
        energies['carrier_J']=float(np.sum(self.vol*((self.Ec+1.5*KB*state.temperature_K)*state.n_m3+
            (self.Eh+1.5*KB*state.temperature_K)*state.p_m3),dtype=np.longdouble))
        for n,k,res in ((state.n_m3,self.kn,self.res_n),(state.p_m3,self.kp,self.res_p)):
            energies['quantum_J']+=float(np.sum(k*self.contact_metric*(np.sqrt(n[self.contact_cells])-np.sqrt(res))**2,dtype=np.longdouble))
        return energies,poisson

    def energy_increments(self,old,new,old_poisson,new_poisson):
        increments=super().energy_increments(old,new,old_poisson,new_poisson)
        ld=np.longdouble;vol=self.vol.astype(ld);oldT=old.temperature_K.astype(ld);newT=new.temperature_K.astype(ld)
        carrier=ld(0);quantum=ld(increments['quantum_J'])
        for a,b,band,k,res in ((old.n_m3,new.n_m3,self.Ec,self.kn,self.res_n),(old.p_m3,new.p_m3,self.Eh,self.kp,self.res_p)):
            a=a.astype(ld);b=b.astype(ld)
            carrier+=np.sum(vol*((band.astype(ld)+ld(1.5)*ld(KB)*(oldT+newT)/2)*(b-a)+
                ld(1.5)*ld(KB)*(a+b)/2*(newT-oldT)))
            da=np.sqrt(a[self.contact_cells])-np.sqrt(res.astype(ld));db=np.sqrt(b[self.contact_cells])-np.sqrt(res.astype(ld))
            quantum+=np.sum(ld(k)*self.contact_metric.astype(ld)*(db-da)*(db+da))
        increments['carrier_J']=float(carrier);increments['quantum_J']=float(quantum)
        return increments

    def step(self,state,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=250):
        self._validate_state(state)
        for name,value in dict(dt_s=dt_s,charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J).items():
            _array(value,1,name,positive=True)
        dt=float(dt_s);nc=self.nc;vol=self.vol;n0,p0,f0=state.n_m3,state.p_m3,state.trap_fraction
        old_energy,old_poisson=self.energies(state,charge_atol_C=charge_atol_C)
        if not old_poisson['valid']:raise ValueError('initial Poisson charge budget failed')
        sn=np.maximum.reduce((n0,self.Nt,np.ones(nc)));sp=np.maximum.reduce((p0,self.Nt,np.ones(nc)))
        cache={}
        def evaluate(x):
            n=np.exp(x[:nc]);p=np.exp(x[nc:2*nc]);f=expit(x[2*nc:3*nc]);T=np.exp(x[3*nc:])
            poisson=self._poisson(n,p,f,charge_atol_C)
            fn,fp,rn,rp,_,_=self.transport(n,p,f,T,poisson)
            heat,transport_heat,capture_heat,carrier_out,eflux=self.heat_terms(state,n,p,T,old_poisson,poisson,fn,fp,rn,rp,dt)
            conducted=self.conduction(T)
            capacity=vol*(self.capacity+1.5*KB*(n+n0+p+p0)/2)
            thermal=capacity*(T-state.temperature_K)+dt*self.mesh.divergence_integrals(conducted)-heat
            residual=np.r_[(n-n0+dt*self.Nt*rn+dt*self.mesh.divergence_integrals(fn)/vol)/sn,
                (p-p0+dt*self.Nt*rp+dt*self.mesh.divergence_integrals(fp)/vol)/sp,
                f-f0-dt*(rn-rp),thermal/(capacity*state.temperature_K)]
            cache.update(n=n,p=p,f=f,T=T,poisson=poisson,fn=fn,fp=fp,rn=rn,rp=rp,thermal=thermal,
                heat=heat,conducted=conducted,transport_heat=transport_heat,capture_heat=capture_heat,
                carrier_out=carrier_out,eflux=eflux)
            return np.asarray(residual,float)
        x0=np.r_[np.log(n0),np.log(p0),np.log(f0/(1-f0)),np.log(state.temperature_K)]
        lower=np.r_[np.full(2*nc,-690.),np.full(nc,-35.),np.full(nc,np.log(1.))]
        upper=np.r_[np.full(2*nc,690.),np.full(nc,35.),np.full(nc,np.log(1e5))]
        if np.any(x0<lower) or np.any(x0>upper):raise ValueError('state outside numerical solve bounds')
        fit=least_squares(evaluate,x0,bounds=(lower,upper),xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=max_nfev)
        evaluate(fit.x);n,p,f,T=(cache[k] for k in ('n','p','f','T'))
        fn,fp,rn,rp=(cache[k] for k in ('fn','fp','rn','rp'))
        balances=np.r_[vol*(n-n0+dt*self.Nt*rn)+dt*self.mesh.divergence_integrals(fn),
            vol*(p-p0+dt*self.Nt*rp)+dt*self.mesh.divergence_integrals(fp),vol*self.Nt*(f-f0-dt*(rn-rp))]
        if not fit.success or np.max(abs(balances),initial=0)>particle_atol:
            raise ValueError('electrothermal particle conservation budget failed')
        if not cache['poisson']['valid'] or np.max(abs(cache['thermal']),initial=0)>energy_atol_J:
            raise ValueError('electrothermal cell heat or Poisson budget failed')
        result=CutCellState(n,p,f,T,state.time_s+dt);new_energy,new_poisson=self.energies(result,charge_atol_C=charge_atol_C)
        increments=self.energy_increments(state,result,old_poisson,new_poisson)
        boundary=[f for f,face in enumerate(self.mesh.faces) if face.neighbor<0]
        delta_q=new_poisson['integrated_D_flux_C']-old_poisson['integrated_D_flux_C']
        electric_charge_flux=Q*(fp-fn)
        terminal={int(face):-delta_q[face]/dt-electric_charge_flux[face] for face in self.bc}
        displacement=sum(-v*delta_q[face] for face,v in self.bc.items())
        conduction_work=-dt*sum(v*electric_charge_flux[face] for face,v in self.bc.items())
        source=displacement+conduction_work
        heat_out=dt*float(np.sum(cache['conducted'][boundary],dtype=np.longdouble))
        residual=float(np.longdouble(source)-sum(map(np.longdouble,increments.values()))-
            np.longdouble(heat_out)-np.longdouble(cache['carrier_out']))
        charge_balance=float(Q*np.sum(vol.astype(np.longdouble)*(p.astype(np.longdouble)-p0-n.astype(np.longdouble)+n0-
            self.Nt.astype(np.longdouble)*(f.astype(np.longdouble)-f0)))+dt*np.sum(electric_charge_flux[boundary],dtype=np.longdouble))
        if abs(residual)>energy_atol_J or abs(charge_balance)>charge_atol_C or abs(dt*sum(terminal.values()))>charge_atol_C:
            raise ValueError('open-contact energy, device charge or terminal KCL budget failed')
        return result,dict(valid=True,scope='monolithic_MB_electrothermal_SG_SRH_graph_DG_open_reservoirs',
            temperature_feedback=True,complete_device_energy=False,modeled_energy_components_complete=True,
            device_energy_ledger_available=True,
            device_energy_components=('carrier','trap','thermal','quantum','electrostatic'),
            physical_validated=False,energy_before_J=old_energy,energy_after_J=new_energy,
            energy_increments_J=increments,source_work_J=float(source),displacement_work_J=float(displacement),
            conduction_work_J=float(conduction_work),outward_heat_J=heat_out,outward_carrier_energy_J=cache['carrier_out'],
            energy_residual_J=residual,cell_heat_residuals_J=np.asarray(cache['thermal'],float),
            transport_heat_J=cache['transport_heat'],capture_heat_J=cache['capture_heat'],
            particle_residuals=np.asarray(balances,float),charge_balance_residual_C=charge_balance,
            terminal_currents_A=terminal,terminal_KCL_residual_A=float(sum(terminal.values())),
            integrated_electron_particle_flux_s=fn,integrated_hole_particle_flux_s=fp,
            integrated_carrier_energy_flux_W=cache['eflux'],integrated_heat_flux_W=cache['conducted'],
            trap_electron_capture_rate_s=rn,trap_hole_capture_rate_s=rp,
            max_nonorthogonality=max(self.skew,self.contact_skew),
            missing_physics=['native_backend_integration','general_skew_consistent_transport',
                'ferroelectric_and_domain_energy','degenerate_statistics_and_thermionic_interfaces',
                'full_material_temperature_dependence','second_law_validation_of_combined_quantum_model'])
