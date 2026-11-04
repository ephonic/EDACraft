"""Exercise root MIPD readback through the compiler, codecs and all SDF backends."""
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

p = argparse.ArgumentParser()
p.add_argument('compiler', type=Path); p.add_argument('output', type=Path)
p.add_argument('--baseline', type=Path); p.add_argument('--case', action='append')
a = p.parse_args(); compiler = a.compiler.resolve()
base = a.output.resolve(); base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))
cases = make(out / 'inputs')
golden = json.loads((Path(__file__).parent / 'expected.json').read_text())['cases']
backends = {'generic': [], 'jobs-folded': ['--gate-scalar-timing', '--gate-sdf-jobs', '--gate-fold-zero-inputs'],
            'dictionary-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--gate-fold-zero-inputs',
                                 '--gate-path-dictionary', '--time-wheel']}
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = dict(status='RUNNING', directory=str(out), compiler_sha256=digest(compiler), cases={},
              captures=0, vendor_signal_comparisons=0, internal_entire_cpp_identities=0,
              only_input_delay_cpp_identities=0, previous_mismatch_reproduced=False)


def save():
    for path in [out / 'results.json', base / 'results.json']: path.write_text(json.dumps(report, indent=2) + '\n')


def run(command, work, label):
    command = list(map(str, command)); (work / (label + '.command.json')).write_text(json.dumps(command) + '\n')
    r = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=240)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    assert r.returncode == 0, (label, r.returncode, r.stdout, r.stderr)
    return r.stdout, r.stderr


try:
    save()
    for name, metadata in cases.items():
        if a.case and name not in a.case: continue
        source = out / 'inputs' / name; oracle = golden[name]; work = out / name; work.mkdir()
        for filename, sha in oracle['sources'].items(): assert digest(source / filename) == sha, (name, filename)
        tb = source / 'tb.v'
        common = ['--gate-netlist', source / 'net.v', '--gate-top', 'dut', '--liberty', source / 'cells.lib',
                  '--gate-models', source / 'cells.v', '--sdf-annotate', source / 'delay.sdf',
                  '--wave-support', tb]
        previous_common = list(common)
        if a.baseline and name == 'root-buffer':
            # Older reference compilers cannot parse unnamed primitives. This
            # vendor-verified spelling is only for the historical comparison;
            # the current compiler always consumes the original fixture.
            text = tb.read_text(); assert text.count('buf(a,stimulus);') == 1
            previous_tb = source / 'previous-tb.v'
            previous_tb.write_text(text.replace('buf(a,stimulus);', 'buf buffer_driver(a,stimulus);'))
            previous_common[-1] = previous_tb
        row = dict(status='RUNNING', backends={}, native_tb_sha256=digest(tb),
                   named_primitive_adapter=False,
                   baseline_named_primitive_adapter=bool(a.baseline and name == 'root-buffer'))
        report['cases'][name] = row
        for backend, flags in backends.items():
            cpp = work / (backend + '.cpp')
            run([compiler, *common, *flags, '--emit-cpp', cpp, '--emit-ir', work / (backend + '.json'),
                 '-o', work / backend], work, backend + '-compile')
            if a.baseline:
                previous = work / (backend + '-previous.cpp')
                run([a.baseline.resolve(), *previous_common, *flags, '--emit-only', '--emit-cpp', previous], work, backend + '-previous')
                def without_delays(path):
                    code = path.read_text(); prefix = 'static const InputDelay input_delays[]={'
                    start = code.index(prefix) + len(prefix); end = code.index('{0,0,0,0}};', start)
                    return code[:start] + code[end:]
                assert without_delays(cpp) == without_delays(previous)
                report['only_input_delay_cpp_identities'] += 1
                if metadata['internal_source']:
                    assert cpp.read_bytes() == previous.read_bytes(); report['internal_entire_cpp_identities'] += 1
                if name == 'root-reg' and backend == 'generic':
                    old_exe = work / 'previous-program'
                    run([a.baseline.resolve(), *common, *flags, '--emit-cpp', work / 'previous-program.cpp',
                         '-o', old_exe], work, 'previous-program-compile')
                    old_output = run([old_exe], work, 'previous-program-run')[0]
                    assert [line for line in old_output.splitlines() if line.startswith('TRACE ')] != oracle['trace']
                    report['previous_mismatch_reproduced'] = True
            observed = run([work / backend], work, backend + '-none')
            assert [line for line in observed[0].splitlines() if line.startswith('TRACE ')] == oracle['trace']
            for mode in ['ordered', 'settled']:
                for codec, suffix in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                    stem = backend + '-' + mode + '-' + codec; wave = work / (stem + '.' + suffix)
                    args = [work / backend, '--waveform', wave, '--wave-format', suffix,
                            '--wave-mode', mode, '--wave-block-events', '7']
                    if suffix == 'dwf': args += ['--wave-codec', codec]
                    if codec == 'zstd': args += ['--wave-compression-jobs', '4']
                    assert run(args, work, stem) == observed
                    compare(work / ('generic-' + mode + '-vcd.vcd'), wave)
                    if mode == 'ordered' and codec == 'vcd':
                        bits = physical_bits(wave)
                        for bit in oracle['native_bits']:
                            key = tuple(bit['path']) + (bit['bit'],)
                            assert json.loads(json.dumps(bits[key])) == bit['changes'], (name, backend, key, bits.get(key), bit['changes'])
                            report['vendor_signal_comparisons'] += 1
                    report['captures'] += 1
            row['backends'][backend] = dict(status='PASS', cpp_sha256=digest(cpp), binary_sha256=digest(work / backend))
        row['status'] = 'PASS'; save(); print('PASS root input', name, flush=True)
    report['status'] = 'PASS'
finally:
    save()
