"""Exercise actual native compilation against original VCS wildcard results."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from cases import make

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from compare_waveforms import compare
from run_flow import physical_bits
parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path); parser.add_argument('output', type=Path)
parser.add_argument('--baseline', type=Path); parser.add_argument('--case', action='append')
args = parser.parse_args(); compiler = args.compiler.resolve()
base = args.output.resolve(); base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))
cases = make(out / 'inputs')
golden = json.loads((Path(__file__).parent / 'expected.json').read_text())['cases']
backends = {'generic': [], 'jobs-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel'],
            'dictionary-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel', '--gate-path-dictionary']}
report = dict(status='RUNNING', directory=str(out), cases={}, captures=0, vendor_signal_comparisons=0,
              old_cpp_comparisons=0, compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest())


def save():
    for p in [out / 'results.json', base / 'results.json']: p.write_text(json.dumps(report, indent=2) + '\n')


def run(cmd, work, label):
    cmd = list(map(str, cmd)); (work / (label + '.command.json')).write_text(json.dumps(cmd) + '\n')
    result = subprocess.run(cmd, cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(result.stdout); (work / (label + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, (label, result.returncode, result.stderr)
    return result.stdout, result.stderr


try:
    save()
    for name, meta in cases.items():
        if args.case and name not in args.case: continue
        source = out / 'inputs' / name; oracle = golden[name]
        for f, value in oracle['sources'].items(): assert hashlib.sha256((source / f).read_bytes()).hexdigest() == value, (name, f)
        work = out / name; work.mkdir(); row = dict(status='RUNNING', backends={}); report['cases'][name] = row
        common = ['--gate-netlist', source / 'net.v', '--gate-top', 'dut', '--liberty', source / 'cells.lib',
                  '--gate-models', source / 'cells.v', '--sdf-annotate', source / 'delay.sdf', source / 'tb.v', '--wave-support']
        for backend, flags in backends.items():
            run([compiler, *common, *flags, '--emit-cpp', work / (backend + '.cpp'), '-o', work / backend], work, backend + '-compile')
            if args.baseline and meta['variant'] not in ['identical', 'comments']:
                run([args.baseline.resolve(), *common, *flags, '--emit-only', '--emit-cpp', work / (backend + '-old.cpp')], work, backend + '-old-emit')
                assert (work / (backend + '.cpp')).read_bytes() == (work / (backend + '-old.cpp')).read_bytes(), (name, backend)
                report['old_cpp_comparisons'] += 1
            reference = run([work / backend], work, backend + '-none')
            assert reference[0].splitlines() == oracle['trace'] and not reference[1], (name, backend, reference)
            for mode in ['ordered', 'settled']:
                for codec, suffix in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                    stem = backend + '-' + mode + '-' + codec; wave = work / (stem + '.' + suffix)
                    command = [work / backend, '--waveform', wave, '--wave-format', suffix, '--wave-mode', mode, '--wave-block-events', '7']
                    if suffix == 'dwf': command += ['--wave-codec', codec]
                    assert run(command, work, stem) == reference
                    compare(work / ('generic-' + mode + '-vcd.vcd'), wave)
                    if mode == 'ordered' and codec == 'vcd':
                        bits = physical_bits(wave)
                        for bit in oracle['bits']:
                            key = tuple(bit['path']) + (bit['bit'],)
                            assert json.loads(json.dumps(bits[key])) == bit['changes'], (name, backend, key)
                            report['vendor_signal_comparisons'] += 1
                    report['captures'] += 1
            row['backends'][backend] = dict(status='PASS')
        row['status'] = 'PASS'; save(); print('PASS model wildcard', name, flush=True)
    report['status'] = 'PASS'
finally:
    save()
