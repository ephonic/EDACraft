"""Independent saved affine collision audit, stdlib only, no constitutive calls."""
from decimal import Decimal,localcontext
from dataclasses import asdict
from tcad.postprocess.boltzmann_affine_transport import _Arithmetic,_point,_metadata,_fingerprint,KB,ZERO,FIELDS

OP_NAMES=('numerator','leading_quotient','division_residual','correction_quotient','trial_lattice','trial_dTl',
    'electron_capacity_product','hole_capacity_product','electron_pre_exchange','hole_pre_exchange',
    'electron_exchange','hole_exchange','lattice_change','committed_dTl','electron_rebase','hole_rebase',
    'electron_physical_change','hole_physical_change','electron_stored_change','hole_stored_change')


def audit_mb_affine_collision(config,old,new,report,*,dt_s,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();dt=m.command(dt_s);atol=m.command(energy_atol_J);q=list(map(m.command,impulses_J))
        if min(dt,atol)<=0 or len(q)!=3:raise ValueError('positive independent collision commands required')
        a=_point(old,m);b=_point(new,m);f=a['frame'];af=a['anchor'].frame;p=list(map(Decimal,config.parameters));V=f[4]
        if any(p[j]!=0 for j in (6,7,10,11)) or min(p[2:4])<=0:raise ValueError('constant tau affine collision required')
        if any(f[j]!=p[k] for j,k in ((3,0),(4,1),(7,12),(8,13))):raise ValueError('independent collision configuration mismatch')
        for valley in (config.valleys_n,config.valleys_p):
            if not valley or len(valley)%4 or any(Decimal(valley[j])!=Decimal(valley[3]) for j in range(3,len(valley),4)):raise ValueError('equal-offset MB valleys required')
        _metadata(report,dict(scope='constant_tau_affine_MB_collision_BE',execution_backend='native',precision_bits=113,
            configuration_sha256=config.sha256,old_sha256=_fingerprint(old),new_sha256=_fingerprint(new),
            quotient_model='one_residual_correction',response_groups='exact_linear_input_expansions',physical_time_advanced=True,expanded_density_collision_supported=True,
            dynamic_lattice_supported=True,constant_tau_only=True,device_statistics_selected=False,complete_device_energy=False,physical_validated=False))
        if new.time_s!=old.time_s+float(dt_s) or not new.time_s>old.time_s or abs(Decimal(report['dt_s'])-dt)>16*m.eps*dt:
            raise ValueError('affine collision clock mismatch')
        L=report['lattice_increment_expansion'];increments=report['carrier_stored_increments'];alpha=m.binary(report['alpha'])
        if len(increments)!=2:raise ValueError('collision carrier coverage required')
        if new.anchor.frame!=(*af,*L) or any(getattr(new.anchor,k)!=getattr(a['anchor'],k) for k in ('electron_excess','hole_excess','time_s','origin_configuration_sha256')):
            raise ValueError('collision anchor rebase/provenance mismatch')
        if any(b['raw'][k]!=a['raw'][k] for k in (0,1)) or any(tuple(b['raw'][k+2])!=(*a['raw'][k+2],*increments[k]) for k in (0,1)):
            raise ValueError('collision particle or stored energy prefix altered')
        names=('exchange_fractions','lattice_quotients','thermal_expansion','densities','kinetic','capacities','excess','capacity_ratios','denominator','source_densities')
        R=report[names[0]];quot=report[names[1]];thermal=report[names[2]];n,K,C,delta,cap=(report[k] for k in names[3:8]);D=report[names[8]];src=report[names[9]]
        if len(R)!=2 or any(len(x)!=2 for x in (n,K,C,delta,cap)) or len(src)!=3:raise ValueError('collision normalization coverage')
        payload=0
        def check(raw,target,canonical=True):
            nonlocal payload
            payload+=len(m.vector(raw));return (not canonical or m.canonical(raw)) and m.bsum(raw)==target
        valid=abs(alpha-Decimal('1.5')*KB)<=128*m.eps*KB
        rb=m.bvector(R);payload+=len(m.vector(R))
        valid &= all(0<r<=1 and abs(r-dt/(dt+tau))<=128*m.eps*dt/(dt+tau) for r,tau in zip(rb,p[2:4]))
        payload+=len(m.vector(quot));valid &= m.bvector(quot)==m.quotients(af[9:],m.binary(af[3]))
        valid &= check(thermal,m.binary(af[2])+m.bsum(quot));tb=m.bsum(thermal)
        for k in range(2):
            nb=m.binary(af[k])+m.bsum(a['raw'][k]);kb=alpha*tb*m.binary(af[k])+m.bsum((a['anchor'].electron_excess,a['anchor'].hole_excess)[k])+m.bsum(a['raw'][k+2])-m.binary(af[k+5])*m.bsum(a['raw'][k])
            valid &= check(n[k],nb) and check(K[k],kb) and check(C[k],alpha*nb) and check(delta[k],kb-alpha*nb*tb)
            valid &= check(cap[k],sum(m.quotients(C[k],m.binary(af[3])),ZERO))
            physical_delta=a['K'][k]-Decimal('1.5')*KB*a['n'][k]*a['Tl']
            dscale=sum(map(abs,(*a['excess'][k],*a['change'][k+2])),ZERO)+abs(f[k+5]*sum(a['change'][k],ZERO))+abs(Decimal('1.5')*KB*a['Tl']*sum(a['change'][k],ZERO))
            valid &= abs(sum(m.vector(delta[k]),ZERO)-physical_delta)<=4096*m.eps*dscale
        valid &= check(D,1+rb[0]*m.bsum(cap[0])+rb[1]*m.bsum(cap[1]))
        if not D or m.binary(D[-1])<=0:raise ValueError('positive normalized collision denominator required')
        for k in range(3):
            payload+=len(m.vector(src[k]));valid &= m.bvector(src[k])==m.quotients([report['impulses_J'][k]],m.binary(af[4]))
            valid &= abs(Decimal(report['impulses_J'][k])-q[k])<=16*m.eps*abs(q[k])
        expected=[(k,False,m.bsum(delta[k])) for k in range(2) if delta[k]]
        expected += [(k,True,m.bsum(src[k])) for k in range(3) if src[k]]
        rows=report['lineage_groups']
        if len(rows)!=len(expected) or len(rows)>4096:raise ValueError('collision input lineage coverage')
        checks=[];budgets=[];Ls=[];uns=[];ups=[];ex=[ZERO,ZERO];physicalC=[Decimal('1.5')*KB*x for x in a['n']]
        for row,(kind,is_source,value) in zip(rows,expected):
            if type(row['kind']) is not int or row['kind']!=kind or type(row['source']) is not bool or row['source']!=is_source :
                raise ValueError('collision input lineage provenance mismatch')
            if not check(row['input_expansion'],value):raise ValueError('collision normalized input expansion mismatch')
            ops=row['operations']
            if not isinstance(ops,list) or len(ops)!=20 or [v['name'] for v in ops]!=list(OP_NAMES):raise ValueError('collision operation DAG coverage')
            v=[];ownn=value if kind==0 else ZERO;ownp=value if kind==1 else ZERO
            qn=ownn if is_source else ZERO;qp=ownp if is_source else ZERO;ql=value if kind==2 else ZERO
            for i,op in enumerate(ops):
                targets=(lambda:value*(rb[kind] if kind<2 else 1),lambda:sum(m.quotients(ops[0]['value'],m.binary(D[-1])),ZERO),
                    lambda:v[0]-m.bsum(D)*v[1],lambda:sum(m.quotients(ops[2]['value'],m.binary(D[-1])),ZERO),lambda:v[1]+v[3],
                    lambda:sum(m.quotients(ops[4]['value'],m.binary(af[3])),ZERO),lambda:m.bsum(C[0])*v[5],lambda:m.bsum(C[1])*v[5],
                    lambda:ownn-v[6],lambda:ownp-v[7],lambda:rb[0]*v[8],lambda:rb[1]*v[9],lambda:v[10]+v[11]+ql,
                    lambda:sum(m.quotients(ops[12]['value'],m.binary(af[3])),ZERO),lambda:-alpha*m.binary(af[0])*v[13],lambda:-alpha*m.binary(af[1])*v[13],
                    lambda:qn-v[10],lambda:qp-v[11],lambda:v[14]+v[16],lambda:v[15]+v[17])
                valid_op=check(op['value'],targets[i]());v.append(m.bsum(op['value']))
                if not valid_op:raise ValueError('collision exact binary DAG mismatch at '+OP_NAMES[i])
            # Independent, unapproximated BE at actual full densities; no
            # production coefficient or scalar-density substitution here.
            x=[sum(m.vector(ops[j]['value']),ZERO) for j in (10,11)];l=sum(m.vector(ops[12]['value']),ZERO);vv=sum(m.vector(row['input_expansion']),ZERO)
            own=[vv if kind==k else ZERO for k in range(2)]
            residual=[V*(x[k]-dt/p[2+k]*(own[k]-x[k]-physicalC[k]*l/f[3])) for k in range(2)]
            source_abs=abs(vv) if is_source else ZERO
            scale=V*(sum(map(abs,x),ZERO)+abs(l)*(1+sum(map(abs,physicalC),ZERO)/f[3])+source_abs)
            budget=min(atol/max(1,len(rows)),4096*m.eps*scale);ok=all(abs(r)<=budget for r in residual)
            checks.append(dict(valid=bool(ok),BE_residuals_J=[format(r,'.12E') for r in residual],energy_budget_J=format(budget,'.12E')))
            valid &= ok;budgets.append(budget);Ls.extend(ops[12]['value']);uns.extend(ops[18]['value']);ups.extend(ops[19]['value'])
            ex=[e+y for e,y in zip(ex,x)]
        valid &= check(L,m.bsum(Ls)) and check(increments[0],m.bsum(uns)) and check(increments[1],m.bsum(ups))
        if payload>4096:raise ValueError('collision evidence component budget exceeded')
        views=m.vector(report['temperatures_K']);valid &= len(views)==3 and all(abs(x-y)<=Decimal('1e-25')*max(1,abs(y)) for x,y in zip(views,b['temperatures']))
        dU=[V*(b['K'][k]-a['K'][k]) for k in range(2)]+[V*f[3]*(b['Tl']-a['Tl'])]
        residual=[dU[0]+V*ex[0]-q[0],dU[1]+V*ex[1]-q[1],dU[2]-V*sum(ex,ZERO)-q[2],sum(dU,ZERO)-sum(q,ZERO)]
        budget=min(atol,sum(budgets,ZERO));closed=all(abs(x)<=budget for x in residual);valid &= closed
        return dict(valid=bool(valid),lineage_checks=checks,actual_particle_densities_unchanged=True,global_particle_energy_closed=bool(closed),
            stored_physical_residuals_J=[format(x,'.12E') for x in residual],global_energy_budget_J=format(budget,'.12E'),
            exact_binary_DAG_checked=True,native_physics_used=False,complete_device_energy=False,physical_validated=False)
