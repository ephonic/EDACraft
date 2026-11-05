"""Independent DOS/Decimal audit of the isolated FD energy-excess state.

No native calls, production relaxation evaluator, or production energy helper.
Unscaled carrier, lattice and endpoint residuals retain the requested J budget.
"""
from decimal import Decimal,localcontext
import math
from .fermi_spectral_energy import reference_reservoir


def _states(config,*states):
    for s in states:
        if s.configuration_sha256!=config.sha256 or (s.density_n_m3,s.density_p_m3)!=config.initial_densities_m3:
            raise ValueError('isolated state configuration or density changed')
        if not Decimal(config.parameters[14])<=Decimal(s.lattice_temperature_K)<=Decimal(config.parameters[15]):
            raise ValueError('isolated lattice temperature outside frozen bracket')


def _eq(config,state,k):
    return Decimal.from_float(float(reference_reservoir(float(config.initial_densities_m3[k]),
        float(state.lattice_temperature_K),float(config.parameters[2+k]),
        (config.valleys_n,config.valleys_p)[k])['energy_density_J_m3']))


def audit_isolated_relaxation_initial(config,state,*,energy_atol_J):
    _states(config,state)
    if state.time_s!=config.initial_time_s or Decimal(state.lattice_temperature_K)!=Decimal(config.initial_temperatures_K[2]):
        raise ValueError('isolated initial clock or lattice changed')
    with localcontext() as context:
        context.prec=90;V=Decimal(config.parameters[1]);errors=[]
        for k,excess in enumerate((state.electron_excess_energy_J_m3,state.hole_excess_energy_J_m3)):
            initial=reference_reservoir(float(config.initial_densities_m3[k]),float(config.initial_temperatures_K[k]),
                float(config.parameters[2+k]),(config.valleys_n,config.valleys_p)[k])['energy_density_J_m3']
            errors.append(V*(Decimal.from_float(float(initial))-_eq(config,state,k)-Decimal(excess)))
        return dict(valid=all(abs(e)<=Decimal.from_float(float(energy_atol_J)) for e in errors),
            independently_reconstructed_initial_energy_errors_J=list(map(str,errors)),native_operators_used=False)


