"""Independent binary-product and Decimal-physics audit of saved flat MB faces."""
from dataclasses import asdict
from decimal import Decimal,localcontext
import hashlib,json,math


def audit_expanded_mb_flat_face(owner,neighbor,report,*,geometry,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    metadata=dict(scope='uniform_DOS_flat_band_common_lattice_MB_expanded_face',face_kind=face_kind,
        execution_backend='native',precision_bits=113,time_s=owner.time_s,physical_time_advanced=False,
        device_statistics_selected=False,field_work_inferred=False,complete_device_energy=False,physical_validated=False)
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in metadata.items()):
        raise ValueError('MB flat face metadata mismatch')
    fingerprint=lambda state:hashlib.sha256(json.dumps(asdict(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if report.get('owner_sha256')!=fingerprint(owner) or report.get('neighbor_sha256')!=fingerprint(neighbor):
        raise ValueError('MB flat face endpoint provenance mismatch')
    if owner.time_s!=neighbor.time_s:raise ValueError('simultaneous endpoints required')
    if (owner.frame[2],owner.frame[3],owner.frame[9:])!=(neighbor.frame[2],neighbor.frame[3],neighbor.frame[9:]):
        raise ValueError('common lattice coordinates required')
    def number(x):
        if isinstance(x,bool) or not hasattr(x,'as_integer_ratio') or not math.isfinite(x):raise ValueError('finite independent face commands required')
        n,d=x.as_integer_ratio();return Decimal(n)/Decimal(d)
    with localcontext() as ctx:
        ctx.prec=10000;eps=Decimal(2)**-112;KB=Decimal('1.380649e-23');QE=Decimal('1.602176634e-19')
        def bounded(x):return x.is_finite() and (x==0 or Decimal('1e-4000')<=abs(x)<=Decimal('1e4000'))
        def vector(raw):
            if not isinstance(raw,(list,tuple)) or len(raw)>4096:raise ValueError('bounded face expansion required')
            v=list(map(Decimal,raw))
            if any(not bounded(x) for x in v):raise ValueError('finite bounded face component required')
            return v
        def binary(raw):
            x=Decimal(raw)
            if not bounded(x):raise ValueError('bounded native binary component required')
            if x==0:return Decimal(0)
            n,d=abs(x).as_integer_ratio();e=n.bit_length()-d.bit_length()
            below=(n < d<<e) if e>=0 else (n<<(-e)<d)
            if below:e-=1
            shift=112-e;n,d=(n<<shift,d) if shift>=0 else (n,d<<(-shift))
            h,r=divmod(n,d)
            if 2*r>d or (2*r==d and h%2):h+=1
            value=Decimal(h)*Decimal(2)**(e-112)
            return value if x>0 else -value
        def bsum(raw):return sum(map(binary,raw),Decimal(0))
        def canonical(raw):
            v=list(map(binary,raw))
            return all(v) and all(abs(a)<=eps*abs(b) for a,b in zip(v,v[1:])) if v else True
        g=list(map(number,geometry));limits=list(map(number,(number_atol_s,energy_atol_W)))
        if len(g)!=5 or min(limits)<=0 or not(g[0]>0 and g[1]>0 and g[2]>=0 and min(g[3:])>0):
            raise ValueError('positive geometry and external flux budgets required')
        if face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):raise ValueError('bulk/contact geometry mismatch')
        rg=vector(report.get('geometry'))
        if len(rg)!=5 or any(abs(x-y)>16*eps*abs(y) for x,y in zip(rg,g)):raise ValueError('face geometry differs from independent command')
        f=vector(owner.frame);h=vector(neighbor.frame)
        if any(f[j]!=h[j] for j in (5,6)):raise ValueError('flat material band required')
        fields=('electron_excess','hole_excess');tails=[]
        for state,frame in ((owner,f),(neighbor,h)):
            if not 10<=len(frame)<=256 or any(not Decimal('1e-1000')<=frame[j]<=Decimal('1e1000') for j in (0,1,3,4)):
                raise ValueError('MB face frame scales invalid')
            if not 1<frame[2]<100000 or not 1<frame[7]<frame[8]<100000 or max(abs(frame[5]),abs(frame[6]))>Decimal('1e1000'):
                raise ValueError('MB face frame domain invalid')
            values=[vector(getattr(state,key)) for key in fields]
            if not all(values):raise ValueError('nonempty carrier state required')
            Tl=frame[2]+sum(frame[9:])/frame[3]
            ts=[Tl,*(Tl+sum(v)/(Decimal('1.5')*KB*frame[k]) for k,v in enumerate(values))]
            envelope=16*eps*max(1,*map(abs,ts),abs(frame[7]),abs(frame[8]))
            if any(t<frame[7]-envelope or t>frame[8]+envelope for t in ts):raise ValueError('MB endpoint temperature outside bounds')
            tails.append(values)
        inverse=Decimal(report['inverse_Cv']);thermal_raw=report['thermal_expansion'];thermal=vector(thermal_raw)
        if not bounded(inverse) or not inverse>0:raise ValueError('positive bounded inverse capacity required')
        Tl=f[2]+sum(f[9:])/f[3]
        valid=abs(inverse-1/f[3])<=128*eps/f[3]
        valid &= bsum(thermal_raw)==binary(owner.frame[2])+binary(inverse)*bsum(owner.frame[9:])
        valid &= canonical(thermal_raw) and abs(sum(thermal)-Tl)<=Decimal('1e-25')*max(1,abs(Tl))
        carriers=report.get('carriers')
        if not isinstance(carriers,list) or len(carriers)!=2:raise ValueError('two carrier face moments required')
        G=g[0]/(g[1]/g[3]+g[2]/g[4])/QE;checks=[];total_terms=total_parts=0
        for k,row in enumerate(carriers):
            coefficients=vector(row['coefficients']);norm=row['normalization']
            if len(coefficients)!=7 or not isinstance(norm,list) or len(norm)!=4:raise ValueError('face coefficient/normalization coverage mismatch')
            for raw in norm:vector(raw)
            expected_norm=[binary(owner.frame[k])-binary(neighbor.frame[k]),
                bsum(getattr(owner,fields[k]))-bsum(getattr(neighbor,fields[k])),
                bsum(getattr(owner,fields[k]))+bsum(getattr(neighbor,fields[k])),bsum(getattr(neighbor,fields[k]))]
            normalized=all(bsum(raw)==target and canonical(raw) for raw,target in zip(norm,expected_norm))
            expected_coef=[G*KB,G*2/3,f[5+k],G*Decimal('2.5')*KB*KB,G*10/3*KB,G*10/9/f[k],-G*10/9/f[k]/h[k]]
            coefficient_ok=all(abs(x-y)<=256*eps*abs(y) for x,y in zip(coefficients,expected_coef))
            rows=row.get('terms')
            if not isinstance(rows,list):raise ValueError('face monomial records required')
            total_terms+=len(rows)
            if total_terms>4096:raise ValueError('face term budget exceeded')
            number_flat=[x for r in rows if r['kind']<2 for x in r['value']]
            energy_flat=[x for r in rows if r['kind']>=2 for x in r['value']]
            if row['number_expansion']!=number_flat or row['energy_expansion']!=energy_flat:
                raise ValueError('submitted face moments differ from monomials')
            vector(number_flat);vector(energy_flat)
            def factors():
                D,d,s,nh=norm
                for x in D:
                    for t in thermal_raw:yield 0,[x,t]
                for x in d:yield 1,[x]
                for x in number_flat:yield 2,[x]
                for x in D:
                    for t in thermal_raw:
                        for u in thermal_raw:yield 3,[x,t,u]
                for x in d:
                    for t in thermal_raw:yield 4,[x,t]
                for x in d:
                    for y in s:yield 5,[x,y]
                for x in nh:
                    for y in nh:
                        for z in D:yield 6,[x,y,z]
            it=iter(factors());product_ok=True
            for r in rows:
                expected=next(it,None)
                if expected is None or type(r['kind']) is not int or (r['kind'],r['factors'])!=expected:
                    raise ValueError('MB monomial coverage/order mismatch')
                parts=vector(r['value']);total_parts+=len(parts)
                if total_parts>4096:raise ValueError('MB face component budget exceeded')
                target=binary(row['coefficients'][r['kind']])
                for x in r['factors']:target*=binary(x)
                product_ok &= canonical(r['value']) and bsum(r['value'])==target
            if next(it,None) is not None:raise ValueError('MB face monomial missing')
            dn=f[k]-h[k];dd=sum(tails[0][k])-sum(tails[1][k]);ss=sum(tails[0][k])+sum(tails[1][k]);nh=sum(tails[1][k])
            N=[G*KB*Tl*dn,G*2/3*dd]
            E=[*(f[5+k]*x for x in N),G*Decimal('2.5')*KB*KB*Tl*Tl*dn,G*10/3*KB*Tl*dd,
                G*10/9/f[k]*dd*ss,-G*10/9/f[k]/h[k]*nh*nh*dn]
            residual=[sum(map(Decimal,number_flat))-sum(N),sum(map(Decimal,energy_flat))-sum(E)]
            budgets=[min(limit,Decimal(32768)*eps*sum(map(abs,terms))) for limit,terms in zip(limits,(N,E))]
            physical_ok=all(abs(x)<=budget for x,budget in zip(residual,budgets))
            passed=normalized and coefficient_ok and product_ok and physical_ok;valid &= passed
            checks.append(dict(valid=bool(passed),normalization_binary_exact=bool(normalized),coefficients_valid=bool(coefficient_ok),
                monomials_binary_exact=bool(product_ok),physical_flux_valid=bool(physical_ok),
                residuals=[format(x,'.12E') for x in residual],budgets=[format(x,'.12E') for x in budgets]))
        return dict(valid=bool(valid),carriers=checks,native_physics_used=False,physical_time_advanced=False,
            complete_device_energy=False,term_count=total_terms,component_count=total_parts)
