"""Actual compiler PORT/DEVICE equivalence, complete waves and checkpoint replay.

--baseline optionally checks whole emitted C++ against a frozen older compiler.
Frozen VCS results below describe the equivalent IC/IOPATH fixtures, not fresh
PORT/DEVICE vendor runs. Native-only comparison alone cannot prove SDF policy.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

from cases import make, wrap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_waveforms import compare
from run_flow import physical_bits
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, bit_timeline

parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path)
parser.add_argument('out', type=Path)
parser.add_argument('--baseline', type=Path)
parser.add_argument('--case', action='append')
parser.add_argument('--sanitize', action='store_true')
args = parser.parse_args()
compiler = args.compiler.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
baseline_compiler = args.baseline.resolve() if args.baseline else compiler
config = {line.split('=', 1)[0].split(':', 1)[0]: line.split('=', 1)[1]
          for line in (compiler.parent / 'CMakeCache.txt').read_text().splitlines()
          if '=' in line and not line.startswith('//')}
ic_oracle = json.loads((ROOT / 'tests/sdf_interconnect/expected.json').read_text())['cases']
path_oracle = json.loads((ROOT / 'tests/sdf_runtime/expected.json').read_text())
policy_oracle = json.loads((ROOT / 'tests/sdf_port_device/policy_expected.json').read_text())['cases']
cases = make(out / 'inputs')
report = dict(status='RUNNING', cases={}, native_captures=0, replay_captures=0,
              baseline_compiler=str(baseline_compiler),
              baseline_sha256=hashlib.sha256(baseline_compiler.read_bytes()).hexdigest(),
              fresh_port_device_vcs=False, sanitizer=args.sanitize)


def save():
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')


def run(command, work, label, success=True):
    command = list(map(str, command))
    (work / (label + '.command.json')).write_text(json.dumps(command, indent=2) + '\n')
    result = subprocess.run(command, cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(result.stdout)
    (work / (label + '.stderr')).write_text(result.stderr)
    assert (result.returncode == 0) == success, (label, result.returncode, result.stdout, result.stderr)
    assert not any(s in result.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
    return result.stdout, result.stderr


def arguments(source, sdf, corner='typ'):
    tb = (source / 'tb.v').read_text()
    # XMR monitors are unsupported in native RTL; physical receiving pins are
    # still checked independently in the waveform dictionary below.
    if 'd.fast.A' in tb:
        tb = '\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
                       if line.startswith('always @') else line for line in tb.splitlines()) + '\n'
    (source / 'native-tb.v').write_text(tb)
    return ['--gate-netlist', source / 'net.v', '--gate-top', 'dut', '--liberty', source / 'cells.lib',
            '--gate-models', source / 'cells.v', '--sdf-annotate', source / sdf,
            '--sdf-corner', corner, source / 'native-tb.v']


def check_oracle(meta, wave, result):
    oracle = meta.get('oracle', '')
    bits = bit_timeline(*read(wave)); checked = 0
    if oracle.startswith('interconnect-'):
        expected = {tuple(r['path']) + (r['bit'],): r['changes']
                    for r in ic_oracle[meta['source']]['bits']}
        keys = [('top', pin, None) for pin in ['x', 'y']]
        keys += [k for k in bits if len(k) >= 5 and k[-2] == 'A']
        for key in keys:
            assert json.loads(json.dumps(bits[key])) == expected[key], (oracle, key, bits[key], expected[key])
            checked += 1
    elif oracle.startswith('path-'):
        expected = path_oracle[meta['source']]
        assert result[0].splitlines() == expected['trace'], (oracle, result[0], expected['trace'])
        for pin, changes in expected['pins'].items():
            assert json.loads(json.dumps(bits[('top', pin, None)])) == changes, (oracle, pin)
            checked += 1
    return checked


backends = {'generic': [], 'scalar': ['--gate-scalar-timing'],
            'jobs': ['--gate-scalar-timing', '--gate-sdf-jobs'],
            'jobs-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel']}
try:
    save()
    for name, meta in cases.items():
        if args.case and name not in args.case:
            continue
        source = out / 'inputs' / name; work = out / name; work.mkdir(exist_ok=True)
        entry = dict(status='RUNNING', configurations={}, metadata=meta)
        report['cases'][name] = entry
        for corner in meta.get('corners', ['typ']):
            baseline_result = None
            for backend, flags in backends.items():
                label = backend + '-' + corner
                candidate = work / (label + '.cpp'); equivalent = work / (label + '-equivalent.cpp')
                run([baseline_compiler, *arguments(source, 'equivalent.sdf', corner), *flags,
                     '--wave-support', '--emit-only', '--emit-cpp', equivalent], work, label + '-control-emit')
                run([compiler, *arguments(source, 'delay.sdf', corner), *flags,
                     '--wave-support', '--emit-cpp', candidate, '--emit-ir', work / (label + '.json'),
                     '-o', work / label], work, label + '-compile')
                assert candidate.read_bytes() == equivalent.read_bytes(), (name, label, 'whole generated CPP')
                ir = json.loads((work / (label + '.json')).read_text())['gate_design']
                if name.startswith('port-') or name.startswith('mixed-'):
                    assert ir['port_delay_pins'] > 0 and ir['port_delay_updates'] > 0
                if name.startswith('device-') or name.startswith('update-') or name == 'port-and-device':
                    assert ir['device_delay_updates'] > 0
                result = run([work / label], work, label + '-none')
                if baseline_result is None:
                    baseline_result = result
                assert result == baseline_result, (name, label, 'full stdout/stderr')
                checked = 0
                for mode in ['ordered', 'settled']:
                    for codec, extension in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                        capture = label + '-' + mode + '-' + codec
                        wave = work / (capture + '.' + extension); wave.unlink(missing_ok=True)
                        command = [work / label, '--waveform', wave, '--wave-format', extension,
                                   '--wave-mode', mode, '--wave-block-events', '7']
                        if codec != 'vcd':
                            command += ['--wave-codec', codec]
                        assert run(command, work, capture) == baseline_result
                        reference = work / ('generic-' + corner + '-' + mode + '-vcd.vcd')
                        compare(reference, wave)
                        if mode == 'ordered' and codec == 'vcd':
                            checked = check_oracle(meta, wave, result)
                            if name in policy_oracle:
                                expected = policy_oracle[name]
                                for filename, identity in expected['source_sha256'].items():
                                    assert hashlib.sha256((source / filename).read_bytes()).hexdigest() == identity
                                assert re.sub(r'\s+', '', (source / 'delay.sdf').read_text()) == expected['sdf_without_whitespace']
                                observed = physical_bits(wave)
                                for bit in expected['bits']:
                                    key = tuple(bit['path']) + (bit['bit'],)
                                    assert json.loads(json.dumps(observed[key])) == bit['changes'], (name, label, key)
                                    checked += 1
                        report['native_captures'] += 1
                entry['configurations'][label] = dict(status='PASS', whole_cpp_equal=True,
                    cpp_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(), oracle_signals=checked)
            print('PASS PORT/DEVICE generated code, four backends and six complete wave streams', name, corner, flush=True)
        entry['status'] = 'PASS'; save()
    # Actual emitted-program replay with pending input/path events. A rejected
    # prediction corrupts both four-state values and path history before restore.
    for name in ['port-and-device', 'device-condition-edge', 'device-flop-all']:
        if name not in report['cases']:
            continue
        work = out / name
        for backend in ['generic', 'jobs-wheel']:
            label = backend + '-typ'; code = (work / (label + '.cpp')).read_text()
            assert code.count('\ns.run();\n') == 1
            control = '''
s.run_until(101);
auto accepted=s.predict_until(125,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i){const auto& signal=probe.signals[i];if(!signal.net)probe.set(int(i),V::x(signal.value.w));}
 probe.run_until(102);
 for(size_t i=0;i<probe.signals.size();++i){const auto& signal=probe.signals[i];if(!signal.net)probe.set(int(i),V(0,0,signal.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing PORT/DEVICE rollback");
if(!s.predict_until(150,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing PORT/DEVICE commit");
s.run();
'''
            variants = [('boundary', '\ns.run_until(101);s.run_until(125);s.run_until(150);s.run();\n'), ('replay', control)]
            for variant, body in variants:
                target = label + '-' + variant
                (work / (target + '.cpp')).write_text(code.replace('\ns.run();\n', body))
                options = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitize else ['-O2']
                run(['c++', '-std=c++17', *options, '-I' + config['DSIM_ZSTD_INCLUDE'],
                     work / (target + '.cpp'), config['DSIM_ZSTD_LIBRARY'], '-o', work / target], work, target + '-compile')
                expected = ((work / (label + '-none.stdout')).read_text(), (work / (label + '-none.stderr')).read_text())
                for mode in ['ordered', 'settled']:
                    wave = work / (target + '-' + mode + '.dwf'); wave.unlink(missing_ok=True)
                    assert run([work / target, '--waveform', wave, '--wave-mode', mode,
                                '--wave-codec', 'zstd', '--wave-block-events', '7'], work, target + '-' + mode) == expected
                    compare(work / (label + '-boundary-' + mode + '.dwf'), wave)
                    # run_until creates observable horizon markers; boundary and
                    # replay must match each other, not the unsplit time stream.
                    report['replay_captures'] += 1
            save()
    strict = out / 'strict'; strict.mkdir(exist_ok=True)
    source = out / 'inputs/port-fanout'
    protected = strict / 'protected.cpp'; ir = strict / 'protected.json'
    protected.write_text('keep-cpp'); ir.write_text('keep-ir')
    rejections = [
        ('scope-port', wrap('(ABSOLUTE(PORT a (7)))', '', 'dut'), 'leaf receiving input pin'),
        ('scope-device', wrap('(ABSOLUTE(DEVICE x (7)))', '', 'dut'), 'leaf output pin'),
        ('sparse-port', wrap('(ABSOLUTE(PORT fast/A ()(7)))', '', 'dut'), 'sparse two-value PORT'),
    ]
    for name, sdf, message in rejections:
        (source / 'strict.sdf').write_text(sdf)
        _, error = run([compiler, *arguments(source, 'strict.sdf'), '--emit-only',
                        '--emit-cpp', protected, '--emit-ir', ir], strict, name, False)
        assert message in error, (name, error)
        assert protected.read_text() == 'keep-cpp' and ir.read_text() == 'keep-ir'
    report.update(status='PASS', strict_rejections=len(rejections))
finally:
    save()
