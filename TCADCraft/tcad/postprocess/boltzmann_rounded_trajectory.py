"""Streaming independent verification of explicitly rounded MB trajectories.

Actual initial-to-current particle/energy changes and all accumulated exchanges
are checked at every prefix. Neither saved audit claims nor production calls
are used. Memory use is bounded independently of the number of journal rows.
"""
from dataclasses import asdict
from decimal import Decimal
from fractions import Fraction
import hashlib,json
from .boltzmann_recomputed_transport import saved_state,point,moment_wire,_values
from .boltzmann_recomputed_endpoint_split import configuration,exchange_budget
from .boltzmann_recomputed_lattice_transport import face_values,_topology
from .boltzmann_accounted_rounding import audit_mb_rounded_conducting_split
from .boltzmann_scaled_split import _command,_display
from .boltzmann_product_range import _binary113
from .boltzmann_scaled_collision_trace import _multiply


def canonical_bytes(value):
    try:return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (TypeError,ValueError) as exc:raise ValueError('finite JSON trajectory data required') from exc


def record_digest(value):return hashlib.sha256(canonical_bytes(value)).hexdigest()


def trajectory_contract(configurations,initial,faces,thermal_faces,dt_s,steps,*,impulses_J=None,
                        particle_atol=1e-9,energy_atol_J=1e-27):
    if type(steps) is not int or not 1<=steps<=16384:raise ValueError('bounded integer trajectory step count required')
    old=tuple(map(saved_state,initial));n=len(old);dt=_command(dt_s)
    pa=min(_command(particle_atol),Fraction(1,10**9));ea=min(_command(energy_atol_J),Fraction(1,10**27))
    if not 1<=n<=256 or min(dt,pa,ea)<=0 or len(configurations)!=n:
        raise ValueError('trajectory cells/configurations/duration/budgets')
    if any(s.time_s!=old[0].time_s or s.physical_clock!=old[0].physical_clock for s in old):
        raise ValueError('trajectory requires synchronized initial clocks')
    cfg=[configuration(c)[0] for c in configurations];fs=[]
    if len(faces)>512:raise ValueError('trajectory carrier face budget')
    for spec in faces:
        if type(spec) is not dict or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):
            raise ValueError('explicit maintained carrier topology required')
        i=spec['owner'];j=spec.get('neighbor')
        if type(i) is not int or not 0<=i<n or ('neighbor' in spec and (type(j) is not int or not 0<=j<n or i==j)):
            raise ValueError('trajectory face index')
        if 'reservoir' in spec:
            reservoir=saved_state(spec['reservoir'])
            if reservoir.time_s!=old[0].time_s or reservoir.physical_clock!=old[0].physical_clock:
                raise ValueError('initial maintained reservoir clock mismatch')
            spec={**spec,'reservoir':asdict(reservoir)}
        fs.append(spec)
    list(_topology(old,thermal_faces))
    impulses=[(0.,0.,0.) for _ in old] if impulses_J is None else impulses_J
    if len(impulses)!=n or any(len(q)!=3 for q in impulses):raise ValueError('trajectory three-source coverage')
    q=[[float(_command(x)) for x in row] for row in impulses]
    result=dict(scope='accounted_rounded_trajectory_v1',precision_bits=113,steps=steps,dt_s=float(dt_s),
        particle_atol=float(pa),energy_atol_J=float(ea),configurations=cfg,initial=list(map(asdict,old)),
        faces=fs,thermal_faces=list(thermal_faces),impulses_J=q,exact_recurrence_preserved=False,
        field_work_included=False,complete_device_energy=False,physical_validated=False)
    return json.loads(canonical_bytes(result))


def maintained_faces(contract,states):
    first=states[0] if isinstance(states[0],dict) else asdict(states[0]);result=[]
    for face in contract['faces']:
        if 'reservoir' in face:
            face={**face,'reservoir':{**face['reservoir'],'time_s':first['time_s'],'physical_clock':first['physical_clock']}}
        result.append(face)
    return result


def _inventory(states):
    total=[Fraction()]*6;frames=[]
    for raw in states:
        p=point(raw['endpoint'] if isinstance(raw,dict) else raw.endpoint);f=p['frame'];V=f[4];frames.append(f)
        U=[V*(p['K'][k]+f[5+k]*p['n'][k]) for k in (0,1)];L=V*f[3]*p['Tl']
        values=[V*p['n'][0],V*p['n'][1],*U,L,sum(U)+L]
        total=[x+y for x,y in zip(total,values)]
    return total,frames


