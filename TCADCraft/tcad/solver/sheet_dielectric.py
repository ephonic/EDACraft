"""Cartesian dielectric Poisson coupled to an aligned, zero-thickness sheet.

Cellwise isotropic permittivity is integrated over node-centred box faces.
Top/bottom planes are ideal gates. Optional finite side electrodes cover
mesh-aligned z intervals at the full-width source/drain faces; remaining
outer faces are insulating. There is
no bulk free charge. The default dense sheet Schur complement eliminates
dielectric unknowns exactly. The opt-in coupled backend retains free bulk
potentials in a sparse system, without constructing dense sheet maps.
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy.sparse import bmat, coo_matrix, csr_matrix, diags, hstack, vstack
from scipy.sparse.linalg import splu, spsolve

from tcad.material.sheet import Q, _finite
from .sheet_drift_diffusion import SheetDriftDiffusion
from ._sheet_linear import _ReusedGMRES
from ._sheet_ordering import _geometric_nd_permutation, _SymmetricPermutation


@dataclass(frozen=True)
class _GateDrive:
    values: np.ndarray
    load: np.ndarray
    electrode_values: np.ndarray
    free_potential_V: np.ndarray | None = None


class SheetDielectricPoisson:
    """Aligned Cartesian box [z,y,x], with an interior sheet at z[sheet_index].

    permittivity_F_m is a positive scalar or cell array (nz-1,ny-1,nx-1).
    Interfaces must follow cell boundaries; no harmonic interpolation of
    nodal material labels is used. The sheet has no effective carrier volume.
    schur_rhs_block_size optionally bounds the number of dense right-hand-side
    columns per bulk solve. None preserves the original all-column algorithm.
    This bounds a temporary workspace, not the LU factor or dense sheet maps.
    backend='coupled' assembles sparse blocks without Schur elimination or a
    stored bulk factor. Its linear solves use sparse direct factorization;
    practical mesh size is limited by available factorization memory.
    """
    def __init__(self,x_m,y_m,z_m,*,sheet_index,permittivity_F_m,contact_z_bounds_m=None,schur_rhs_block_size=None,backend='schur'):
        if not isinstance(backend,str) or backend not in ('schur','coupled'):
            raise ValueError("backend must be 'schur' or 'coupled'")
        if backend=='coupled' and schur_rhs_block_size is not None:
            raise ValueError('schur_rhs_block_size requires the schur backend')
        self.backend=backend
        if schur_rhs_block_size is not None and (isinstance(schur_rhs_block_size,(bool,np.bool_))
                or not isinstance(schur_rhs_block_size,(int,np.integer)) or schur_rhs_block_size<=0):
            raise ValueError('schur_rhs_block_size must be a positive integer or None')
        self.schur_rhs_block_size=None if schur_rhs_block_size is None else int(schur_rhs_block_size)
        self.x=SheetDriftDiffusion._axis(x_m,'x_m')
        self.y=SheetDriftDiffusion._axis(y_m,'y_m')
        self.z=SheetDriftDiffusion._axis(z_m,'z_m')
        nz,ny,nx=len(self.z),len(self.y),len(self.x)
        if isinstance(sheet_index,(bool,np.bool_)) or not isinstance(sheet_index,(int,np.integer)) or not 0<sheet_index<nz-1:
            raise ValueError('sheet_index must select an interior z node plane')
        if backend=='schur' and (nx*ny>1024 or nx*ny*nz>100000):
            raise ValueError('dense sheet Schur complement is limited to 1024 sheet / 100000 bulk nodes')
        self.sheet_index=int(sheet_index);self.shape=(nz,ny,nx);self.sheet_shape=(ny,nx)
        self.size=nx*ny;self.area=np.outer(SheetDriftDiffusion._widths(self.y),SheetDriftDiffusion._widths(self.x)).ravel()
        self.contact_z_bounds_m=None
        if contact_z_bounds_m is not None:
            raw=_finite(contact_z_bounds_m,'contact_z_bounds_m')
            if raw.shape not in ((2,),(2,2)):
                raise ValueError('contact_z_bounds_m must be (lower,upper) or (2,2) for source/drain')
            bounds=np.array(np.broadcast_to(raw,(2,2)),copy=True)
            for pair in bounds:
                if not self.z[0]<pair[0]<self.z[self.sheet_index]<pair[1]<self.z[-1]:
                    raise ValueError('contact bounds must strictly enclose the sheet and lie inside the gates')
                for k,value in enumerate(pair):
                    index=int(np.argmin(abs(self.z-value)))
                    roundoff=32*np.finfo(float).eps*max(abs(self.z[0]),abs(self.z[-1]),self.z[-1]-self.z[0])
                    if abs(self.z[index]-value)>roundoff:
                        raise ValueError('contact bounds must coincide with z mesh nodes')
                    pair[k]=self.z[index]
                if not self.z[0]<pair[0]<self.z[self.sheet_index]<pair[1]<self.z[-1]:
                    raise ValueError('contact bounds must select nodes strictly below and above the sheet')
            bounds.setflags(write=False);self.contact_z_bounds_m=bounds
        try:
            eps=np.array(np.broadcast_to(_finite(permittivity_F_m,'permittivity_F_m'),(nz-1,ny-1,nx-1)),copy=True)
        except ValueError as exc:
            raise ValueError('permittivity_F_m must be scalar or cell-shaped (nz-1,ny-1,nx-1)') from exc
        if np.any(eps<=0):raise ValueError('permittivity_F_m must be positive')
        self.permittivity_F_m=eps
        dx,dy,dz=np.diff(self.x),np.diff(self.y),np.diff(self.z)
        # Each cell contributes a quarter face to each of its parallel edges.
        gx=np.zeros((nz,ny,nx-1));gy=np.zeros((nz,ny-1,nx));gz=np.zeros((nz-1,ny,nx))
        for a in (0,1):
            for b in (0,1):
                gx[a:a+nz-1,b:b+ny-1,:]+=eps*dz[:,None,None]*dy[None,:,None]/(4*dx[None,None,:])
                gy[a:a+nz-1,:,b:b+nx-1]+=eps*dz[:,None,None]*dx[None,None,:]/(4*dy[None,:,None])
                gz[:,a:a+ny-1,b:b+nx-1]+=eps*dy[None,:,None]*dx[None,None,:]/(4*dz[:,None,None])
        nodes=np.arange(nx*ny*nz).reshape(self.shape)
        starts=np.r_[nodes[:,:,:-1].ravel(),nodes[:,:-1,:].ravel(),nodes[:-1,:,:].ravel()]
        ends=np.r_[nodes[:,:,1:].ravel(),nodes[:,1:,:].ravel(),nodes[1:,:,:].ravel()]
        g=np.r_[gx.ravel(),gy.ravel(),gz.ravel()]
        if not np.all(np.isfinite(g)) or np.any(g<=0):raise FloatingPointError('dielectric conductances are not representable')
        self.edge_nodes=np.column_stack((starts,ends));self.edge_capacitance_F=g
        self.laplacian=coo_matrix((np.r_[g,g,-g,-g],(np.r_[starts,ends,starts,ends],np.r_[starts,ends,ends,starts])),shape=(nodes.size,nodes.size)).tocsr()
        self.sheet_nodes=nodes[self.sheet_index].ravel()
        self.gate_nodes=np.r_[nodes[0].ravel(),nodes[-1].ravel()] # bottom, top
        self.sheet_contact_nodes=np.r_[np.arange(ny)*nx,np.arange(ny)*nx+nx-1]
        electrodes=[]
        for terminal,xindex in enumerate((0,nx-1)):
            mask=np.zeros(nz,dtype=bool)
            if self.contact_z_bounds_m is not None:
                lower,upper=self.contact_z_bounds_m[terminal]
                mask=(self.z>=lower)&(self.z<=upper)
                mask[self.sheet_index]=False # sheet-edge reaction is accounted separately
            electrodes.append(nodes[mask,:,xindex].ravel())
        self.source_electrode_nodes,self.drain_electrode_nodes=electrodes
        self.electrode_nodes=np.r_[*electrodes]
        self.free_nodes=np.setdiff1d(nodes.ravel(),np.r_[self.sheet_nodes,self.gate_nodes,self.electrode_nodes])
        S,G,E,F=self.sheet_nodes,self.gate_nodes,self.electrode_nodes,self.free_nodes
        L=self.laplacian
        self._lfs=L[F][:,S].tocsc();self._lfg=L[F][:,G].tocsc();self._lfe=L[F][:,E].tocsc()
        if backend=='coupled':
            self._factor=None
            self._lff=L[F][:,F].tocsr();self._lsf=L[S][:,F].tocsr()
            self.sheet_matrix_F=L[S][:,S].tocsr()
            self._gate_map=L[S][:,G].tocsr();self._contact_map=L[S][:,E].tocsr()
            self._diagonal=self.sheet_matrix_F.diagonal()
            self._offdiagonal=self.sheet_matrix_F-diags(self._diagonal)
            self._scale_F=np.asarray(abs(L[S]).sum(axis=1)).ravel()
            self._bulk_scale_F=np.asarray(abs(L[F]).sum(axis=1)).ravel()
        elif len(F):
            self._factor=splu(L[F][:,F].tocsc())
            if self.schur_rhs_block_size is None:
                h=self._factor.solve(self._lfs.toarray())
                b=self._factor.solve(self._lfg.toarray())
                matrix=L[S][:,S].toarray()-L[S][:,F]@h
                drive=L[S][:,G].toarray()-L[S][:,F]@b
                contact_drive=L[S][:,E].toarray()
                if len(E):contact_drive-=L[S][:,F]@self._factor.solve(self._lfe.toarray())
            else:
                lsf=L[S][:,F]
                def eliminate(right,direct):
                    out=direct.toarray()
                    for begin in range(0,right.shape[1],self.schur_rhs_block_size):
                        end=min(begin+self.schur_rhs_block_size,right.shape[1])
                        out[:,begin:end]-=lsf@self._factor.solve(right[:,begin:end].toarray())
                    return out
                matrix=eliminate(self._lfs,L[S][:,S])
                drive=eliminate(self._lfg,L[S][:,G])
                contact_drive=eliminate(self._lfe,L[S][:,E])
        else:
            self._factor=None;matrix=L[S][:,S].toarray();drive=L[S][:,G].toarray()
            contact_drive=L[S][:,E].toarray()
        if backend=='schur':
            if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(drive)) or not np.all(np.isfinite(contact_drive)):
                raise FloatingPointError('dielectric Schur map is not representable')
            self.sheet_matrix_F=csr_matrix(matrix);self._gate_map=drive
            self._contact_map=contact_drive
            self._diagonal=matrix.diagonal().copy()
            self._offdiagonal=self.sheet_matrix_F-diags(self._diagonal)
            self._scale_F=np.sum(np.abs(matrix),axis=1)
        for value in (self.area,self.permittivity_F_m,self.edge_nodes,self.edge_capacitance_F,
                      self.sheet_nodes,self.gate_nodes,self.free_nodes,self._diagonal,self._scale_F,
                      self.sheet_contact_nodes,self.source_electrode_nodes,self.drain_electrode_nodes,
                      self.electrode_nodes):
            value.setflags(write=False)
        if backend=='schur':
            self._gate_map.setflags(write=False);self._contact_map.setflags(write=False)
        else:
            self._bulk_scale_F.setflags(write=False)

    def _field(self,value,name):
        try:return np.array(np.broadcast_to(_finite(value,name),self.sheet_shape),copy=True).ravel()
        except ValueError as exc:raise ValueError(f'{name} must be scalar or shape {self.sheet_shape}') from exc

    def gate_drive(self,*,top_gate_voltage_V,bottom_gate_voltage_V,
                   source_electrode_potential_V=None,drain_electrode_potential_V=None):
        values=np.r_[self._field(bottom_gate_voltage_V,'bottom_gate_voltage_V'),self._field(top_gate_voltage_V,'top_gate_voltage_V')]
        potentials=[]
        for value,name in ((source_electrode_potential_V,'source_electrode_potential_V'),
                           (drain_electrode_potential_V,'drain_electrode_potential_V')):
            if self.contact_z_bounds_m is None:
                if value is not None:raise ValueError('electrode potentials require contact_z_bounds_m')
            else:
                if value is None:raise ValueError(name+' is required for finite side electrodes')
                scalar=_finite(value,name)
                if scalar.ndim:raise ValueError(name+' must be scalar')
                potentials.append(float(scalar))
        electrodes=np.concatenate([np.full(len(nodes),v) for nodes,v in zip(
            (self.source_electrode_nodes,self.drain_electrode_nodes),potentials)]) if potentials else np.empty(0)
        load=self._gate_map@values
        if len(electrodes):load+=self._contact_map@electrodes
        values.setflags(write=False);load.setflags(write=False);electrodes.setflags(write=False)
        return _GateDrive(values,load,electrodes)

    def reconstruct(self,sheet_phi_V,drive):
        """Reconstruct all dielectric nodes, integrated D fluxes and gate charges."""
        phi=self._field(sheet_phi_V,'sheet_phi_V')
        full=np.zeros(np.prod(self.shape));full[self.sheet_nodes]=phi;full[self.gate_nodes]=drive.values
        full[self.electrode_nodes]=drive.electrode_values
        if len(self.free_nodes):
            rhs=-self._lfs@phi-self._lfg@drive.values
            if len(self.electrode_nodes):rhs-=self._lfe@drive.electrode_values
            if self.backend=='coupled':
                full[self.free_nodes]=(spsolve(self._lff,rhs) if drive.free_potential_V is None
                    else drive.free_potential_V)
            else:full[self.free_nodes]=self._factor.solve(rhs)
        if not np.all(np.isfinite(full)):
            raise FloatingPointError('dielectric potentials are not representable')
        reaction=self.laplacian@full
        delta=full[self.edge_nodes[:,0]]-full[self.edge_nodes[:,1]]
        flux=self.edge_capacitance_F*delta
        out=dict(dielectric_phi_V=full.reshape(self.shape),
            dielectric_edge_nodes=self.edge_nodes.copy(),dielectric_edge_displacement_C=flux,
            dielectric_node_flux_sum_C=reaction.reshape(self.shape),
            bottom_gate_charge_C=float(np.sum(reaction[self.gate_nodes[:self.size]])),
            top_gate_charge_C=float(np.sum(reaction[self.gate_nodes[self.size:]])),
            dielectric_energy_J=float(.5*np.dot(flux,delta)))
        if self.contact_z_bounds_m is not None:
            out.update(contact_z_bounds_m=self.contact_z_bounds_m.copy(),
                dielectric_electrode_nodes={name:nodes.copy() for name,nodes in (
                    ('source',self.source_electrode_nodes),('drain',self.drain_electrode_nodes))},
                dielectric_contact_charge_C={name:float(np.sum(reaction[nodes])) for name,nodes in (
                    ('source',self.source_electrode_nodes),('drain',self.drain_electrode_nodes))},
                dielectric_electrode_potential_V=dict(source=float(drive.electrode_values[0]),
                    drain=float(drive.electrode_values[len(self.source_electrode_nodes)])))
        return out

    def solve_linear(self,*,sheet_charge_C_m2,top_gate_voltage_V,bottom_gate_voltage_V,
                     source_electrode_potential_V=None,drain_electrode_potential_V=None):
        """Prescribed charge; finite side electrodes also pin intersecting sheet edges."""
        drive=self.gate_drive(top_gate_voltage_V=top_gate_voltage_V,bottom_gate_voltage_V=bottom_gate_voltage_V,
            source_electrode_potential_V=source_electrode_potential_V,drain_electrode_potential_V=drain_electrode_potential_V)
        charge=self._field(sheet_charge_C_m2,'sheet_charge_C_m2')
        rhs=self.area*charge-drive.load
        if self.backend=='coupled':
            full=np.zeros(np.prod(self.shape));full[self.gate_nodes]=drive.values
            full[self.electrode_nodes]=drive.electrode_values
            fixed=np.r_[self.gate_nodes,self.electrode_nodes]
            if self.contact_z_bounds_m is not None:
                sheet_fixed=self.sheet_nodes[self.sheet_contact_nodes]
                full[sheet_fixed]=np.repeat([source_electrode_potential_V,drain_electrode_potential_V],len(self.y))
                fixed=np.r_[fixed,sheet_fixed]
            free=np.setdiff1d(np.arange(full.size),fixed)
            load=np.zeros(full.size);load[self.sheet_nodes]=self.area*charge
            full[free]=spsolve(self.laplacian[free][:,free],load[free]-self.laplacian[free][:,fixed]@full[fixed])
            phi=full[self.sheet_nodes]
            drive=replace(drive,free_potential_V=full[self.free_nodes])
        else:matrix=self.sheet_matrix_F.toarray()
        if self.backend=='schur' and self.contact_z_bounds_m is None:
            phi=np.linalg.solve(matrix,rhs)
        elif self.backend=='schur':
            fixed=self.sheet_contact_nodes;free=np.setdiff1d(np.arange(self.size),fixed)
            phi=np.zeros(self.size);phi[fixed]=np.repeat(
                [source_electrode_potential_V,drain_electrode_potential_V],len(self.y))
            phi[free]=np.linalg.solve(matrix[np.ix_(free,free)],rhs[free]-matrix[np.ix_(free,fixed)]@phi[fixed])
        out=self.reconstruct(phi.reshape(self.sheet_shape),drive)
        out['phi_V']=phi.reshape(self.sheet_shape)
        out['sheet_charge_C']=float(np.dot(self.area,charge))
        out['gauss_charge_sum_C']=out['sheet_charge_C']+out['bottom_gate_charge_C']+out['top_gate_charge_C']
        if self.contact_z_bounds_m is not None:
            fixed=self.sheet_contact_nodes
            reaction=(out['dielectric_node_flux_sum_C'].ravel()[self.sheet_nodes]-self.area*charge
                if self.backend=='coupled' else self.sheet_matrix_F@phi-rhs)
            sheet_contacts={name:float(np.sum(reaction[nodes])) for name,nodes in (
                ('source',fixed[:len(self.y)]),('drain',fixed[len(self.y):]))}
            out['sheet_contact_charge_C']=sheet_contacts
            out['contact_charge_C']={name:sheet_contacts[name]+out['dielectric_contact_charge_C'][name] for name in sheet_contacts}
            out['gauss_charge_sum_C']+=sum(out['contact_charge_C'].values())
        return out


class DielectricSheetDriftDiffusion(SheetDriftDiffusion):
    """Simultaneous sheet DD and full box dielectric Poisson.

    Other sheet/transport assumptions and contact conventions match
    SheetDriftDiffusion. No local gate capacitor is present in this model.
    electrostatic_backend='schur' is the original small-mesh dense elimination.
    'coupled' retains bulk potentials alongside independent sheet phi/Fn/Fp,
    using sparse Newton solves for DC and SheetTransient backward Euler.
    linear_solver='reused_gmres' opts into bounded preconditioned iteration
    with a true row-scaled residual guard. Its optional linear_ordering can
    reduce LU fill for some grids; COLAMD remains the default. No automatic
    mesh control.
    """
    def __init__(self,x_m,y_m,z_m,material,*,sheet_index,permittivity_F_m,contact_z_bounds_m=None,schur_rhs_block_size=None,electrostatic_backend='schur',linear_solver='direct',linear_ordering='COLAMD',**kwargs):
        if not isinstance(linear_solver,str) or linear_solver not in ('direct','reused_gmres'):
            raise ValueError("linear_solver must be 'direct' or 'reused_gmres'")
        if linear_solver=='reused_gmres' and electrostatic_backend!='coupled':
            raise ValueError('reused_gmres requires the coupled electrostatic backend')
        if not isinstance(linear_ordering,str) or linear_ordering not in ('COLAMD','MMD_AT_PLUS_A','GEOMETRIC_ND'):
            raise ValueError("linear_ordering must be 'COLAMD', 'MMD_AT_PLUS_A' or 'GEOMETRIC_ND'")
        if linear_solver!='reused_gmres' and linear_ordering!='COLAMD':
            raise ValueError('nondefault linear_ordering requires reused_gmres')
        self.linear_solver=linear_solver
        self.linear_ordering=linear_ordering
        self._linear_factor=None
        self._geometric_permutation=None
        if 'gate_capacitance_F_m2' in kwargs:
            raise ValueError('explicit dielectric coupling cannot also use a local gate capacitor')
        self.dielectric=SheetDielectricPoisson(x_m,y_m,z_m,sheet_index=sheet_index,
            permittivity_F_m=permittivity_F_m,contact_z_bounds_m=contact_z_bounds_m,
            schur_rhs_block_size=schur_rhs_block_size,backend=electrostatic_backend)
        # Base mesh/transport setup; the local capacitor is discarded and never evaluated.
        super().__init__(x_m,y_m,material,gate_capacitance_F_m2=1.,**kwargs)
        self.cap=None

    def _linear_context(self,tolerance):
        if self.linear_solver=='reused_gmres':
            storage=getattr(self,'_transient_storage',None)
            key=None if storage is None else ('backward_euler',float(storage[2]))
            permutation=None
            if self.linear_ordering=='GEOMETRIC_ND':
                if self._geometric_permutation is None:
                    d=self.dielectric
                    nodes=np.concatenate((np.tile(d.sheet_nodes,3),d.free_nodes))
                    coordinates=np.column_stack(np.unravel_index(nodes,d.shape))
                    self._geometric_permutation=_SymmetricPermutation(_geometric_nd_permutation(coordinates))
                permutation=self._geometric_permutation
            return _ReusedGMRES(self._linear_factor,tolerance,key,self.linear_ordering,permutation)
        return None

    def _finish_linear_context(self,context,result):
        if context is not None:
            result['linear_solver_diagnostics']=context.diagnostics()
            if result['converged']:
                self._linear_factor=context.factor

    def _field(self,value,name):
        if name=='gate_voltage_V' and isinstance(value,_GateDrive):return value
        return super()._field(value,name)

    def _electrostatic(self,phi,gate,st):
        d=self.dielectric
        rho=st.charge_C_m2+Q*self.doping+self.fixed_charge
        bulk=d._lsf@gate.free_potential_V if d.backend=='coupled' else 0.
        return (d.sheet_matrix_F@phi+gate.load+bulk-self.area*rho,
            d._scale_F*self.vt+self.area*(Q*(st.n_m2+st.p_m2+np.abs(self.doping))+np.abs(self.fixed_charge)),
            d._diagonal+self.area*st.quantum_capacitance_F_m2,d._offdiagonal)

    def _initial_unknowns(self,u,gate,initial):
        d=self.dielectric
        if d.backend=='schur':return u
        if initial is not None and 'dielectric_phi_V' in initial:
            full=_finite(initial['dielectric_phi_V'],'dielectric_phi_V')
            if full.shape!=d.shape:raise ValueError('dielectric_phi_V must have shape '+str(d.shape))
            bulk=full.ravel()[d.free_nodes]
        else:
            rhs=-d._lfs@u[:self.size]-d._lfg@gate.values-d._lfe@gate.electrode_values
            bulk=spsolve(d._lff,rhs) if len(d.free_nodes) else np.empty(0)
        if not np.all(np.isfinite(bulk)):raise FloatingPointError('initial bulk potential is not representable')
        return np.r_[u,bulk]

    def _evaluate(self,u,gate,bc,jacobian=True):
        d=self.dielectric
        if d.backend=='schur':return super()._evaluate(u,gate,bc,jacobian)
        N=self.size;sheet=u[:3*N];bulk=u[3*N:]
        local=replace(gate,free_potential_V=bulk)
        r,scale,J,st,currents,power,electrostatic=super()._evaluate(sheet,local,bc,jacobian)
        bulk_r=d._lfs@sheet[:N]+d._lff@bulk+d._lfg@gate.values+d._lfe@gate.electrode_values
        bulk_scale=d._bulk_scale_F*self.vt
        if not np.all(np.isfinite(bulk_r)):
            raise FloatingPointError('bulk Poisson equations are not representable')
        if jacobian:
            # Pinned sheet phi rows must also lose their bulk coupling.
            mask=np.ones(N);mask[self.contacts]=0.
            cross=vstack((d._lsf.multiply(mask[:,None]),csr_matrix((2*N,len(bulk)))),format='csr')
            cross.eliminate_zeros()
            lower=hstack((d._lfs,csr_matrix((len(bulk),2*N))),format='csr')
            J=bmat(((J,cross),(lower,d._lff)),format='csr')
        return np.r_[r,bulk_r],np.r_[scale,bulk_scale],J,st,currents,power,electrostatic

    def _result(self,u,gate,bc,evaluated,**kwargs):
        if self.dielectric.backend=='schur':return super()._result(u,gate,bc,evaluated,**kwargs)
        N=self.size;local=replace(gate,free_potential_V=u[3*N:])
        result=super()._result(u[:3*N],local,bc,evaluated,**kwargs)
        result['electrostatic_backend']='coupled'
        result['dielectric_free_residual_scaled_linf']=float(np.max(abs(evaluated[0][3*N:]/evaluated[1][3*N:]),initial=0.))
        return result

    def _charge_ledger(self,phi,gate,st,electrostatic):
        fields=self.dielectric.reconstruct(phi.reshape(self.shape),gate)
        gate_charge=fields['bottom_gate_charge_C']+fields['top_gate_charge_C']
        sheet_charge=float(np.sum(self.area*(st.charge_C_m2+Q*self.doping+self.fixed_charge)))
        contacts={name:float(np.sum(electrostatic[nodes])) for name,nodes in (('source',self.left),('drain',self.right))}
        if self.dielectric.contact_z_bounds_m is not None:
            fields['sheet_contact_charge_C']=contacts.copy()
            contacts={name:value+fields['dielectric_contact_charge_C'][name] for name,value in contacts.items()}
        return dict(**fields,gate_charge_C=gate_charge,sheet_charge_C=sheet_charge,contact_charge_C=contacts,
            gauss_charge_sum_C=gate_charge+sheet_charge+sum(contacts.values()))

    def solve(self,*,top_gate_voltage_V,bottom_gate_voltage_V=0.,**kwargs):
        electrodes={}
        if self.dielectric.contact_z_bounds_m is not None:
            voltages=[]
            for name in ('source_voltage_V','drain_voltage_V','fermi_offset_eV'):
                value=_finite(kwargs.get(name,0.),name)
                if value.ndim:raise ValueError(name+' must be scalar')
                voltages.append(float(value))
            bc=self._contact_boundary_conditions(*voltages)
            electrodes=dict(source_electrode_potential_V=float(bc[0][0]),drain_electrode_potential_V=float(bc[0][-1]))
        drive=self.dielectric.gate_drive(top_gate_voltage_V=top_gate_voltage_V,bottom_gate_voltage_V=bottom_gate_voltage_V,**electrodes)
        out=super().solve(gate_voltage_V=drive,**kwargs)
        out['model']='isothermal_sheet_dd_cartesian_dielectric'
        return out
