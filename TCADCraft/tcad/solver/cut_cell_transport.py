"""Positive shared-face SG transport, SRH traps and calorimetric heat.

Electrons and holes use a fixed reference temperature. The lattice receives
transport/capture heat and conducts it implicitly; lattice temperature does
not feed back into electronic coefficients. Density-gradient energy is the
explicit graph functional kappa*sum(A/d)*(sqrt(n_i)-sqrt(n_j))**2.

Poisson uses the hybrid mimetic operator. SG/heat use a positive two-point
graph metric, which is conservative on skew cuts but only geometrically
consistent on orthogonal center connections. This is a scoped Python solver,
not a replacement for the native fully coupled transient backend.
"""
from dataclasses import dataclass, fields
import numpy as np
from scipy.optimize import least_squares
from scipy.special import expit
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve
from .cut_cell_poisson import solve_cut_cell_poisson

Q=1.602176634e-19
KB=1.380649e-23


def _array(value,n,name,*,positive=False,nonnegative=False):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu':raise ValueError(name+' must be real')
    try:a=np.broadcast_to(raw,(n,)).astype(float).copy()
    except ValueError:raise ValueError(name+' must be scalar or one value per cell') from None
    if (not np.all(np.isfinite(a)) or (positive and np.any(a<=0)) or (nonnegative and np.any(a<0))):
        raise ValueError('invalid '+name)
    return a


def _bernoulli(x):
    x=np.asarray(x);out=np.empty_like(x,dtype=float);small=abs(x)<1e-4
    out[small]=1-x[small]/2+x[small]**2/12-x[small]**4/720
    pos=(~small)&(x>50);out[pos]=x[pos]*np.exp(-x[pos])
    mid=(~small)&(~pos);out[mid]=x[mid]/np.expm1(x[mid])
    return out


def _immutable_state_array(value, dtype):
    """Detached numeric storage whose NumPy write flag cannot be re-enabled."""
    a = np.array(value, dtype=dtype, copy=True)
    return np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)


def _restore_transport_state(state_type, values):
    # Re-enter validation and buffer freezing even when NumPy unpickles its
    # arrays as writable, including protocol 5 out-of-band buffers.
    return state_type(**values)


@dataclass(frozen=True)
class CutCellState:
    n_m3: np.ndarray
    p_m3: np.ndarray
    trap_fraction: np.ndarray
    temperature_K: np.ndarray
    time_s: float=0.

    def __post_init__(self):
        for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
            object.__setattr__(self,name,_immutable_state_array(getattr(self,name),float))

    def __copy__(self):
        return type(self)(**{f.name: getattr(self, f.name) for f in fields(self)})

    def __deepcopy__(self, memo):
        from copy import deepcopy
        state = type(self)(**{f.name: deepcopy(getattr(self, f.name), memo) for f in fields(self)})
        memo[id(self)] = state
        return state

    def __reduce_ex__(self, protocol):
        return (_restore_transport_state,
                (type(self), {f.name: getattr(self, f.name) for f in fields(self)}))


