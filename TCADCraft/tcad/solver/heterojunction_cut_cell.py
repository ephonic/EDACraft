"""Isothermal Boltzmann transport with two traces at finite-transfer interfaces.

The interface law is F=A*s*w_barrier*(a_owner-a_neighbor), where n=w*a,
w=Nc*exp(-(Ec-q*phi)/kT) for electrons, and analogously for holes. It obeys
detailed balance for arbitrary supplied band/DOS jumps. Finite s represents
an interface resistance; omitting an interface gives continuous activity.
This is a steady Python solver, with no thermal/quantum/trap energy claim.
"""
from collections.abc import Mapping
import warnings
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning
from .cut_cell_transport import Q,KB,_array
from .hybrid_mimetic import HybridMimeticOperator
from .cut_cell_poisson import solve_cut_cell_poisson
from .electrothermal_cut_cell import CarrierReservoir
from tcad.postprocess.cut_cell_terminals import validate_terminal_groups


class HeterojunctionActivityOperator:
    """HMM diffusion with two independent traces joined by positive conductance."""
    def __init__(self,mesh,interface_faces=()):
        self.base=HybridMimeticOperator(mesh);self.mesh=mesh
        self.nc=self.base.nc;self.nf=self.base.nf
        faces=list(interface_faces)
        if any(isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer)) or
               not 0<=f<self.nf or mesh.faces[f].neighbor<0 for f in faces):
            raise ValueError('interface requires internal face indices')
        if len(set(faces))!=len(faces):raise ValueError('duplicate interface face')
        self.interfaces=tuple(sorted(map(int,faces)));self.size=self.base.size+len(faces)
        self.other={f:self.base.size+k for k,f in enumerate(self.interfaces)}
        self.local=[];rows=[];cols=[];entries=[];cells=[]
        for c,(ids,matrix,gradient,local_faces,signs) in enumerate(self.base.local):
            ids=ids.copy()
            for k,(f,sign) in enumerate(zip(local_faces,signs)):
                if sign<0 and int(f) in self.other:ids[k+1]=self.other[int(f)]
            self.local.append((ids,matrix,local_faces,signs))
            rows.extend(np.repeat(ids,len(ids)));cols.extend(np.tile(ids,len(ids)))
            entries.extend(matrix.ravel());cells.extend([c]*matrix.size)
        self.rows=np.array(rows);self.cols=np.array(cols);self.entries=np.array(entries);self.cells=np.array(cells)

    def matrix(self,coefficient,interface_conductance):
        coefficient=_array(coefficient,self.nc,'activity diffusion',nonnegative=True)
        conductance=_array(interface_conductance,len(self.interfaces),'interface conductance',nonnegative=True)
        a=coo_matrix((self.entries*coefficient[self.cells],(self.rows,self.cols)),shape=(self.size,self.size)).tocsr()
        if len(conductance):
            i=np.array([self.nc+f for f in self.interfaces]);j=np.array([self.other[f] for f in self.interfaces])
            a+=coo_matrix((np.r_[conductance,conductance,-conductance,-conductance],
                (np.r_[i,j,i,j],np.r_[i,j,j,i])),shape=a.shape).tocsr()
        return a,coefficient,conductance

    def _result(self,values,coefficient,conductance,bc):
        flux=np.zeros(self.nf);opposite=np.zeros(self.nf)
        for c,(ids,matrix,faces,signs) in enumerate(self.local):
            outward=-coefficient[c]*(matrix@(values[ids]-values[c]))[1:]
            owner=signs>0;flux[faces[owner]]=outward[owner];opposite[faces[~owner]]=outward[~owner]
        local_flux=flux.copy()
        for f,face in enumerate(self.mesh.faces):
            if face.neighbor<0 and f not in bc:flux[f]=0.
        interface_flux=np.array([g*(values[self.nc+f]-values[self.other[f]]) for f,g in zip(self.interfaces,conductance)])
        internal=np.array([f for f,face in enumerate(self.mesh.faces) if face.neighbor>=0],int)
        neighbor_trace=values[self.nc:self.nc+self.nf].copy()
        for f in self.interfaces:neighbor_trace[f]=values[self.other[f]]
        return dict(cell_values=values[:self.nc],owner_trace=values[self.nc:self.nc+self.nf],
            neighbor_trace=neighbor_trace,flux=flux,local_owner_flux=local_flux,local_neighbor_flux=opposite,
            shared_flux_mismatch=flux[internal]+opposite[internal],interface_flux=interface_flux,
            interface_law_residual=np.array([flux[f]-v for f,v in zip(self.interfaces,interface_flux)]))

    def reconstruct(self,cell_values,coefficient,*,dirichlet,interface_conductance=()):
        v=_array(cell_values,self.nc,'activity');bc=self.base.boundary(dirichlet)
        matrix,a,g=self.matrix(coefficient,interface_conductance)
        values=np.r_[v,np.zeros(self.size-self.nc)]
        fixed=np.array([self.nc+f for f in bc],int);values[fixed]=list(bc.values())
        active=np.flatnonzero(matrix.diagonal()>0);free=np.setdiff1d(active,np.r_[np.arange(self.nc),fixed])
        if len(free):
            rhs=-matrix[free,:self.nc]@v-matrix[free][:,fixed]@values[fixed]
            values[free]=self.base._solve(matrix[free][:,free],rhs)
        return self._result(values,a,g,bc)

    def solve(self,source_integrals,coefficient,*,dirichlet,interface_conductance=()):
        source=_array(source_integrals,self.nc,'activity source');bc=self.base.boundary(dirichlet)
        if not bc:raise ValueError('Dirichlet activity reference required')
        matrix,a,g=self.matrix(coefficient,interface_conductance);values=np.zeros(self.size)
        fixed=np.array([self.nc+f for f in bc],int);values[fixed]=list(bc.values())
        free=np.setdiff1d(np.arange(self.size),fixed)
        rhs=np.r_[source,np.zeros(self.size-self.nc)]-matrix[:,fixed]@values[fixed]
        with warnings.catch_warnings():
            warnings.simplefilter('error',MatrixRankWarning)
            try:values[free]=self.base._solve(matrix[free][:,free],rhs[free])
            except MatrixRankWarning as error:raise ValueError('unanchored activity component') from error
        return self._result(values,a,g,bc)


