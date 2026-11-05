"""FD spectral energy transport with independent electron, hole and lattice T.

Five cell unknowns (n,p,Tn,Tp,Tl), static orthogonal geometry.
Bands may have explicit affine lattice-temperature shifts with internal work.
Relaxation transfers [u(n,Ts)-u(n,Tl)]/tau from carrier s to lattice.
Mobilities depend on Tl; contact reservoirs retain their prescribed T.
The default path assembles residuals and iterates entirely in C++. An explicit
Python orchestration mode is retained as a reference, with no automatic fallback.
"""
from dataclasses import dataclass
import numpy as np

from .cut_cell_transport import Q, _array, _immutable_state_array
from .fermi_electrothermal import FermiSpectralElectrothermal, FermiSpectralState


@dataclass(frozen=True)
class ThreeTemperatureState(FermiSpectralState):
    electron_temperature_K: np.ndarray = None
    hole_temperature_K: np.ndarray = None

    def __post_init__(self):
        for name in ('n_m3', 'p_m3', 'trap_fraction', 'temperature_K'):
            if np.asarray(getattr(self, name)).dtype.kind not in 'iuf':
                raise ValueError('real state arrays required')
        super().__post_init__()
        for name in ('electron_temperature_K', 'hole_temperature_K'):
            value = getattr(self, name)
            if value is None:
                raise ValueError('explicit independent carrier temperatures required')
            if np.asarray(value).dtype.kind not in 'iuf':
                raise ValueError('real independent carrier temperatures required')
            a = np.array(value, dtype=float, copy=True)
            if a.shape != self.temperature_K.shape or np.any(~np.isfinite(a)) or np.any(a <= 0):
                raise ValueError('positive nodal ' + name + ' required')
            object.__setattr__(self, name, _immutable_state_array(a, float))


