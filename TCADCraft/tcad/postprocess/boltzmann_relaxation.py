"""Saved-state Decimal audit, no native calls or production law/energy helper."""
from decimal import Decimal,localcontext
import math


def audit_mb_relaxation_step(config,old,new,report,*,energy_atol_J,impulses_J=(0.,0.,0.)):
    if isinstance(energy_atol_J,bool) or not math.isfinite(energy_atol_J) or energy_atol_J<=0:
        raise ValueError('positive finite MB energy budget required')
    expected=dict(scope='closed_equal_offset_MB_energy_excess_BE',configuration_sha256=config.sha256,
        execution_backend='native',complete_device_energy=False,physical_validated=False,
        measured_ac_material_calibration=False,device_statistics_selected=False,carrier_temperature_exponent_supported=0)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in expected.items()):raise ValueError('MB report scope mismatch')
    if old.configuration_sha256!=config.sha256 or new.configuration_sha256!=config.sha256:
        raise ValueError('MB saved-state configuration mismatch')
    if (len(old.raw_state)<6 or len(new.raw_state)!=len(old.raw_state)+1 or old.raw_state[:4]!=new.raw_state[:4]
        or old.raw_state[6:]!=new.raw_state[6:-1]):
        raise ValueError('MB fixed densities/reference or lattice history changed')
    if type(report.get('dt_s')) is not float or not math.isfinite(report['dt_s']) or report['dt_s']<=0:
        raise ValueError('positive finite MB duration required')
    if new.time_s<=old.time_s or report.get('dt_s')!=new.time_s-old.time_s:
        # Float addition can round the difference; require the recorded dt to
        # reproduce the endpoint instead of changing its physical duration.
        if not isinstance(report.get('dt_s'),float) or report['dt_s']<=0 or old.time_s+report['dt_s']!=new.time_s:
            raise ValueError('MB clock mismatch')
    widths={'impulses_J':3,'temperatures_K':3,'exchange_J':2,'energy_increments_J':3,'residuals_J':4,'log_relaxation_times_s':2}
    if any(not isinstance(report.get(k),(list,tuple)) or len(report[k])!=n for k,n in widths.items()):raise ValueError('MB report coverage mismatch')
    if isinstance(report.get('residual_evaluations'),bool) or not isinstance(report.get('residual_evaluations'),int) or report['residual_evaluations']<1:
        raise ValueError('MB evaluation metadata mismatch')
    # High precision keeps the stiff tails separate from finite heat transfer.
    # Constitutive relative checks below do not use the absolute J budget.
    with localcontext() as ctx:
        ctx.prec=800
        p=list(map(Decimal,config.parameters));a=list(map(Decimal,old.raw_state));b=list(map(Decimal,new.raw_state))
        rows={k:list(map(Decimal,report[k])) for k in widths}
        if any(not x.is_finite() for x in (*p,*a,*b,*(v for r in rows.values() for v in r))):raise ValueError('finite MB values required')
        Cv,V=p[:2];capacity=[Decimal('1.5')*Decimal('1.380649e-23')*a[k] for k in (0,1)]
        if Cv<=0 or V<=0 or min(a[:2])<=0:raise ValueError('positive MB scales required')
        for vs in (config.valleys_n,config.valleys_p):
            v=list(map(Decimal,vs))
            if not v or len(v)%4 or any(v[j]!=v[3] for j in range(3,len(v),4)):raise ValueError('independent equal-offset scope failed')
        increment=b[-1];oldTl=a[2]+(a[3]+sum(a[6:]))/Cv;Tl=b[2]+(b[3]+sum(b[6:]))/Cv
        temperatures=[Tl,Tl+b[4]/capacity[0],Tl+b[5]/capacity[1]]
        # Saved native products/divisions round at 113 bits. Reconstructing a
        # boundary state with exact Decimal constants can lie a few ulps outside.
        # This envelope covers that reconstruction only; no energy/tail gate changes.
        domain_temperatures=(*temperatures,oldTl,oldTl+a[4]/capacity[0],oldTl+a[5]/capacity[1])
        domain_roundoff=Decimal(16)*Decimal(2)**-112*max(Decimal(1),*map(abs,domain_temperatures),abs(p[12]),abs(p[13]))
        if not all(p[12]-domain_roundoff<=t<=p[13]+domain_roundoff for t in domain_temperatures):
            raise ValueError('independent MB energy-domain violation')
        dt=Decimal.from_float(report['dt_s']);Q=rows['impulses_J'];budget=Decimal.from_float(float(energy_atol_J))
        if len(impulses_J)!=3 or any(isinstance(x,bool) or not math.isfinite(x) for x in impulses_J):raise ValueError('three finite independent MB impulses required')
        def exact_number(value):
            numerator,denominator=value.as_integer_ratio()
            return Decimal(numerator)/Decimal(denominator)
        expected_Q=list(map(exact_number,impulses_J))
        if any(abs(q-e)>Decimal('1e-32')*max(abs(q),abs(e)) for q,e in zip(Q,expected_Q)):
            raise ValueError('MB report impulse differs from independent command')
        du=[V*(capacity[k]/Cv*increment+b[4+k]-a[4+k]) for k in (0,1)]+[V*increment]
        errors=[];relative=[];log_errors=[]
        for k in (0,1):
            j=4+4*k;logtau=p[2+k].ln()+p[j+2]*(Tl/p[j]).ln()+p[j+3]*(a[k]/p[j+1]).ln()
            x=logtau-dt.ln()
            retained=(Decimal(1)/(1+(-x).exp())) if x>=0 else x.exp()/(1+x.exp())
            lost=(Decimal(1)/(1+x.exp())) if x<=0 else (-x).exp()/(1+(-x).exp())
            drive=a[4+k]+Q[k]/V-capacity[k]/Cv*increment
            for actual,wanted in ((b[4+k],retained*drive),(rows['exchange_J'][k],V*lost*drive)):
                relative.append(abs(actual-wanted)/abs(wanted) if wanted else Decimal(0 if actual==0 else 1))
            log_errors.append(abs(rows['log_relaxation_times_s'][k]-logtau))
        errors.extend(du[k]-rows['energy_increments_J'][k] for k in range(3))
        physical=[du[0]+rows['exchange_J'][0]-Q[0],du[1]+rows['exchange_J'][1]-Q[1],
            du[2]-sum(rows['exchange_J'])-Q[2],sum(du)-sum(Q)]
        errors.extend(physical);errors.extend(physical[k]-rows['residuals_J'][k] for k in range(4))
        # A coherent forged collision can satisfy both constitutive equations
        # yet omit an entire lattice signal smaller than the absolute J gate.
        # Reconstruct a second budget from independently saved input energy,
        # never from the submitted residual or a cached acceptance flag.
        signal_scale=max(abs(V*a[4]),abs(V*a[5]),*map(abs,expected_Q))
        signal_budget=min(budget,Decimal(1024)*Decimal(2)**-112*signal_scale)
        signal_valid=all(abs(e)<=signal_budget for e in errors)
        # Temperatures are views; audit both their native rounding and state.
        temperature_errors=[abs(x-y) for x,y in zip(rows['temperatures_K'],temperatures)]
        valid=(signal_valid and all(abs(e)<=budget for e in errors) and all(e<=Decimal('1e-25') for e in relative)
            and all(e<=Decimal('1e-24') for e in log_errors)
            and all(e<=Decimal('1e-25')*max(abs(t),Decimal(1)) for e,t in zip(temperature_errors,temperatures)))
        return dict(valid=valid,energy_errors_J=list(map(str,errors)),constitutive_relative_errors=list(map(str,relative)),
            log_tau_errors=list(map(str,log_errors)),temperature_errors_K=list(map(str,temperature_errors)),native_operators_used=False,
            production_law_used=False,strict_relative_tail_check=True,domain_roundoff_K=str(domain_roundoff),
            signal_energy_valid=signal_valid,signal_scale_J=str(signal_scale),signal_energy_budget_J=str(signal_budget),
            strict_signal_balance_check=True)
