"""Decimal-only verification of a coordinate change, without production physics."""
from decimal import Decimal,localcontext
import math


def audit_mb_reference_rebase(config,old,new,report,*,reference_temperature_K,energy_atol_J):
    if (isinstance(energy_atol_J,bool) or not math.isfinite(energy_atol_J) or energy_atol_J<=0
        or isinstance(reference_temperature_K,bool) or not math.isfinite(reference_temperature_K)):
        raise ValueError('finite independent reference command and positive energy budget required')
    metadata=dict(scope='equal_offset_MB_reference_rebase',configuration_sha256=config.sha256,execution_backend='native',
        precision_bits=113,physical_time_advanced=False,complete_device_energy=False,physical_validated=False,device_statistics_selected=False)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in metadata.items()):raise ValueError('MB rebase scope mismatch')
    a0=old.raw_state;b0=new.raw_state
    if (old.configuration_sha256!=config.sha256 or new.configuration_sha256!=config.sha256 or old.time_s!=new.time_s
        or len(a0)<6 or len(a0)>4092 or len(b0)!=len(a0)+4 or a0[:2]!=b0[:2] or a0[3:6]!=b0[3:6] or a0[6:]!=b0[6:-4]):
        raise ValueError('MB rebase changed density, tail, clock, configuration or prior history')
    if any(not isinstance(report.get(k),(list,tuple)) or len(report[k])!=3 for k in ('old_temperatures_K','temperatures_K')):
        raise ValueError('MB rebase view coverage mismatch')
    if report.get('reference_temperature_K')!=b0[2]:raise ValueError('MB rebase reported reference mismatch')
    with localcontext() as ctx:
        ctx.prec=800
        p=list(map(Decimal,config.parameters));a=list(map(Decimal,a0));b=list(map(Decimal,b0))
        views=[*map(Decimal,report['old_temperatures_K']),*map(Decimal,report['temperatures_K'])]
        if any(not x.is_finite() for x in (*p,*a,*b,*views)):raise ValueError('finite MB rebase values required')
        Cv,V=p[:2];eps=Decimal(2)**-112
        if Cv<Decimal('1e-1000') or Cv>Decimal('1e1000') or V<=0 or min(a[:2])<=0:raise ValueError('MB rebase positive normal scales required')
        for valley in (config.valleys_n,config.valleys_p):
            v=list(map(Decimal,valley))
            if not v or len(v)%4 or any(v[j]!=v[3] for j in range(3,len(v),4)):raise ValueError('MB rebase equal offsets required')
        num,den=reference_temperature_K.as_integer_ratio();requested=Decimal(num)/Decimal(den)
        if not 1<requested<100000 or abs(b[2]-requested)>16*eps*max(1,abs(requested)):
            raise ValueError('MB rebase reference differs from independent command')
        if not 1<a[2]<100000 or not 1<b[2]<100000 or not 1<p[12]<p[13]<100000:raise ValueError('MB reference domain mismatch')
        C=[Decimal('1.5')*Decimal('1.380649e-23')*a[k] for k in (0,1)]
        oldT=a[2]+(a[3]+sum(a[6:]))/Cv;newT=b[2]+(b[3]+sum(b[6:]))/Cv
        independent=[oldT,oldT+a[4]/C[0],oldT+a[5]/C[1],newT,newT+b[4]/C[0],newT+b[5]/C[1]]
        envelope=16*eps*max(1,*map(abs,independent),abs(p[12]),abs(p[13]))
        if any(t<p[12]-envelope or t>p[13]+envelope for t in independent):raise ValueError('MB rebase physical domain violation')
        coordinate_error=sum(b[-4:])+Cv*(b[2]-a[2])
        energy_errors=[V*c/Cv*coordinate_error for c in (*C,Cv)]
        # Input command and capacities set the bound; a forged cancelling
        # expansion must not enlarge its own acceptance budget.
        scale=V*max(*C,Cv)*abs(requested-a[2])
        rounding_budget=128*eps*scale
        budget=min(Decimal.from_float(float(energy_atol_J)),rounding_budget)
        temperature_errors=[abs(x-y) for x,y in zip(views,independent)]
        valid=all(abs(e)<=budget for e in energy_errors) and all(e<=Decimal('1e-25')*max(1,abs(t)) for e,t in zip(temperature_errors,independent))
        return dict(valid=valid,coordinate_error_J_m3=str(coordinate_error),energy_errors_J=list(map(str,energy_errors)),
            rounding_budget_J=str(rounding_budget),acceptance_budget_J=str(budget),temperature_errors_K=list(map(str,temperature_errors)),
            carrier_tails_and_prior_history_unchanged=True,native_operators_used=False,physical_time_advanced=False)
