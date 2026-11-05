"""Independent DOS/Decimal audit of implicit lattice faces and carrier excess."""
from decimal import Decimal,localcontext
import math
import numpy as np
from .isolated_relaxation import _eq,_states,audit_isolated_relaxation_initial


def _coverage(config,*states):
    for state in states:
        if state.configuration_sha256!=config.sha256 or len(state.cells)!=len(config.cells):
            raise ValueError('lattice excess configuration/coverage mismatch')
        for c,s in zip(config.cells,state.cells):
            _states(c,s)
            if s.time_s!=state.time_s:raise ValueError('lattice excess cell clocks disagree')


def audit_lattice_excess_initial(config,state,*,energy_atol_J):
    _coverage(config,state)
    audits=[audit_isolated_relaxation_initial(c,s,energy_atol_J=energy_atol_J) for c,s in zip(config.cells,state.cells)]
    with localcontext() as ctx:
        ctx.prec=90
        endpoint=sum(Decimal(v) for a in audits for v in a['independently_reconstructed_initial_energy_errors_J'])
        valid=all(a['valid'] for a in audits) and abs(endpoint)<=Decimal.from_float(float(energy_atol_J))
    return dict(valid=valid,cells=audits,whole_device_initial_energy_error_J=str(endpoint),native_operators_used=False)