class ThreeTemperatureElectrothermal(FermiSpectralElectrothermal):
    """Conservative independent-temperature extension of the scoped FD model.

    This is an energy-transport closure, not a momentum/hydrodynamic PDE.
    No material relaxation calibration is inferred from conservation.
    """
    def __init__(self, *args, relaxation_time_n_s, relaxation_time_p_s,
                 relaxation_law_n=None, relaxation_law_p=None,
                 intercarrier_conductance_W_m3_K=0.,
                 pair_generation_rate_m3_s=0., pair_generation_kinetic_n_J=0.,
                 pair_generation_kinetic_p_J=0.,
                 trap_capture_law=None,
                 radiative_law=None, radiative_transition_rate_s=0., photon_bath_temperature_K=300.,
                 auger_events=None,
                 band_temperature_slope_n_J_K=0., band_temperature_slope_p_J_K=0.,
                 band_varshni_alpha_n_J_K=0., band_varshni_alpha_p_J_K=0.,
                 band_varshni_beta_n_K=0., band_varshni_beta_p_K=0.,
                 bulk_potential_path='endpoint_barrier',
                 residual_orchestration='native', transport_reconstruction='cell_mean',
                 contact_carrier_temperature_K=None, **kwargs):
        self.transport_reconstruction=transport_reconstruction
        if bulk_potential_path not in ('endpoint_barrier','linear_series'):
            raise ValueError('bulk_potential_path must be endpoint_barrier or linear_series')
        self.bulk_potential_path=bulk_potential_path
        if trap_capture_law not in (None,'energy_resolved_local_detailed_balance'):
            raise ValueError('explicit energy-resolved local-detailed-balance trap law required')
        if trap_capture_law is not None and residual_orchestration!='native':
            raise ValueError('dynamic traps require native residual orchestration')
        self.trap_capture_law=trap_capture_law
        trap_inputs={}
        if trap_capture_law is not None:
            # The shared-temperature parent must retain its no-trap contract.
            for key in ('trap_density_m3','capture_n_m3_s','capture_p_m3_s'):
                trap_inputs[key]=kwargs.pop(key,0.)
        if residual_orchestration not in ('native', 'python'):
            raise ValueError('three-temperature residual orchestration must be native or python')
        if residual_orchestration == 'native':
            from tcad.core._bindings import native_three_temperature_dispatch_raw
        self.residual_orchestration = residual_orchestration
        for name in ('spectral_backend', 'local_backend', 'poisson_backend', 'nonlinear_backend'):
            if name in kwargs and kwargs[name] != 'native':
                raise ValueError('three-temperature solver requires native primitive ' + name)
            kwargs[name] = 'native'
        if kwargs.pop('residual_backend', 'native') != 'native':
            raise ValueError('three-temperature local residual assembly requires native backend')
        from tcad.core._bindings import native_three_temperature_local_raw
        # The parent's native dispatch implements shared-temperature equations.
        # Initialize only its physical primitives, then install our five-row path.
        kwargs['residual_backend'] = 'python'
        super().__init__(*args, **kwargs)
        from .three_temperature_contacts import normalize_contact_temperatures
        self.contact_carrier_temperature_K = normalize_contact_temperatures(self.contacts, contact_carrier_temperature_K)
        self.residual_backend = 'native'
        self.band_temperature_slopes = tuple(_immutable_state_array(_array(value,self.nc,
            'band temperature slope'),float) for value in
            (band_temperature_slope_n_J_K,band_temperature_slope_p_J_K))
        self.band_varshni_alpha = tuple(_immutable_state_array(_array(value,self.nc,
            'band Varshni alpha'),float) for value in
            (band_varshni_alpha_n_J_K,band_varshni_alpha_p_J_K))
        self.band_varshni_beta = tuple(_immutable_state_array(_array(value,self.nc,
            'band Varshni beta',nonnegative=True),float) for value in
            (band_varshni_beta_n_K,band_varshni_beta_p_K))
        if self.temperature_dependent_bands:
            if residual_orchestration!='native':
                raise ValueError('temperature-dependent bands require native orchestration')
            self._validate_band_interfaces()
        if trap_capture_law is not None:
            for name,key in (('Nt','trap_density_m3'),('cn','capture_n_m3_s'),('cp','capture_p_m3_s')):
                setattr(self,name,_immutable_state_array(_array(trap_inputs[key],self.nc,key,nonnegative=True),float))
            self.Et=_immutable_state_array(self.Et,float)
            self.trap_parameters()
        self.tau_n = _array(relaxation_time_n_s, self.nc, 'electron relaxation time', positive=True)
        self.tau_p = _array(relaxation_time_p_s, self.nc, 'hole relaxation time', positive=True)
        self.relaxation_laws = (relaxation_law_n,relaxation_law_p)
        self.relaxation_parameters()
        self.intercarrier_conductance_W_m3_K = _immutable_state_array(_array(
            intercarrier_conductance_W_m3_K, self.nc, 'intercarrier conductance', nonnegative=True), float)
        for name,value in (('pair_generation_rate_m3_s',pair_generation_rate_m3_s),
                           ('pair_generation_kinetic_n_J',pair_generation_kinetic_n_J),
                           ('pair_generation_kinetic_p_J',pair_generation_kinetic_p_J)):
            setattr(self,name,_immutable_state_array(_array(value,self.nc,name,nonnegative=True),float))
        self.pair_generation_parameters()
        self.radiative_law=radiative_law
        self.radiative_transition_rate_s=_immutable_state_array(_array(
            radiative_transition_rate_s,self.nc,'radiative transition rate',nonnegative=True),float)
        self.photon_bath_temperature_K=_immutable_state_array(_array(
            photon_bath_temperature_K,self.nc,'photon bath temperature',positive=True),float)
        self.radiative_parameters()

        # A tuple per cell makes material event coverage explicit. Detach each
        # frozen event, including its normalized momentum tuples.
        from tcad.physics.spectral_auger import AugerEvent
        if auger_events is None:self.auger_events=None
        else:
            try:
                tables=tuple(tuple(row) for row in auger_events)
            except TypeError as error:raise ValueError('per-cell Auger event tables required') from error
            if len(tables)!=self.nc or any(not row or len(row)>4096 or
                    any(type(e) is not AugerEvent for e in row) for row in tables):
                raise ValueError('one nonempty table of 1..4096 AugerEvent objects per cell required')
            self.auger_events=tuple(tuple(AugerEvent(e.channel,e.momentum_shape,e.weight_m3_s) for e in row) for row in tables)
        self.auger_parameters()
        from .reconstruction_configuration import validate_reconstruction
        validate_reconstruction(self)

    def auger_parameters(self):
        """Discrete on-shell weights; no continuum or material fit is implied.

        The native device parameter vector stores coefficients in float64.
        Source algebra and conservative deposits use native real_t.
        """
        if self.auger_events is None:return None
        from tcad.physics.spectral_auger import AugerEvent
        if self.residual_orchestration!='native':raise ValueError('Auger device requires native orchestration')
        if not isinstance(self.auger_events,tuple) or len(self.auger_events)!=self.nc:
            raise ValueError('immutable per-cell Auger event coverage required')
        masses=[]
        for label in ('electrons','holes'):
            if len(self.valleys[label])!=1:raise ValueError('one Auger valley per carrier required')
            v=self.valleys[label][0]
            if (v.mass_normal!=v.mass_tangent_1 or v.mass_normal!=v.mass_tangent_2 or
                v.band_offset_owner_J!=0 or v.band_offset_neighbor_J!=0 or v.degeneracy!=np.floor(v.degeneracy)):
                raise ValueError('isotropic zero-offset integer-degeneracy Auger valleys required')
            masses.append(np.longdouble(v.mass_normal))
        if np.any(self.Ec.astype(np.longdouble)+self.Eh<=0):raise ValueError('positive Auger gap required')
        packed=[]
        for row in self.auger_events:
            if not isinstance(row,tuple) or not 1<=len(row)<=4096 or any(type(e) is not AugerEvent for e in row):
                raise ValueError('immutable nonempty AugerEvent tables required')
            values=[];keys=[]
            for event in row:
                with np.errstate(over='ignore',under='ignore',invalid='ignore'):
                    weight=float(event.weight_m3_s);q=np.asarray(event.momentum_shape,float)
                if not np.isfinite(weight) or (event.weight_m3_s>0 and weight==0) or not np.all(np.isfinite(q)):
                    raise ValueError('Auger device coefficients must fit float64')
                # Validate the geometry actually sent to C++, including any
                # float64 rounding of nearly coincident or threshold shapes.
                q=q.astype(np.longdouble);q=q/np.max(abs(q))
                if np.array_equal(q[0],q[1]):raise ValueError('distinct packed majority momenta required')
                if tuple(q[0])>tuple(q[1]):q=q[[1,0,2]]
                key=(event.channel,tuple(q.ravel()))
                if key in keys:raise ValueError('duplicate packed Auger event')
                keys.append(key)
                mass=masses[1 if event.channel=='hhe' else 0];other=masses[0 if event.channel=='hhe' else 1]
                D=np.sum(np.sum(q,axis=0)**2)/mass-np.sum(q[:2]**2)/mass-np.sum(q[2]**2)/other
                if D<=0:raise ValueError('Auger event has no positive-gap on-shell scale')
                values.extend((0. if event.channel=='eeh' else 1.,weight,*np.asarray(event.momentum_shape,float).ravel()))
            packed.append(values)
        return packed

    def radiative_parameters(self):
        """Validate the explicit matched isotropic direct-gap source contract."""
        if self.radiative_law not in (None,'matched_direct_gap_FD_Planck'):
            raise ValueError('explicit matched direct-gap FD/Planck radiative law required')
        rate=_array(self.radiative_transition_rate_s,self.nc,'radiative rate',nonnegative=True)
        bath=_array(self.photon_bath_temperature_K,self.nc,'photon bath temperature',positive=True)
        if self.radiative_law is None:
            if np.any(rate!=0):raise ValueError('nonzero radiative rate requires explicit direct-gap law')
            return None
        if self.residual_orchestration!='native':raise ValueError('radiative device requires native orchestration')
        valleys=[]
        for label in ('electrons','holes'):
            if len(self.valleys[label])!=1:raise ValueError('one isotropic radiative valley per carrier required')
            v=self.valleys[label][0]
            if (v.mass_normal!=v.mass_tangent_1 or v.mass_normal!=v.mass_tangent_2 or
                v.band_offset_owner_J!=0 or v.band_offset_neighbor_J!=0 or
                v.degeneracy!=np.floor(v.degeneracy)):
                raise ValueError('isotropic zero-offset integer-degeneracy radiative valleys required')
            valleys.append(v)
        if valleys[0].degeneracy!=valleys[1].degeneracy or np.any(self.Ec.astype(np.longdouble)+self.Eh<=0):
            raise ValueError('matched radiative degeneracies and positive direct gap required')
        return bath,rate

    def pair_generation_parameters(self):
        """Prescribed pair rate and mean material energy of each injected carrier.

        Kinetic energies are measured above the lowest matched valley edge.
        The sum of the two material energies is absorbed energy per pair.
        No absorption, photon distribution or transition rate is calculated.
        """
        rate=_array(self.pair_generation_rate_m3_s,self.nc,'pair generation rate',nonnegative=True)
        energies=[]
        for label,band,kinetic in (('electrons',self.Ec,self.pair_generation_kinetic_n_J),
                                   ('holes',self.Eh,self.pair_generation_kinetic_p_J)):
            edge=min(v.band_offset_owner_J for v in self.valleys[label])
            energy=band+edge+_array(kinetic,self.nc,'injected kinetic energy',nonnegative=True)
            _array(energy,self.nc,'injected material energy')
            energies.append(energy)
        total=energies[0].astype(np.longdouble)+energies[1]
        if np.any((rate>0)&((total<=0)|~np.isfinite(total)|~np.isfinite(total.astype(float)))):
            raise ValueError('positive finite absorbed energy per generated pair required')
        return rate,*energies

    def trap_parameters(self):
        if self.trap_capture_law not in (None,'energy_resolved_local_detailed_balance'):
            raise ValueError('invalid trap capture law')
        if self.trap_capture_law is None:
            if any(np.any(a!=0) for a in (self.Nt,self.cn,self.cp)):
                raise ValueError('three-temperature traps require explicit energy-resolved law')
            return None
        if self.residual_orchestration!='native':raise ValueError('dynamic traps require native orchestration')
        for v in (self.Nt,self.cn,self.cp):_array(v,self.nc,'trap density/capture',nonnegative=True)
        _array(self.Et,self.nc,'trap energy')
        en=self.Ec+min(v.band_offset_owner_J for v in self.valleys['electrons'])
        ep=self.Eh+min(v.band_offset_owner_J for v in self.valleys['holes'])
        if np.any(en.astype(np.longdouble)+ep<=0) or np.any(self.Et>en) or np.any(self.Et<-ep):
            raise ValueError('positive gap and in-gap trap energy required')
        return self.Nt,self.Et,self.cn,self.cp

    def relaxation_parameters(self):
        from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
        if not isinstance(self.relaxation_laws,tuple) or len(self.relaxation_laws)!=2:
            raise ValueError('two immutable relaxation law specifications required')
        values=[]
        for law in self.relaxation_laws:
            if law is not None and type(law) is not EnergyRelaxationPowerLaw:
                raise ValueError('explicit EnergyRelaxationPowerLaw or None required; callbacks are unsupported')
            row=(300.,1e25,0.,0.,0.) if law is None else law.parameters()
            _array(row,5,'relaxation law parameters')
            if min(row[:2])<=0:raise ValueError('positive relaxation references required')
            values.extend(row)
        return values

    @property
    def relaxation_law_descriptor(self):
        parameters=self.relaxation_parameters()
        variable=any(v!=0 for v in parameters[2:5]+parameters[7:10])
        return ('fixed_density_FD_energy_difference_over_state_dependent_tau' if variable else
                'fixed_density_FD_energy_difference_over_tau')

    def relaxation_times(self,n,p,Tn,Tp,Tl):
        self.relaxation_parameters()
        return {s:tau.copy() if law is None else law.evaluate(tau,density,T,Tl)
                for s,tau,density,T,law in (
                    ('electrons',self.tau_n,n,Tn,self.relaxation_laws[0]),
                    ('holes',self.tau_p,p,Tp,self.relaxation_laws[1]))}

    def _validate_state(self, state):
        from .three_temperature_contacts import normalize_contact_temperatures
        normalize_contact_temperatures(self.contacts, self.contact_carrier_temperature_K)
        from .reconstruction_configuration import validate_reconstruction
        validate_reconstruction(self)
        if self.bulk_potential_path not in ('endpoint_barrier','linear_series'):
            raise ValueError('invalid bulk_potential_path')
        super()._validate_state(state)
        if self.residual_orchestration not in ('native', 'python'):
            raise ValueError('invalid three-temperature residual orchestration')
        if (self.spectral_backend, self.local_backend, self.poisson_backend,
                self.nonlinear_backend, self.residual_backend) != ('native',)*5:
            raise ValueError('three-temperature solver requires native physics and nonlinear backends')
        if not isinstance(state, ThreeTemperatureState):
            raise ValueError('ThreeTemperatureState with independent carrier temperatures required')
        for name in ('electron_temperature_K', 'hole_temperature_K'):
            _array(getattr(state, name), self.nc, name, positive=True)
        self.trap_parameters()
        if self.kn != 0 or self.kp != 0:
            raise ValueError('three-temperature quantum energy is not implemented')
        for tau in (self.tau_n, self.tau_p):
            _array(tau, self.nc, 'relaxation time', positive=True)
        self.relaxation_parameters()
        _array(self.intercarrier_conductance_W_m3_K, self.nc, 'intercarrier conductance', nonnegative=True)
        self.pair_generation_parameters()
        self.radiative_parameters()
        self.auger_parameters()
        for slope in self.band_temperature_slopes:_array(slope,self.nc,'band temperature slope')
        for alpha in self.band_varshni_alpha:_array(alpha,self.nc,'band Varshni alpha')
        for beta in self.band_varshni_beta:_array(beta,self.nc,'band Varshni beta',nonnegative=True)
        self.band_edges(state.temperature_K)
        if self.temperature_dependent_bands:
            if self.residual_orchestration!='native':raise ValueError('temperature-dependent bands require native orchestration')
            self._validate_band_interfaces()
            derivatives=self.band_derivatives(state.temperature_K)
            effective=self.capacity.astype(np.longdouble)+state.n_m3*derivatives[0]+state.p_m3*derivatives[1]
            if np.any(~np.isfinite(effective)) or np.any(effective<=0):
                raise ValueError('positive coupled lattice band heat capacity required')

    def _validate_band_interfaces(self):
        # A smooth same-material lattice gradient uses the existing bulk
        # spectral diffusion edge. Only a discontinuity of the material law
        # requires a thermionic interface and its additional resistance.
        explicit=set(self.thermionic_faces)
        for f,i,j in zip(self.internal,self.i,self.j):
            if int(f) not in explicit and any(a[i]!=a[j] for a in
                    (self.Ec,self.Eh,*self.band_temperature_slopes,*self.band_varshni_alpha,*self.band_varshni_beta)):
                raise ValueError('material band discontinuities require explicit thermionic faces')

    @property
    def temperature_dependent_bands(self):
        return any(np.any(a!=0) for a in (*self.band_temperature_slopes,*self.band_varshni_alpha))

    @property
    def nonlinear_temperature_bands(self):
        return any(np.any(a!=0) for a in self.band_varshni_alpha)

    @property
    def band_temperature_law(self):
        return 'affine_plus_Varshni_lattice_temperature' if self.nonlinear_temperature_bands else 'affine_lattice_temperature'

    def band_derivatives(self,lattice_temperature_K):
        T=_array(lattice_temperature_K,self.nc,'band lattice temperature',positive=True).astype(np.longdouble)
        derivatives=[]
        for s,a,b in zip(self.band_temperature_slopes,self.band_varshni_alpha,self.band_varshni_beta):
            x,y=self._varshni_ratios(T,b)
            # f'(T)=x*(x+2*y), f(T)=T^2/(T+beta). Do not form
            # 2*beta in float64, or subtract nearly equal numbers from one.
            derivatives.append(s.astype(np.longdouble)-a.astype(np.longdouble)*x*(x+2*y))
        return tuple(derivatives)

    @staticmethod
    def _varshni_ratios(T,beta):
        t=np.asarray(T,np.longdouble);b=np.asarray(beta,np.longdouble)
        scale=np.maximum(t,b);u=t/scale;v=b/scale
        return u/(u+v),v/(u+v)

    def band_edges(self,lattice_temperature_K):
        """Prescribed affine plus Varshni effective bands, referenced at self.T.

        This energy bookkeeping law does not supply band entropy, a microscopic
        bandgap renormalization model, or measured material coefficients.
        """
        T=_array(lattice_temperature_K,self.nc,'band lattice temperature',positive=True)
        if not self.temperature_dependent_bands:return self.Ec,self.Eh
        t=T.astype(np.longdouble);r=np.longdouble(self.T)
        edges=[]
        for band,slope,alpha,beta in zip((self.Ec,self.Eh),self.band_temperature_slopes,
                self.band_varshni_alpha,self.band_varshni_beta):
            x,y=self._varshni_ratios(t,beta);z,_=self._varshni_ratios(r,beta)
            # Divided difference f[t,r]=x+y*z avoids both cancellation
            # at t~=r and products/sums of very large beta values.
            edges.append(np.asarray(band.astype(np.longdouble)+(t-r)*(
                slope.astype(np.longdouble)-alpha.astype(np.longdouble)*(x+y*z)),float))
        if any(np.any(~np.isfinite(b)) for b in edges) or np.any(edges[0].astype(np.longdouble)+edges[1]<=0):
            raise ValueError('finite positive temperature-dependent gap required')
        return tuple(edges)

    def _native_step(self, state, dt, charge_atol_C, particle_atol, energy_atol_J, max_nfev):
        from .native_three_temperature_dispatch import native_three_temperature_step
        return native_three_temperature_step(self, state, dt, charge_atol_C, particle_atol, energy_atol_J, max_nfev)

    def carrier_reservoirs(self, n, p, Tn, Tp, lattice_temperature_K=None):
        from tcad.physics.native_fermi_local import native_fermi_reservoirs
        if lattice_temperature_K is None:
            if self.temperature_dependent_bands:raise ValueError('explicit lattice temperature required for band edges')
            bands=(self.Ec,self.Eh)
        else:bands=self.band_edges(lattice_temperature_K)
        return {label: native_fermi_reservoirs(density, T, band, self.valleys[label])
                for label, density, T, band in (
                    ('electrons', n, Tn, bands[0]), ('holes', p, Tp, bands[1]))}

    def face_transport(self, *args, **kwargs):
        raise ValueError('use split_face_transport with explicit electron/hole/lattice temperatures')

    def carrier_density_energy(self, *args, **kwargs):
        raise ValueError('independent carrier temperatures required; use carrier_reservoirs')

    def energies(self, state, *, charge_atol_C):
        self._validate_state(state)
        poisson = self._poisson(state.n_m3, state.p_m3, state.trap_fraction, charge_atol_C)
        r = self.carrier_reservoirs(state.n_m3, state.p_m3,
                                  state.electron_temperature_K, state.hole_temperature_K,state.temperature_K)
        values = {s: float(np.sum(self.vol.astype(np.longdouble)*np.array(
            [v['energy_density_J_m3'] for v in rows], dtype=np.longdouble))) for s, rows in r.items()}
        values.update(lattice=float(np.sum(self.vol.astype(np.longdouble)*self.capacity*state.temperature_K)),
                      electrostatic=poisson['electrostatic_energy_J'])
        if self.trap_capture_law is not None:
            values['traps']=float(np.sum(self.vol.astype(np.longdouble)*self.Nt*self.Et*state.trap_fraction))
        return values, poisson

    def energy_increments(self, *args, **kwargs):
        raise ValueError('use the independently audited three-temperature step energy increments')

    def split_face_transport(self, n, p, Tn, Tp, Tl, poisson):
        from tcad.physics.native_fermi_local import native_fermi_reservoirs
        from tcad.physics.native_spectral import native_spectral_face
        if self.transport_reconstruction!='cell_mean':
            raise ValueError('configured reconstruction requires the native interval driver and midpoint work potentials')
        reservoirs = self.carrier_reservoirs(n, p, Tn, Tp,Tl)
        bands=self.band_edges(Tl)
        fluxes, energies, records = {}, {}, {}
        for label, base, exponent, z, band in (
                ('electrons', self.mn, self.mn_exponent, -1, bands[0]),
                ('holes', self.mp, self.mp_exponent, 1, bands[1])):
            mobility = base*(self.T/Tl)**exponent
            flux = np.zeros(len(self.mesh.faces)); energy = flux.copy(); rows = {}
            for f in list(self.internal) + list(self.contact_faces):
                f = int(f); face = self.mesh.faces[f]; i, j = face.owner, face.neighbor
                if j >= 0:
                    two = reservoirs[label][j]; potential = poisson['cell_potential_V'][j]
                    mu = mobility[j]; dn = self.dn[f]
                else:
                    contact = self.contacts[f]
                    density = contact.n_m3 if label == 'electrons' else contact.p_m3
                    contact_band=self.band_edges(np.full(self.nc,contact.temperature_K))[0 if label=='electrons' else 1][i]
                    from .three_temperature_contacts import carrier_contact_temperature
                    two = native_fermi_reservoirs([density], [carrier_contact_temperature(self,f,label)],
                                                 [contact_band], self.valleys[label])[0]
                    potential = self.bc[f]; dn = 0.
                    mu = base[i]*(self.T/contact.temperature_K)**exponent
                row = native_spectral_face(reservoirs[label][i], two, self.valleys[label],
                    potential_owner_V=poisson['cell_potential_V'][i], potential_neighbor_V=potential,
                    potential_face_V=poisson['face_potential_V'][f], charge_sign=z,
                    mobility_owner_m2_Vs=mobility[i], mobility_neighbor_m2_Vs=mu,
                    area_m2=self.area[f], distance_owner_m=self.do[f], distance_neighbor_m=dn,
                    emission_factor=self.emission[label].get(f),bulk_potential_path=self.bulk_potential_path)
                flux[f] = row['particle_flux_s']; energy[f] = row['material_energy_flux_W']
                rows[f] = row
            fluxes[label] = flux; energies[label] = energy; records[label] = rows
        return fluxes, energies, records, reservoirs

    def conduction(self, temperature):
        """Half-cell thermal resistances in series, including graded meshes."""
        heat = np.zeros(len(self.mesh.faces))
        for f, face in enumerate(self.mesh.faces):
            i, j = face.owner, face.neighbor
            if j >= 0:
                heat[f] = self.area[f]/(self.do[f]/self.conductivity[i] +
                    self.dn[f]/self.conductivity[j])*(temperature[i]-temperature[j])
            elif f in self.bath:
                heat[f] = self.area[f]*self.conductivity[i]/self.do[f]*(temperature[i]-self.bath[f])
        return heat

    def step(self, state, dt_s, *, charge_atol_C, particle_atol, energy_atol_J, max_nfev=600):
        self._validate_state(state)
        for name, value in dict(dt=dt_s, charge=charge_atol_C, particle=particle_atol, energy=energy_atol_J).items():
            _array(value, 1, name, positive=True)
        if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)) or max_nfev < 1:
            raise ValueError('positive integer residual evaluation budget required')
        dt = float(dt_s); endpoint = state.time_s + dt
        if not np.isfinite(endpoint) or endpoint <= state.time_s:
            raise ValueError('representable increasing clock required')
        dt = endpoint - state.time_s
        nc = self.nc; ld = np.longdouble; V = self.vol.astype(ld)
        if self.residual_orchestration == 'native':
            from .native_three_temperature_dispatch import native_three_temperature_step
            cache, old_poisson, statistics, history = self._native_step(
                state, dt, charge_atol_C, particle_atol, energy_atol_J, int(max_nfev))
        else:
            old_poisson = self._poisson(state.n_m3, state.p_m3, state.trap_fraction, charge_atol_C)
            if not old_poisson['valid']:
                raise ValueError('initial Poisson charge budget failed')
            old_r = self.carrier_reservoirs(state.n_m3, state.p_m3,
                                           state.electron_temperature_K, state.hole_temperature_K)
            old_u = {s: np.array([r['energy_density_J_m3'] for r in rows], dtype=ld) for s, rows in old_r.items()}
            scale_n = np.maximum(abs(old_u['electrons'])*V, V*self.capacity*state.electron_temperature_K)
            scale_p = np.maximum(abs(old_u['holes'])*V, V*self.capacity*state.hole_temperature_K)
            scale_l = V*self.capacity*state.temperature_K
            cache = {}
            def evaluate(x):
                n = state.n_m3.astype(ld)*np.exp(np.asarray(x[:nc], dtype=ld))
                p = state.p_m3.astype(ld)*np.exp(np.asarray(x[nc:2*nc], dtype=ld))
                Tn = state.electron_temperature_K*np.exp(x[2*nc:3*nc])
                Tp = state.hole_temperature_K*np.exp(x[3*nc:4*nc])
                Tl = state.temperature_K*np.exp(x[4*nc:])
                poisson = self._poisson(n, p, state.trap_fraction, charge_atol_C)
                rates, energies, records, reservoirs = self.split_face_transport(n, p, Tn, Tp, Tl, poisson)
                equilibrium = self.carrier_reservoirs(n, p, Tl, Tl)
                from tcad.physics.native_three_temperature import native_three_temperature_local
                u = {s: np.array([r['energy_density_J_m3'] for r in v], dtype=ld) for s,v in reservoirs.items()}
                ue = {s: np.array([r['energy_density_J_m3'] for r in v], dtype=ld) for s,v in equilibrium.items()}
                local = native_three_temperature_local(self,state,n,p,Tl,old_u,u,ue,
                    old_poisson,poisson,rates,energies,dt,Tn=Tn,Tp=Tp)
                du = dict(electrons=local['du_n'], holes=local['du_p'])
                exchange = dict(electrons=local['exchange_n'], holes=local['exchange_p'])
                work = dict(electrons=local['work_n'], holes=local['work_p'])
                carrier_rows = dict(electrons=local['energy_n'], holes=local['energy_p'])
                heat,dl,lattice_row = local['heat'],local['dl'],local['energy_l']
                rn,rp = local['rn'],local['rp']
                rows = np.r_[carrier_rows['electrons'], carrier_rows['holes'], lattice_row]
                merit = max(float(np.max(abs(rn)))/particle_atol, float(np.max(abs(rp)))/particle_atol,
                    float(np.max(abs(rows)))/energy_atol_J,
                    abs(float(Q*np.sum(rp-rn, dtype=ld)))/charge_atol_C)
                cache.update(n=n, p=p, Tn=Tn, Tp=Tp, Tl=Tl, poisson=poisson,
                    rates=rates, energies=energies, records=records, du=du, dl=dl,
                    exchange=exchange, work=work, heat=heat, rn=rn, rp=rp, rows=rows, merit=merit,tau=local['tau'])
                cache['intercarrier_exchange_J'] = local['intercarrier_exchange_J']
                cache['generated_pairs'] = local['generated_pairs']
                cache['generation_energy_J'] = local['generation_energy_J']
                from .three_temperature_merit import global_conservation_merit
                merit = max(merit, global_conservation_merit(
                    self, state, cache, old_poisson, dt, charge_atol_C, energy_atol_J))
                cache['merit'] = merit
                normalized = np.r_[rn/(V*state.n_m3), rp/(V*state.p_m3),
                    carrier_rows['electrons']/scale_n, carrier_rows['holes']/scale_p, lattice_row/scale_l]
                return np.asarray(normalized, dtype=float), merit
            origin = np.r_[np.log(state.n_m3), np.log(state.p_m3), np.log(state.electron_temperature_K),
                           np.log(state.hole_temperature_K), np.log(state.temperature_K)]
            lower = np.r_[np.full(2*nc, -600.), np.full(3*nc, 0.)]-origin
            upper = np.r_[np.full(2*nc, 600.), np.full(3*nc, np.log(1e5))]-origin
            from tcad.core._bindings import native_fermi_newton_raw
            solution, statistics, history = native_fermi_newton_raw(evaluate, np.zeros(5*nc),
                np.asarray(lower, float), np.asarray(upper, float), int(max_nfev))
            evaluate(np.asarray(solution, float))
        if cache['merit'] > 1 or not cache['poisson']['valid']:
            raise ValueError('three-temperature local conservation budget failed')
        new = ThreeTemperatureState(cache['n'], cache['p'], cache.get('trap_fraction',state.trap_fraction), cache['Tl'], endpoint,
                                    cache['Tn'], cache['Tp'])
        boundary = np.array([f for f, face in enumerate(self.mesh.faces) if face.neighbor < 0], int)
        b = cache['poisson']; a = old_poisson
        qflux = Q*(cache['rates']['holes']-cache['rates']['electrons'])
        dq = b['integrated_D_flux_C']-a['integrated_D_flux_C']
        terminals = {f: float(-dq[f]/dt-qflux[f]) for f in self.bc}
        displacement = -sum(value*dq[f] for f, value in self.bc.items())
        conduction = -dt*sum(value*qflux[f] for f, value in self.bc.items())
        increments = {s: float(np.sum(cache['du'][s], dtype=ld)) for s in ('electrons', 'holes')}
        increments.update(lattice=float(np.sum(cache['dl'], dtype=ld)),
            electrostatic=float(ld(b['electrostatic_energy_J'])-ld(a['electrostatic_energy_J'])))
        if self.trap_capture_law is not None:increments['traps']=float(np.sum(cache['trap_energy_increment_J'],dtype=ld))
        outward = {s: dt*float(np.sum(cache['energies'][s][boundary], dtype=ld)) for s in ('electrons', 'holes')}
        outward['lattice'] = dt*float(np.sum(cache['heat'][boundary], dtype=ld))
        if self.radiative_law is not None:
            outward['photons']=float(np.sum(cache['radiative_photon_energy_J'],dtype=ld))
        absorbed = sum(np.sum(v.astype(ld),dtype=ld) for v in cache['generation_energy_J'].values())
        residual = float(ld(displacement)+ld(conduction)+absorbed-sum(map(ld, increments.values()))-sum(map(ld, outward.values())))
        charge = float(Q*np.sum(V*(new.p_m3-state.p_m3-new.n_m3+state.n_m3-
                       self.Nt.astype(ld)*(new.trap_fraction.astype(ld)-state.trap_fraction)), dtype=ld) +
                       dt*np.sum(qflux[boundary], dtype=ld))
        if abs(residual) > energy_atol_J or max(abs(charge), abs(dt*sum(terminals.values()))) > charge_atol_C:
            raise ValueError('three-temperature global energy or charge budget failed')
        report = dict(valid=True, scope='FD_spectral_three_temperature_energy_transport', dt_s=dt,
            bulk_potential_path=self.bulk_potential_path,
            state_advanced=True, modeled_device_energy_closed=True, complete_device_energy=False,
            physical_validated=False, residual_backend='native', physics_backend='native',
            residual_orchestration=self.residual_orchestration, local_conservation_backend='native',
            native_residual_dispatch=self.residual_orchestration == 'native',
            mobility_temperature='lattice', relaxation_law=self.relaxation_law_descriptor,
            cell_relaxation_time_s=cache['tau'],
            energy_increments_J=increments, outward_energy_J=outward,
            source_work_J=float(displacement+conduction), displacement_work_J=float(displacement),
            conduction_work_J=float(conduction), energy_residual_J=residual,
            terminal_currents_A=terminals, charge_balance_residual_C=charge,
            integrated_particle_flux_s=cache['rates'], integrated_carrier_energy_flux_W=cache['energies'],
            integrated_heat_flux_W=cache['heat'], face_moments=cache['records'],
            cell_energy_residuals_J=np.asarray(cache['rows'], float),
            cell_exchange_J={s: np.asarray(v, float) for s, v in cache['exchange'].items()},
            cell_intercarrier_exchange_J=cache['intercarrier_exchange_J'],
            intercarrier_exchange_law='linear_temperature_conductance',
            cell_electrical_work_J=cache['work'], particle_residuals=np.asarray(np.r_[cache['rn'], cache['rp']], float),
            nonlinear_statistics=np.asarray(statistics), nonlinear_history=np.asarray(history),
            missing_physics=['traps_quantum_FE_recombination', 'momentum_equation', 'general_mass_jumps_nonorthogonal',
                             'main_DeviceSimulator_integration', 'experimental_relaxation_calibration'] +
                            ([] if self.residual_orchestration == 'native' else ['monolithic_native_dispatch']))
        if self.transport_reconstruction!='cell_mean':
            report.update(transport_reconstruction=self.transport_reconstruction,
                reconstruction_storage='unchanged_cell_mean_FD',fully_discrete_entropy_closed=False)
        if self.temperature_dependent_bands:
            report.update(band_temperature_law=self.band_temperature_law,
                band_work_law='symmetric_density_times_band_increment',
                cell_band_work_from_lattice_J=cache['band_work_J'],
                temperature_dependent_band_energy_coupled=True,
                temperature_dependent_band_entropy_closed=False)
        if np.any(self.pair_generation_rate_m3_s != 0):
            report.update(cell_generated_pairs=cache['generated_pairs'],
                cell_pair_generation_energy_J=cache['generation_energy_J'],absorbed_pair_energy_J=float(absorbed),
                pair_generation_law='prescribed_constant_pair_rate_and_mean_injection_energy')
        if self.trap_capture_law is not None:
            report.update(trap_capture_law=self.trap_capture_law,cell_trap_moments=cache['trap_moments'],
                cell_trap_particle_residuals=cache['trap_particle_residuals'],
                cell_trap_capture_counts=cache['trap_capture_counts'],
                cell_trap_carrier_energy_removed_J=cache['trap_carrier_energy_removed_J'],
                cell_trap_energy_increment_J=cache['trap_energy_increment_J'],
                cell_trap_lattice_heat_J=cache['trap_lattice_heat_J'],
                cell_trap_entropy_production_J_K=cache['trap_entropy_J_K'],
                dynamic_trap_device_coupled=True)
            report['particle_residuals']=np.r_[report['particle_residuals'],cache['trap_particle_residuals']]
            report['missing_physics'][0]='quantum_FE_radiative_Auger_avalanche'
        if self.radiative_law is not None:
            report.update(radiative_law=self.radiative_law,radiative_device_coupled=True,
                photon_bath_law='maintained_Planck_zero_chemical_potential',
                cell_radiative_moments=cache['radiative_moments'],
                cell_radiative_recombined_pairs=cache['radiative_pairs'],
                cell_radiative_carrier_energy_removed_J=cache['radiative_carrier_energy_removed_J'],
                cell_radiative_photon_energy_J=cache['radiative_photon_energy_J'],
                cell_radiative_entropy_production_J_K=cache['radiative_entropy_J_K'])
            report['missing_physics'][0]=('quantum_FE_Auger_avalanche' if self.trap_capture_law is not None
                                          else 'traps_quantum_FE_Auger_avalanche')
        if self.auger_events is not None:
            from tcad.physics.spectral_auger import LAW
            report.update(auger_law=LAW,auger_device_coupled=True,
                auger_material_calibrated=False,auger_continuum_kernel_integrated=False,
                cell_auger_moments=cache['auger_moments'],
                cell_auger_recombined_pairs=cache['auger_pairs'],
                cell_auger_carrier_energy_added_J=cache['auger_carrier_energy_added_J'],
                cell_auger_entropy_production_J_K=cache['auger_entropy_J_K'])
            report['missing_physics'][0]='general_bands_continuum_Auger_avalanche_quantum_FE'+(
                '_traps' if self.trap_capture_law is None else '')+('_radiation' if self.radiative_law is None else '')
        from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
        audit = audit_three_temperature_energy(self, state, new, report, charge_atol_C=charge_atol_C,
                                               particle_atol=particle_atol, energy_atol_J=energy_atol_J)
        if not audit['valid']:
            raise ValueError('independent three-temperature energy audit failed: ' + str(audit))
        report['independent_audit'] = audit
        return new, report
