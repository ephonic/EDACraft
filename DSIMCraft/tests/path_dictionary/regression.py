"""Actual CLI path dictionary: old code identity, full streams and FIFO budgets."""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
from tables import expand

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_waveforms import compare

parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path); parser.add_argument('out', type=Path)
parser.add_argument('--baseline', type=Path); parser.add_argument('--case', action='append')
args = parser.parse_args(); compiler = args.compiler.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
baseline_compiler = args.baseline.resolve() if args.baseline else compiler


def fixtures(name, source, dest):
    spec = importlib.util.spec_from_file_location(name, ROOT / source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.make(dest)


fixtures('dictionary_paths', 'tests/sdf_runtime/cases.py', out / 'inputs/path')
conditions = fixtures('dictionary_conditions', 'tests/sdf_conditional/cases.py', out / 'inputs/condition')
fixtures('dictionary_checks', 'tests/timing_checks/cases.py', out / 'inputs/checks')
fixtures('dictionary_port_device', 'tests/sdf_port_device/cases.py', out / 'inputs/port-device')
cases = {name: out / 'inputs/path' / name for name in ['twelve', 'latest', 'multiple', 'ff', 'full']}
cases.update({'condition-' + name: out / 'inputs/condition' / name for name in ['edge', 'output-state']})
cases['checks-composed'] = out / 'inputs/checks/composed'
cases['port-and-device'] = out / 'inputs/port-device/port-and-device'
backends = {'generic': [], 'scalar': ['--gate-scalar-timing'],
            'jobs': ['--gate-scalar-timing', '--gate-sdf-jobs'],
            'jobs-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel']}
report = dict(status='RUNNING', cases={}, captures=0, default_enabled=False, baseline_compiler=str(baseline_compiler))


def save():
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')


def run(command, work, label, success=True):
    command = list(map(str, command))
    (work / (label + '.command.json')).write_text(json.dumps(command, indent=2) + '\n')
    r = subprocess.run(command, cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    (work / (label + '.exit')).write_text(str(r.returncode) + '\n')
    if success is not None:
        assert (r.returncode == 0) == success, (label, r.returncode, r.stdout, r.stderr)
    assert not any(s in r.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
    return r.returncode, r.stdout, r.stderr


def arguments(source):
    tb = (source / 'tb.v').read_text()
    if 'd.fast.A' in tb:
        tb = '\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
                       if line.startswith('always @') else line for line in tb.splitlines()) + '\n'
    (source / 'native-tb.v').write_text(tb)
    return ['--gate-netlist', source / 'net.v', '--gate-top', 'dut', '--liberty', source / 'cells.lib',
            '--gate-models', source / 'cells.v', '--sdf-annotate', source / 'delay.sdf', source / 'native-tb.v']


try:
    save()
    for name, source in cases.items():
        if args.case and name not in args.case:
            continue
        work = out / name; work.mkdir(exist_ok=True); base_result = None
        row = dict(status='RUNNING', configurations={}); report['cases'][name] = row
        for backend, flags in backends.items():
            run([baseline_compiler, *arguments(source), *flags, '--wave-support', '--emit-only',
                 '--emit-cpp', work / (backend + '-control.cpp')], work, backend + '-control-emit')
            for dictionary in [False, True]:
                label = backend + ('-dictionary' if dictionary else '-baseline')
                options = ['--gate-path-dictionary'] if dictionary else []
                run([compiler, *arguments(source), *flags, *options, '--wave-support', '--emit-cpp',
                     work / (label + '.cpp'), '--emit-ir', work / (label + '.json'), '-o', work / label], work, label + '-compile')
                cpp = (work / (label + '.cpp')).read_text()
                if dictionary:
                    expanded, stats = expand(cpp)
                    assert expanded == (work / (backend + '-control.cpp')).read_text(), (name, backend, 'restored whole CPP')
                else:
                    assert cpp == (work / (backend + '-control.cpp')).read_text(), (name, backend, 'default whole CPP')
                    stats = {}
                ir = json.loads((work / (label + '.json')).read_text())
                assert ir['gate_design'].get('path_delay_dictionary', False) == dictionary
                result = run([work / label], work, label + '-none')
                if base_result is None:
                    base_result = result
                assert result == base_result, (name, label, 'full streams')
                if name.startswith('condition-'):
                    assert result[1].splitlines() == conditions[name.removeprefix('condition-')]['expected']
                for mode in ['ordered', 'settled']:
                    for codec, extension in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                        capture = label + '-' + mode + '-' + codec
                        wave = work / (capture + '.' + extension); wave.unlink(missing_ok=True)
                        command = [work / label, '--waveform', wave, '--wave-format', extension,
                                   '--wave-mode', mode, '--wave-block-events', '7']
                        if codec != 'vcd': command += ['--wave-codec', codec]
                        assert run(command, work, capture) == base_result
                        compare(work / ('generic-baseline-' + mode + '-vcd.vcd'), wave)
                        report['captures'] += 1
                for budget in [1, 5, 15]:
                    r = run([work / label, '--max-events', str(budget)], work, label + '-budget-' + str(budget), None)
                    baseline_label = backend + '-baseline-budget-' + str(budget)
                    assert r[1] == (work / (baseline_label + '.stdout')).read_text()
                    assert r[2] == (work / (baseline_label + '.stderr')).read_text()
                    assert r[0] == int((work / (baseline_label + '.exit')).read_text())
                    if budget == 1: assert r[0] != 0
                row['configurations'][label] = dict(status='PASS', table_stats=stats)
            # IR may differ only in this explicit optional feature field.
            def semantic_ir(label):
                data = json.loads((work / (label + '.json')).read_text())
                elapsed = {('gate_design', 'parse_seconds'), ('gate_design', 'bind_seconds'),
                           ('gate_design', 'gate_preprocessing', 'seconds')}
                def scrub(value, path=()):
                    if isinstance(value, dict):
                        return {k: scrub(v, path + (k,)) for k, v in value.items()
                                if path + (k,) not in elapsed | {('gate_design', 'path_delay_dictionary')}}
                    return [scrub(v, path + (str(i),)) for i, v in enumerate(value)] if isinstance(value, list) else value
                return scrub(data)
            assert semantic_ir(backend + '-baseline') == semantic_ir(backend + '-dictionary'), (name, backend, 'IR')
        row['status'] = 'PASS'; save()
        print('PASS actual dictionary/default, whole CPP, full streams and FIFO budgets', name, flush=True)
    strict = out / 'strict'; strict.mkdir(exist_ok=True)
    cpp = strict / 'protected.cpp'; ir = strict / 'protected.json'; cpp.write_text('keep-cpp'); ir.write_text('keep-ir')
    _, _, error = run([compiler, '--gate-path-dictionary', '--emit-only', '--emit-cpp', cpp,
                       '--emit-ir', ir], strict, 'missing-sdf', False)
    assert '--gate-path-dictionary requires SDF-annotated gate simulation' in error
    assert cpp.read_text() == 'keep-cpp' and ir.read_text() == 'keep-ir'
    report['status'] = 'PASS'
finally:
    save()