class IsothermalHeterojunctionDevice:
    """Self-consistent steady Poisson/electron/hole solve, fixed T and reservoirs.

    Band energies share one global reference. A particle contact is required
    on every electrical boundary. Both carrier velocity maps must explicitly
    cover the same internal faces; zero velocity blocks that carrier.
    The high-band-side DOS defines w_barrier. This user-supplied detailed-
    balance law is not a universal mass/valley-dependent thermionic model.
    """
    def __init__(self,mesh,*,permittivity_F_m,dirichlet_V,particle_contacts,terminal_groups,
                 mobility_n_m2_Vs,mobility_p_m2_Vs,Nc_m3,Nv_m3,Ec_J,Eh_J,
                 temperature_K=300.,fixed_charge_C_m3=0.,
                 interface_velocity_n_m_s=None,interface_velocity_p_m_s=None):
        self.mesh=mesh;self.nc=len(mesh.volumes_m3);self.vol=mesh.volumes_m3
        self.T=float(_array(temperature_K,1,'temperature',positive=True)[0]);self.kt=KB*self.T
        self.bc=HybridMimeticOperator(mesh).boundary(dirichlet_V)
        self.groups=validate_terminal_groups(mesh,self.bc,terminal_groups)
        if not isinstance(particle_contacts,Mapping) or set(particle_contacts)!=set(self.bc):
            raise ValueError('particle reservoirs must cover every electrical boundary')
        self.contacts={}
        for f,r in particle_contacts.items():
            if isinstance(r,dict):r=CarrierReservoir(**r)
            if not isinstance(r,CarrierReservoir) or r.temperature_K!=self.T:
                raise ValueError('reservoir must have the device isothermal temperature')
            self.contacts[f]=r
        for name,value,positive in [('eps',permittivity_F_m,True),('mn',mobility_n_m2_Vs,True),
                ('mp',mobility_p_m2_Vs,True),('Nc',Nc_m3,True),('Nv',Nv_m3,True),
                ('Ec',Ec_J,False),('Eh',Eh_J,False),('fixed',fixed_charge_C_m3,False)]:
            setattr(self,name,_array(value,self.nc,name,positive=positive))
        vn={} if interface_velocity_n_m_s is None else interface_velocity_n_m_s
        vp={} if interface_velocity_p_m_s is None else interface_velocity_p_m_s
        if not isinstance(vn,Mapping) or not isinstance(vp,Mapping) or set(vn)!=set(vp):
            raise ValueError('electron/hole interface velocity maps must cover the same faces')
        self.operator=HeterojunctionActivityOperator(mesh,vn)
        self.vn=_array([vn[f] for f in self.operator.interfaces],len(vn),'electron transfer velocity',nonnegative=True)
        self.vp=_array([vp[f] for f in self.operator.interfaces],len(vp),'hole transfer velocity',nonnegative=True)

    def poisson(self,n,p,atol):
        return solve_cut_cell_poisson(self.mesh,self.eps,self.fixed+Q*(p-n),dirichlet_V=self.bc,charge_atol_C=atol)

    def carrier(self,density,poisson,*,hole=False):
        density=_array(density,self.nc,'carrier density',positive=True)
        band,dos,mu,sign,velocity=(self.Eh,self.Nv,self.mp,1,self.vp) if hole else (self.Ec,self.Nc,self.mn,-1,self.vn)
        logw=np.log(dos)-(band+sign*Q*poisson['cell_potential_V'])/self.kt
        gauge=float(max(logw));exponents=logw-gauge
        if min(exponents)<-600:raise ValueError('activity coefficient dynamic range exceeded')
        w=np.exp(exponents);activity=density/w;bc={};facew={}
        for f,r in self.contacts.items():
            c=self.mesh.faces[f].owner
            x=np.log(dos[c])-(band[c]+sign*Q*self.bc[f])/self.kt-gauge
            if abs(x)>600:raise ValueError('boundary activity dynamic range exceeded')
            bc[f]=(r.p_m3 if hole else r.n_m3)/np.exp(x)
        g=[]
        for f,s in zip(self.operator.interfaces,velocity):
            face=self.mesh.faces[f];i,j=face.owner,face.neighbor
            high=i if band[i]>=band[j] else j
            x=np.log(dos[high])-(band[high]+sign*Q*poisson['face_potential_V'][f])/self.kt-gauge
            if abs(x)>600:raise ValueError('interface activity dynamic range exceeded')
            g.append(np.linalg.norm(face.area_vector_m2)*s*np.exp(x))
            facew[f]=tuple(np.exp(np.log(dos[c])-(band[c]+sign*Q*poisson['face_potential_V'][f])/self.kt-gauge) for c in (i,j))
        result=self.operator.reconstruct(activity,mu*self.kt/Q*w,dirichlet=bc,interface_conductance=g)
        result['interface_owner_density_m3']=np.array([result['owner_trace'][f]*facew[f][0] for f in self.operator.interfaces])
        result['interface_neighbor_density_m3']=np.array([result['neighbor_trace'][f]*facew[f][1] for f in self.operator.interfaces])
        return result

    def solve(self,initial_n_m3,initial_p_m3,*,charge_atol_C,particle_flux_atol_s,current_atol_A,max_nfev=250):
        n0=_array(initial_n_m3,self.nc,'initial electron density',positive=True)
        p0=_array(initial_p_m3,self.nc,'initial hole density',positive=True)
        for name,value in dict(charge=charge_atol_C,particle=particle_flux_atol_s,current=current_atol_A).items():
            _array(value,1,name,positive=True)
        L=float(np.max(np.ptp(self.mesh.centroids_m,axis=0)))
        time=max(L,1e-12)**2/(max(max(self.mn),max(self.mp))*self.kt/Q)
        sn=self.vol*np.maximum(n0,1.)/time;sp=self.vol*np.maximum(p0,1.)/time;cache={}
        def evaluate(x):
            n,p=np.exp(x[:self.nc]),np.exp(x[self.nc:]);poisson=self.poisson(n,p,charge_atol_C)
            electrons=self.carrier(n,poisson);holes=self.carrier(p,poisson,hole=True)
            dn=self.mesh.divergence_integrals(electrons['flux']);dp=self.mesh.divergence_integrals(holes['flux'])
            cache.update(n=n,p=p,poisson=poisson,electrons=electrons,holes=holes,dn=dn,dp=dp)
            return np.r_[dn/sn,dp/sp]
        x0=np.r_[np.log(n0),np.log(p0)]
        fit=least_squares(evaluate,x0,bounds=(-600.,600.),xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=max_nfev)
        evaluate(fit.x)
        if not fit.success:raise ValueError('isothermal heterojunction nonlinear solve failed')
        result=dict(n_m3=cache['n'],p_m3=cache['p'],poisson=cache['poisson'],
            electrons=cache['electrons'],holes=cache['holes'],nfev=fit.nfev)
        totals={name:float(Q*sum(cache['electrons']['flux'][f]-cache['holes']['flux'][f] for f in faces))
            for name,faces in self.groups.items()}
        result.update(terminal_currents_A=totals,temperature_K=self.T,scope='isothermal_MB_two_trace_steady_Poisson_transport',
            energy_closure_accepted=False,complete_device_energy=False,physical_validated=False)
        audit=self.audit(result,charge_atol_C=charge_atol_C,particle_flux_atol_s=particle_flux_atol_s,current_atol_A=current_atol_A)
        if not audit['valid']:raise ValueError('isothermal heterojunction conservation or interface budget failed')
        result['audit']=audit
        return result

    def audit(self,result,*,charge_atol_C,particle_flux_atol_s,current_atol_A):
        """Recompute fields/fluxes and independently check the two-sided law."""
        for name,value in dict(charge=charge_atol_C,particle=particle_flux_atol_s,current=current_atol_A).items():
            _array(value,1,name,positive=True)
        n=_array(result['n_m3'],self.nc,'reported electrons',positive=True)
        p=_array(result['p_m3'],self.nc,'reported holes',positive=True)
        poisson=self.poisson(n,p,charge_atol_C);valid=bool(poisson['valid']);errors=[];laws=[];balances=[];fluxes=[]
        given_poisson=result['poisson']
        potential_error=max(float(np.max(abs(_array(given_poisson[key],len(poisson[key]),'reported '+key)-poisson[key]),initial=0))
            for key in ('cell_potential_V','face_potential_V'))
        displacement_error=float(np.max(abs(_array(given_poisson['integrated_D_flux_C'],len(self.mesh.faces),
            'reported displacement flux')-poisson['integrated_D_flux_C']),initial=0))
        valid=valid and potential_error<=64*np.finfo(float).eps*max(1.,float(np.max(abs(poisson['cell_potential_V']))))
        valid=valid and displacement_error<=charge_atol_C
        for density,hole,label in ((n,False,'electrons'),(p,True,'holes')):
            expected=self.carrier(density,poisson,hole=hole);given=result[label]
            flux=_array(given['flux'],len(self.mesh.faces),'reported number flux')
            errors.extend(expected['flux']-flux);balances.extend(self.mesh.divergence_integrals(flux));fluxes.append(flux)
            band,dos,speeds=(self.Eh,self.Nv,self.vp) if hole else (self.Ec,self.Nc,self.vn)
            one=_array(given['interface_owner_density_m3'],len(speeds),'owner interface density',positive=True)
            two=_array(given['interface_neighbor_density_m3'],len(speeds),'neighbor interface density',positive=True)
            for k,(f,s) in enumerate(zip(self.operator.interfaces,speeds)):
                face=self.mesh.faces[f];i,j=face.owner,face.neighbor;high=i if band[i]>=band[j] else j
                law=np.linalg.norm(face.area_vector_m2)*s*dos[high]*(one[k]/dos[i]*np.exp((band[i]-band[high])/self.kt)-
                    two[k]/dos[j]*np.exp((band[j]-band[high])/self.kt))
                laws.append(law-flux[f])
                # A blocked interface still has independently determined traces.
                speed=max(s,max(self.mn[i],self.mp[i])*self.kt/Q/self.vol[i]**(1/3))
                errors.extend([speed*np.linalg.norm(face.area_vector_m2)*(one[k]-expected['interface_owner_density_m3'][k]),
                    speed*np.linalg.norm(face.area_vector_m2)*(two[k]-expected['interface_neighbor_density_m3'][k])])
            errors.extend(expected['shared_flux_mismatch']);errors.extend(expected['interface_law_residual'])
        currents={name:float(Q*sum(fluxes[0][f]-fluxes[1][f] for f in faces)) for name,faces in self.groups.items()}
        if set(result['terminal_currents_A'])!=set(currents):raise ValueError('terminal coverage mismatch')
        current_errors=[float(result['terminal_currents_A'][name])-v for name,v in currents.items()]
        if not np.all(np.isfinite(current_errors)):raise ValueError('nonfinite reported terminal current')
        worst=lambda a:float(max(map(abs,a),default=0.))
        valid=valid and max(worst(errors),worst(laws),worst(balances))<=particle_flux_atol_s
        valid=valid and max(worst(current_errors),abs(sum(currents.values())))<=current_atol_A
        return dict(valid=bool(valid),max_constitutive_error_s=worst(errors),max_interface_law_error_s=worst(laws),
            max_particle_balance_s=worst(balances),terminal_KCL_residual_A=float(sum(currents.values())),
            max_terminal_current_error_A=worst(current_errors),max_potential_error_V=potential_error,
            max_displacement_flux_error_C=displacement_error,energy_closure_accepted=False)