def audit_lattice_excess_step(config,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J,source_power_W=None):
    _coverage(config,old,new);nc=len(config.cells);nf=len(config.faces)
    if any(isinstance(v,(bool,np.bool_)) or not math.isfinite(v) or v<=0 for v in (charge_atol_C,particle_atol,energy_atol_J)):
        raise ValueError('positive finite lattice excess audit budgets required')
    dt=new.time_s-old.time_s
    if not math.isfinite(dt) or dt<=0 or report.get('dt_s')!=dt:raise ValueError('matching increasing lattice excess clocks required')
    expected=dict(scope='carrier_blocked_lattice_Fourier_FD_excess_BE',configuration_sha256=config.sha256,
        execution_backend='native',state_owner='C++ DeviceSimulator::isolated_relaxation',
        state_transaction='prepare-independent-audit-commit',carrier_faces='explicit_zero_transmission',
        carrier_temperature_exponent_supported=0,complete_device_energy=False,physical_validated=False,
        measured_ac_material_calibration=False,general_carrier_transport_integrated=False)
    if config.baths:
        expected.update(scope='carrier_blocked_lattice_Fourier_bath_FD_excess_BE',
            thermal_boundary_law='maintained_temperature_half_cell_Fourier',bath_energy_sign='positive_outward_from_device')
    elif 'boundary_energy_impulses_J' in report:
        raise ValueError('unconfigured bath impulses are not allowed')
    band_keys={'band_temperature_law','temperature_dependent_band_energy_coupled',
        'temperature_dependent_band_entropy_closed','cell_band_work_from_lattice_J','nonlinear_band_storage_primitive'}
    if config.affine_bands:
        if len(config.affine_bands)!=nc:raise ValueError('affine band cell coverage mismatch')
        expected.update(band_temperature_law='affine_lattice_temperature',
            temperature_dependent_band_energy_coupled=True,temperature_dependent_band_entropy_closed=False)
    elif band_keys.intersection(report):
        raise ValueError('unconfigured affine band work is not allowed')
    if config.varshni_bands:
        if not config.affine_bands or len(config.varshni_bands)!=nc:raise ValueError('Varshni band coverage mismatch')
        expected.update(band_temperature_law='affine_plus_Varshni_lattice_temperature',
            nonlinear_band_storage_primitive='exact_Varshni_divided_difference')
    elif 'nonlinear_band_storage_primitive' in report:
        raise ValueError('unconfigured nonlinear band primitive')
    precision_keys={'lattice_coordinate_precision','precision_fallback_reason','iteration_counter_scope'}
    if precision_keys.intersection(report):
        if (not precision_keys.issubset(report) or report['lattice_coordinate_precision']!='float128' or
                report['precision_fallback_reason'] not in ('float64_line_search','float64_derivative_stagnation','float64_singular_Jacobian') or
                report['iteration_counter_scope']!='float128_retry_only; residual_evaluations_include_all_attempts'):
            raise ValueError('invalid lattice precision retry metadata')
    if any(type(report.get(k)) is not type(v) or report[k]!=v for k,v in expected.items()):
        raise ValueError('lattice excess execution/scope metadata mismatch')
    power=np.zeros((nc,3)) if source_power_W is None else np.asarray(source_power_W)
    if power.shape!=(nc,3) or power.dtype.kind not in 'fiu' or not np.all(np.isfinite(power)):
        raise ValueError('independent cell powers required')
    power=np.asarray(power,float)
    if report.get('source_power_W')!=power.tolist():raise ValueError('independent power contract mismatch')
    def vector(values,count):
        if not isinstance(values,(list,tuple)) or len(values)!=count:raise ValueError('lattice excess report coverage mismatch')
        result=list(map(Decimal,values))
        if not all(v.is_finite() for v in result):raise ValueError('finite lattice excess report decimals required')
        return result
    def matrix(key,width):
        rows=report[key]
        if not isinstance(rows,(list,tuple)) or len(rows)!=nc:raise ValueError('lattice excess report cell coverage mismatch')
        return [vector(row,width) for row in rows]
    with localcontext() as ctx:
        ctx.prec=90;h=Decimal.from_float(dt);gate=Decimal.from_float(float(energy_atol_J))
        source=[[h*Decimal.from_float(float(v)) for v in row] for row in power]
        if matrix('source_impulses_J',3)!=source:raise ValueError('source impulses disagree with powers and clocks')
        given_exchange=matrix('cell_exchange_J',2);given_du=matrix('cell_carrier_energy_increments_J',2)
        given_rows=matrix('cell_energy_residuals_J',3);given_tau=matrix('cell_effective_relaxation_times_s',2)
        given_dl=vector(report['cell_lattice_energy_increments_J'],nc)
        given_face=vector(report['face_energy_impulses_J'],nf)
        given_work=matrix('cell_band_work_from_lattice_J',2) if config.affine_bands else None
        errors=[];rows=[];endpoint=Decimal(0);tau_errors=[];div=[Decimal(0)]*nc;face_impulses=[];face_entropy=[]
        for a,b,area,do,dn,ko,kn in config.faces:
            area,do,dn,ko,kn=map(Decimal,(area,do,dn,ko,kn))
            if any(v<=0 for v in (area,do,dn,ko,kn)) or not (0<=a<nc and 0<=b<nc and a!=b):
                raise ValueError('invalid independent Fourier geometry')
            Ta,Tb=Decimal(new.cells[a].lattice_temperature_K),Decimal(new.cells[b].lattice_temperature_K)
            impulse=h*area/(do/ko+dn/kn)*(Ta-Tb)
            face_impulses.append(impulse);div[a]+=impulse;div[b]-=impulse
            face_entropy.append(impulse*(1/Tb-1/Ta))
        errors.extend(a-b for a,b in zip(given_face,face_impulses))
        # Boundaries are external energy exchange: do not cancel them as faces.
        boundary=[Decimal(0)]*nc;bath_impulses=[];bath_entropy=[];seen=set()
        for face,owner,area,distance,k,Tbath in config.baths:
            values=list(map(Decimal,(area,distance,k,Tbath)))
            if (not isinstance(face,int) or isinstance(face,bool) or face<0 or face in seen or
                    not isinstance(owner,int) or isinstance(owner,bool) or not 0<=owner<nc or
                    any(not v.is_finite() or v<=0 for v in values)):
                raise ValueError('invalid independent bath geometry and temperature')
            seen.add(face);area,distance,k,Tbath=values;T=Decimal(new.cells[owner].lattice_temperature_K)
            impulse=h*area*k/distance*(T-Tbath)
            bath_impulses.append(impulse);boundary[owner]+=impulse
            bath_entropy.append(impulse*(1/Tbath-1/T))
        if config.baths:errors.extend(a-b for a,b in zip(vector(report['boundary_energy_impulses_J'],len(config.baths)),bath_impulses))
        signs=[]
        for i,(config_cell,before,after) in enumerate(zip(config.cells,old.cells,new.cells)):
            p=list(map(Decimal,config_cell.parameters));V=p[1];T=Decimal(after.lattice_temperature_K)
            exchanges=[];increments=[];work=[Decimal(0),Decimal(0)]
            if config.affine_bands:
                sn,sp,reference=map(Decimal,config.affine_bands[i])
                if not all(v.is_finite() for v in (sn,sp,reference)) or reference<=0:
                    raise ValueError('finite affine slopes and positive reference temperature required')
                densities=list(map(Decimal,config_cell.initial_densities_m3))
                coeff=vector(config.varshni_bands[i],4) if config.varshni_bands else [Decimal(0)]*4
                if any(v<0 for v in coeff):raise ValueError('nonnegative independent Varshni coefficients required')
                # Independent divided difference: f[A,B]=1-beta^2/((A+beta)(B+beta)).
                # Use the equivalent positive ratios to avoid cancellation for huge beta.
                def divided(A,B,beta):
                    return A/(A+beta)+(beta/(A+beta))*(B/(B+beta))
                slopes=(sn,sp)
                capacity=p[0]+sum(n*(s-coeff[2*k]*divided(p[15],p[15],coeff[2*k+1]))
                    for k,(n,s) in enumerate(zip(densities,slopes)))
                if capacity<=0:
                    raise ValueError('positive independent effective capacity required')
                for bound in p[14:16]:
                    gap=p[2]+p[3]+(bound-reference)*sum(s-coeff[2*k]*divided(bound,reference,coeff[2*k+1]) for k,s in enumerate(slopes))
                    if gap<=0:raise ValueError('positive independent band gap required')
                work=[V*n*(T-Decimal(before.lattice_temperature_K))*(s-coeff[2*k]*divided(T,
                    Decimal(before.lattice_temperature_K),coeff[2*k+1])) for k,(n,s) in enumerate(zip(densities,slopes))]
                if not config.varshni_bands:
                    work=[V*n*s*(T-Decimal(before.lattice_temperature_K)) for n,s in zip(densities,(sn,sp))]
                errors.extend(given_work[i][k]-work[k] for k in range(2))
            for k,field in enumerate(('electron_excess_energy_J_m3','hole_excess_energy_J_m3')):
                for state in (before,after):
                    edge=p[2+k]+min(Decimal.from_float(float(v.band_offset_owner_J)) for v in (config_cell.valleys_n,config_cell.valleys_p)[k])
                    if _eq(config_cell,state,k)+Decimal(getattr(state,field))<=Decimal(config_cell.initial_densities_m3[k])*edge:
                        raise ValueError('independent lattice excess carrier energy below band minimum')
                b=6+4*k
                logtau=p[4+k].ln()+p[b+2]*(T/p[b]).ln()+p[b+3]*(Decimal(config_cell.initial_densities_m3[k])/p[b+1]).ln()
                if not Decimal(-750)<logtau<Decimal(711):raise ValueError('independent lattice excess tau out of range')
                tau=logtau.exp()
                if not math.isfinite(float(tau)) or float(tau)<=0 or given_tau[i][k]<=0:raise ValueError('positive representable tau required')
                tau_errors.append(abs(given_tau[i][k]/tau-1))
                excess=Decimal(getattr(after,field));ex=h*V*excess/tau
                du=V*(_eq(config_cell,after,k)-_eq(config_cell,before,k)+excess-Decimal(getattr(before,field)))+work[k]
                exchanges.append(ex);increments.append(du);signs.append(ex*excess>=0)
                errors.extend((given_exchange[i][k]-ex,given_du[i][k]-du))
            dl=V*p[0]*(T-Decimal(before.lattice_temperature_K));errors.append(given_dl[i]-dl)
            row=[increments[k]+exchanges[k]-work[k]-source[i][k] for k in range(2)]
            row.append(dl-sum(exchanges)+sum(work)-source[i][2]+div[i]+boundary[i]);rows.append(row)
            endpoint+=sum(increments)+dl-sum(source[i])+boundary[i]
            errors.extend(a-b for a,b in zip(given_rows[i],row))
        all_residuals=[v for row in rows for v in row]+errors+[endpoint,sum(div)]
        valid=all(abs(v)<=gate for v in all_residuals) and all(signs) and all(v>=0 for v in face_entropy+bath_entropy) and max(tau_errors)<=Decimal('1e-12')
        result=dict(valid=valid,local_energy_residuals_J=[list(map(str,row)) for row in rows],
            whole_device_endpoint_energy_residual_J=str(endpoint),independent_face_energy_impulses_J=list(map(str,face_impulses)),
            net_internal_face_divergence_J=str(sum(div)),face_conduction_entropy_J_K=list(map(str,face_entropy)),
            maximum_report_error_J=str(max(map(abs,errors),default=Decimal(0))),
            maximum_relative_tau_error=str(max(tau_errors)),relaxation_exchange_sign_nonnegative=all(signs),
            native_operators_used=False,particle_residual=0,charge_residual_C=0,
            complete_device_energy=False,physical_validated=False)
        if config.baths:result.update(independent_boundary_energy_impulses_J=list(map(str,bath_impulses)),
            net_outward_boundary_energy_J=str(sum(bath_impulses)),boundary_conduction_entropy_J_K=list(map(str,bath_entropy)))
        return result
