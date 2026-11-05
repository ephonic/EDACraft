"""Independent saved-state audit with per-lineage, signal-scaled budgets."""
from decimal import Decimal,localcontext
import math


def audit_mb_expanded_collision(config,old,new,report,*,dt_s,impulses_J,energy_atol_J):
    def number(x):
        if isinstance(x,bool) or not hasattr(x,'as_integer_ratio') or not math.isfinite(x):
            raise ValueError('finite independent numeric commands required')
        n,d=x.as_integer_ratio();return Decimal(n)/Decimal(d)
    metadata=dict(scope='closed_equal_offset_MB_expanded_BE',execution_backend='native',precision_bits=113,
        configuration_sha256=config.sha256,origin_configuration_sha256=old.origin_configuration_sha256,
        complete_device_energy=False,physical_validated=False,device_statistics_selected=False,
        measured_ac_material_calibration=False,carrier_temperature_exponent_supported=0)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in metadata.items()):
        raise ValueError('expanded MB collision scope/configuration mismatch')
    if (new.origin_configuration_sha256!=old.origin_configuration_sha256 or new.frame[:len(old.frame)]!=old.frame
        or new.time_s!=old.time_s+float(dt_s) or not new.time_s>old.time_s or report.get('dt_s')!=float(dt_s)):
        raise ValueError('expanded MB collision changed fixed frame, provenance or clock')
    for key,width in (('old_temperatures_K',3),('temperatures_K',3),('log_relaxation_times_s',2),('impulses_J',3)):
        if not isinstance(report.get(key),(tuple,list)) or len(report[key])!=width:raise ValueError('expanded MB report coverage mismatch')
    rows=report.get('lineage_groups');count=len(old.electron_excess)+len(old.hole_excess)+3
    if not isinstance(rows,(list,tuple)) or len(rows)!=count:raise ValueError('expanded MB lineage coverage mismatch')
    packed=report.get('lattice_increment_expansion')
    if not isinstance(packed,(list,tuple)) or len(packed)>246:raise ValueError('expanded MB lattice packing coverage mismatch')
    if type(report.get('residual_evaluations')) is not int or not 1<=report['residual_evaluations']<=4096:
        raise ValueError('expanded MB evaluation coverage mismatch')
    with localcontext() as ctx:
        ctx.prec=10000
        dt=number(dt_s);atol=number(energy_atol_J)
        if dt<=0 or atol<=0 or len(impulses_J)!=3:raise ValueError('positive independent clock/budget and three sources required')
        q=list(map(number,impulses_J));qr=list(map(Decimal,report['impulses_J']))
        f=list(map(Decimal,old.frame));g=list(map(Decimal,new.frame));p=list(map(Decimal,config.parameters))
        if any(not x.is_finite() for x in (*f,*g,*p,*qr)):raise ValueError('finite MB frame/configuration required')
        if any(f[j]!=p[k] for j,k in ((3,0),(4,1),(7,12),(8,13))):raise ValueError('MB collision capacity/volume/bounds mismatch')
        if min(f[0],f[1],f[3],f[4],*p[2:6],p[8],p[9])<=0 or not 1<f[7]<f[8]<100000:
            raise ValueError('positive MB scales and temperature domain required')
        for valley in (config.valleys_n,config.valleys_p):
            if not valley or len(valley)%4 or any(Decimal(valley[j])!=Decimal(valley[3]) for j in range(3,len(valley),4)):
                raise ValueError('equal-offset MB configuration required')
        eps=Decimal(2)**-112;alpha=Decimal('1.5')*Decimal('1.380649e-23');Cv,V=f[3:5]
        for a,b in zip(qr,q):
            if not a.is_finite() or abs(a-b)>16*eps*abs(b):raise ValueError('MB source differs from independent command')
        old_d=[list(map(Decimal,getattr(old,k))) for k in ('electron_excess','hole_excess')]
        new_d=[list(map(Decimal,getattr(new,k))) for k in ('electron_excess','hole_excess')]
        if any(not x.is_finite() for pair in (*old_d,*new_d) for x in pair):raise ValueError('finite MB carrier components required')
        def bounded(x):return x==0 or Decimal('1e-4000')<=abs(x)<=Decimal('1e4000')
        if any(not bounded(x) for x in (*f,*g,*(x for a in (*old_d,*new_d) for x in a))):raise ValueError('MB expansion range exceeded')
        if any(not Decimal('1e-1000')<=f[j]<=Decimal('1e1000') for j in (0,1,3,4)) or not 1<f[2]<100000:
            raise ValueError('MB positive frame scales outside supported range')
        if any(abs(f[j])>Decimal('1e1000') for j in (5,6)):raise ValueError('MB band energy range exceeded')
        C=[alpha*f[0],alpha*f[1]];ratioC=[x/Cv for x in C]
        oldTl=f[2]+sum(f[9:])/Cv;Tl=g[2]+sum(g[9:])/Cv
        physical=[oldTl,*(oldTl+sum(d)/c for d,c in zip(old_d,C)),Tl,*(Tl+sum(d)/c for d,c in zip(new_d,C))]
        views=list(map(Decimal,(*report['old_temperatures_K'],*report['temperatures_K'])))
        if any(not x.is_finite() for x in views):raise ValueError('finite MB temperature views required')
        envelope=16*eps*max(1,*map(abs,physical),abs(f[7]),abs(f[8]))
        if any(t<f[7]-envelope or t>f[8]+envelope for t in physical):raise ValueError('MB collision physical temperature domain violation')
        view_ok=all(abs(a-b)<=Decimal('1e-25')*max(1,abs(b)) for a,b in zip(views,physical))
        # Transcendental coefficients use 200 independent decimal digits.
        # Wide exact sums below retain the full native expansion range.
        with localcontext() as coefficients:
            coefficients.prec=200
            logtau=[];retained=[];lost=[];logdt=dt.ln()
            for k in range(2):
                b=4+4*k
                logtau.append(p[2+k].ln()+p[b+2]*(Tl/p[b]).ln()+p[b+3]*(f[k]/p[b+1]).ln())
                z=logtau[-1]-logdt;u=(-abs(z)).exp()
                retained.append(1/(1+u) if z>=0 else u/(1+u))
                lost.append(u/(1+u) if z>=0 else 1/(1+u))
            denominator=1+lost[0]*ratioC[0]+lost[1]*ratioC[1]
            threshold=Decimal(-1).exp()
            coeff=[]
            for kind in range(3):
                L=(lost[kind] if kind<2 else Decimal(1))/denominator
                drive=[(Decimal(1) if kind==k else Decimal(0))-ratioC[k]*L for k in range(2)]
                # Own response avoids cancellation when the capacity dominates.
                if kind<2:drive[kind]=(1+lost[1-kind]*ratioC[1-kind])/denominator
                coeff.append((L,*(retained[k]*drive[k] for k in range(2)),*(lost[k]*drive[k] for k in range(2))))
        lr=list(map(Decimal,report['log_relaxation_times_s']))
        log_ok=all(x.is_finite() and abs(x-y)<=Decimal('1e-24') for x,y in zip(lr,logtau))
        inputs=[(x,0,False,raw) for x,raw in zip(old_d[0],old.electron_excess)]
        inputs += [(x,1,False,raw) for x,raw in zip(old_d[1],old.hole_excess)]
        inputs += [(q[k]/V,k,True,None) for k in range(3)]
        flat=[[],[]];lattice=[];checks=[];all_ok=view_ok and log_ok
        totals=[Decimal(0)]*4;budgets=[];exchanges=[Decimal(0),Decimal(0)]
        factor=Decimal(8192)*eps*max(1,*map(abs,logtau),abs(logdt))
        for row,(value,kind,source,original) in zip(rows,inputs):
            if not isinstance(row,dict) or set(row)!={'lattice_increment_density','exchange_densities','electron_excess','hole_excess'}:
                raise ValueError('MB lineage fields mismatch')
            if len(row['exchange_densities'])!=2:raise ValueError('MB exchange coverage mismatch')
            L=Decimal(row['lattice_increment_density']);X=list(map(Decimal,row['exchange_densities']))
            rawparts=[row[k] for k in ('electron_excess','hole_excess')]
            if any(not isinstance(a,(list,tuple)) or len(a) not in (1,4) for a in rawparts):raise ValueError('MB carrier response coverage mismatch')
            parts=[list(map(Decimal,a)) for a in rawparts]
            if any(not x.is_finite() for x in (L,*X,*(x for a in parts for x in a))):raise ValueError('finite MB lineage evidence required')
            if any(not bounded(x) for x in (L,*X,*(x for a in parts for x in a))):raise ValueError('MB lineage range exceeded')
            if L!=0:lattice.append(row['lattice_increment_density'])
            expected=[value*x for x in coeff[kind]];actual=[L,*map(sum,parts),*X]
            response_ok=all(abs(a-b)<=Decimal('1e-25')*abs(b) for a,b in zip(actual,expected))
            representation_ok=True
            for k in range(2):
                flat[k].extend(raw for raw,x in zip(rawparts[k],parts[k]) if x!=0)
                if len(parts[k])==4:
                    prefix=value if kind==k else Decimal(0)
                    if original is not None and kind==k:representation_ok &= rawparts[k][0]==original
                    else:representation_ok &= abs(parts[k][0]-prefix)<=16*eps*abs(prefix)
                    baseline=-ratioC[k]*L
                    representation_ok &= abs(sum(parts[k][1:3])-baseline)<=256*eps*abs(baseline)
                    representation_ok &= abs(parts[k][2])<=eps*abs(parts[k][1])
                    representation_ok &= parts[k][3]==-X[k]
                    representation_ok &= retained[k]>=threshold*(1-Decimal('1e-25'))
                else:representation_ok &= retained[k]<=threshold*(1+Decimal('1e-25'))
            target=[q[k] if source and kind==k else Decimal(0) for k in range(3)]
            previous_carrier=[value if not source and kind==k else Decimal(0) for k in range(2)]
            dU=[V*(ratioC[k]*L+sum(parts[k])-previous_carrier[k]) for k in range(2)]+[V*L]
            residual=[dU[0]+V*X[0]-target[0],dU[1]+V*X[1]-target[1],dU[2]-V*sum(X)-target[2],sum(dU)-sum(target)]
            # Scale only physical changes and independently predicted exchanges,
            # not an unchanged finite input. This resolves near-unity micro-loss.
            scale=V*(abs(expected[0])*(1+sum(map(abs,ratioC)))+abs(expected[3])+abs(expected[4]))+sum(map(abs,target))
            budget=min(atol/count,factor*scale);budgets.append(budget)
            valid=response_ok and representation_ok and all(abs(x)<=budget for x in residual)
            all_ok &= valid
            totals=[a+b for a,b in zip(totals,residual)]
            exchanges=[a+b for a,b in zip(exchanges,X)]
            checks.append(dict(valid=bool(valid),response_valid=bool(response_ok),representation_valid=bool(representation_ok),
                max_energy_residual_J=format(max(map(abs,residual)),'.12E'),energy_budget_J=format(budget,'.12E')))
        if tuple((*old.frame,*packed))!=new.frame:raise ValueError('MB submitted lattice differs from packed expansion')
        # Independently round each decimal to nearest-even 113-bit binary.
        # Exact sums of these values prove packing did not discard tiny native
        # increments; physical Decimal energy is also checked separately below.
        def binary113(raw):
            value=Decimal(raw)
            if not value.is_finite() or not bounded(value):raise ValueError('finite bounded packed component required')
            if value==0:return Decimal(0)
            numerator,denominator=abs(value).as_integer_ratio()
            exponent=numerator.bit_length()-denominator.bit_length()
            below=(numerator < denominator<<exponent) if exponent>=0 else (numerator<<(-exponent) < denominator)
            if below:exponent-=1
            shift=112-exponent
            n,d=(numerator<<shift,denominator) if shift>=0 else (numerator,denominator<<(-shift))
            integer,remainder=divmod(n,d)
            if 2*remainder>d or (2*remainder==d and integer%2):integer+=1
            result=Decimal(integer)*Decimal(2)**(exponent-112)
            return result if value>0 else -result
        packing_ok=sum(map(binary113,lattice))==sum(map(binary113,packed))
        for k,field in enumerate(('electron_excess','hole_excess')):
            if tuple(flat[k] or ['0'])!=getattr(new,field):raise ValueError('MB submitted carrier components differ from lineage responses')
        global_budget=min(atol,sum(budgets))
        storedL=sum(g[len(f):]);actualU=[V*(ratioC[k]*storedL+sum(new_d[k])-sum(old_d[k])) for k in range(2)]+[V*storedL]
        stored_residuals=[actualU[0]+V*exchanges[0]-q[0],actualU[1]+V*exchanges[1]-q[1],
                          actualU[2]-V*sum(exchanges)-q[2],sum(actualU)-sum(q)]
        all_ok &= packing_ok and all(abs(x)<=global_budget for x in (*totals,*stored_residuals))
        return dict(valid=bool(all_ok),lineage_checks=checks,temperature_views_valid=view_ok,log_relaxation_times_valid=log_ok,
            global_residuals_J=[format(x,'.12E') for x in totals],global_budget_J=format(global_budget,'.12E'),
            stored_physical_residuals_J=[format(x,'.12E') for x in stored_residuals],lattice_packing_binary_exact=packing_ok,
            native_operators_used=False,physical_time_advanced=True,per_input_response_checked=True)
