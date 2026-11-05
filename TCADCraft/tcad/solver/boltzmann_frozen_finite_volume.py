"""One explicit flat-band FV transaction with expanded particle/energy changes.

The output is an authoritative affine state, not a scalar-density MB state.
It deliberately cannot be fed to the existing face or collision APIs. Those
APIs need expanded-density constitutive laws before a second transport step.
"""
from dataclasses import dataclass,asdict
from decimal import Decimal
import hashlib,json,math
from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal

FIELDS=('electron_density_change','hole_density_change','electron_energy_density_change','hole_energy_density_change')


@dataclass(frozen=True)
class MBFiniteVolumeState:
    anchor: MBParticleEnergyState
    electron_density_change: tuple
    hole_density_change: tuple
    electron_energy_density_change: tuple
    hole_energy_density_change: tuple
    time_s: float

    def __post_init__(self):
        if type(self.anchor) is not MBParticleEnergyState:raise ValueError('original expanded MB anchor required')
        for key in FIELDS:
            raw=tuple(str(x) for x in getattr(self,key))
            if len(raw)>4096 or any(not Decimal(x).is_finite() for x in raw):raise ValueError('bounded finite FV increment required')
            object.__setattr__(self,key,raw)
        if isinstance(self.time_s,bool) or not math.isfinite(self.time_s) or self.time_s<=self.anchor.time_s:
            raise ValueError('strictly advancing FV clock required')


def _fingerprint(state):
    return hashlib.sha256(json.dumps(asdict(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def advance_mb_frozen_finite_volume(states,faces,dt_s,*,particle_atol=1e-9,energy_atol_J=1e-27,
                                    number_atol_s=1e-6,energy_atol_W=1e-15):
    """Atomic one-step FV update. Face specs have owner, neighbor OR reservoir,
    geometry. Internal orientation is owner -> neighbor, contacts are outward.
    Closed cells with no faces are allowed. No field, collision or lattice flux.
    """
    from tcad.core._bindings import native_mb_fv_integrate_raw,native_mb_fv_cell_raw
    from tcad.physics.boltzmann_expanded_flat_face import expanded_mb_flat_face
    states=tuple(states);faces=tuple(faces)
    values=_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,))
    if min(values)<=0 or not states or len(states)>256 or len(faces)>512:raise ValueError('positive bounded FV problem required')
    if any(type(s) is not MBParticleEnergyState for s in states):raise ValueError('FV input requires original expanded-density anchors; repeat transport is unsupported')
    if any(s.time_s!=states[0].time_s for s in states):raise ValueError('simultaneous FV cells required')
    end=states[0].time_s+float(dt_s)
    if not math.isfinite(end) or end<=states[0].time_s:raise ValueError('unrepresentable FV clock advance')
    transfers=[];commands=[[] for _ in states];seen=set()
    for spec in faces:
        if not isinstance(spec,dict) or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):
            raise ValueError('explicit internal/contact face specification required')
        i=spec['owner'];j=spec.get('neighbor')
        if type(i) is not int or not 0<=i<len(states):raise ValueError('FV owner index invalid')
        contact='reservoir' in spec
        if not contact and (type(j) is not int or not 0<=j<len(states) or i==j):raise ValueError('FV neighbor index invalid')
        if not contact:
            key=tuple(sorted((i,j)))
            if key in seen:raise ValueError('duplicate internal FV face')
            seen.add(key)
        other=spec['reservoir'] if contact else states[j]
        if type(other) is not MBParticleEnergyState:raise ValueError('expanded MB reservoir required')
        moment=expanded_mb_flat_face(states[i],other,spec['geometry'],face_kind='contact' if contact else 'bulk',
            number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
        source=[moment['carriers'][k][field] for field in ('number_expansion','energy_expansion') for k in range(2)]
        integrated=[native_mb_fv_integrate_raw(v,_decimal(values[0])) for v in source]
        transfer=dict(owner=i,neighbor=None if contact else j,moment=moment,integrated=integrated)
        index=len(transfers);transfers.append(transfer);commands[i].append((index,-1))
        if not contact:commands[j].append((index,1))
    new=[];cells=[]
    for i,old in enumerate(states):
        signed=[[] for _ in range(4)]
        for face_index,sign in commands[i]:
            for target,raw in zip(signed,transfers[face_index]['integrated']):
                target.extend(raw if sign>0 else [('-'+x if not x.startswith('-') else x[1:]) for x in raw])
        if any(len(x)>4096 for x in signed):raise ValueError('FV cell transfer budget exceeded')
        raw=native_mb_fv_cell_raw(old.frame,old.electron_excess,old.hole_excess,*signed)
        index=0;changes=[]
        for _ in range(4):
            count=Decimal(raw[index]);index+=1
            if count!=count.to_integral_value() or not 0<=count<=4096:raise ValueError('FV native increment coverage invalid')
            count=int(count);changes.append(tuple(raw[index:index+count]));index+=count
            if len(changes[-1])!=count:raise ValueError('FV native output truncated')
        if len(raw)!=index+3:raise ValueError('FV native output coverage invalid')
        new.append(MBFiniteVolumeState(old,*changes,end));cells.append(dict(temperatures_K=raw[index:]))
    report=dict(scope='one_frozen_flat_MB_finite_volume_transaction',execution_backend='native',precision_bits=113,
        dt_s=_decimal(values[0]),old_sha256=[_fingerprint(s) for s in states],new_sha256=[_fingerprint(s) for s in new],
        transfers=transfers,cells=cells,time_s=end,physical_time_advanced=True,repeat_transport_supported=False,
        device_statistics_selected=False,field_work_inferred=False,lattice_flux_included=False,
        complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_frozen_finite_volume import audit_mb_frozen_finite_volume
    check=audit_mb_frozen_finite_volume(states,new,report,faces=faces,dt_s=dt_s,particle_atol=particle_atol,
        energy_atol_J=energy_atol_J,number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    if not check['valid']:raise ValueError('independent MB finite-volume audit failed')
    report['independent_audit']=check
    return tuple(new),report