class CutCellTransport:
    """Closed particle boundaries, fixed voltage contacts, optional heat baths.

    Band energies are joules per particle, measured from a common reference.
    Trap occupancy represents one negative electron per occupied neutral trap.
    Material interfaces use the supplied band offsets and effective DOS.
    """
    def __init__(self,mesh,*,permittivity_F_m,dirichlet_V,
                 mobility_n_m2_Vs,mobility_p_m2_Vs,temperature_K=300.,
                 Nc_m3=2.8e25,Nv_m3=1.04e25,Ec_J=0.,Eh_J=0.,
                 trap_density_m3=0.,trap_energy_J=0.,capture_n_m3_s=0.,capture_p_m3_s=0.,
                 fixed_charge_C_m3=0.,quantum_n_J_m2=0.,quantum_p_J_m2=0.,
                 heat_capacity_J_m3_K=1.6e6,thermal_conductivity_W_m_K=1.,heat_bath_K=None):
        self.mesh=mesh;self.nc=len(mesh.volumes_m3)
        if not self.nc:raise ValueError('nonempty cut-cell geometry required')
        self.vol=mesh.volumes_m3;self.bc=dict(dirichlet_V)
        self.T=float(_array(temperature_K,1,'reference temperature',positive=True)[0]);self.kt=KB*self.T
        names=dict(eps=(permittivity_F_m,True),mn=(mobility_n_m2_Vs,False),mp=(mobility_p_m2_Vs,False),
            Nc=(Nc_m3,True),Nv=(Nv_m3,True),Nt=(trap_density_m3,False),cn=(capture_n_m3_s,False),
            cp=(capture_p_m3_s,False),capacity=(heat_capacity_J_m3_K,True),conductivity=(thermal_conductivity_W_m_K,True))
        for name,(value,positive) in names.items():
            setattr(self,name,_array(value,self.nc,name,positive=positive,nonnegative=True))
        for name,value in dict(Ec=Ec_J,Eh=Eh_J,Et=trap_energy_J,rhofix=fixed_charge_C_m3).items():
            setattr(self,name,_array(value,self.nc,name))
        self.kn=float(_array(quantum_n_J_m2,1,'quantum n',nonnegative=True)[0])
        self.kp=float(_array(quantum_p_J_m2,1,'quantum p',nonnegative=True)[0])
        self.internal=np.array([f for f,face in enumerate(mesh.faces) if face.neighbor>=0],int)
        self.i=np.array([mesh.faces[f].owner for f in self.internal],int)
        self.j=np.array([mesh.faces[f].neighbor for f in self.internal],int)
        area=np.array([mesh.faces[f].area_vector_m2 for f in self.internal]).reshape(-1,3)
        delta=mesh.centroids_m[self.j]-mesh.centroids_m[self.i]
        norm=np.linalg.norm(area,axis=1);dist=np.sum(area*delta,axis=1)/norm
        if np.any(dist<=0):raise ValueError('positive projected center distances required')
        self.metric=norm/dist
        self.skew=float(np.max(np.linalg.norm(delta-area/norm[:,None]*dist[:,None],axis=1)/
            np.linalg.norm(delta,axis=1),initial=0))
        self.bath={} if heat_bath_K is None else dict(heat_bath_K)
        for f,t in self.bath.items():
            if (isinstance(f,bool) or not isinstance(f,(int,np.integer)) or not 0<=f<len(mesh.faces)
                    or mesh.faces[f].neighbor>=0 or not np.isscalar(t) or not np.isfinite(t) or t<=0):
                raise ValueError('heat bath requires boundary face indices and positive temperatures')

    def _validate_state(self,state):
        if not isinstance(state,CutCellState):raise ValueError('CutCellState required')
        for name in ('n_m3','p_m3','trap_fraction','temperature_K'):
            a=getattr(state,name)
            if a.shape!=(self.nc,) or not np.all(np.isfinite(a)):raise ValueError('invalid state '+name)
        if (np.any(state.n_m3<=0) or np.any(state.p_m3<=0) or np.any(state.temperature_K<=0)
                or np.any(state.trap_fraction<=0) or np.any(state.trap_fraction>=1)
                or not np.isfinite(state.time_s) or state.time_s<0):raise ValueError('invalid positive state or clock')

    def _poisson(self,n,p,f,atol):
        return solve_cut_cell_poisson(self.mesh,self.eps,self.rhofix+Q*(p-n-self.Nt*f),
            dirichlet_V=self.bc,charge_atol_C=atol)

    def _quantum(self,n,kappa,old=None):
        root=np.sqrt(n);previous=root if old is None else np.sqrt(old)
        diff=(root[self.i]-root[self.j])+(previous[self.i]-previous[self.j])
        weighted=kappa*self.metric*diff
        gradient=np.bincount(self.i,weighted,minlength=self.nc)-np.bincount(self.j,weighted,minlength=self.nc)
        return gradient/(self.vol*(root+previous))

    def _flux(self,n,phi,band,dos,mobility,sign,quantum):
        psi=(sign*Q*phi+band+quantum)/self.kt-np.log(dos)
        d=psi[self.j]-psi[self.i]
        a,b=mobility[self.i],mobility[self.j]
        mu=np.divide(2*a*b,a+b,out=np.zeros_like(a),where=(a+b)>0)
        return mu*self.kt/Q*self.metric*(_bernoulli(d)*n[self.i]-_bernoulli(-d)*n[self.j])

    def _div(self,flux):
        return np.bincount(self.i,flux,minlength=self.nc)-np.bincount(self.j,flux,minlength=self.nc)

    def energies(self,state,*,charge_atol_C):
        self._validate_state(state);n,p,f=state.n_m3,state.p_m3,state.trap_fraction
        poisson=self._poisson(n,p,f,charge_atol_C)
        qenergy=lambda a,k:float(np.sum(k*self.metric*(np.sqrt(a[self.i])-np.sqrt(a[self.j]))**2,dtype=np.longdouble))
        un=self.Ec+1.5*self.kt;up=self.Eh+1.5*self.kt
        return dict(electrostatic_J=poisson['electrostatic_energy_J'],
            carrier_J=float(np.sum(self.vol*(un*n+up*p),dtype=np.longdouble)),
            trap_J=float(np.sum(self.vol*self.Nt*self.Et*f,dtype=np.longdouble)),
            quantum_J=qenergy(n,self.kn)+qenergy(p,self.kp),
            thermal_J=float(np.sum(self.vol*self.capacity*state.temperature_K,dtype=np.longdouble))),poisson

    def step(self,state,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=250):
        """Advance owned state; failed conservation/energy gates raise atomically.

        Particle and energy budgets are absolute; no relative cancellation gate.
        Heat is computed from face work and capture reactions before the thermal
        solve, independently of the final stored-energy difference.
        """
        self._validate_state(state)
        for name,value in dict(dt_s=dt_s,particle_atol=particle_atol,energy_atol_J=energy_atol_J,charge_atol_C=charge_atol_C).items():
            _array(value,1,name,positive=True)
        n0,p0,f0=state.n_m3,state.p_m3,state.trap_fraction;nc=self.nc;dt=float(dt_s)
        scale_n=np.maximum.reduce([n0,self.Nt,np.ones(nc)])
        scale_p=np.maximum.reduce([p0,self.Nt,np.ones(nc)])
        cache={}
        def evaluate(x):
            n=np.exp(x[:nc]);p=np.exp(x[nc:2*nc]);f=expit(x[2*nc:])
            poisson=self._poisson(n,p,f,charge_atol_C);phi=poisson['cell_potential_V']
            qn=self._quantum(n,self.kn);qp=self._quantum(p,self.kp)
            fn=self._flux(n,phi,self.Ec,self.Nc,self.mn,-1,qn)
            fp=self._flux(p,phi,self.Eh,self.Nv,self.mp,1,qp)
            n1=self.Nc*np.exp(np.clip((self.Et-self.Ec-qn)/self.kt,-690,690))
            p1=self.Nv*np.exp(np.clip((-self.Et-self.Eh-qp)/self.kt,-690,690))
            rn=self.cn*(n*(1-f)-n1*f);rp=self.cp*(p*f-p1*(1-f))
            residual=np.r_[(n-n0+dt*self._div(fn)/self.vol+dt*self.Nt*rn)/scale_n,
                (p-p0+dt*self._div(fp)/self.vol+dt*self.Nt*rp)/scale_p,
                f-f0-dt*(rn-rp)]
            cache.update(n=n,p=p,f=f,poisson=poisson,fn=fn,fp=fp,rn=rn,rp=rp,residual=residual)
            return residual
        x0=np.r_[np.log(n0),np.log(p0),np.log(f0/(1-f0))]
        lower=np.r_[np.full(2*nc,-690.),np.full(nc,-35.)];upper=np.r_[np.full(2*nc,690.),np.full(nc,35.)]
        fit=least_squares(evaluate,x0,bounds=(lower,upper),xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=max_nfev)
        evaluate(fit.x);n,p,f=(cache[k] for k in ('n','p','f'))
        rn,rp,fn,fp=(cache[k] for k in ('rn','rp','fn','fp'))
        balances=np.r_[self.vol*(n-n0+dt*self.Nt*rn)+dt*self._div(fn),
            self.vol*(p-p0+dt*self.Nt*rp)+dt*self._div(fp),self.vol*self.Nt*(f-f0-dt*(rn-rp))]
        if not fit.success or np.max(abs(balances),initial=0)>particle_atol:
            raise ValueError('carrier/trap step failed absolute particle conservation budget')
        old_energy,old_poisson=self.energies(state,charge_atol_C=charge_atol_C)
        new_poisson=cache['poisson']
        if not old_poisson['valid'] or not new_poisson['valid']:raise ValueError('Poisson charge budget failed')
        midphi=(old_poisson['cell_potential_V']+new_poisson['cell_potential_V'])/2
        qn=self._quantum(n,self.kn,n0);qp=self._quantum(p,self.kp,p0)
        un=self.Ec+1.5*self.kt;up=self.Eh+1.5*self.kt
        en=un+qn-Q*midphi;ep=up+qp+Q*midphi
        face_heat=dt*(fn*(en[self.i]-en[self.j])+fp*(ep[self.i]-ep[self.j]))
        capture_heat=dt*self.vol*self.Nt*(rn*(un+qn-self.Et)+rp*(up+qp+self.Et))
        heat=capture_heat+np.bincount(self.i,face_heat/2,minlength=nc)+np.bincount(self.j,face_heat/2,minlength=nc)
        a,b=self.conductivity[self.i],self.conductivity[self.j]
        conductance=2*a*b/(a+b)*self.metric
        rows=np.r_[self.i,self.j,self.i,self.j];cols=np.r_[self.i,self.j,self.j,self.i]
        matrix=coo_matrix((np.r_[conductance,conductance,-conductance,-conductance],(rows,cols)),shape=(nc,nc)).tocsr()
        storage=self.vol*self.capacity;rhs=storage*state.temperature_K+heat
        bath_g=np.zeros(nc)
        for face_index,temp in self.bath.items():
            face=self.mesh.faces[face_index];i=face.owner;area=np.linalg.norm(face.area_vector_m2)
            dist=np.dot(face.area_vector_m2,face.centroid_m-self.mesh.centroids_m[i])/area
            g=self.conductivity[i]*area/dist;bath_g[i]+=g;rhs[i]+=dt*g*temp
        matrix=diags(storage+dt*bath_g)+dt*matrix
        temperature=spsolve(diags(1/storage)@matrix,rhs/storage)
        if not np.all(np.isfinite(temperature)) or np.any(temperature<=0):raise ValueError('nonpositive thermal state')
        result=CutCellState(n,p,f,temperature,state.time_s+dt)
        new_energy,_=self.energies(result,charge_atol_C=charge_atol_C)
        source=sum(-v*(new_poisson['integrated_D_flux_C'][face]-old_poisson['integrated_D_flux_C'][face]) for face,v in self.bc.items())
        heat_out=0.
        for face_index,temp in self.bath.items():
            face=self.mesh.faces[face_index];i=face.owner;area=np.linalg.norm(face.area_vector_m2)
            dist=np.dot(face.area_vector_m2,face.centroid_m-self.mesh.centroids_m[i])/area
            heat_out+=dt*self.conductivity[i]*area/dist*(temperature[i]-temp)
        increments=self.energy_increments(state,result,old_poisson,new_poisson)
        residual=float(np.longdouble(source)-sum(map(np.longdouble,increments.values()))-np.longdouble(heat_out))
        if abs(residual)>energy_atol_J:raise ValueError('full modeled energy residual exceeds absolute budget')
        flux_n=np.zeros(len(self.mesh.faces));flux_p=flux_n.copy();flux_n[self.internal]=fn;flux_p[self.internal]=fp
        return result,dict(valid=True,scope='fixed_electronic_temperature_SG_SRH_graph_DG_lattice_heat',
            complete_device_energy=False,modeled_energy_components_complete=True,
            device_energy_ledger_available=True,
            device_energy_components=('carrier','trap','thermal','quantum','electrostatic'),
            physical_validated=False,
            energy_before_J=old_energy,energy_after_J=new_energy,energy_increments_J=increments,
            source_work_J=float(source),outward_heat_J=float(heat_out),energy_residual_J=residual,
            transport_heat_J=float(face_heat.sum()),capture_heat_J=float(capture_heat.sum()),
            particle_residuals=balances,integrated_electron_particle_flux_s=flux_n,
            integrated_hole_particle_flux_s=flux_p,trap_electron_capture_rate_s=rn,trap_hole_capture_rate_s=rp,
            max_nonorthogonality=self.skew,orthogonal_transport_consistent=bool(self.skew<1e-12),
            missing_physics=['lattice_temperature_feedback_to_carriers','open_carrier_contact_energy_flux',
                'ferroelectric_and_domain_energy','native_backend_integration','general_skew_consistent_transport'])

    def energy_increments(self,old,new,old_poisson,new_poisson):
        """Factored differences avoid subtracting large absolute storage totals.

        With fixed voltage boundaries, the symmetric Poisson quadratic gives
        dU = rho_mid*V*dphi_cell. Stabilization energy is included by this
        identity, unlike an E_cell**2-only reconstruction on skew cuts.
        """
        ld=np.longdouble;vol=self.vol.astype(ld)
        dn=new.n_m3.astype(ld)-old.n_m3;dp=new.p_m3.astype(ld)-old.p_m3
        df=new.trap_fraction.astype(ld)-old.trap_fraction
        midrho=self.rhofix.astype(ld)+ld(Q)*((new.p_m3.astype(ld)+old.p_m3-new.n_m3.astype(ld)-old.n_m3
            -self.Nt.astype(ld)*(new.trap_fraction.astype(ld)+old.trap_fraction))/2)
        field=np.sum(vol*midrho*(new_poisson['cell_potential_V'].astype(ld)-old_poisson['cell_potential_V']))
        quantum=ld(0)
        for a,b,k in ((old.n_m3,new.n_m3,self.kn),(old.p_m3,new.p_m3,self.kp)):
            ra=np.sqrt(a.astype(ld));rb=np.sqrt(b.astype(ld))
            da=ra[self.i]-ra[self.j];db=rb[self.i]-rb[self.j]
            quantum+=np.sum(ld(k)*self.metric.astype(ld)*(db-da)*(db+da))
        return dict(electrostatic_J=float(field),
            carrier_J=float(np.sum(vol*((self.Ec.astype(ld)+ld(1.5)*ld(self.kt))*dn+
                (self.Eh.astype(ld)+ld(1.5)*ld(self.kt))*dp))),
            trap_J=float(np.sum(vol*self.Nt.astype(ld)*self.Et.astype(ld)*df)),quantum_J=float(quantum),
            thermal_J=float(np.sum(vol*self.capacity.astype(ld)*(new.temperature_K.astype(ld)-old.temperature_K))))
