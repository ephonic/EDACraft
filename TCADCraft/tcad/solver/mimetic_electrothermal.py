"""Hybrid mimetic log-activity transport, heat and variational quantum energy.

Linear-consistent scalar geometry on skew polyhedra. This is a centered
logarithmic-density scheme, with no SG large-field monotonicity guarantee.
Uniform band edges and reference DOS only; thermionic interfaces are excluded.
"""
import numpy as np
from types import MappingProxyType
from .cut_cell_transport import Q,KB
from .electrothermal_cut_cell import ElectrothermalCutCellTransport
from .hybrid_mimetic import HybridMimeticOperator


class MimeticElectrothermalCutCellTransport(ElectrothermalCutCellTransport):
    def __init__(self,*args,terminal_groups=None,**kwargs):
        super().__init__(*args,**kwargs)
        for name in ('Ec','Eh','Nc','Nv'):
            a=getattr(self,name)
            if np.any(a!=a[0]):raise ValueError('mimetic transport currently requires uniform band edges and reference DOS')
        self.mimetic=HybridMimeticOperator(self.mesh)
        from tcad.postprocess.cut_cell_terminals import validate_terminal_groups
        self.terminal_groups=None if terminal_groups is None else MappingProxyType(
            validate_terminal_groups(self.mesh,self.bc,terminal_groups))

    def _root_field(self,density,reservoir):
        return self.mimetic.reconstruct(np.sqrt(density),1.,
            dirichlet={int(f):float(np.sqrt(r)) for f,r in zip(self.contact_faces,reservoir)})

    def quantum_potentials(self,n,p,old_n=None,old_p=None):
        result=[]
        for density,old,k,reservoir in ((n,old_n,self.kn,self.res_n),(p,old_p,self.kp,self.res_p)):
            if not k:result.append(np.zeros(self.nc));continue
            new=self._root_field(density,reservoir)
            previous=new if old is None else self._root_field(old,reservoir)
            result.append(k*(new['cell_action']+previous['cell_action'])/
                (self.vol*(np.sqrt(density)+np.sqrt(density if old is None else old))))
        return tuple(result)

    def transport(self,n,p,f,temperature,poisson):
        qn,qp=self.quantum_potentials(n,p);fluxes=[]
        for density,band,dos,base,exponent,sign,quantum,reservoir in (
            (n,self.Ec,self.Nc,self.mn,self.mn_exponent,-1,qn,self.res_n),
            (p,self.Eh,self.Nv,self.mp,self.mp_exponent,1,qp,self.res_p)):
            mu=base*(self.T/temperature)**exponent
            if np.any(quantum):
                qface=self.mimetic.reconstruct(quantum,1.,dirichlet={int(f):0. for f in self.contact_faces})['face_values']
            else:qface=np.zeros(len(self.mesh.faces))
            U=np.r_[band+quantum+sign*Q*poisson['cell_potential_V'],
                band[0]+qface+sign*Q*poisson['face_potential_V']]
            boundary={int(face):float(np.log(res)-np.log(dos[cell]))
                for face,cell,res in zip(self.contact_faces,self.contact_cells,reservoir)}
            reconstructed=self.mimetic.reconstruct(np.log(density)-np.log(dos),mu*density*KB*temperature/Q,
                dirichlet=boundary,drift=U,drift_coefficient=mu*density/Q)
            fluxes.append(reconstructed['flux'])
        Nc=self.Nc*(temperature/self.T)**1.5;Nv=self.Nv*(temperature/self.T)**1.5
        n1=Nc*np.exp(np.clip((self.Et-self.Ec-qn)/(KB*temperature),-690,690))
        p1=Nv*np.exp(np.clip((-self.Et-self.Eh-qp)/(KB*temperature),-690,690))
        rn=self.cn*(n*(1-f)-n1*f);rp=self.cp*(p*f-p1*(1-f))
        return *fluxes,rn,rp,qn,qp

    def conduction(self,temperature):
        return self.mimetic.reconstruct(temperature,self.conductivity,dirichlet=self.bath)['flux']

    def energies(self,state,*,charge_atol_C):
        energies,poisson=super().energies(state,charge_atol_C=charge_atol_C)
        energies['quantum_J']=sum(k*self._root_field(density,res)['quadratic']
            for density,k,res in ((state.n_m3,self.kn,self.res_n),(state.p_m3,self.kp,self.res_p)) if k)
        return energies,poisson

    def energy_increments(self,old,new,old_poisson,new_poisson):
        increments=super().energy_increments(old,new,old_poisson,new_poisson)
        increments['quantum_J']=sum(k*self.mimetic.quadratic_difference(self._root_field(a,res),self._root_field(b,res),1.)
            for a,b,k,res in ((old.n_m3,new.n_m3,self.kn,self.res_n),(old.p_m3,new.p_m3,self.kp,self.res_p)) if k)
        return increments

    def step(self,*args,**kwargs):
        state,report=super().step(*args,**kwargs)
        if self.terminal_groups is not None:
            from tcad.postprocess.cut_cell_terminals import integrate_cut_cell_terminals
            old=args[0] if args else kwargs['state'];dt=state.time_s-old.time_s
            # Reconstruct from the states so named totals do not inherit an
            # accidental omission or sign error in reported face currents.
            a=self._poisson(old.n_m3,old.p_m3,old.trap_fraction,kwargs['charge_atol_C'])
            b=self._poisson(state.n_m3,state.p_m3,state.trap_fraction,kwargs['charge_atol_C'])
            report['terminal_groups']={name:list(faces) for name,faces in self.terminal_groups.items()}
            report['terminals']=integrate_cut_cell_terminals(self.mesh,self.bc,self.terminal_groups,a,b,
                report['integrated_electron_particle_flux_s'],report['integrated_hole_particle_flux_s'],
                report['integrated_carrier_energy_flux_W'],report['integrated_heat_flux_W'],dt)
        report.update(scope='hybrid_mimetic_log_activity_electrothermal_SRH_quantum',
            spatial_discretization='hybrid_mimetic_log_activity',linear_consistent_spatial_operator=True,
            SG_large_field_monotonicity=False,
            missing_physics=[p for p in report['missing_physics'] if p!='general_skew_consistent_transport']+
                ['thermionic_material_band_and_DOS_jumps','large_field_discrete_maximum_principle',
                 'general_skew_nonlinear_transport_validation'])
        return state,report
