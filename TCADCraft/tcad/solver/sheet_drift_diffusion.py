"""Isothermal planar sheet DD with a local parallel-plate gate approximation.

This is a dedicated SI sheet path, separate from the volume Simulator. It uses
full-width ideal or resistive contacts, constant mobilities, no recombination and one
homogeneous sheet band model. It does not solve the surrounding 3D dielectric.
"""
import warnings
from dataclasses import replace

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from tcad.material.sheet import SheetMaterial, Q, KB, _finite, _positive_scalar


class SheetDriftDiffusion:
    """Finite-volume x/y sheet, with unknown phi, Fn and Fp at each node.

    x/y coordinates [m] strictly increase and each have >=2 nodes. Arrays have
    shape (ny,nx), C ordering. The left/right complete planes are contacts.
    Contact phi=terminal voltage. By default Fn=Fp=fermi_offset_eV-voltage.
    contact_resistance_ohm_m selects linear electrochemical edge contacts:
    scalar or (2,2), rows source/drain, columns electron/hole, in ohm*m.
    Each entry is positive and finite; this is not area resistivity or a
    Schottky/thermionic injection law. Electrostatic contacts remain pinned.
    Other boundaries block in-plane flux. Gate capacitance is per area [F/m²],
    in-plane sheet permittivity is epsilon_parallel*thickness [F]. Neither is
    a conversion of sheet carriers into effective volume densities.
    """
    def __init__(self, x_m, y_m, material, *, gate_capacitance_F_m2,
                 mobility_n_m2_Vs, mobility_p_m2_Vs, temperature_K=300.,
                 sheet_permittivity_F=0., doping_m2=0., fixed_charge_C_m2=0.,
                 transport_scheme='midpoint', contact_resistance_ohm_m=None,
                 thermionic_barrier_n_eV=None, dirac_contact_offset_eV=None):
        if not isinstance(material, SheetMaterial):
            raise TypeError('material must be a SheetMaterial, not a volume Material')
        self.material = material
        if transport_scheme not in ('midpoint','diffusion_enhanced'):
            raise ValueError('transport_scheme must be midpoint or diffusion_enhanced')
        self.transport_scheme=transport_scheme
        self.temperature_K = _positive_scalar(temperature_K, 'temperature_K')
        self.mu_n = _positive_scalar(mobility_n_m2_Vs, 'mobility_n_m2_Vs')
        self.mu_p = _positive_scalar(mobility_p_m2_Vs, 'mobility_p_m2_Vs')
        self.vt = KB*self.temperature_K/Q
        self.x = self._axis(x_m, 'x_m'); self.y = self._axis(y_m, 'y_m')
        self.shape = (len(self.y), len(self.x)); self.size = int(np.prod(self.shape))
        self.area = np.outer(self._widths(self.y), self._widths(self.x)).ravel()
        self.cap = self._field(gate_capacitance_F_m2, 'gate_capacitance_F_m2')
        if np.any(self.cap <= 0):
            raise ValueError('local gate capacitance must be positive')
        dielectric = _finite(sheet_permittivity_F, 'sheet_permittivity_F')
        if dielectric.ndim or dielectric < 0:
            raise ValueError('sheet_permittivity_F must be a nonnegative scalar')
        self.epsilon = float(dielectric)
        self.doping = self._field(doping_m2, 'doping_m2')
        self.fixed_charge = self._field(fixed_charge_C_m2, 'fixed_charge_C_m2')
        edges=[]
        for j in range(len(self.y)):
            for i in range(len(self.x)):
                a=j*len(self.x)+i
                if i+1<len(self.x):
                    edges.append((a,a+1,self._widths(self.y)[j]/(self.x[i+1]-self.x[i]),0,self.x[i+1]-self.x[i]))
                if j+1<len(self.y):
                    edges.append((a,a+len(self.x),self._widths(self.x)[i]/(self.y[j+1]-self.y[j]),1,self.y[j+1]-self.y[j]))
        self.edges=tuple(edges)
        self._edge_i=np.array([e[0] for e in edges]);self._edge_j=np.array([e[1] for e in edges])
        self._edge_geometry=np.array([e[2] for e in edges])
        for value in (self._edge_i,self._edge_j,self._edge_geometry):value.setflags(write=False)
        self.left=np.arange(len(self.y))*len(self.x)
        self.right=self.left+len(self.x)-1
        self.contacts=np.r_[self.left,self.right]
        self.dirac_contact_offset_eV=None
        self._dirac_contact_offsets=None
        if dirac_contact_offset_eV is not None:
            if contact_resistance_ohm_m is not None or thermionic_barrier_n_eV is not None:
                raise ValueError('choose one finite contact model')
            if material.dispersion!='dirac' or material.gap_eV!=0:
                raise ValueError('Dirac mode contacts require a gapless Dirac sheet')
            raw=_finite(dirac_contact_offset_eV,'dirac_contact_offset_eV')
            if raw.ndim!=0 and raw.shape!=(2,):
                raise ValueError('dirac_contact_offset_eV must be scalar or (source,drain)')
            offset=np.array(np.broadcast_to(raw,(2,)),copy=True)
            self.dirac_contact_offset_eV=offset
            self._dirac_contact_offsets=np.repeat(np.stack((offset,-offset)),len(self.y),axis=1)
            offset.setflags(write=False);self._dirac_contact_offsets.setflags(write=False)
        self.thermionic_barrier_n_eV=None
        self._thermionic_barriers=None
        if thermionic_barrier_n_eV is not None:
            if contact_resistance_ohm_m is not None:
                raise ValueError('choose either thermionic barriers or contact resistance')
            if material.dispersion!='parabolic':
                raise ValueError('thermionic edge contacts currently require parabolic sheet bands')
            raw=_finite(thermionic_barrier_n_eV,'thermionic_barrier_n_eV')
            if raw.ndim!=0 and raw.shape!=(2,):
                raise ValueError('thermionic_barrier_n_eV must be scalar or (source,drain)')
            barrier=np.array(np.broadcast_to(raw,(2,)),copy=True)
            if np.any(barrier<0) or np.any(barrier>material.gap_eV):
                raise ValueError('electron barrier must lie between zero and the band gap')
            self.thermionic_barrier_n_eV=barrier
            self._thermionic_barriers=np.repeat(np.stack((barrier,material.gap_eV-barrier)),len(self.y),axis=1)
            barrier.setflags(write=False);self._thermionic_barriers.setflags(write=False)
        self.contact_resistance_ohm_m=None
        self._contact_conductance=None
        if contact_resistance_ohm_m is not None:
            raw=_finite(contact_resistance_ohm_m,'contact_resistance_ohm_m')
            if raw.ndim!=0 and raw.shape!=(2,2):
                raise ValueError('contact_resistance_ohm_m must be scalar or (2,2): terminals x carriers')
            resistance=np.array(np.broadcast_to(raw,(2,2)),copy=True)
            if np.any(resistance<=0):
                raise ValueError('contact_resistance_ohm_m must be positive; use None for ideal contacts')
            with np.errstate(over='ignore',under='ignore',divide='ignore',invalid='ignore'):
                conductance=(self._widths(self.y)[None,None,:]/resistance[:,:,None])
            if not np.all(np.isfinite(conductance)) or np.any(conductance<=0):
                raise ValueError('contact node conductance must be representable and positive')
            self.contact_resistance_ohm_m=resistance
            self._contact_conductance=conductance.transpose(1,0,2).reshape(2,-1).copy()
            resistance.setflags(write=False);self._contact_conductance.setflags(write=False)
        self._has_finite_contacts=(self._contact_conductance is not None or self._thermionic_barriers is not None
                                   or self._dirac_contact_offsets is not None)
        for value in (self.area,self.cap,self.doping,self.fixed_charge,self.left,self.right,self.contacts):
            value.setflags(write=False)

    @staticmethod
    def _axis(value, name):
        result=np.array(_finite(value,name),copy=True)
        if result.ndim!=1 or len(result)<2 or np.any(np.diff(result)<=0):
            raise ValueError(f'{name} must be a strictly increasing vector with >=2 nodes')
        result.setflags(write=False)
        return result

    @staticmethod
    def _widths(axis):
        return np.r_[np.diff(axis)[0]/2,(axis[2:]-axis[:-2])/2,np.diff(axis)[-1]/2]

    def _field(self,value,name):
        raw=_finite(value,name)
        try:result=np.array(np.broadcast_to(raw,self.shape),copy=True).ravel()
        except ValueError as exc:raise ValueError(f'{name} must be scalar or shape {self.shape}') from exc
        return result

    def _contact_terms(self,u,bc):
        fields=u.reshape(3,self.size)
        drops=np.stack((fields[1,self.contacts]-bc[1],fields[2,self.contacts]-bc[2]))
        if self._dirac_contact_offsets is not None:
            from .sheet_dirac_contact import dirac_edge_current
            values=[dirac_edge_current(drops[s],self._dirac_contact_offsets[s],temperature_K=self.temperature_K,
                fermi_velocity_m_s=self.material.fermi_velocity_m_s,degeneracy=deg,
                width_m=np.tile(self._widths(self.y),2),sign=sign)
                for s,deg,sign in ((0,self.material.degeneracy_n,1),(1,self.material.degeneracy_p,-1))]
            return drops,np.array([v[0] for v in values]),np.array([v[1] for v in values])
        if self._thermionic_barriers is None:
            return drops,self._contact_conductance*drops,self._contact_conductance
        from .sheet_thermionic import thermionic_current
        currents=[];slopes=[]
        for species,(mass,deg,sign) in enumerate(((self.material.mass_n_m0,self.material.degeneracy_n,1),
                                                 (self.material.mass_p_m0,self.material.degeneracy_p,-1))):
            current,slope=thermionic_current(drops[species],self._thermionic_barriers[species],
                temperature_K=self.temperature_K,mass_m0=mass,degeneracy=deg,
                width_m=np.tile(self._widths(self.y),2),sign=sign)
            currents.append(current);slopes.append(slope)
        return drops,np.array(currents),np.array(slopes)

    def _trap_statistics(self,st,u):
        trap=getattr(self,'_sheet_trap',None)
        if trap is None:return st,None,None,None
        model,old,dt=trap
        from .sheet_trap_balance import EnergySheetTrap
        if type(model) is EnergySheetTrap:
            phi,fn,fp=u.reshape(3,self.size)
            terms=model.evaluate(self.material,phi,fn,fp,self.temperature_K,old,dt,
                equilibrium_fermi_eV=getattr(self,'_sheet_equilibrium_fermi_eV',None))
            dfn=terms['df_dFn'];dfp=terms['df_dFp']
        else:
            terms=model.evaluate(st.n_m2,st.p_m2,old,dt)
            dfn=terms['df_dn']*st.dn_dFn_m2_eV
            dfp=-terms['df_dp']*st.minus_dp_dFp_m2_eV
        dphi=terms['df_dphi'] if 'df_dphi' in terms else dfn+dfp
        charged=replace(st,charge_C_m2=st.charge_C_m2+terms['charge_C_m2'],
            quantum_capacitance_F_m2=st.quantum_capacitance_F_m2+Q*model.density_m2*dphi)
        return charged,terms,dfn,dfp

    def _evaluate(self,u,gate,bc,jacobian=True):
        N=self.size;phi,fn,fp=u.reshape(3,N)
        st=self.material.statistics(phi,fn,fp,self.temperature_K)
        n,p,an,ap=st.n_m2,st.p_m2,st.dn_dFn_m2_eV,st.minus_dp_dFp_m2_eV
        charged,trap,dfn,dfp=self._trap_statistics(st,u)
        electrostatic, electrostatic_scale, diagonal, extra = self._electrostatic(phi,gate,charged)
        r=np.zeros((3,N));r[0]=electrostatic
        scales=np.zeros((3,N))
        scales[0]=electrostatic_scale
        rows=[];cols=[];data=[]
        def add(a,b,v):
            if jacobian:rows.append(a);cols.append(b);data.append(v)
        if jacobian:
            for i in range(N):
                add(i,i,diagonal[i])
                tn=0. if trap is None else self._sheet_trap[0].density_m2[i]*dfn[i]
                tp=0. if trap is None else self._sheet_trap[0].density_m2[i]*dfp[i]
                add(i,N+i,self.area[i]*Q*(an[i]+tn));add(i,2*N+i,self.area[i]*Q*(ap[i]+tp))
            if extra is not None:
                extra=extra.tocoo()
                rows.extend(extra.row.tolist());cols.extend(extra.col.tolist());data.extend(extra.data.tolist())
        fitted={}
        if self.transport_scheme=='diffusion_enhanced':
            from .sheet_flux import fitted_conductance
            a,b=self._edge_i,self._edge_j
            for block,density,F,mu,sign in ((1,n,fn,self.mu_n,1),(2,p,fp,self.mu_p,-1)):
                offset=-self.material.reference_eV-self.material.gap_eV/2 if sign==1 else self.material.reference_eV-self.material.gap_eV/2
                eta=(sign*(F+phi)+offset)/self.vt
                fitted[block]=fitted_conductance(phi[a],phi[b],F[a],F[b],eta[a],eta[b],density[a],
                    vt=self.vt,dispersion=self.material.dispersion,sign=sign,prefactor=Q*mu*self._edge_geometry)
        currents=[];dissipation=0.
        for edge_index,(i,j,geometry,axis,distance) in enumerate(self.edges):
            k=self.epsilon*geometry
            field=k*(phi[i]-phi[j]);r[0,i]+=field;r[0,j]-=field
            scales[0,i]+=k*self.vt;scales[0,j]+=k*self.vt
            add(i,i,k);add(i,j,-k);add(j,j,k);add(j,i,-k)
            edge=[]
            for block,density,derivative,mu,fermi,sign in ((1,n,an,self.mu_n,fn,1),(2,p,ap,self.mu_p,fp,-1)):
                factor=Q*mu*geometry/2
                conductance=fitted[block][0][edge_index] if fitted else factor*(density[i]+density[j])
                if not np.isfinite(conductance) or conductance<=0:
                    raise FloatingPointError('sheet edge conductivity is not representable and positive')
                delta=fermi[i]-fermi[j];flow=conductance*delta
                r[block,i]+=flow;r[block,j]-=flow
                scales[block,i]+=conductance*self.vt;scales[block,j]+=conductance*self.vt
                # I along i -> j is +G*(F_j-F_i); continuity residual is -div(I).
                edge.append(-flow)
                dissipation+=conductance*delta*delta
                for endpoint,node in enumerate((i,j)):
                    if fitted:
                        partial=fitted[block][1]
                        dphi=conductance*delta*partial[endpoint][edge_index]
                        dfermi=conductance*delta*partial[endpoint+2][edge_index]+(conductance if node==i else -conductance)
                    else:
                        dphi=sign*factor*derivative[node]*delta
                        dfermi=dphi+(conductance if node==i else -conductance)
                    add(block*N+i,node,dphi);add(block*N+j,node,-dphi)
                    add(block*N+i,block*N+node,dfermi);add(block*N+j,block*N+node,-dfermi)
            currents.append(edge)
        electrostatic_rows=r[0].copy()
        storage=getattr(self,'_transient_storage',None)
        if storage is not None:
            old_n,old_p,dt=storage
            # r=-div(J). Electron/hole charge is -q*n/+q*p, respectively.
            for block,density,old,derivative,sign in ((1,n,old_n,an,1),(2,p,old_p,ap,-1)):
                mass=Q*self.area/dt
                r[block]+=sign*mass*(density-old)
                scales[block]+=mass*(density+old+self.vt*derivative)
                for i in range(N):
                    add(block*N+i,i,mass[i]*derivative[i])
                    add(block*N+i,block*N+i,mass[i]*derivative[i])
        if trap is not None and self._sheet_trap[2] is not None:
            factor=Q*self.area*self._sheet_trap[0].density_m2
            for block,name,sign in ((1,'electron',1),(2,'hole',-1)):
                short='rn' if block==1 else 'rp'
                r[block]+=sign*factor*trap[name+'_capture_s']
                scales[block]+=factor*trap[name+'_activity_s']
                if 'df_dFn' in trap:
                    dn=trap['d'+short+'_dFn'];dp=trap['d'+short+'_dFp']
                else:
                    dn=trap['d'+short+'_dn']*an;dp=-trap['d'+short+'_dp']*ap
                for i in range(N):
                    if factor[i]==0:continue
                    add(block*N+i,i,sign*factor[i]*(dn[i]+dp[i]))
                    add(block*N+i,N+i,sign*factor[i]*dn[i])
                    add(block*N+i,2*N+i,sign*factor[i]*dp[i])
        contact_terms=self._contact_terms(u,bc) if self._has_finite_contacts else None
        for block in range(3):
            for position,(i,value) in enumerate(zip(self.contacts,bc[block])):
                row=block*N+i
                if block and self._has_finite_contacts:
                    # r=-div(I_sheet), I_metal=Gc*(F_sheet-F_metal).
                    # Thus r+I_metal=0, retaining every in-plane FV term.
                    g=contact_terms[2][block-1,position]
                    r[block,i]+=contact_terms[1][block-1,position];scales[block,i]+=g*self.vt
                    add(row,row,g)
                else:
                    r[block,i]=u[row]-value;scales[block,i]=self.vt
        flat_scale=scales.ravel()
        if not np.all(np.isfinite(r)) or not np.all(np.isfinite(flat_scale)) or np.any(flat_scale<=0):
            raise FloatingPointError('sheet equations or row scales are not representable')
        J=None
        if jacobian:
            J=coo_matrix((data,(rows,cols)),shape=(3*N,3*N)).tolil()
            for block in range(3):
                if block and self._has_finite_contacts:continue
                for i in self.contacts:
                    row=block*N+i;J.rows[row]=[row];J.data[row]=[1.]
            J=J.tocsr()
        return r.ravel(),flat_scale,J,st,np.asarray(currents),float(dissipation),electrostatic_rows

    def _electrostatic(self,phi,gate,st):
        """Local gate terms; subclasses may supply a nonlocal dielectric map."""
        rho=st.charge_C_m2+Q*self.doping+self.fixed_charge
        return (self.area*(self.cap*(phi-gate)-rho),
            self.area*(self.cap*self.vt+Q*(st.n_m2+st.p_m2+np.abs(self.doping))+np.abs(self.fixed_charge)),
            self.area*(self.cap+st.quantum_capacitance_F_m2),None)

    def _charge_ledger(self,phi,gate,st,electrostatic):
        gate_charge=float(np.sum(self.area*self.cap*(gate-phi)))
        sheet_charge=float(np.sum(self.area*(st.charge_C_m2+Q*self.doping+self.fixed_charge)))
        contact_charge={name:float(np.sum(electrostatic[nodes])) for name,nodes in (('source',self.left),('drain',self.right))}
        return dict(gate_charge_C=gate_charge,sheet_charge_C=sheet_charge,contact_charge_C=contact_charge,
            gauss_charge_sum_C=gate_charge+sheet_charge+sum(contact_charge.values()))

    def _contact_boundary_conditions(self,source,drain,offset):
        """Pinned sheet potential and metal Fermi energies at both contacts.

        The dielectric subclass uses the same pinned potential on finite
        side electrodes, including the existing band-alignment convention.
        Callers validate the three scalar voltage arguments first.
        """
        contact_voltage=np.r_[np.full(len(self.left),source),np.full(len(self.right),drain)]
        bc=(contact_voltage,offset-contact_voltage,offset-contact_voltage)
        if self._thermionic_barriers is not None:
            bc=(contact_voltage+self.material.reference_eV+self.material.gap_eV/2-offset-
                self._thermionic_barriers[0],bc[1],bc[2])
        elif self._dirac_contact_offsets is not None:
            bc=(contact_voltage+self.material.reference_eV-offset-self._dirac_contact_offsets[0],bc[1],bc[2])
        return bc

    def solve(self, *, gate_voltage_V, drain_voltage_V=0., source_voltage_V=0.,
              fermi_offset_eV=0., initial=None, max_iter=80, tolerance=1e-10):
        """Solve simultaneous nonlinear sheet Poisson and both continuity rows.

        The default midpoint scheme uses arithmetic sheet conductivity.
        transport_scheme='diffusion_enhanced' selects modified SG with a
        logarithmic-statistics diffusion enhancement. Both are conservative
        and preserve equilibrium. The latter is not an exact FD edge BVP.
        Boundary currents are positive entering the sheet. In steady state
        their sum is zero; terminal voltage work equals sheet plus contact
        dissipation. With finite contacts, returned metal currents come from
        the injection law, including at nonconverged iterates. Separate sheet
        crossing currents and contact drops expose continuity defects.
        Iteration/line-search stops return the last accepted iterate with
        converged=False. Invalid inputs, unrepresentable quantities and a
        singular linear system may raise exceptions.
        """
        if isinstance(max_iter,(bool,np.bool_)) or not isinstance(max_iter,(int,np.integer)) or max_iter<1:
            raise ValueError('max_iter must be a positive integer')
        tol=_positive_scalar(tolerance,'tolerance')
        voltages=[]
        for value,name in ((source_voltage_V,'source_voltage_V'),(drain_voltage_V,'drain_voltage_V'),(fermi_offset_eV,'fermi_offset_eV')):
            raw=_finite(value,name)
            if raw.ndim:raise ValueError(f'{name} must be scalar')
            voltages.append(float(raw))
        source,drain,offset=voltages;gate=self._field(gate_voltage_V,'gate_voltage_V')
        bc=self._contact_boundary_conditions(source,drain,offset)
        fraction=(self.x-self.x[0])/(self.x[-1]-self.x[0])
        potential=np.broadcast_to(source+(drain-source)*fraction,self.shape).ravel()
        u=np.r_[potential,offset-potential,offset-potential].copy()
        if initial is not None:
            if not isinstance(initial,dict):raise ValueError('initial must contain phi_V, Fn_eV and Fp_eV')
            u=np.concatenate([self._field(initial[k],k) for k in ('phi_V','Fn_eV','Fp_eV')])
        for block in range(3):
            if block and self._has_finite_contacts:continue
            u[block*self.size+self.contacts]=bc[block]
        u=self._initial_unknowns(u,gate,initial)
        linear=self._linear_context(tol)
        history=[];status='max_iterations';iterations=0
        for iteration in range(max_iter+1):
            evaluated=self._evaluate(u,gate,bc)
            r,scale,J=evaluated[:3];norm=float(np.max(np.abs(r/scale)));history.append(norm)
            iterations=iteration
            if norm<=tol:status='converged';break
            if iteration==max_iter:break
            with warnings.catch_warnings():
                warnings.simplefilter('error',MatrixRankWarning)
                A=J.multiply((1/scale)[:,None]).tocsr()
                step=spsolve(A,-r/scale) if linear is None else linear.solve(A,-r/scale)
            if not np.all(np.isfinite(step)):
                status='linear_failure';break
            factor=min(1.,8*self.vt/max(float(np.max(np.abs(step))),self.vt))
            accepted=False
            for backtrack in range(32):
                trial=u+factor*step
                try:
                    trial_r=self._evaluate(trial,gate,bc,False)[0]
                    merit=float(np.max(np.abs(trial_r/scale)))
                    accepted=merit<=(1-1e-4*factor)*norm or merit<=tol
                except (FloatingPointError,OverflowError):accepted=False
                if accepted:u=trial;break
                factor*=.5
            if not accepted:status='line_search_failed';break
        # Re-evaluate at the actual final accepted iterate, never at a trial.
        evaluated=self._evaluate(u,gate,bc)
        result=self._result(u,gate,bc,evaluated,status=status,iterations=iterations,
            history=history,source=source,drain=drain)
        self._finish_linear_context(linear,result)
        return result

    def _linear_context(self,tolerance):
        return None

    def _finish_linear_context(self,context,result):
        pass

    def _initial_unknowns(self,u,gate,initial):
        """Allow a dielectric backend to append its own potential unknowns."""
        return u

    def _result(self,u,gate,bc,evaluated,*,status,iterations,history,source,drain):
        """Format an evaluated accepted iterate without running another solve."""
        r,scale,J,st,currents,power,electrostatic=evaluated
        terminal={}
        for name,nodes in (('source',self.left),('drain',self.right)):
            node_set=set(nodes.tolist());value=0.
            for edge,current in zip(self.edges,currents):
                i,j=edge[:2]
                if i in node_set and j not in node_set:value+=float(np.sum(current))
                elif j in node_set and i not in node_set:value-=float(np.sum(current))
            terminal[name]=value
        phi,fn,fp=u.reshape(3,self.size)
        contact_result={}
        if self._has_finite_contacts:
            drops,injection,_=self._contact_terms(u,bc)
            contact_power=float(np.sum(injection*drops))
            if not np.all(np.isfinite(injection)) or not np.isfinite(contact_power):
                raise FloatingPointError('contact currents or dissipation are not representable')
            contact_result=dict(contact_model='linear_electrochemical_edge',
                contact_fermi_drop_eV=drops.reshape(2,2,len(self.y)).transpose(1,0,2).copy(),
                contact_currents_into_sheet_A=injection.reshape(2,2,len(self.y)).transpose(1,0,2).copy(),
                sheet_terminal_currents_into_sheet_A=terminal.copy(),
                sheet_dissipation_W=power,contact_dissipation_W=contact_power)
            if self._dirac_contact_offsets is not None:
                contact_result.update(contact_model='dirac_fd_mode_supply_edge',
                    dirac_contact_offset_eV=self.dirac_contact_offset_eV.copy())
            elif self._thermionic_barriers is None:
                contact_result['contact_resistance_ohm_m']=self.contact_resistance_ohm_m.copy()
            else:
                contact_result.update(contact_model='parabolic_fd_thermionic_edge',
                    thermionic_barrier_n_eV=self.thermionic_barrier_n_eV.copy())
            terminal={name:float(np.sum(injection[:,a*len(self.y):(a+1)*len(self.y)]))
                      for a,name in enumerate(('source','drain'))}
            power+=contact_power
        charged,trap,_,_=self._trap_statistics(st,u)
        charge_ledger=self._charge_ledger(phi,gate,charged,electrostatic)
        result=dict(converged=status=='converged',status=status,iterations=iterations,
            residual_scaled_linf=float(np.max(np.abs(r/scale))),residual_history=np.array(history),
            terminal_currents_into_sheet_A=terminal,terminal_current_sum_A=sum(terminal.values()),
            dissipation_W=power,terminal_power_W=source*terminal['source']+drain*terminal['drain'],
            **contact_result,
            **charge_ledger,
            edge_nodes=np.array([e[:2] for e in self.edges],dtype=int),edge_currents_A=currents.copy(),
            model='isothermal_sheet_dd_local_gate',constants_profile='si_sheet',
            phi_V=phi.reshape(self.shape).copy(),Fn_eV=fn.reshape(self.shape).copy(),Fp_eV=fp.reshape(self.shape).copy())
        for name,value in (('n_m2',st.n_m2),('p_m2',st.p_m2),('charge_C_m2',st.charge_C_m2),
                           ('quantum_capacitance_F_m2',st.quantum_capacitance_F_m2)):
            result[name]=value.reshape(self.shape).copy()
        if self.transport_scheme!='midpoint':result['transport_scheme']=self.transport_scheme
        if trap is not None:
            trap_charge=float(np.dot(self.area,trap['charge_C_m2']))
            result.update(trap_occupancy=trap['occupancy'].reshape(self.shape).copy(),
                trap_charge_C_m2=trap['charge_C_m2'].reshape(self.shape).copy(),
                trap_electron_capture_s=trap['electron_capture_s'].reshape(self.shape).copy(),
                trap_hole_capture_s=trap['hole_capture_s'].reshape(self.shape).copy(),
                trap_charge_C=trap_charge,untrapped_sheet_charge_C=result['sheet_charge_C']-trap_charge,
                trap_rates_active=self._sheet_trap[2] is not None)
        return result
