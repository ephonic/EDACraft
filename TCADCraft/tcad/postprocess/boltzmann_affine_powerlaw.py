"""Independent nonlinear affine BE verification; stdlib only, no law calls."""
from dataclasses import replace
from decimal import Decimal,localcontext
from tcad.postprocess.boltzmann_affine_collision import audit_mb_affine_collision
from tcad.postprocess.boltzmann_affine_transport import _Arithmetic,_point,_metadata,_fingerprint,KB,ZERO


def audit_mb_affine_powerlaw(config,old,new,report,*,dt_s,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();dt=m.command(dt_s);atol=m.command(energy_atol_J)
        if min(dt,atol)<=0:raise ValueError('positive independent nonlinear commands required')
        a=_point(old,m);b=_point(new,m);p=list(map(Decimal,config.parameters));V=a['frame'][4];Cv=a['frame'][3]
        if any(abs(p[j])>8 for j in (6,7,10,11)):raise ValueError('bounded independent powerlaw abs(a,c)<=8 required')
        _metadata(report,dict(scope='bounded_powerlaw_affine_MB_collision_BE',execution_backend='native',precision_bits=113,
            configuration_sha256=config.sha256,old_sha256=_fingerprint(old),new_sha256=_fingerprint(new),
            coefficient_model='binary113_log_head_plus_log1p_low',root_trace_is_diagnostic=True,
            physical_time_advanced=True,expanded_density_collision_supported=True,dynamic_lattice_supported=True,
            nonzero_ac_supported=True,extreme_stiffness_supported=False,same_interval_coupled_integrator_supported=False,
            device_statistics_selected=False,complete_device_energy=False,physical_validated=False))
        inner=report['collision'];tau=m.vector(report['effective_tau_s']);trace=report['root_trace']
        if len(tau)!=2 or not 1<=len(trace)<=256:raise ValueError('independent nonlinear root coverage')
        pp=list(config.parameters);pp[2:4]=report['effective_tau_s']
        for j in (6,7,10,11):pp[j]='0'
        effective=replace(config,parameters=tuple(pp))
        check=audit_mb_affine_collision(effective,old,new,inner,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J)
        valid=check['valid'] and report['dt_s']==inner['dt_s'] and report['impulses_J']==inner['impulses_J']
        # Decimal transcendental work is independently performed at 180 digits.
        # Full authoritative density and Tl, rather than cached scalar views,
        # supply the law. This is a numerical constitutive check, not an exact
        # binary DAG proof of log/exp and not a material calibration.
        def laws(T):
            with localcontext() as lc:
                lc.prec=180
                return [+(p[k+2]*(T/p[j])**p[j+2]*(a['n'][k]/p[j+1])**p[j+3]) for k,j in ((0,4),(1,8))]
        for row in trace:
            if set(row)!=set(('temperature_K','tau_n_s','tau_p_s','candidate_lattice_temperature_K')):raise ValueError('root trace fields')
            T=m.binary(row['temperature_K']);values=m.vector([row['tau_n_s'],row['tau_p_s']]);m.vector([row['candidate_lattice_temperature_K']])
            if not p[12]<=T<=p[13]:raise ValueError('root trial outside temperature domain')
            exact=laws(T)
            for x,y in zip(values,exact):
                valid &= Decimal('1e-3')<=x/dt<=Decimal('1e3') and abs(x-y)<=4096*m.eps*abs(y)
        last=trace[-1]
        valid &= last['temperature_K']==report['root_temperature_K'] and [last['tau_n_s'],last['tau_p_s']]==report['effective_tau_s']
        root=m.binary(report['root_temperature_K'])
        valid &= abs(root-b['Tl'])<=32*m.eps*max(1,abs(p[12]),abs(p[13]))
        valid &= abs(Decimal(last['candidate_lattice_temperature_K'])-b['Tl'])<=32*m.eps*max(1,abs(b['Tl']))
        true_tau=laws(b['Tl']);physicalC=[Decimal('1.5')*KB*x for x in a['n']];rows=inner['lineage_groups'];checks=[]
        for row in rows:
            kind=row['kind'];v=sum(m.vector(row['input_expansion']),ZERO);ops=row['operations']
            x=[sum(m.vector(ops[j]['value']),ZERO) for j in (10,11)];L=sum(m.vector(ops[12]['value']),ZERO)
            own=[v if kind==k else ZERO for k in range(2)]
            residual=[V*(x[k]-dt/true_tau[k]*(own[k]-x[k]-physicalC[k]*L/Cv)) for k in range(2)]
            scale=V*(sum(map(abs,x),ZERO)+abs(L)*(1+sum(map(abs,physicalC),ZERO)/Cv)+(abs(v) if row['source'] else ZERO))
            budget=min(atol/max(1,len(rows)),4096*m.eps*scale);ok=all(abs(r)<=budget for r in residual);valid &= ok
            checks.append(dict(valid=bool(ok),BE_residuals_J=[format(r,'.12E') for r in residual],energy_budget_J=format(budget,'.12E')))
        return dict(valid=bool(valid),constant_coefficient_ledger_audit=check,nonlinear_lineage_checks=checks,
            actual_state_tau_s=[format(x,'.40E') for x in true_tau],constitutive_decimal_precision=180,
            original_energy_gates_changed=False,full_density_and_committed_lattice_law_checked=True,native_physics_used=False,
            complete_device_energy=False,physical_validated=False)
