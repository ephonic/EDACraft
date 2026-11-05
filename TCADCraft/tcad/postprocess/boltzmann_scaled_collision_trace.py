"""Independent exact replay of complete or budget-stopped collision traces."""
from decimal import Decimal, localcontext
from fractions import Fraction

from .boltzmann_product_range import _binary113, _vector
from .boltzmann_scaled_arithmetic import _count, _tokens, scaled_value_fraction
from .boltzmann_scaled_collision_tail import _endpoint


def _wire(x):
    if not x:
        return ['mb_scaled_value_v1', '113', '0']
    n, exponent = abs(x.numerator), -(x.denominator.bit_length()-1)
    if x.denominator != 1 << -exponent:
        raise ValueError('dyadic trace value required')
    low = (n & -n).bit_length()-1
    n >>= low
    exponent += low
    parts = []
    for start in range(0, n.bit_length(), 113):
        part = (n >> start) & ((1 << 113)-1)
        if part:
            zeros = (part & -part).bit_length()-1
            coefficient = (part >> zeros) * (1 if x > 0 else -1)
            parts.extend((hex(coefficient), str(exponent+start+zeros)))
    return ['mb_scaled_value_v1', '113', str(len(parts)//2), *parts]


def _atoms(x):
    wire = _wire(x)
    return [Fraction(int(c,16) << int(e)) if int(e) >= 0 else Fraction(int(c,16),1 << -int(e))
            for c,e in zip(wire[3::2],wire[4::2])]


def _divide(atoms, b):
    if not b:
        raise ValueError('trace division by zero')
    result = Fraction()
    for a in atoms:
        h = _binary113(a/b)
        l = _binary113((a-b*h)/b)
        result += h+l
    return result, sum(atoms,Fraction())-b*result


def _multiply(a,b):
    if int(_wire(a)[2])*int(_wire(b)[2]) > 65536:
        raise ValueError('original trace product pair budget exceeded')
    return a*b


def _expected(endpoint, command):
    f,en,ep,dn,dp,un0,up0 = _endpoint(endpoint)
    c = _vector(command)
    if len(c) != 6 or min(c[:3]) <= 0:
        raise ValueError('positive fixed-tau trace command required')
    alpha = _binary113(Fraction(3,2)*_binary113(Fraction(Decimal('1.380649e-23'))))
    cv, volume = f[3:5]
    if cv <= 0 or volume <= 0:
        raise ValueError('positive trace storage scales required')
    yield 'alpha',alpha,Fraction()
    R = [_binary113(c[0]/_binary113(c[0]+c[k+1])) for k in (0,1)]
    for k,r in enumerate(R):
        if not 0 < r <= 1:
            raise ValueError('trace exchange coefficient outside range')
        yield f'R{k}',r,Fraction()
    qold,rest = _divide(f[9:],cv)
    yield 'qold',qold,rest
    thermal = f[2]+qold
    yield 'thermal',thermal,Fraction()
    n,K,C,delta,capacity = [],[],[],[],[]
    for k,changes in enumerate((dn,dp)):
        n.append(f[k]+sum(changes,Fraction()))
        if not Fraction(1,10**1000) <= n[-1] <= 10**1000:
            raise ValueError('trace density outside range')
        yield f'n{k}',n[-1],Fraction()
        K.append(_multiply(_multiply(alpha,thermal),f[k])+sum((en,ep)[k]+(un0,up0)[k],Fraction())
                 -_multiply(f[5+k],sum(changes,Fraction())))
        yield f'K{k}',K[-1],Fraction()
        C.append(_multiply(alpha,n[-1]))
        yield f'C{k}',C[-1],Fraction()
        delta.append(K[-1]-_multiply(C[-1],thermal))
        yield f'delta{k}',delta[-1],Fraction()
        q,r = _divide(_atoms(C[-1]),cv)
        capacity.append(q)
        yield f'capacity{k}',q,r
    D = 1+_multiply(R[0],capacity[0])+_multiply(R[1],capacity[1])
    if D <= 0:
        raise ValueError('positive scaled denominator required')
    yield 'D',D,Fraction()
    head = _binary113(D)
    yield 'Dhead',head,Fraction()
    inputs = [(d,k,False) for k,d in enumerate(delta) if d]
    for k in range(3):
        q,r = _divide([c[k+3]],volume)
        yield f'source{k}',q,r
        if q:
            inputs.append((q,k,True))
    lineages = []
    L=un=up=Fraction()
    for j,(value,kind,source) in enumerate(inputs):
        prefix = f'lineage{j}.'
        yield prefix+'input',value,Fraction()
        ownn,ownp = (value if kind == k else Fraction() for k in (0,1))
        qn,qp = (ownn,ownp) if source else (Fraction(),Fraction())
        ql = value if kind == 2 else Fraction()
        v = []
        for i in range(20):
            r=Fraction()
            if i == 0: q = _multiply(value,1 if kind == 2 else R[kind])
            elif i == 1: q,r = _divide(_atoms(v[0]),head)
            elif i == 2: q = v[0]-_multiply(D,v[1])
            elif i == 3: q,r = _divide(_atoms(v[2]),head)
            elif i == 4: q = v[1]+v[3]
            elif i == 5: q,r = _divide(_atoms(v[4]),cv)
            elif i in (6,7): q = _multiply(C[i-6],v[5])
            elif i == 8: q = ownn-v[6]
            elif i == 9: q = ownp-v[7]
            elif i in (10,11): q = _multiply(R[i-10],v[i-2])
            elif i == 12: q = v[10]+v[11]+ql
            elif i == 13: q,r = _divide(_atoms(v[12]),cv)
            elif i in (14,15): q = _multiply(_multiply(alpha,-f[i-14]),v[13])
            elif i == 16: q = qn-v[10]
            elif i == 17: q = qp-v[11]
            elif i == 18: q = v[14]+v[16]
            else: q = v[15]+v[17]
            v.append(q)
            yield prefix+str(i),q,r
        L+=v[12];un+=v[18];up+=v[19]
        lineages.append((value,kind,source,v))
    yield 'aggregate.L',L,Fraction()
    yield 'aggregate.un',un,Fraction()
    yield 'aggregate.up',up,Fraction()
    physical_alpha = Fraction(3,2)*Fraction(Decimal('1.380649e-23'))
    budgets=[]
    for value,kind,source,v in lineages:
        X=v[10:12];lattice=v[12]
        own=[value if kind == k else 0 for k in (0,1)]
        be=[volume*(X[k]-c[0]/c[k+1]*(own[k]-X[k]-physical_alpha*n[k]*lattice/cv)) for k in (0,1)]
        sourceJ=[c[k+3] if source and kind == k else 0 for k in range(3)]
        carrier=[volume*(v[18+k]+physical_alpha*f[k]*lattice/cv) for k in (0,1)]
        energy=[carrier[k]+volume*X[k]-sourceJ[k] for k in (0,1)]
        energy += [volume*(lattice-sum(X))-sourceJ[2],sum(carrier)+volume*lattice-sum(sourceJ)]
        scale=volume*(sum(map(abs,X))+abs(lattice)*(1+physical_alpha*sum(map(abs,n))/cv)
                      +(abs(value) if source else 0))
        budget=min(Fraction(1,10**27)/max(1,len(inputs)),4096*Fraction(1,1 << 112)*scale)
        if any(abs(x)>budget for x in be+energy):
            raise ValueError('full trace fixed-tau lineage BE or physical energy gate failed')
        budgets.append(budget)
    carrier=[volume*(stored+physical_alpha*f[k]*L/cv) for k,stored in enumerate((un,up))]
    total=sum(carrier)+volume*L-sum(c[3:])
    budget=min(Fraction(1,10**27),sum(budgets,Fraction()))
    if abs(total)>budget:
        raise ValueError('full trace aggregate physical energy gate failed')
    # Actual final temperatures are checked on full density and saved lattice,
    # not on a rounded diagnostic scalar.
    finalTl=f[2]+(sum(f[9:],Fraction())+L)/cv
    temperatures=[finalTl]
    for k,stored in enumerate((un,up)):
        kinetic=physical_alpha*finalTl*f[k]+sum((en,ep)[k]+(un0,up0)[k],Fraction())+stored-f[5+k]*sum((dn,dp)[k],Fraction())
        temperatures.append(kinetic/(physical_alpha*n[k]))
    if any(not f[7] <= t <= f[8] for t in temperatures):
        raise ValueError('full trace final physical temperature outside bounds')
    return dict(lineages=len(lineages),energy_gate_passed=True,final_temperature_bounds_passed=True)


def audit_mb_scaled_collision_trace(endpoint,command,wire):
    _tokens(wire,100000)
    if len(wire)<7 or tuple(wire[:2]) != ('mb_scaled_collision_trace_v1','113'):
        raise ValueError('collision trace version/precision mismatch')
    status=wire[2]
    if status not in ('complete','evidence_budget_exceeded'):
        raise ValueError('collision trace status invalid')
    records=_count(wire[3],4096)
    declared=_count(wire[4],4096)
    requested=_count(wire[6],8192)
    expected=_expected(endpoint,command)
    cursor=7;payload=0;nonzero_remainders=0;completed_lineages=0
    for _ in range(records):
        if cursor>=len(wire): raise ValueError('missing collision trace record')
        label=wire[cursor];cursor+=1
        try: wanted,q,r=next(expected)
        except StopIteration as exc: raise ValueError('unexpected collision trace record') from exc
        if label != wanted: raise ValueError('collision trace operation provenance mismatch')
        for value in (q,r):
            if cursor>=len(wire): raise ValueError('missing collision trace value')
            size=_count(wire[cursor],8195)
            raw=list(wire[cursor+1:cursor+1+size]);cursor+=size+1
            if len(raw)!=size or raw != _wire(value):
                raise ValueError('collision trace exact canonical value or remainder mismatch')
            scaled_value_fraction(raw)
            payload+=int(raw[2])
        nonzero_remainders+=bool(r)
        completed_lineages+=label.startswith('lineage') and label.endswith('.19')
        if payload>4096: raise ValueError('original trace cumulative evidence budget exceeded')
    if cursor != len(wire) or payload != declared:
        raise ValueError('collision trace coverage or evidence count mismatch')
    if status == 'evidence_budget_exceeded':
        try: label,q,r=next(expected)
        except StopIteration as exc: raise ValueError('false collision trace budget exhaustion') from exc
        cost=int(_wire(q)[2])+int(_wire(r)[2])
        if wire[5] != label or requested != payload+cost or requested<=4096:
            raise ValueError('collision trace first blocked operation or budget mismatch')
        details={}
    else:
        if wire[5] != '-' or requested:
            raise ValueError('complete collision trace has a false blocker')
        try: next(expected)
        except StopIteration as done: details=done.value
        else: raise ValueError('collision trace falsely claims completion')
    return dict(scope='scaled_fixed_tau_collision_trace',status=status,records_audited=records,
                evidence_components=payload,original_evidence_budget=4096,
                first_blocked_operation=wire[5],requested_components=requested,
                completed_lineages=completed_lineages,nonzero_division_remainders=nonzero_remainders,
                full_fixed_tau_trace_audited=status=='complete',
                full_fixed_tau_energy_gate_passed=details.get('energy_gate_passed',False),
                state_committed=False,physical_time_advanced=False,nonlinear_root_audited=False,
                physical_validated=False)
