"""Monolithic MB heat/particle steps with finite two-trace thermionic faces.

Orthogonal TPFA geometry; optional matched multi-valley MB interfaces.
Half-cell SG and the elastic interface are in series, not parallel. Each
trace uses its adjacent cell's temperature (piecewise-constant thermal
reconstruction). A face-reconstructed density-gradient potential is included
in the half-cell electrochemical drops and in the thermionic barrier energy.
"""
import numpy as np
from scipy.optimize import brentq
from types import MappingProxyType
from .cut_cell_transport import Q,KB,_array,_bernoulli
from .electrothermal_cut_cell import ElectrothermalCutCellTransport
from tcad.physics.thermionic_interface import H,thermionic_interface_flux
from tcad.physics.multivalley_thermionic import multivalley_thermionic_interface_flux, ThermionicValley


class ThermionicElectrothermalCutCellTransport(ElectrothermalCutCellTransport):
    def __init__(self,*args,thermionic_faces,emission_factor_n=2.,emission_factor_p=2.,
                 terminal_groups=None,thermionic_valleys=None,
                 thermionic_statistics='boltzmann',**kwargs):
        super().__init__(*args,**kwargs)
        faces=list(thermionic_faces);nf=len(self.mesh.faces)
        if any(isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer)) or
               not 0<=f<nf or self.mesh.faces[f].neighbor<0 for f in faces):
            raise ValueError('thermionic interfaces require internal face indices')
        if len(faces)!=len(set(faces)):raise ValueError('duplicate thermionic face')
        if not faces:raise ValueError('at least one thermionic face required')
        if max(self.skew,self.contact_skew)>1e-10:raise ValueError('orthogonal transport geometry required')
        self.thermionic_faces=tuple(sorted(map(int,faces)));self.tf=np.array(self.thermionic_faces,int)
        self.ti=np.array([self.mesh.faces[f].owner for f in self.tf],int)
        self.tj=np.array([self.mesh.faces[f].neighbor for f in self.tf],int)
        area=np.array([self.mesh.faces[f].area_vector_m2 for f in self.tf]);self.ta=np.linalg.norm(area,axis=1)
        normal=area/self.ta[:,None];centers=np.array([self.mesh.faces[f].centroid_m for f in self.tf])
        left=centers-self.mesh.centroids_m[self.ti];right=self.mesh.centroids_m[self.tj]-centers
        dl=np.sum(left*normal,axis=1);dr=np.sum(right*normal,axis=1)
        if np.any(dl<=0) or np.any(dr<=0):raise ValueError('positive interface half distances required')
        if max(np.max(np.linalg.norm(left-dl[:,None]*normal,axis=1)/dl),
               np.max(np.linalg.norm(right-dr[:,None]*normal,axis=1)/dr))>1e-10:
            raise ValueError('orthogonal interface half geometry required')
        self.half_owner_metric=self.ta/dl;self.half_neighbor_metric=self.ta/dr
        self.An=_array(emission_factor_n,len(faces),'electron emission factor',nonnegative=True)
        self.Ap=_array(emission_factor_p,len(faces),'hole emission factor',nonnegative=True)
        if thermionic_statistics not in ('boltzmann','fermi_dirac'):
            raise ValueError('thermionic_statistics must be boltzmann or fermi_dirac')
        if thermionic_valleys is None:
            thermionic_valleys={}
        if not isinstance(thermionic_valleys,dict):
            raise ValueError('thermionic_valleys must map carrier names to valley tuples')
        self.thermionic_statistics=thermionic_statistics
        if thermionic_statistics=='fermi_dirac' and not thermionic_valleys:
            raise ValueError('Fermi interface statistics require explicit valleys')
        self.thermionic_valleys={}
        for label,valleys in thermionic_valleys.items():
            if label not in ('electrons','holes') or not valleys:
                raise ValueError('thermionic_valleys keys must be nonempty electron/hole tuples')
            values=tuple(valleys)
            if not all(isinstance(v,ThermionicValley) for v in values):
                raise ValueError('thermionic_valleys entries must be ThermionicValley objects')
            if len({v.name for v in values}) != len(values):
                raise ValueError('valley names must be unique')
            self.thermionic_valleys[label]=values
        # An array is indexed by sorted thermionic_faces; a scalar applies to all.
        self.masses={}
        for name,dos,mu in [('electrons',self.Nc,self.mn),('holes',self.Nv,self.mp)]:
            mass=H**2/(2*np.pi*KB*self.T)*(dos/2)**(2/3)
            if name not in self.thermionic_valleys and not np.allclose(mass[self.ti],mass[self.tj],rtol=2e-13,atol=0):
                raise ValueError('equal DOS masses required at thermionic faces')
            if np.any(mu[self.ti]<=0) or np.any(mu[self.tj]<=0):
                raise ValueError('positive half-cell mobilities required')
            self.masses[name]=mass[self.ti]
        configured=set(faces)
        for f,i,j in zip(self.internal,self.i,self.j):
            if (self.Ec[i]!=self.Ec[j] or self.Eh[i]!=self.Eh[j]) and int(f) not in configured:
                raise ValueError('every band jump requires an explicit thermionic face')
        from tcad.postprocess.cut_cell_terminals import validate_terminal_groups
        self.terminal_groups=None if terminal_groups is None else MappingProxyType(
            validate_terminal_groups(self.mesh,self.bc,terminal_groups))

    def interface_moments(self,n,p,temperature,poisson,*,quantum=None):
        """Eliminate both positive density traces from three equal face fluxes."""
        i,j,faces=self.ti,self.tj,self.tf;rows={};phi=poisson['cell_potential_V'];pf=poisson['face_potential_V'][faces]
        To,Tn=temperature[i],temperature[j]
        if quantum is None: quantum={}
        for label,density,band,base,exponent,z,A in (
                ('electrons',n,self.Ec,self.mn,self.mn_exponent,-1,self.An),
                ('holes',p,self.Eh,self.mp,self.mp_exponent,1,self.Ap)):
            q=np.zeros(self.nc) if label not in quantum else _array(quantum[label],self.nc,label+' quantum potential')
            qface=(q[i]+q[j])/2
            effective_band=band+q
            mu=base*(self.T/temperature)**exponent
            dl=(z*Q*(pf-phi[i])+qface-q[i])/(KB*To)
            dr=(z*Q*(phi[j]-pf)+q[j]-qface)/(KB*Tn)
            lo=mu[i]*KB*To/Q*self.half_owner_metric;ln=mu[j]*KB*Tn/Q*self.half_neighbor_metric
            ao=lo*_bernoulli(dl);bo=lo*_bernoulli(-dl)
            an=ln*_bernoulli(dr);bn=ln*_bernoulli(-dr)
            mass=self.masses[label];high=np.maximum(effective_band[i],effective_band[j])
            go=A*self.ta*np.sqrt(KB*To/(2*np.pi*mass))*np.exp(-(high-effective_band[i])/(KB*To))
            gn=A*self.ta*np.sqrt(KB*Tn/(2*np.pi*mass))*np.exp(-(high-effective_band[j])/(KB*Tn))
            if label in self.thermionic_valleys:
                def evaluate(k,one,two):
                    return multivalley_thermionic_interface_flux(
                        one,two,To[k],Tn[k],effective_band[i[k]],effective_band[j[k]],
                        self.thermionic_valleys[label],self.ta[k],potential_V=pf[k],charge_sign=z,
                        statistics=self.thermionic_statistics,emission_factor=A[k])
                if self.thermionic_statistics=='boltzmann':
                    unit=[evaluate(k,1.,1.) for k in range(len(i))]
                    go=np.array([r['forward_particle_rate_s'] for r in unit])
                    gn=np.array([r['reverse_particle_rate_s'] for r in unit])
            ao,bo,an,bn,go,gn=[a.astype(np.longdouble) for a in (ao,bo,an,bn,go,gn)]
            determinant=bo*an+bo*gn+an*go
            if np.any(~np.isfinite(determinant)) or np.any(determinant<=0):
                raise ValueError('interface half-cell dynamic range exceeded')
            owner=np.asarray((ao*density[i]*(an+gn)+gn*bn*density[j])/determinant,float)
            neighbor=np.asarray((bn*density[j]*(bo+go)+go*ao*density[i])/determinant,float)
            moments=thermionic_interface_flux(owner,neighbor,To,Tn,effective_band[i],effective_band[j],mass,self.ta,
                potential_V=pf,charge_sign=z,emission_factor=A)
            if label in self.thermionic_valleys:
                if self.thermionic_statistics=='fermi_dirac':
                    # One bounded flux determines both positive SG traces.
                    # Solve the actual nonlinear FD law, rather than replacing
                    # the moments after a single-mass MB trace elimination.
                    for k in range(len(i)):
                        lower=-float(bn[k])*density[j[k]]
                        upper=float(ao[k])*density[i[k]]
                        span=upper-lower
                        def traces(t):
                            return span*(1-t)/float(bo[k]),span*t/float(an[k])
                        def residual(t):
                            one,two=traces(t)
                            return (evaluate(k,one,two)['particle_flux_s']-(lower+span*t))/span
                        t=brentq(residual,1e-14,1-1e-14,xtol=5e-15,rtol=1e-14)
                        owner[k],neighbor[k]=traces(t)
                records=[evaluate(k,owner[k],neighbor[k]) for k in range(len(i))]
                keys=('particle_flux_s','forward_particle_rate_s','reverse_particle_rate_s',
                    'kinetic_owner_flux_W','kinetic_neighbor_flux_W','material_energy_flux_W',
                    'electrochemical_energy_flux_W','lattice_heat_owner_W','lattice_heat_neighbor_W',
                    'entropy_production_W_K')
                moments={key:np.asarray([r[key] for r in records]) for key in keys}
                moments.update(statistics=self.thermionic_statistics,valley_count=len(self.thermionic_valleys[label]),
                    complete_device_energy=False,physical_validated=False)
                moments['scope']='matched_multivalley_interface_with_MB_SG_half_cells'
            rows[label]=dict(owner_density_m3=owner,neighbor_density_m3=neighbor,
                quantum_owner_J=q[i],quantum_neighbor_J=q[j],quantum_face_J=qface,moments=moments)
        return rows

    def transport(self,n,p,f,temperature,poisson):
        fn,fp,rn,rp,qn,qp=super().transport(n,p,f,temperature,poisson)
        rows=self.interface_moments(n,p,temperature,poisson,
            quantum={'electrons':qn,'holes':qp})
        fn[self.tf]=rows['electrons']['moments']['particle_flux_s']
        fp[self.tf]=rows['holes']['moments']['particle_flux_s']
        return fn,fp,rn,rp,qn,qp

    def heat_terms(self,old,n,p,temperature,old_poisson,new_poisson,fn,fp,rn,rp,dt):
        heat,total,capture,carrier_out,energy_flux=super().heat_terms(
            old,n,p,temperature,old_poisson,new_poisson,fn,fp,rn,rp,dt)
        # The face energy flux is reported at the accepted thermal/electronic
        # state.  The bulk DG heat term still carries its independent old/new
        # chain-rule audit in the parent implementation.
        qn,qp=self.quantum_potentials(n,p)
        rows=self.interface_moments(n,p,temperature,new_poisson,
            quantum={'electrons':qn,'holes':qp})
        wanted=sum(r['moments']['material_energy_flux_W'] for r in rows.values())
        change=np.zeros(len(self.mesh.faces));change[self.tf]=wanted-energy_flux[self.tf]
        correction=-dt*self.mesh.divergence_integrals(change)
        # Material energy is evaluated at the new thermal state. The electrical
        # face work retains the base method's midpoint discrete gradient.
        heat+=correction;energy_flux[self.tf]=wanted
        return heat,float(np.longdouble(total)+np.sum(correction,dtype=np.longdouble)),capture,carrier_out,energy_flux

    def step(self,state,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=250):
        if self.thermionic_statistics!='boltzmann':
            raise ValueError('FD device stepping requires FD bulk transport and carrier storage')
        for label,valleys in self.thermionic_valleys.items():
            if any(v.band_offset_owner_J!=0 or v.band_offset_neighbor_J!=0 for v in valleys):
                raise ValueError('valley-offset device stepping requires valley-resolved bulk storage')
            # The bulk SRH/activity DOS must describe the same valleys.
            dos=sum(v.degeneracy*2*(2*np.pi*v.dos_mass_ratio*9.1093837015e-31*KB*self.T/H**2)**1.5
                for v in valleys)
            bulk=self.Nc if label=='electrons' else self.Nv
            if not np.allclose(bulk[np.r_[self.ti,self.tj]],dos,rtol=2e-12,atol=0):
                raise ValueError('bulk DOS must match the configured thermionic valleys')
        new,report=super().step(state,dt_s,charge_atol_C=charge_atol_C,particle_atol=particle_atol,
            energy_atol_J=energy_atol_J,max_nfev=max_nfev)
        a=self._poisson(state.n_m3,state.p_m3,state.trap_fraction,charge_atol_C)
        b=self._poisson(new.n_m3,new.p_m3,new.trap_fraction,charge_atol_C)
        report['thermionic_faces']=list(self.thermionic_faces)
        qn,qp=self.quantum_potentials(new.n_m3,new.p_m3)
        report['thermionic_interfaces']=self.interface_moments(new.n_m3,new.p_m3,new.temperature_K,b,
            quantum={'electrons':qn,'holes':qp})
        if self.terminal_groups is not None:
            from tcad.postprocess.cut_cell_terminals import integrate_cut_cell_terminals
            report['terminal_groups']={name:list(faces) for name,faces in self.terminal_groups.items()}
            report['terminals']=integrate_cut_cell_terminals(self.mesh,self.bc,self.terminal_groups,a,b,
                report['integrated_electron_particle_flux_s'],report['integrated_hole_particle_flux_s'],
                report['integrated_carrier_energy_flux_W'],report['integrated_heat_flux_W'],dt_s)
        scope=('monolithic_matched_multivalley_MB_two_trace_thermionic_electrothermal_SG_SRH'
            if self.thermionic_valleys else 'monolithic_equal_mass_MB_two_trace_thermionic_electrothermal_SG_SRH')
        report.update(scope=scope,
            state_advanced=True,interface_temperature_reconstruction='adjacent_cell_piecewise_constant',
            nonisothermal_commercial_accepted=False,
            missing_physics=['native_backend_integration','general_skew_consistent_transport',
                'ferroelectric_and_domain_energy','degenerate_statistics',
                'mass_discontinuities_within_matched_valleys','valley_offset_bulk_storage','full_material_temperature_dependence',
                'nonisothermal_commercial_energy_validation','combined_model_second_law_validation'])
        return new,report
