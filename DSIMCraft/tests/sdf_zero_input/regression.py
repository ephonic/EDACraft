"""Compile zero-channel elimination and compare physical pins to raw VCS.

The native TB removes passive XMR monitors and the unannotated control instance;
the original five vendor input files remain hashed and unchanged. Ordered native
streams are compared across codecs/backends, not claimed delta-identical to VCS.
"""
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
cases = make(out / 'inputs'); cases.update(make(out / 'controls', True))
golden = json.loads((Path(__file__).parent / 'expected.json').read_text())['cases']
backends = {'generic': [], 'jobs-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel'],
            'dictionary-wheel': ['--gate-scalar-timing', '--gate-sdf-jobs', '--time-wheel', '--gate-path-dictionary']}
report = dict(status='RUNNING', directory=str(out), cases={}, captures=0,
              vendor_signal_comparisons=0, disabled_cpp_comparisons=0,
              compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest())


def save():
    for f in [out / 'results.json', base / 'results.json']: f.write_text(json.dumps(report, indent=2) + '\n')


def run(cmd, work, label):
    cmd = list(map(str, cmd)); (work / (label + '.command.json')).write_text(json.dumps(cmd) + '\n')
    r = subprocess.run(cmd, cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    assert r.returncode == 0, (label, r.returncode, r.stderr)
    return r.stdout, r.stderr


try:
    save()
    for name in cases:
        if a.case and name not in a.case: continue
        source = out / ('controls' if name == 'ic-positive' else 'inputs') / name
        oracle = golden[name]; work = out / name; work.mkdir()
        for f, digest in oracle['sources'].items():
            assert hashlib.sha256((source / f).read_bytes()).hexdigest() == digest
        tb = (source / 'tb.v').read_text().replace(',e(a,b,ze)', '')
        tb = '\n'.join(line for line in tb.splitlines() if not line.startswith(('initial begin $sdf_annotate', 'always @')))
        tb = tb.replace('$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);', '')
        (source / 'native-tb.v').write_text(tb + '\n')
        common = ['--gate-netlist', source / 'net.v', '--gate-top', 'dut', '--liberty', source / 'cells.lib',
                  '--gate-models', source / 'cells.v', '--sdf-annotate', source / 'delay.sdf', source / 'native-tb.v', '--wave-support']
        row = dict(status='RUNNING', backends={}); report['cases'][name] = row
        for backend, flags in backends.items():
            cpp = work / (backend + '.cpp')
            run([compiler, *common, *flags, '--gate-fold-zero-inputs', '--emit-cpp', cpp,
                 '--emit-ir', work / (backend + '.json'), '-o', work / backend], work, backend + '-compile')
            ir = json.loads((work / (backend + '.json')).read_text())['gate_design']
            assert ir['zero_input_pins_folded'] == int(oracle['zero_input']), (name, ir)
            assert ('struct InputDelay' not in cpp.read_text()) == oracle['zero_input']
            if a.baseline and name != 'ic-replace-zero':
                run([compiler, *common, *flags, '--emit-only', '--emit-cpp', work / (backend + '-off.cpp')], work, backend + '-off')
                run([a.baseline.resolve(), *common, *flags, '--emit-only', '--emit-cpp', work / (backend + '-old.cpp')], work, backend + '-old')
                assert (work / (backend + '-off.cpp')).read_bytes() == (work / (backend + '-old.cpp')).read_bytes()
                report['disabled_cpp_comparisons'] += 1
            reference = run([work / backend], work, backend + '-none')
            for mode in ['ordered', 'settled']:
                for codec, suffix in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                    stem = backend + '-' + mode + '-' + codec; wave = work / (stem + '.' + suffix)
                    cmd = [work / backend, '--waveform', wave, '--wave-format', suffix, '--wave-mode', mode, '--wave-block-events', '7']
                    if suffix == 'dwf': cmd += ['--wave-codec', codec]
                    assert run(cmd, work, stem) == reference
                    compare(work / ('generic-' + mode + '-vcd.vcd'), wave)
                    if mode == 'ordered' and codec == 'vcd':
                        bits = physical_bits(wave)
                        for bit in oracle['bits']:
                            path = bit['path']
                            if path[:2] not in [['top', 'a'], ['top', 'b'], ['top', 'zd'], ['top', 'd']]: continue
                            # Leaf output aliases are not exported by the
                            # existing gate wave dictionary; observe d.z/zd.
                            if path == ['top', 'd', 'u0', 'Z']: continue
                            key = tuple(path) + (bit['bit'],)
                            assert json.loads(json.dumps(bits[key])) == bit['changes'], (name, backend, key, bits.get(key), bit['changes'])
                            report['vendor_signal_comparisons'] += 1
                    report['captures'] += 1
            row['backends'][backend] = dict(status='PASS', folded_pins=ir['zero_input_pins_folded'])
        row['status'] = 'PASS'; save(); print('PASS zero input', name, flush=True)
    report['status'] = 'PASS'
finally:
    save()
