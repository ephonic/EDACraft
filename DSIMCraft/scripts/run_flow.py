#!/usr/bin/env python3
"""Compile/run RTL, gates or SDF, verify VCD/DWF, optionally compare with VCS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, bit_timeline
from compare_waveforms import compare as compare_ordered_waveforms


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def measure(command, work, label, timeout, record):
    """Measure each process tree separately; preserve logs and failed stages."""
    command = list(map(str, command))
    row = dict(command=command, status='RUNNING')
    record[label] = row
    metrics = work / (label + '.time')
    mac = sys.platform == 'darwin'
    timed = ['/usr/bin/time', '-l'] if mac else ['/usr/bin/time', '-v', '-o', str(metrics)]
    start = time.perf_counter()
    with (work / (label + '.log')).open('w') as out, (work / (label + '.stderr')).open('w') as err:
        p = subprocess.Popen(timed + command, cwd=work, stdout=out, stderr=err, start_new_session=True)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
            row.update(status='TIMEOUT', wall_seconds=time.perf_counter() - start)
            raise RuntimeError(f'{label}: timeout after {timeout}s; process group terminated')
    row.update(returncode=p.returncode, wall_seconds=time.perf_counter() - start)
    text = (work / (label + '.stderr')).read_text() if mac else metrics.read_text()
    if mac:
        cpu = re.search(r'([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys', text)
        rss = re.search(r'(\d+)\s+maximum resident set size', text)
        if cpu:
            row.update(user_seconds=float(cpu[2]), system_seconds=float(cpu[3]))
    else:
        user = re.search(r'User time \(seconds\): ([\d.]+)', text)
        system = re.search(r'System time \(seconds\): ([\d.]+)', text)
        rss = re.search(r'Maximum resident set size \(kbytes\): (\d+)', text)
        if user and system:
            row.update(user_seconds=float(user[1]), system_seconds=float(system[1]))
    if 'user_seconds' in row:
        row['cpu_seconds'] = row['user_seconds'] + row['system_seconds']
    row['peak_rss_kb'] = int(rss[1]) / (1024 if mac else 1) if rss else None
    row['status'] = 'PASS' if p.returncode == 0 else 'FAIL'
    if p.returncode:
        diagnostic = (work / (label + '.stderr')).read_text().strip()
        if not diagnostic:
            diagnostic = (work / (label + '.log')).read_text().strip()
        row['diagnostic'] = diagnostic[:4000]
        raise RuntimeError(f'{label}: exit {p.returncode}: {diagnostic[:1600]}; see {work / (label + ".stderr")} and .log')
    return (work / (label + '.log')).read_text()


def physical_tick(meta):
    scale = [t for t in meta['header'] if t[0] == '$timescale']
    if len(scale) != 1:
        raise ValueError('waveform requires exactly one timescale')
    match = re.fullmatch(r'(1|10|100)(s|ms|us|ns|ps|fs)', ''.join(scale[0][1:-1]))
    if not match:
        raise ValueError(f'unsupported waveform timescale {scale}')
    return int(match[1]) * dict(s=10**15, ms=10**12, us=10**9, ns=10**6, ps=1000, fs=1)[match[2]]


def physical_bits(path, window=None):
    meta, events = read(path)
    tick = physical_tick(meta)
    result = {key: [(t * tick, value) for t, value in changes]
              for key, changes in bit_timeline(meta, events).items()}
    if window is not None:
        start, end = window
        last = max((event[0] * tick for event in events), default=-1)
        for key, changes in result.items():
            selected = []
            if start <= last:
                before = [value for time, value in changes if time < start]
                if before:
                    selected.append((start, before[-1]))
                for time, value in changes:
                    if start <= time <= end:
                        if selected and selected[-1][0] == time:
                            selected[-1] = (time, value)
                        elif not selected or selected[-1][1] != value:
                            selected.append((time, value))
            result[key] = selected
    return result


def run_case(config, base, work, compiler, use_vcs, timeout, row):
    selection = []
    for key, option in [('wave_scopes', '--wave-scope'), ('wave_include', '--wave-include'),
                        ('wave_exclude', '--wave-exclude')]:
        if key in config:
            selectors = config[key]
            if (not isinstance(selectors, list) or not selectors or
                    any(not isinstance(s, str) or not s or '\0' in s for s in selectors)):
                raise ValueError(f'{key} must be a nonempty list of nonempty strings without NUL')
            for value in selectors:
                selection += [option, value]
    for key, maximum in [('wave_depth', 10000), ('wave_start', 2**64-1), ('wave_end', 2**64-1)]:
        if key in config:
            value = config[key]
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(f'{key} must be an integer in 0..{maximum}')
            selection += ['--' + key.replace('_', '-'), value]
    if config.get('wave_start', 0) > config.get('wave_end', 2**64-1):
        raise ValueError('wave_start must not exceed wave_end')
    if selection:
        row['wave_selection'] = {k: config[k] for k in
            ['wave_scopes', 'wave_include', 'wave_exclude', 'wave_depth', 'wave_start', 'wave_end'] if k in config}
    # These controls apply only to the DWF run. Passing them through run_args
    # would also affect the no-wave and VCD runs and can reject those modes.
    wave_controls = {}
    for key, maximum in [('wave_compression_jobs', 16), ('wave_block_events', 1000000)]:
        if key in config:
            value = config[key]
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f'{key} must be an integer in 1..{maximum}')
            wave_controls[key] = value
    if 'wave_async' in config:
        if type(config['wave_async']) is not bool:
            raise ValueError('wave_async must be a boolean')
        if config['wave_async']:
            if wave_controls.get('wave_compression_jobs',1)!=1:
                raise ValueError('wave_async requires exactly one compression job')
            wave_controls['wave_async']=True
    if 'wave_buffer_bytes' in config:
        value=config['wave_buffer_bytes']
        if type(value) is not int or not 1024<=value<=67108864:
            raise ValueError('wave_buffer_bytes must be an integer in 1024..67108864')
        if not wave_controls.get('wave_async'):
            raise ValueError('wave_buffer_bytes requires wave_async')
        wave_controls['wave_buffer_bytes']=value
    if wave_controls:
        row['wave_controls'] = wave_controls

    def path(value):
        p = (base / value).resolve()
        if not p.is_file():
            raise ValueError(f'missing input: {p}')
        return p

    sources = [path(p) for p in config['sources']]
    if not sources:
        raise ValueError('sources must contain an RTL testbench/design')
    top = config.get('top', 'top')
    native = work / 'native'
    command = [compiler, '--top', top, '--wave-support', '--emit-ir', work / 'ir.json']
    inputs = list(sources)
    models = []
    prepared = None
    if 'prepare_sdf_models' in config and type(config['prepare_sdf_models']) is not bool:
        raise ValueError('prepare_sdf_models must be a boolean')
    if config.get('prepare_sdf_models') and 'sdf' not in config:
        raise ValueError('prepare_sdf_models requires sdf')
    if 'partition_report' in config:
        count = config['partition_report']
        if type(count) is not int or not 1 <= count <= 65536:
            raise ValueError('partition_report must be an integer in 1..65536')
        if 'gate_netlist' not in config:
            raise ValueError('partition_report requires gate_netlist')
        command += ['--gate-partition-report', count]
    if 'gate_netlist' in config:
        net = path(config['gate_netlist'])
        command += ['--gate-netlist', net, '--gate-top', config['gate_top']]
        inputs.append(net)
        for lib in config['liberty']:
            lib = path(lib)
            command += ['--liberty', lib]
            inputs.append(lib)
    if 'sdf' in config:
        if 'gate_netlist' not in config:
            raise ValueError('sdf requires gate_netlist, gate_top, liberty and gate_models')
        for model in config['gate_models']:
            model = path(model)
            models.append(model)
            inputs.append(model)
        sdf = path(config['sdf'])
        command += ['--sdf-annotate', sdf, '--sdf-corner', config.get('corner', 'typ')]
        inputs.append(sdf)
        if config.get('disable_timingchecks', False):
            command += ['--no-timingchecks']
    row.update(kind='sdf' if 'sdf' in config else 'gate' if 'gate_netlist' in config else 'rtl',
               inputs_sha256={str(p): sha(p) for p in inputs}, stages={})
    stages = row['stages']
    if config.get('prepare_sdf_models'):
        generator = compiler.with_name('dsim_sdf_models')
        prepared = work / 'prepared-models.v'
        prepare = [generator, '--sdf', sdf, '-o', prepared, '--report', work / 'model-coverage.json']
        for model in models:
            prepare += ['--models', model]
        for lib in config['liberty']:
            prepare += ['--liberty', path(lib)]
        measure(prepare, work, 'model-prepare', timeout, stages)
        row['model_preparation'] = dict(generator_sha256=sha(generator), prepared_sha256=sha(prepared),
                                        coverage=json.loads((work / 'model-coverage.json').read_text()))
    for model in ([prepared] if prepared else models):
        command += ['--gate-models', model]
    command += config.get('dsim_args', []) + sources + ['-o', native]
    measure(command, work, 'native-compile', timeout, stages)
    elaboration = json.loads((work / 'ir.json').read_text())
    analysis = elaboration.get('gate_design', {}).get('partition_analysis')
    if 'partition_report' in config and analysis is None:
        raise AssertionError('compiler IR is missing the requested partition analysis')
    if analysis is not None:
        row['partition_analysis'] = analysis
    row['native_sha256'] = sha(native)
    trace_prefix = config.get('trace_prefix', 'TRACE ')

    def trace(text):
        return [line for line in text.splitlines() if line.startswith(trace_prefix)]

    baseline = None
    for mode in ['none', 'vcd', 'dwf']:
        run = [native] + config.get('run_args', [])
        if mode != 'none':
            run += ['--waveform', work / ('native.' + mode), '--wave-format', mode, '--wave-mode', 'settled']
            run += selection
        if mode == 'dwf':
            for key, value in wave_controls.items():
                run += ['--' + key.replace('_', '-')] if key=='wave_async' else ['--' + key.replace('_', '-'), value]
        current = trace(measure(run, work, 'native-' + mode, timeout, stages))
        if not current:
            raise AssertionError(f'no {trace_prefix!r} trace; choose a trace_prefix or add a monitor')
        if baseline is None:
            baseline = current
        if current != baseline:
            raise AssertionError(f'native {mode} trace differs from no-wave run')
    if 'expected_trace' in config and baseline != config['expected_trace']:
        raise AssertionError('native trace differs from expected_trace')
    row['trace'] = baseline
    row['native_wave_comparison'] = compare_ordered_waveforms(work / 'native.vcd', work / 'native.dwf')
    row['waves'] = {fmt: dict(bytes=(work / ('native.' + fmt)).stat().st_size,
                              sha256=sha(work / ('native.' + fmt))) for fmt in ['vcd', 'dwf']}
    row['vcs_comparison'] = 'NOT_REQUESTED'
    if not use_vcs:
        return
    vcs = config['vcs']
    vcs_sources = [path(p) for p in vcs['sources']]
    if prepared:
        if not set(models).issubset(vcs_sources):
            raise ValueError('prepared VCS sources must contain every original gate_models file')
        vcs_sources = [p for p in vcs_sources if p not in models] + [prepared]
    row['vcs_inputs_sha256'] = {str(p): sha(p) for p in vcs_sources}
    # Scope names are emitted as Verilog identifiers; paths use JSON string escaping.
    scope = vcs.get('dump_scope', top)
    instance = vcs.get('sdf_instance', '')
    for name in [top, scope] + ([instance] if 'sdf' in config else []):
        if not re.fullmatch(r'[a-zA-Z_][\w$]*(?:\.[a-zA-Z_][\w$]*)*', name):
            raise ValueError(f'capture scope requires simple hierarchical identifiers: {name!r}')
    annotate = ''
    if 'sdf' in config:
        corner = dict(min='MINIMUM', typ='TYPICAL', max='MAXIMUM')[config.get('corner', 'typ')]
        annotate = f'$sdf_annotate({json.dumps(str(sdf))},{instance},,"annotation.log","{corner}");'
    capture = work / 'capture.v'
    capture.write_text('module dsim_flow_capture; initial begin ' + annotate +
                       f'$dumpfile("vcs.vcd");$dumpvars(0,{scope});end endmodule\n')
    executable = work / 'vcs_simv'
    args = ['vcs', '-full64', '-sverilog', '-top', top, '-top', 'dsim_flow_capture']
    args += vcs.get('compile_args', [])
    if config.get('disable_timingchecks', False):
        args += ['+notimingcheck']
    measure(args + vcs_sources + [capture, '-o', executable], work, 'vcs-compile', timeout, stages)
    reference = trace(measure([executable] + vcs.get('run_args', []), work, 'vcs-run', timeout, stages))
    if 'sdf' in config:
        annotation = (work / 'annotation.log').read_text()
        counts = {name: re.search(r'Total ' + name + r':\s*(\d+)', annotation)
                  for name in ['errors', 'warnings']}
        if not all(counts.values()):
            raise AssertionError('VCS SDF annotation summary is missing')
        row['vcs_annotation'] = {name: int(match[1]) for name, match in counts.items()}
        if any(row['vcs_annotation'].values()):
            raise AssertionError('VCS SDF annotation reported errors/warnings; see annotation.log')
    if reference != baseline:
        raise AssertionError('VCS/native TRACE differs; see native-none.log and vcs-run.log')
    window = None
    if 'wave_start' in config or 'wave_end' in config:
        tick = physical_tick(read(work / 'native.dwf')[0])
        window = (config.get('wave_start', 0) * tick, config.get('wave_end', 2**64-1) * tick)
    native_bits, vcs_bits = physical_bits(work / 'native.dwf'), physical_bits(work / 'vcs.vcd', window)
    keys = [tuple(key) for key in config.get('wave_bits', [])]
    if not keys:
        keys = list(native_bits) if selection else [key for key in native_bits if len(key) == 3 and key[0] == top]
    if not keys:
        raise AssertionError('no waveform bits selected for VCS comparison')
    for key in keys:
        if key not in native_bits or key not in vcs_bits or native_bits[key] != vcs_bits[key]:
            raise AssertionError(f'VCS/native settled bit differs or is missing: {key}')
    row.update(vcs_comparison='PASS', compared_wave_bits=len(keys), vcs_sha256=sha(executable))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--dsim', type=Path, default=ROOT / 'build/dsim')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/flow')
    parser.add_argument('--vcs', action='store_true')
    parser.add_argument('--case', action='append')
    parser.add_argument('--timeout', type=float, default=600)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    manifest = args.manifest.resolve()
    config = json.loads(manifest.read_text())
    cases = config['cases']
    if not cases or len({c['name'] for c in cases}) != len(cases):
        parser.error('cases must be nonempty and have unique names')
    if args.case and set(args.case) - {c['name'] for c in cases}:
        parser.error('unknown --case')
    args.output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=args.output.resolve()))
    (work / 'manifest.json').write_bytes(manifest.read_bytes())
    report = dict(schema='dsim.flow.v1', status='RUNNING', directory=str(work),
                  host=platform.node(), platform=platform.platform(), manifest_sha256=sha(manifest),
                  runner_sha256=sha(__file__),
                  compiler_sha256=sha(args.dsim), cases={},
                  note='One run per mode; stage CPU/wall/RSS and wave sizes are observations, not a performance acceptance benchmark. VCS checks selected settled bits on physical time; native VCD/DWF checks complete decoded streams. Trace-only checks cannot establish full equivalence.')
    def save():
        (work / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    failed = False
    for case in cases:
        name = case['name']
        if args.case and name not in args.case:
            continue
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
            parser.error('case names may contain letters, digits, underscores and hyphens')
        w = work / name
        w.mkdir()
        row = dict(status='RUNNING')
        report['cases'][name] = row
        save()
        try:
            run_case(case, manifest.parent, w, args.dsim.resolve(), args.vcs, args.timeout, row)
            row['status'] = 'PASS'
        except Exception as exc:
            row.update(status='FAIL', error=str(exc))
            failed = True
        save()
        print(row['status'], name, row.get('error', ''), flush=True)
    report['status'] = 'FAIL' if failed else 'PASS'
    save()
    print('Report:', work / 'results.json', flush=True)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
