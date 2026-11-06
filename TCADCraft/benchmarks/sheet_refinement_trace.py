"""Compare complete BE traces at common times and common current intervals.

Needs NumPy only; imports no TCAD solver/native extension. BE total/displacement
currents are interval values. Average fine substeps before comparing them with
a coarse step, including at discontinuous gate-drive edges. Conduction currents
are also compared at common ending times. This diagnoses error, not qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


def load_record(stem):
    stem = Path(stem)
    metadata = json.loads(Path(str(stem) + '.json').read_bytes())
    with np.load(str(stem) + '.npz', allow_pickle=False) as arrays:
        def decode(value):
            if isinstance(value, dict):
                if set(value) == {'__ndarray__'}:
                    return arrays[value['__ndarray__']].copy()
                return {key: decode(item) for key, item in value.items()}
            if isinstance(value, list):
                return [decode(item) for item in value]
            return value
        return decode(metadata)


def _positive(value, name):
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
        raise ValueError(name + ' must be a positive finite scalar')
    result = float(value)
    if not np.isfinite(result) or result <= 0:
        raise ValueError(name + ' must be a positive finite scalar')
    return result


def _flatten(value, path=''):
    if isinstance(value, dict):
        out = {}
        for key in sorted(value):
            out.update(_flatten(value[key], path + '/' + key))
        return out
    item = np.asarray(value)
    if item.ndim != 0 or item.dtype.kind not in 'fiu' or not np.isfinite(item):
        raise ValueError('trace quantity must be a finite scalar: ' + path)
    return {path: float(item)}


def _same_configuration(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        return (isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys()
                and all(_same_configuration(a[key], b[key]) for key in a))
    return np.array_equal(a, b)


def _metric(delta, coarse, fine, scale, times, count):
    index = int(np.argmax(abs(delta)))
    step = index + 1
    return dict(max_absolute=float(abs(delta[index])),
                max_normalized=float(abs(delta[index]) / scale),
                coarse_step=step, phase=index // count + 1,
                step_in_phase=index % count + 1, time_s=float(times[index]),
                coarse_value=float(coarse[index]), fine_value=float(fine[index]))


def compare_traces(coarse, fine, *, charge_scale_C=1e-18,
                   energy_scale_J=2.5e-20, current_scale_A=1e-7,
                   time_atol_s=1e-24):
    """Compare same-mesh full trajectories with an integral time-refinement ratio.

    Scales normalize descriptive differences; no acceptance threshold is inferred.
    Phase count comes from the complete coarse trace and must match the fine one.
    Scalar states use common ending times. Rate/total-current values use averages
    over the corresponding fine substeps. Their cumulative integrals are compared
    at every common observation time, retaining signed terminal quantities.
    """
    scales = {'C': _positive(charge_scale_C, 'charge_scale_C'),
              'J': _positive(energy_scale_J, 'energy_scale_J'),
              'A': _positive(current_scale_A, 'current_scale_A')}
    atol = _positive(time_atol_s, 'time_atol_s')
    n, nf = coarse['steps_per_phase'], fine['steps_per_phase']
    if (type(n) is not int or type(nf) is not int or n < 1 or nf <= n or nf % n):
        raise ValueError('fine steps_per_phase must be an integer multiple of coarse')
    ratio = nf // n
    phase_s = _positive(coarse['phase_s'], 'phase_s')
    if fine['phase_s'] != coarse['phase_s']:
        raise ValueError('phase durations differ')
    for key in ('contact', 'dielectric', 'boundary', 'contact_z_bounds_m'):
        if key in coarse or key in fine:
            if key not in coarse or key not in fine or not np.array_equal(coarse[key], fine[key]):
                raise ValueError('incompatible record: ' + key)
    ca, fa = coarse['checkpoints'][0], fine['checkpoints'][0]
    for key in ('x_m', 'y_m', 'z_m', 'sheet_index', 'material'):
        if key not in ca or key not in fa:
            raise ValueError('missing same-mesh metadata: ' + key)
        if key == 'material':
            equal = ca[key] == fa[key]
        else:
            equal = np.array_equal(ca[key], fa[key])
        if not equal:
            raise ValueError('same-mesh comparison required: ' + key)
    c, f = coarse['trace'], fine['trace']
    if len(c) < n + 1 or (len(c) - 1) % n:
        raise ValueError('incomplete coarse phases')
    phases = (len(c) - 1) // n
    if len(f) != (len(c) - 1) * ratio + 1:
        raise ValueError('incomplete fine trace')
    if len(coarse['checkpoints']) != phases+1 or len(fine['checkpoints']) != phases+1:
        raise ValueError('incomplete checkpoint/drive inventory')
    for old, new in zip(coarse['checkpoints'], fine['checkpoints']):
        skip = {'result', 'previous', 'dt_s'}
        config_old = {key:value for key,value in old.items() if key not in skip}
        config_new = {key:value for key,value in new.items() if key not in skip}
        if not _same_configuration(config_old, config_new):
            raise ValueError('physical configuration or phase drive differs')
    dt = phase_s / n
    for trace, count, step_dt in ((c, n, dt), (f, nf, phase_s / nf)):
        if trace[0]['time_s'] != 0:
            raise ValueError('trace must start at zero')
        for i, state in enumerate(trace[1:], 1):
            t = state['time_s']
            if (not np.isfinite(t) or state['dt_s'] != step_dt or
                    state['phase'] != (i - 1) // count + 1 or
                    t != trace[i - 1]['time_s'] + step_dt):
                raise ValueError('invalid accepted-step time/phase/dt')
        if abs(trace[-1]['time_s'] - phases * phase_s) > atol:
            raise ValueError('incomplete physical duration')
    ct = np.asarray([row['time_s'] for row in c[1:]])
    ft = np.asarray([row['time_s'] for row in f[ratio::ratio]])
    if not np.all(abs(ct - ft) <= atol):
        raise ValueError('common observation times differ')
    state_units = {'sheet_charge_C': 'C', 'trap_charge_C': 'C',
                   'untrapped_sheet_charge_C': 'C', 'contact_charge_C': 'C',
                   'sheet_contact_charge_C': 'C', 'dielectric_contact_charge_C': 'C',
                   'gates': 'C', 'dielectric_energy_J': 'J'}
    rate_keys = ('conduction', 'total', 'trap_charge_rate_A', 'free_carrier_charge_rate_A')
    states, intervals, ending_conduction, cumulative = {}, {}, {}, {}
    for category, unit in state_units.items():
        cv = [_flatten(row[category], category) for row in c[1:]]
        fv = [_flatten(row[category], category) for row in f[ratio::ratio]]
        keys = set(cv[0])
        if any(set(row) != keys for row in cv + fv):
            raise ValueError('inconsistent state terminals: ' + category)
        for key in sorted(keys):
            old = np.asarray([row[key] for row in cv]); new = np.asarray([row[key] for row in fv])
            states[key] = dict(unit=unit, **_metric(new-old, old, new, scales[unit], ct, n))
    for category in rate_keys:
        cv = [_flatten(row[category], category) for row in c[1:]]
        fv = [_flatten(row[category], category) for row in f[1:]]
        keys = set(cv[0])
        if any(set(row) != keys for row in cv + fv):
            raise ValueError('inconsistent current/rate terminals: ' + category)
        for key in sorted(keys):
            old = np.asarray([row[key] for row in cv])
            raw = np.asarray([row[key] for row in fv])
            grouped = raw.reshape(-1, ratio).mean(axis=1)
            intervals[key] = dict(unit='A', **_metric(grouped-old, old, grouped, scales['A'], ct, n))
            ci = np.cumsum(old * dt); fi = np.cumsum(grouped * dt)
            cumulative[key] = dict(unit='C', coarse_final_C=float(ci[-1]), fine_final_C=float(fi[-1]),
                final_signed_difference_C=float(fi[-1]-ci[-1]),
                **_metric(fi-ci, ci, fi, scales['C'], ct, n))
            if category == 'conduction':
                ending = raw[ratio-1::ratio]
                ending_conduction[key] = dict(unit='A', **_metric(ending-old, old, ending, scales['A'], ct, n))
    return dict(status='descriptive_common_time_and_interval_BE_comparison',
                phases=phases,coarse_steps=len(c)-1,fine_steps=len(f)-1,
                refinement_ratio=ratio,coarse_dt_s=dt,fine_dt_s=phase_s/nf,
                max_common_time_difference_s=float(np.max(abs(ct-ft))),
                normalization=dict(charge_scale_C=scales['C'],energy_scale_J=scales['J'],current_scale_A=scales['A']),
                state_at_common_times=states,interval_average_currents_and_rates=intervals,
                conduction_at_common_ending_times=ending_conduction,cumulative_current_and_rate_integrals=cumulative,
                temporal_convergence_order_established=False,physical_device_qualified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('coarse', type=Path, help='Coarse JSON/NPZ output stem')
    p.add_argument('fine', type=Path, help='Fine JSON/NPZ output stem')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = compare_traces(load_record(args.coarse), load_record(args.fine))
    result['input_sha256'] = {str(Path(str(stem)+'.'+ext)):hashlib.sha256(Path(str(stem)+'.'+ext).read_bytes()).hexdigest()
                              for stem in (args.coarse,args.fine) for ext in ('json','npz')}
    text = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output is not None:
        args.output.write_text(text,encoding='utf-8')
    else:
        print(text,end='')


if __name__ == '__main__':
    main()
