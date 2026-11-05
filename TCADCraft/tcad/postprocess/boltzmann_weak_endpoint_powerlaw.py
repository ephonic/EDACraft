"""Independent actual-state nonlinear audit of a saved scaled root candidate."""
from decimal import Decimal,localcontext
from fractions import Fraction

from .boltzmann_product_range import _vector,_binary113
from .boltzmann_scaled_arithmetic import _tokens,_count
from .boltzmann_dyadic_codec import scaled_value_fraction
from .boltzmann_recomputed_endpoint_collision import _groups as _endpoint
from .boltzmann_recomputed_endpoint_collision import _expected,_wire
from .boltzmann_recomputed_endpoint_collision import audit_mb_recomputed_endpoint_collision_compact


def split_mb_weak_endpoint_powerlaw(wire):
    _tokens(wire,24000)
    if len(wire)<7 or tuple(wire[:2])!=('mb_weak_endpoint_powerlaw_v1','113'):
        raise ValueError('scaled powerlaw version/precision mismatch')
    n=_count(wire[2],256)
    if not n or len(wire)<7+4*n:
        raise ValueError('scaled root history coverage mismatch')
    evidence=_count(wire[6],4096);cursor=7+4*n;packets=[]
    for maximum in (8195,8195,20000):
        if cursor>=len(wire):raise ValueError('missing scaled root packet')
        size=_count(wire[cursor],maximum)
        packet=list(wire[cursor+1:cursor+1+size]);cursor+=size+1
        if len(packet)!=size:raise ValueError('scaled root packet truncated')
        packets.append(packet)
    if cursor!=len(wire):raise ValueError('unexpected scaled root token')
    return dict(trials=n,evidence=evidence,chosen=list(wire[3:6]),
                history=[list(wire[j:j+4]) for j in range(7,7+4*n,4)],
                start=packets[0],end=packets[1],proof=packets[2])


def scaled_powerlaw_aggregates(proof):
    result={};cursor=9
    for _ in range(_count(proof[4],29)):
        if cursor+3>len(proof):raise ValueError('scaled state proof truncated')
        label,kind=proof[cursor:cursor+2];size=_count(proof[cursor+2],8195);cursor+=3
        raw=list(proof[cursor:cursor+size]);cursor+=size
        if len(raw)!=size:raise ValueError('scaled state value truncated')
        if kind=='aggregate_value':
            if label in result:raise ValueError('duplicate scaled state aggregate')
            result[label]=raw
    if cursor!=len(proof) or set(result)!={'aggregate.L','aggregate.un','aggregate.up'}:
        raise ValueError('scaled state aggregate coverage')
    return result