def audit_isolated_relaxation_step(config,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J,
                                 source_power_W=(0.,0.,0.)):
    _states(config,old,new)
    if any(isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in (charge_atol_C,particle_atol,energy_atol_J)):
        raise ValueError('positive finite independent isolated budgets required')
    dt=new.time_s-old.time_s
    if dt<=0 or not math.isfinite(dt) or report.get('dt_s')!=dt:
        raise ValueError('matching increasing isolated clocks required')
    power=tuple(source_power_W)
    if len(power)!=3 or any(isinstance(v,bool) or not math.isfinite(v) for v in power):
        raise ValueError('three finite independent reservoir powers required')
    power=tuple(map(float,power));driven=any(power)
    expected=dict(scope='driven_single_cell_FD_energy_excess_BE' if driven else 'isolated_single_cell_FD_energy_excess_BE',configuration_sha256=config.sha256,
        execution_backend='native',thermodynamic_state='same_density_FD_equilibrium_at_Tl_plus_signed_carrier_energy_excess',
        complete_device_energy=False,physical_validated=False,measured_ac_material_calibration=False,
        main_DeviceSimulator_integrated=False,carrier_temperature_exponent_supported=0)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in expected.items()):
        raise ValueError('isolated execution/scope metadata mismatch')
    # Stage61 stateless saved reports remain auditable. New owner claims must
    # carry the complete restricted transaction schema; no broad integration.
    ownership=dict(state_owner='C++ DeviceSimulator::isolated_relaxation',
        main_DeviceSimulator_scoped_isolated_relaxation_integrated=True,
        state_transaction='prepare-independent-audit-commit')
    if any(k in report for k in ownership):
        if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in ownership.items()):
            raise ValueError('isolated native ownership metadata mismatch')
    def decimals(key,count):
        values=report[key]
        if not isinstance(values,(list,tuple)) or len(values)!=count:raise ValueError('isolated report coverage mismatch')
        result=[Decimal(v) for v in values]
        if not all(v.is_finite() for v in result):raise ValueError('finite isolated report decimals required')
        return result
    with localcontext() as context:
        context.prec=90
        p=list(map(Decimal,config.parameters));V=p[1];t=Decimal(new.lattice_temperature_K)
        for state in (old,new):
            for k,field in enumerate(('electron_excess_energy_J_m3','hole_excess_energy_J_m3')):
                valleys=(config.valleys_n,config.valleys_p)[k]
                edge=p[2+k]+min(Decimal.from_float(float(v.band_offset_owner_J)) for v in valleys)
                if _eq(config,state,k)+Decimal(getattr(state,field))<=Decimal(config.initial_densities_m3[k])*edge:
                    raise ValueError('independent driven carrier energy below band minimum')
        h=Decimal.from_float(dt);gate=Decimal.from_float(float(energy_atol_J))
        source=[h*Decimal.from_float(v) for v in power]
        if driven:
            if (report.get('source_power_W')!=list(power) or
                    report.get('source_model')!='prescribed_constant_reservoir_power' or
                    report.get('source_order')!=['electrons','holes','lattice']):
                raise ValueError('prescribed source metadata mismatch')
            given_source=decimals('source_impulses_J',3)
            if given_source!=source:raise ValueError('source impulses disagree with independent powers and physical clock')
        elif any(k in report for k in ('source_power_W','source_impulses_J','source_model','source_order')):
            raise ValueError('unexpected source declaration in closed step')
        given_exchange=decimals('exchange_J',2);given_du=decimals('carrier_energy_increments_J',2)
        given_tau=decimals('effective_relaxation_times_s',2);given_rows=decimals('energy_residuals_J',3)
        errors=[];rows=[];du=[];exchange=[];tau_errors=[];entropy_sign=[]
        for k,(before,after) in enumerate(zip((old.electron_excess_energy_J_m3,old.hole_excess_energy_J_m3),
                                             (new.electron_excess_energy_J_m3,new.hole_excess_energy_J_m3))):
            b=6+4*k
            logtau=p[4+k].ln()+p[b+2]*(t/p[b]).ln()+p[b+3]*(Decimal(config.initial_densities_m3[k])/p[b+1]).ln()
            if not Decimal(-750)<logtau<Decimal(711):raise ValueError('independent isolated relaxation time out of range')
            tau=logtau.exp()
            if not math.isfinite(float(tau)) or float(tau)<=0:raise ValueError('positive float64 isolated relaxation time required')
            if given_tau[k]<=0:raise ValueError('positive reported isolated relaxation time required')
            tau_errors.append(abs(given_tau[k]/tau-1))
            # The tiny excess is an explicit thermodynamic state coordinate.
            # Never replace it by subtracting rounded absolute FD energies.
            ex=h*V*Decimal(after)/tau
            delta=V*((_eq(config,new,k)-_eq(config,old,k))+Decimal(after)-Decimal(before))
            exchange.append(ex);du.append(delta);rows.append(delta+ex-source[k])
            errors.extend((given_exchange[k]-ex,given_du[k]-delta))
            entropy_sign.append(ex*Decimal(after)>=0)
        lattice=V*p[0]*(t-Decimal(old.lattice_temperature_K))
        rows.append(lattice-sum(exchange)-source[2]);endpoint=sum(du)+lattice-sum(source)
        errors.extend(a-b for a,b in zip(given_rows,rows))
        given_lattice=Decimal(report['lattice_energy_increment_J'])
        if not given_lattice.is_finite():raise ValueError('finite isolated lattice increment required')
        errors.append(given_lattice-lattice)
        valid=all(abs(x)<=gate for x in [*rows,*errors,endpoint]) and all(entropy_sign) and max(tau_errors)<=Decimal('1e-12')
        result=dict(valid=valid,local_energy_residuals_J=list(map(str,rows)),endpoint_energy_residual_J=str(endpoint),
            independently_reconstructed_exchange_J=list(map(str,exchange)),
            maximum_report_error_J=str(max(map(abs,errors),default=Decimal(0))),
            maximum_relative_relaxation_error=str(max(tau_errors)),
            relaxation_entropy_sign_nonnegative=all(entropy_sign),native_operators_used=False,
            particle_residual=0,charge_residual_C=0,complete_device_energy=False,physical_validated=False)
        if driven:result['external_energy_input_J']=list(map(str,source))
        return result