def _ledger(contract,report):
    totals=[Fraction()]*6;child=report['conducting'];base=child['carrier_split'];dt=_binary113(_command(contract['dt_s']))
    for face,proof in zip(contract['faces'],base['transport']['transfers']):
        if 'reservoir' not in face:continue
        values,packets,j=_values(moment_wire(proof['raw']),'mb_scaled_moments_v1',4)
        Nn,Np,Un,Up=[_multiply(x,dt) for x in values]
        totals=[x+y for x,y in zip(totals,[Nn,Np,Un,Up,Fraction(),Un+Up])]
    for face,raw in zip(contract['thermal_faces'],child['lattice']['faces']):
        if 'bath_temperature_K' in face:
            G,values,parts=face_values(raw);heat=_multiply(values[4],dt);totals[4]+=heat;totals[5]+=heat
    for mid,collision,q in zip(base['transported_states'],base['collisions'],contract['impulses_J']):
        exchange,budget=exchange_budget(mid['endpoint'],collision['command'],collision['root_packet']);q=list(map(_command,q))
        totals[2]+=exchange[0]-q[0];totals[3]+=exchange[1]-q[1]
        totals[4]-=sum(exchange)+q[2];totals[5]-=sum(q)
    return totals


def audit_mb_rounded_trajectory(contract,records,*,checkpoint_stride=64):
    if type(contract) is not dict:raise ValueError('explicit trajectory contract required')
    try:
        expected=trajectory_contract(contract['configurations'],contract['initial'],contract['faces'],contract['thermal_faces'],
            contract['dt_s'],contract['steps'],impulses_J=contract['impulses_J'],particle_atol=contract['particle_atol'],energy_atol_J=contract['energy_atol_J'])
    except (KeyError,TypeError) as exc:raise ValueError('trajectory contract coverage') from exc
    if contract!=expected:raise ValueError('trajectory contract metadata/coverage mismatch')
    if type(checkpoint_stride) is not int or not 1<=checkpoint_stride<=16384:raise ValueError('bounded checkpoint stride required')
    previous=record_digest(contract);old=contract['initial'];initial,frames=_inventory(old)
    ledger=[Fraction()]*6;budgets=[Fraction()]*6;count=0;checkpoints=[];maximum=Fraction()
    pa=min(_command(contract['particle_atol']),Fraction(1,10**9));ea=min(_command(contract['energy_atol_J']),Fraction(1,10**27))
    limits=[pa,pa,ea,ea,ea,ea];last=None
    for row in records:
        if count>=contract['steps']:raise ValueError('trajectory extra record')
        if type(row) is not dict or set(row)!={'index','previous_sha256','new','report','sha256'}:
            raise ValueError('trajectory record coverage')
        payload={k:v for k,v in row.items() if k!='sha256'}
        if type(row['index']) is not int or row['index']!=count or row['previous_sha256']!=previous or row['sha256']!=record_digest(payload):
            raise ValueError('trajectory record sequence/hash chain mismatch')
        faces=maintained_faces(contract,old)
        check=audit_mb_rounded_conducting_split(contract['configurations'],old,row['new'],row['report'],faces=faces,
            thermal_faces=contract['thermal_faces'],dt_s=contract['dt_s'],impulses_J=contract['impulses_J'],
            particle_atol=1e-9,energy_atol_J=1e-27)
        if not check['valid']:raise ValueError('trajectory child audit failed')
        actual,newframes=_inventory(row['new'])
        if frames!=newframes:raise ValueError('trajectory changed frozen material/geometric frames')
        ledger=[x+y for x,y in zip(ledger,_ledger(contract,row['report']))]
        # Freshly recomputed .12E displays have 13 significant digits. This
        # upper envelope covers <=5e-13 relative display error in either direction.
        upper=[Fraction(Decimal(x))*Fraction(1000000000002,1000000000000) for x in check['global_budgets']]
        budgets=[x+y for x,y in zip(budgets,upper)]
        if any(x>y for x,y in zip(budgets,limits)):raise ValueError('cumulative trajectory error allowance exhausted')
        residual=[a-b+c for a,b,c in zip(actual,initial,ledger)]
        if any(abs(x)>y for x,y in zip(residual,budgets)):raise ValueError('trajectory actual prefix particle/energy gate failed')
        ratios=[abs(x)/y if y else Fraction() for x,y in zip(residual,budgets)];maximum=max(maximum,*ratios)
        count+=1;previous=row['sha256'];old=row['new']
        last=dict(step=count,time_s=old[0]['time_s'],global_residuals=list(map(_display,residual)),global_budgets=list(map(_display,budgets)))
        if count%checkpoint_stride==0 or count==contract['steps']:checkpoints.append(last)
    if count!=contract['steps']:raise ValueError('trajectory missing records')
    return dict(valid=True,scope='streamed_independent_rounded_trajectory',accepted_steps=count,
        contract_sha256=record_digest(contract),last_record_sha256=previous,checkpoints=checkpoints,
        start_time_s=contract['initial'][0]['time_s'],end_time_s=old[0]['time_s'],
        global_residuals=last['global_residuals'],global_budgets=last['global_budgets'],
        maximum_prefix_budget_utilization=_display(maximum),all_actual_prefix_energy_closed=True,
        cumulative_error_allowance_enforced=True,maintained_contact_controls_checked=True,
        rounding_error_included=True,exact_recurrence_preserved=False,native_physics_used=False,
        lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
