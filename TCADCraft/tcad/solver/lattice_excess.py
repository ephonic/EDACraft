"""Coupled implicit lattice conduction with fixed-density FD carrier excess.

Only explicit zero-transmission carrier interfaces are admitted. No carrier
face moment, particle transport or general device-energy closure is implied.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from threading import RLock
import numpy as np
from tcad.physics.native_fermi_local import _decimal
from .isolated_relaxation import IsolatedRelaxationState,IsolatedRelaxationConfiguration


def _varshni_secant(T,old,beta):
    """Stable divided difference of f(T)=T^2/(T+beta), including beta=0."""
    def ratios(t):
        scale=max(t,beta);u=t/scale;v=beta/scale
        return u/(u+v),v/(u+v)
    x,y=ratios(T);z,_=ratios(old)
    return x+y*z


@dataclass(frozen=True)
class LatticeExcessConfiguration:
    cells: tuple
    # owner,neighbor,area,owner half-distance,neighbor half-distance,k_owner,k_neighbor
    faces: tuple
    # boundary face id,owner,area,owner half-distance,k_owner,maintained Tb
    baths: tuple=()
    # Prescribed affine slopes per cell (electron,hole), and reference T.
    # Empty keeps the original fixed-band configuration fingerprint unchanged.
    affine_bands: tuple=()
    # alpha_n,beta_n,alpha_p,beta_p. Nonnegative alpha certifies concave gaps
    # and a nonincreasing combined storage capacity across the frozen bounds.
    varshni_bands: tuple=()

    @property
    def sha256(self):
        data=dict(cells=[c.sha256 for c in self.cells],faces=self.faces)
        if self.baths:data['baths']=self.baths
        if self.affine_bands:data['affine_bands']=self.affine_bands
        if self.varshni_bands:data['varshni_bands']=self.varshni_bands
        return sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

    def packed_parameters(self):
        """Eliminate prescribed band work exactly at constant particle density.

        Carrier storage contains W_k=N_k*s_k*dTl, with -W_k in its row.
        The lattice receives +sum(W_k), hence Cv_eff=Cv+n*s_n+p*s_p.
        Cv itself and both physical carrier storage increments are retained in
        the public configuration/report. This is an equation transformation.
        """
        with localcontext() as ctx:
            ctx.prec=90;result=[]
            for i,c in enumerate(self.cells):
                p=list(c.parameters)
                if self.affine_bands:
                    slopes=self.affine_bands[i][:2]
                    effective=Decimal(p[0])+sum(Decimal(n)*Decimal(s) for n,s in zip(c.initial_densities_m3,slopes))
                    if not effective.is_finite() or not np.isfinite(float(effective)) or effective<=0:
                        raise ValueError('positive finite effective lattice-plus-band capacity required')
                    p[0]=format(effective,'.36g')
                result.extend(p)
            return result

    def packed_varshni(self):return [v for row in self.varshni_bands for v in row]

    def packed_faces(self):
        with localcontext() as ctx:
            ctx.prec=90
            return [v for a,b,area,do,dn,ko,kn in self.faces
                for v in (str(a),str(b),format(Decimal(area)/(Decimal(do)/Decimal(ko)+Decimal(dn)/Decimal(kn)),'.36g'))]

    def packed_baths(self):
        with localcontext() as ctx:
            ctx.prec=90
            return [v for face,owner,area,distance,k,T in self.baths
                for v in (str(owner),format(Decimal(area)*Decimal(k)/Decimal(distance),'.36g'),T)]


@dataclass(frozen=True)
class LatticeExcessState:
    cells: tuple
    time_s: float
    configuration_sha256: str

    def __post_init__(self):
        if not isinstance(self.cells,tuple) or not self.cells or any(type(c) is not IsolatedRelaxationState for c in self.cells):
            raise ValueError('immutable excess cell states required')
        if isinstance(self.time_s,(bool,np.bool_)) or not np.isfinite(self.time_s) or self.time_s<0 or any(c.time_s!=self.time_s for c in self.cells):
            raise ValueError('matching finite lattice excess clocks required')
        if not isinstance(self.configuration_sha256,str) or len(self.configuration_sha256)!=64:
            raise ValueError('lattice excess configuration fingerprint required')

    def raw(self):return [v for c in self.cells for v in c.raw()]


class LatticeCoupledExcessRelaxation:
    """Native DeviceSimulator mode for heat-conducting, carrier-blocked cells."""
    def __init__(self,model,initial_state,*,temperature_bounds_K=None):
        from .three_temperature import ThreeTemperatureElectrothermal
        if type(model) is not ThreeTemperatureElectrothermal:raise ValueError('unmodified three-temperature model required')
        model._validate_state(initial_state)
        if (not 2<=model.nc<=64 or not len(model.internal) or model.contacts or
                model.trap_capture_law is not None or
                model.radiative_law is not None or model.auger_events is not None or
                np.any(model.intercarrier_conductance_W_m3_K) or np.any(model.pair_generation_rate_m3_s)):
            raise ValueError('lattice excess requires 2..64 fixed-density cells without carrier contacts or other sources')
        if (set(model.thermionic_faces)!=set(model.internal) or any(
                model.emission[label].get(int(f))!=0 for label in ('electrons','holes') for f in model.internal)):
            raise ValueError('every internal carrier face must have explicit zero transmission for both species')
        laws=[]
        for law in model.relaxation_laws:
            if law is not None and law.carrier_temperature_exponent!=0:
                raise ValueError('lattice excess requires carrier exponent b=0')
            laws.extend((model.T,1.,0.,0.) if law is None else (law.reference_temperature_K,
                law.reference_density_m3,law.lattice_temperature_exponent,law.density_exponent))
        baths=[]
        for f,T in model.bath.items():
            if (isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer)) or not 0<=f<len(model.mesh.faces) or
                    model.mesh.faces[f].neighbor>=0 or isinstance(T,(bool,np.bool_)) or not np.isscalar(T) or
                    not np.isfinite(T) or T<=0):
                raise ValueError('valid exterior thermal face and maintained positive bath temperature required')
            owner=int(model.mesh.faces[f].owner)
            values=(model.area[f],model.do[f],model.conductivity[owner],T)
            if any(not np.isfinite(v) or v<=0 for v in values):raise ValueError('positive finite bath geometry and conductivity required')
            baths.append((int(f),owner,*map(_decimal,values)))
        baths.sort(key=lambda row:row[0])
        temps=np.array([initial_state.electron_temperature_K,initial_state.hole_temperature_K,initial_state.temperature_K])
        lo,hi=float(temps.min()),float(temps.max())
        if baths:lo=min(lo,min(float(b[-1]) for b in baths));hi=max(hi,max(float(b[-1]) for b in baths))
        if lo==hi:lo*=.5;hi*=1.5
        if temperature_bounds_K is not None:
            bounds=np.asarray(temperature_bounds_K)
            if (bounds.shape!=(2,) or bounds.dtype.kind not in 'fiu' or not np.all(np.isfinite(bounds)) or
                    bounds[0]<=0 or bounds[0]>=bounds[1] or bounds[0]>temps.min() or bounds[1]<temps.max()):
                raise ValueError('positive enclosing lattice excess temperature bounds required')
            lo,hi=map(float,bounds)
        if np.any(initial_state.temperature_K<=lo) or np.any(initial_state.temperature_K>=hi):
            raise ValueError('strict initial lattice temperature bounds required')
        cells=[];initial=[]
        for i in range(model.nc):
            T=tuple(_decimal(a[i]) for a in temps)
            density=tuple(_decimal(a[i]) for a in (initial_state.n_m3,initial_state.p_m3))
            params=tuple(_decimal(v) for v in (model.capacity[i],model.vol[i],model.Ec[i],model.Eh[i],
                model.tau_n[i],model.tau_p[i],*laws,lo,hi))
            cells.append(IsolatedRelaxationConfiguration(params,deepcopy(tuple(model.valleys['electrons'])),
                deepcopy(tuple(model.valleys['holes'])),density,T,float(initial_state.time_s)))
            initial.extend((*density,T[2],T[0],T[1]))
        faces=[]
        for f in model.internal:
            face=model.mesh.faces[f];a,b=int(face.owner),int(face.neighbor)
            values=(model.area[f],model.do[f],model.dn[f],model.conductivity[a],model.conductivity[b])
            if any(not np.isfinite(v) or v<=0 for v in values):raise ValueError('positive finite Fourier geometry and conductivities required')
            faces.append((a,b,*map(_decimal,values)))
        bands=();varshni=()
        if model.temperature_dependent_bands:
            bands=tuple((_decimal(model.band_temperature_slopes[0][i]),
                _decimal(model.band_temperature_slopes[1][i]),_decimal(model.T)) for i in range(model.nc))
            if model.nonlinear_temperature_bands:
                varshni=tuple(tuple(_decimal(v) for v in (model.band_varshni_alpha[0][i],
                    model.band_varshni_beta[0][i],model.band_varshni_alpha[1][i],model.band_varshni_beta[1][i])) for i in range(model.nc))
                if any(not Decimal(v).is_finite() or Decimal(v)<0 for row in varshni for v in row):
                    raise ValueError('nonnegative finite Varshni alpha and beta required in lattice excess mode')
            with localcontext() as ctx:
                ctx.prec=90
                for i,(c,band) in enumerate(zip(cells,bands)):
                    slope=list(map(Decimal,band[:2]));reference=Decimal(band[2])
                    densities=list(map(Decimal,c.initial_densities_m3))
                    coeff=list(map(Decimal,varshni[i])) if varshni else [Decimal(0)]*4
                    upper=Decimal.from_float(hi)
                    capacity=Decimal(c.parameters[0])+sum(n*(s-coeff[2*k]*_varshni_secant(upper,upper,coeff[2*k+1]))
                        for k,(n,s) in enumerate(zip(densities,slope)))
                    if capacity<=0:raise ValueError('positive effective capacity over frozen temperature bounds required')
                    for T in (lo,hi):
                        bound=Decimal.from_float(T)
                        gap=sum(map(Decimal,c.parameters[2:4]))+(bound-reference)*sum(
                            s-coeff[2*k]*_varshni_secant(bound,reference,coeff[2*k+1]) for k,s in enumerate(slope))
                        if gap<=0:raise ValueError('positive band gap over the frozen temperature bounds required')
        self._configuration=LatticeExcessConfiguration(tuple(cells),tuple(faces),tuple(baths),bands,varshni)
        from tcad.core._bindings import PyDeviceSimulator
        self._backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
        self._backend.configure_lattice_excess(initial,self._configuration.packed_parameters(),
            self._configuration.packed_faces(),*cells[0].packed_valleys(),float(initial_state.time_s),
            baths=self._configuration.packed_baths(),varshni=self._configuration.packed_varshni())
        owned=self.native_state();self._state=self._decode_state(owned['state'],owned['time_s']);self._lock=RLock()

    @property
    def configuration(self):return self._configuration

    @property
    def state(self):return self._state

    def native_state(self):return self._backend.isolated_relaxation_state()

    def _decode_state(self,raw,time):
        if len(raw)!=5*len(self.configuration.cells):raise ValueError('lattice excess state coverage mismatch')
        cells=tuple(IsolatedRelaxationState(*raw[5*i:5*i+5],time,c.sha256) for i,c in enumerate(self.configuration.cells))
        return LatticeExcessState(cells,time,self.configuration.sha256)

    def _decode_candidate(self,old,raw,time,dt,power,impulses):
        nc=len(old.cells);nf=len(self.configuration.faces);nb=len(self.configuration.baths)
        expected=13*nc+nf+nb+3;precision=None
        if len(raw)==expected+1:
            reason={'1':'float64_line_search','2':'float64_derivative_stagnation','3':'float64_singular_Jacobian'}.get(raw[-1])
            if reason is None:raise ValueError('unknown lattice precision retry reason')
            precision=reason;raw=raw[:-1]
        if len(raw)!=expected:raise ValueError('lattice excess native report coverage mismatch')
        blocks=[raw[13*i:13*i+13] for i in range(nc)]
        state=self._decode_state([v for c,b in zip(old.cells,blocks) for v in (*c.raw()[:2],*b[:3])],time)
        report=dict(scope='carrier_blocked_lattice_Fourier_FD_excess_BE',configuration_sha256=self.configuration.sha256,
            dt_s=dt,execution_backend='native',state_owner='C++ DeviceSimulator::isolated_relaxation',
            state_transaction='prepare-independent-audit-commit',carrier_faces='explicit_zero_transmission',
            carrier_temperature_exponent_supported=0,source_power_W=power.tolist(),source_impulses_J=impulses,
            cell_exchange_J=[b[3:5] for b in blocks],cell_carrier_energy_increments_J=[b[5:7] for b in blocks],
            cell_lattice_energy_increments_J=[b[7] for b in blocks],cell_energy_residuals_J=[b[8:11] for b in blocks],
            cell_effective_relaxation_times_s=[b[11:13] for b in blocks],face_energy_impulses_J=raw[13*nc:13*nc+nf],
            residual_evaluations=int(Decimal(raw[-3])),iterations=int(Decimal(raw[-2])),backtracks=int(Decimal(raw[-1])),
            complete_device_energy=False,physical_validated=False,measured_ac_material_calibration=False,
            general_carrier_transport_integrated=False)
        if nb:
            report.update(scope='carrier_blocked_lattice_Fourier_bath_FD_excess_BE',
                thermal_boundary_law='maintained_temperature_half_cell_Fourier',
                bath_energy_sign='positive_outward_from_device',
                boundary_energy_impulses_J=raw[13*nc+nf:13*nc+nf+nb])
        if precision:
            report.update(lattice_coordinate_precision='float128',precision_fallback_reason=precision,
                iteration_counter_scope='float128_retry_only; residual_evaluations_include_all_attempts')
        if self.configuration.affine_bands:
            with localcontext() as ctx:
                ctx.prec=90;work=[];du=[];dl=[]
                for i,(c,before,after) in enumerate(zip(self.configuration.cells,old.cells,state.cells)):
                    delta=Decimal(after.lattice_temperature_K)-Decimal(before.lattice_temperature_K)
                    coeff=list(map(Decimal,self.configuration.varshni_bands[i])) if self.configuration.varshni_bands else [Decimal(0)]*4
                    w=[Decimal(c.parameters[1])*Decimal(n)*delta*(Decimal(s)-coeff[2*k]*_varshni_secant(
                        Decimal(after.lattice_temperature_K),Decimal(before.lattice_temperature_K),coeff[2*k+1]))
                        for k,(n,s) in enumerate(zip(c.initial_densities_m3,self.configuration.affine_bands[i][:2]))]
                    if not self.configuration.varshni_bands:
                        # Retain the parent's exact Decimal operation order.
                        w=[Decimal(c.parameters[1])*Decimal(n)*Decimal(s)*delta for n,s in
                            zip(c.initial_densities_m3,self.configuration.affine_bands[i][:2])]
                    work.append(list(map(str,w)))
                    du.append([str(Decimal(v)+w[k]) for k,v in enumerate(report['cell_carrier_energy_increments_J'][i])])
                    # Reconstruct physical Cv storage directly, avoiding cancellation
                    # when band work dominates the transformed lattice row.
                    dl.append(str(Decimal(c.parameters[1])*Decimal(c.parameters[0])*delta))
                report.update(band_temperature_law='affine_lattice_temperature',
                    temperature_dependent_band_energy_coupled=True,temperature_dependent_band_entropy_closed=False,
                    cell_band_work_from_lattice_J=work,cell_carrier_energy_increments_J=du,
                    cell_lattice_energy_increments_J=dl)
                if self.configuration.varshni_bands:
                    report.update(band_temperature_law='affine_plus_Varshni_lattice_temperature',
                        nonlinear_band_storage_primitive='exact_Varshni_divided_difference')
        return state,report

    def advance(self,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=600,source_power_W=None):
        gates=(charge_atol_C,particle_atol,energy_atol_J)
        if any(isinstance(v,(bool,np.bool_)) or not np.isfinite(v) or v<=0 for v in (dt_s,*gates)):
            raise ValueError('positive finite timestep and physical budgets required')
        power=np.zeros((len(self.configuration.cells),3)) if source_power_W is None else np.asarray(source_power_W)
        if power.shape!=(len(self.configuration.cells),3) or power.dtype.kind not in 'fiu' or not np.all(np.isfinite(power)):
            raise ValueError('finite cell-by-reservoir power matrix required')
        power=np.array(power,dtype=float,copy=True)
        if not np.all(np.isfinite(power)):raise ValueError('representable cell powers required')
        with self._lock:
            old=self.state
            if old.configuration_sha256!=self.configuration.sha256 or self.native_state()!=dict(state=old.raw(),time_s=old.time_s):
                raise ValueError('lattice excess configuration or accepted native state mismatch')
            time=old.time_s+float(dt_s);dt=time-old.time_s
            if not np.isfinite(time) or dt<=0:raise ValueError('lattice excess physical clock cannot advance')
            with localcontext() as ctx:
                ctx.prec=90;impulses=[[str(Decimal.from_float(float(v))*Decimal.from_float(dt)) for v in row] for row in power]
            token=None
            try:
                raw,token=self._backend.prepare_isolated_relaxation(float(dt_s),*gates,max_nfev=max_nfev,
                    source_impulses_J=[v for row in impulses for v in row])
                new,report=self._decode_candidate(old,raw,time,dt,power,impulses)
                from tcad.postprocess.lattice_excess import audit_lattice_excess_step,audit_lattice_excess_initial
                if old.time_s==self.configuration.cells[0].initial_time_s:
                    initial=audit_lattice_excess_initial(self.configuration,old,energy_atol_J=energy_atol_J)
                    if not initial['valid']:raise ValueError('lattice excess initial independent audit failed')
                audit=audit_lattice_excess_step(self.configuration,old,new,report,source_power_W=power,**dict(
                    charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J))
                if not audit['valid']:raise ValueError('lattice excess independent audit failed: '+str(audit))
                report['independent_audit']=audit;self._backend.commit_isolated_relaxation(token)
            except BaseException:
                if token is not None:self._backend.discard_isolated_relaxation(token)
                raise
            self._state=new;return new,report
