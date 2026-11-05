"""Independent Decimal audit; no native operators or production constitutive laws."""
from decimal import Decimal,localcontext
import math


def audit_mb_particle_energy(old,new,report,*,densities,bands_J,energy_impulses_J,energy_atol_J):
    def independent(values,width):
        if len(values)!=width:raise ValueError('independent MB command coverage mismatch')
        result=[]
        for v in values:
            if isinstance(v,bool) or not math.isfinite(v):raise ValueError('finite numeric independent MB commands required')
            num,den=v.as_integer_ratio();result.append(Decimal(num)/Decimal(den))
        return result
    metadata=dict(scope='equal_offset_MB_particle_band_energy_transaction',execution_backend='native',precision_bits=113,
                  origin_configuration_sha256=old.origin_configuration_sha256,physical_time_advanced=False,
                  band_work_inferred=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in metadata.items()):raise ValueError('MB particle energy scope mismatch')
    if (old.time_s!=new.time_s or old.origin_configuration_sha256!=new.origin_configuration_sha256
        or len(old.frame)!=len(new.frame) or old.frame[2:5]!=new.frame[2:5] or old.frame[7:]!=new.frame[7:]):
        raise ValueError('MB particle transaction changed frame, lattice history or clock')
    for a,b in ((old.electron_excess,new.electron_excess),(old.hole_excess,new.hole_excess)):
        if b[:len(a)]!=a:raise ValueError('MB particle transaction changed authoritative old carrier components')
    for key,width in (('old_temperatures_K',3),('temperatures_K',3),('energy_impulses_J',2)):
        if not isinstance(report.get(key),(list,tuple)) or len(report[key])!=width:raise ValueError('MB report coverage mismatch')
    if isinstance(energy_atol_J,bool) or not math.isfinite(energy_atol_J) or energy_atol_J<=0:raise ValueError('positive finite independent budget required')
    with localcontext() as ctx:
        # The native range is [1e-4000,1e4000]; 10000 digits also recover a
        # microscopic component after cancellation of the largest allowed terms.
        ctx.prec=10000
        f=list(map(Decimal,old.frame));g=list(map(Decimal,new.frame))
        ds=[[list(map(Decimal,getattr(s,k))) for k in ('electron_excess','hole_excess')] for s in (old,new)]
        views=list(map(Decimal,(*report['old_temperatures_K'],*report['temperatures_K'])))
        qr=list(map(Decimal,report['energy_impulses_J']))
        n=independent(densities,2);e=independent(bands_J,2);q=independent(energy_impulses_J,2)
        if any(not x.is_finite() for x in (*f,*g,*views,*qr,*(x for pair in ds for a in pair for x in a))):raise ValueError('finite MB evidence required')
        eps=Decimal(2)**-112;alpha=Decimal('1.5')*Decimal('1.380649e-23');Cv,V=f[3:5]
        if min(*f[:2],*g[:2],Cv,V)<=0 or not 1<f[2]<100000 or not 1<f[7]<f[8]<100000:raise ValueError('MB frame domain invalid')
        for got,want in zip((*g[:2],*g[5:7],*qr),(*n,*e,*q)):
            if (want==0 and got!=0) or abs(got-want)>16*eps*abs(want):raise ValueError('MB result differs from independent command')
        Tl=f[2]+sum(f[9:])/Cv
        physical=[Tl,Tl+sum(ds[0][0])/(alpha*f[0]),Tl+sum(ds[0][1])/(alpha*f[1]),
                  Tl,Tl+sum(ds[1][0])/(alpha*g[0]),Tl+sum(ds[1][1])/(alpha*g[1])]
        envelope=16*eps*max(1,*map(abs,physical),abs(f[7]),abs(f[8]))
        if any(t<f[7]-envelope or t>f[8]+envelope for t in physical):raise ValueError('MB physical temperature domain violation')
        errors=[];budgets=[];scales=[]
        atol=Decimal.from_float(float(energy_atol_J))
        for k in range(2):
            added=sum(ds[1][k][len(ds[0][k]):])
            # Use changes, rather than subtracting rounded total stored energies.
            # Reconstruct the physical energy of the SUBMITTED frame. The
            # independent commands determine its budget, not its energy.
            baseline=(g[k]-f[k])*(f[5+k]+alpha*Tl)+g[k]*(g[5+k]-f[5+k])
            errors.append(V*(added+baseline)-q[k])
            scale=abs(q[k])+V*(abs(n[k]-f[k])*(abs(f[5+k])+alpha*(abs(f[2])+sum(map(abs,f[9:]))/Cv))+abs(n[k]*(e[k]-f[5+k])))
            scales.append(scale);budgets.append(min(atol,512*eps*scale))
        total_error=sum(errors);total_budget=min(atol,512*eps*sum(scales))
        view_ok=all(abs(a-b)<=Decimal('1e-25')*max(1,abs(b)) for a,b in zip(views,physical))
        valid=view_ok and all(abs(x)<=b for x,b in zip(errors,budgets)) and abs(total_error)<=total_budget
        return dict(valid=valid,carrier_energy_residuals_J=list(map(str,errors)),carrier_energy_budgets_J=list(map(str,budgets)),
                    total_energy_residual_J=str(total_error),total_energy_budget_J=str(total_budget),temperature_views_valid=view_ok,
                    old_components_preserved=True,native_operators_used=False,physical_time_advanced=False)
