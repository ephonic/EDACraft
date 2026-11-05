"""Energy-derived generalized SRH rates for the isothermal sheet prototype.

The density-based capture coefficients are phenomenological. Emission uses
n1=n*exp((Et-Fn)/VT)/g and p1=p*exp((Fp-Et)/VT)*g, with the *actual* FD
reservoir densities. Thus n1/p1 are state dependent, not Boltzmann constants.
This enforces local detailed balance but is not a microscopic capture kernel,
an oxide tunneling model, or a calibrated material/defect parameter set.
"""
from dataclasses import dataclass
import numpy as np
from tcad.material.sheet import _finite, _positive_scalar, Q, KB


@dataclass(frozen=True)
class EnergySheetTrap:
    density_m2: object
    capture_n_m2_s: object
    capture_p_m2_s: object
    energy_offset_eV: object = 0.
    degeneracy: object = 1.
    kind: str = 'acceptor'

    def __post_init__(self):
        if self.kind not in ('acceptor', 'donor'):
            raise ValueError('trap kind must be acceptor or donor')
        for name in ('density_m2', 'capture_n_m2_s', 'capture_p_m2_s',
                     'energy_offset_eV', 'degeneracy'):
            value = np.array(_finite(getattr(self, name), name), copy=True)
            if name == 'degeneracy':
                if np.any(value <= 0):raise ValueError('degeneracy must be positive')
            elif name != 'energy_offset_eV' and np.any(value < 0):
                raise ValueError(name+' must be nonnegative')
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    def bind(self, shape):
        values = {}
        for name in ('density_m2', 'capture_n_m2_s', 'capture_p_m2_s',
                     'energy_offset_eV', 'degeneracy'):
            try:values[name] = np.broadcast_to(getattr(self, name), shape).copy().ravel()
            except ValueError as exc:raise ValueError(name+' must be scalar or sheet-shaped') from exc
        return EnergySheetTrap(**values, kind=self.kind)

    def evaluate(self, material, phi, Fn, Fp, temperature_K, old_occupancy, dt_s=None,
                 *, equilibrium_fermi_eV=None):
        """BE elimination; derivatives are with respect to Fn/Fp in eV.

        Et = material.reference_eV + energy_offset_eV - phi. g is the ratio
        of occupied to empty statistical weights: f_eq/(1-f_eq)=g*exp((F-Et)/VT).
        dt=None freezes the externally prepared occupancy, as in SheetTrap.
        equilibrium_fermi_eV selects initialization at a fixed common reservoir
        Fermi energy, with old_occupancy=None and dt_s=None. Then df_dphi is
        returned separately; Fn/Fp partials of occupancy are zero. This mode
        must not be used to advance a transient history.
        Accepted reservoir eta is [-600,200]; unrepresentable rates fail.
        """
        vt = KB*_positive_scalar(temperature_K, 'temperature_K')/Q
        equilibrium = equilibrium_fermi_eV is not None
        if equilibrium:
            if dt_s is not None or old_occupancy is not None:
                raise ValueError('thermal equilibrium is initialization only; omit occupancy and dt_s')
            common = _finite(equilibrium_fermi_eV, 'equilibrium_fermi_eV')
            if common.ndim:raise ValueError('equilibrium_fermi_eV must be scalar')
            old_occupancy = .5
        phi, Fn, Fp, f0 = np.broadcast_arrays(*[_finite(v, n) for v, n in
            ((phi, 'phi'), (Fn, 'Fn'), (Fp, 'Fp'), (old_occupancy, 'old_occupancy'))])
        if np.any((f0 < 0) | (f0 > 1)):raise ValueError('occupancy must be in [0,1]')
        eta_n = (Fn+phi-material.reference_eV-material.gap_eV/2)/vt
        eta_p = (material.reference_eV-material.gap_eV/2-phi-Fp)/vt
        if np.any((eta_n < -600) | (eta_n > 200) | (eta_p < -600) | (eta_p > 200)):
            raise ValueError('energy trap reservoir eta must be in [-600,200]')
        st = material.statistics(phi, Fn, Fp, temperature_K)
        n, p = st.n_m2, st.p_m2
        an, ap = st.dn_dFn_m2_eV, st.minus_dp_dFp_m2_eV
        logg = np.log(self.degeneracy)
        # Log products avoid exp(600)*exp(-600) intermediates.
        def emission(c, density, exponent):
            c, density, exponent = np.broadcast_arrays(c, density, exponent)
            result = np.zeros_like(density); active = c > 0
            with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
                result[active] = np.exp(np.log(c[active])+np.log(density[active])+exponent[active])
            if np.any(active & ((result <= 0) | ~np.isfinite(result))):
                raise FloatingPointError('energy trap emission is not representable')
            return result
        en = emission(self.capture_n_m2_s, n,
            (self.energy_offset_eV-material.gap_eV/2)/vt-eta_n-logg)
        ep = emission(self.capture_p_m2_s, p,
            -(self.energy_offset_eV+material.gap_eV/2)/vt-eta_p+logg)
        with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
            cn = self.capture_n_m2_s*n; cp = self.capture_p_m2_s*p
            dcn = self.capture_n_m2_s*an; dcp = -self.capture_p_m2_s*ap
            den = en*(an/n-1/vt); dep = ep*(1/vt-ap/p)
            a = cn+ep; b = en+cp
            if equilibrium:
                from scipy.special import expit
                eta = (common+phi-material.reference_eV-self.energy_offset_eV)/vt+logg
                if not np.all(np.isfinite(eta)):
                    raise FloatingPointError('thermal trap energy is not representable')
                f = expit(eta); empty = expit(-eta)
                dfn = np.zeros_like(f); dfp = np.zeros_like(f)
            elif dt_s is None:
                f = f0.copy(); empty = 1-f; dfn = np.zeros_like(f); dfp = np.zeros_like(f)
            else:
                dt = _positive_scalar(dt_s, 'dt_s')
                if dt < 1/np.finfo(float).max:raise ValueError('inverse dt_s must be representable')
                h = 1/dt; D = h+a+b
                if np.any(~np.isfinite(D)) or np.any(D <= 0):
                    raise FloatingPointError('energy trap denominator is not representable')
                f = (h*f0+a)/D; empty = (h*(1-f0)+b)/D
                dfn = (dcn*empty-den*f)/D; dfp = (dep*empty-dcp*f)/D
            kn = cn+en; kp = cp+ep
            out = dict(occupancy=f, empty=empty, df_dFn=dfn, df_dFp=dfp,
                charge_C_m2=Q*self.density_m2*(empty if self.kind == 'donor' else 0.-f),
                electron_capture_s=cn*empty-en*f, hole_capture_s=cp*f-ep*empty,
                electron_activity_s=cn*empty+en*f, hole_activity_s=cp*f+ep*empty,
                drn_dFn=dcn*empty-den*f-kn*dfn, drn_dFp=-kn*dfp,
                drp_dFn=kp*dfn, drp_dFp=dcp*f-dep*empty+kp*dfp,
                emission_n_s=en, emission_p_s=ep)
            if equilibrium:out['df_dphi'] = f*empty/vt
        if not all(np.all(np.isfinite(v)) for v in out.values()) or np.any((f < 0) | (f > 1)):
            raise FloatingPointError('energy trap state or rate is not representable')
        return out