def audit_mb_weak_endpoint_powerlaw(endpoint,command,clock,wire):
    parts=split_mb_weak_endpoint_powerlaw(wire)
    f,en,ep,dn,dp,un0,up0=_endpoint(endpoint)
    c=_vector(command);times=[scaled_value_fraction(clock)]
    if list(clock)!=_wire(times[0]):raise ValueError("canonical exact endpoint root source clock required")
    if len(c)!=18 or len(times)!=1 or times[0]<0 or min(c[2:6]+c[8:10]+[c[14]])<=0:
        raise ValueError('positive scaled constitutive references and nonnegative clock required')
    if any(abs(c[j])>8 for j in (6,7,10,11)):
        raise ValueError('bounded scaled constitutive exponents required')
    if [c[j] for j in (0,1,12,13)]!=[f[j] for j in (3,4,7,8)]:
        raise ValueError('scaled constitutive frame mismatch')
    start=scaled_value_fraction(parts['start']);end=scaled_value_fraction(parts['end'])
    if parts['start']!=_wire(times[0]) or parts['end']!=_wire(times[0]+c[14]) or start!=times[0] or end-start!=c[14]:
        raise ValueError('scaled exact clock identity mismatch')
    chosen=_vector(parts['chosen'])
    if parts['chosen']!=parts['history'][-1][:3]:
        raise ValueError('scaled root chosen coefficient provenance mismatch')
    fixed_command=[command[14],*parts['chosen'][1:],*command[15:]]
    fixed=audit_mb_recomputed_endpoint_collision_compact(endpoint,fixed_command,parts['proof'])
    if not fixed['full_fixed_tau_energy_gate_passed']:
        raise ValueError('complete scaled fixed-tau proof required')
    evidence=4*parts['trials']+fixed['evidence_components']+int(parts['start'][2])+int(parts['end'][2])
    if evidence!=parts['evidence'] or evidence>4096:
        raise ValueError('scaled root combined saved evidence mismatch')
    aggregates=scaled_powerlaw_aggregates(parts['proof'])
    L,un,up=[scaled_value_fraction(aggregates[k]) for k in ('aggregate.L','aggregate.un','aggregate.up')]
    density=[f[0]+sum(dn,Fraction()),f[1]+sum(dp,Fraction())]
    finalTl=f[2]+(sum(f[9:],Fraction())+L)/f[3]
    eps=Fraction(1,1 << 112)
    if abs(chosen[0]-finalTl)>32*eps*max(1,abs(f[7]),abs(f[8])):
        raise ValueError('scaled root not converged on actual saved lattice')
    if _vector([parts['history'][-1][3]])[0]!=_binary113(finalTl):
        raise ValueError('scaled chosen candidate lattice mismatch')

    def decimal(x):return Decimal(x.numerator)/Decimal(x.denominator)
    def laws(T):
        with localcontext() as ctx:
            ctx.prec=180
            return [+(decimal(c[k+2])*(decimal(T)/decimal(c[j]))**decimal(c[j+2])*
                      (decimal(density[k])/decimal(c[j+1]))**decimal(c[j+3])) for k,j in ((0,4),(1,8))]

    for row in parts['history']:
        T,tn,tp,candidate=_vector(row)
        if not f[7]<=T<=f[8] or not f[7]<=candidate<=f[8]:
            raise ValueError('scaled root diagnostic trial temperature outside bounds')
        exact=laws(T)
        for saved,reference in zip((tn,tp),exact):
            target=Fraction(reference)
            if not Fraction(1,1000)<=saved/c[14]<=4096 or abs(saved-target)>4096*eps*abs(target):
                raise ValueError('scaled independent constitutive trial mismatch')
    true_tau=list(map(Fraction,laws(finalTl)))
    values={};groups=[];generator=_expected(endpoint,fixed_command)
    for label,q,r in generator:
        values[label]=q
        if label.startswith('lineage') and label.endswith('.input'):
            groups.append(label.split('.')[0])
    # The two RN113 operations used by the native exchange coefficient must
    # remain relatively accurate even when the collision is weak. Use exact
    # rational dt and tau, not a displayed coefficient or a native residual.
    coefficient_errors = []
    for k in (0, 1):
        exact_R = c[14] / (c[14] + chosen[1+k])
        error = abs(values['R'+str(k)] - exact_R) / exact_R
        if error > 4*eps:
            raise ValueError('weak exchange coefficient relative error gate failed')
        coefficient_errors.append(error)
    # Replay uses the original group order: nonzero carrier deltas, then
    # nonzero physical source divisions. No native law or solver is called.
    kinds=[(k,False) for k in (0,1) if values[f'delta{k}']]
    kinds += [(k,True) for k in range(3) if values[f'source{k}']]
    if len(kinds)!=len(groups):raise ValueError('nonlinear lineage coverage mismatch')
    physical_alpha=Fraction(3,2)*Fraction(Decimal('1.380649e-23'))
    rows=[];budgets=[]
    def display(x):
        with localcontext() as ctx:
            ctx.prec=40
            return format(decimal(x),'.12E')
    for prefix,(kind,source) in zip(groups,kinds):
        value=values[prefix+'.input'];X=[values[prefix+'.'+str(j)] for j in (10,11)];lattice=values[prefix+'.12']
        own=[value if kind==k else 0 for k in (0,1)]
        residual=[f[4]*(X[k]-c[14]/true_tau[k]*(own[k]-X[k]-physical_alpha*density[k]*lattice/f[3])) for k in (0,1)]
        scale=f[4]*(sum(map(abs,X))+abs(lattice)*(1+physical_alpha*sum(map(abs,density))/f[3])+(abs(value) if source else 0))
        budget=min(Fraction(1,10**27)/max(1,len(groups)),4096*eps*scale)
        if any(abs(r)>budget for r in residual):raise ValueError('actual-state nonlinear lineage BE gate failed')
        budgets.append(budget)
        rows.append(dict(BE_residuals_J=list(map(display,residual)),energy_budget_J=display(budget)))
    # Audit the actual immutable source endpoint plus the exact saved scaled
    # increments, rather than treating the root's rounded temperature as state.
    carrier=[f[4]*(stored+physical_alpha*f[k]*L/f[3]) for k,stored in enumerate((un,up))]
    total=sum(carrier)+f[4]*L-sum(c[15:])
    budget=min(Fraction(1,10**27),sum(budgets,Fraction()))
    if abs(total)>budget:raise ValueError('scaled actual new-state total energy gate failed')
    temperatures=[finalTl]
    for k,stored in enumerate((un,up)):
        kinetic=physical_alpha*finalTl*f[k]+sum((en,ep)[k]+(un0,up0)[k],Fraction())+stored-f[5+k]*sum((dn,dp)[k],Fraction())
        temperatures.append(kinetic/(physical_alpha*density[k]))
    if any(not f[7]<=T<=f[8] for T in temperatures):raise ValueError('scaled actual new-state temperature bounds')
    return dict(scope='bounded_weak_complete_endpoint_powerlaw_saved_candidate',valid=True,precision_bits=113,
                root_trials=parts['trials'],combined_saved_evidence_components=evidence,
                weak_collision_ratio_limit=4096,weak_collision_coefficient_gate_passed=True,
                chosen_tau_dt_ratios=list(map(display,[x/c[14] for x in chosen[1:]])),
                coefficient_relative_errors=list(map(display,coefficient_errors)),
                full_fixed_tau_audit=fixed,nonlinear_lineage_checks=rows,
                actual_state_temperatures_K=list(map(display,temperatures)),
                actual_state_total_energy_residual_J=display(total),unchanged_total_energy_budget_J=display(budget),
                actual_state_constitutive_decimal_precision=180,actual_state_nonlinear_BE_passed=True,
                exact_saved_clock_identity_checked=True,source_endpoint_preserved=True,
                candidate_state_energy_audited=True,application_state_committed=False,
                production_binding_integrated=False,whole_spatial_interval_audited=False,
                physical_time_advanced=False,extreme_stiffness_supported=False,physical_validated=False)
