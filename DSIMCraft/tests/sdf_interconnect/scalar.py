"""Compare actual generic/scalar SDF executables and every native wave event."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from cases import make

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('compiler', type=Path)
p.add_argument('out', type=Path)
a = p.parse_args()
compiler, out = a.compiler.resolve(), a.out.resolve()
out.mkdir(parents=True, exist_ok=True)
make(out / 'inputs')
spec = importlib.util.spec_from_file_location('checks', ROOT / 'tests/timing_checks/cases.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.make(out / 'checks')
config = {line.split('=', 1)[0].split(':', 1)[0]: line.split('=', 1)[1]
          for line in (compiler.parent / 'CMakeCache.txt').read_text().splitlines()
          if '=' in line and not line.startswith('//')}
cases = {name: out / 'inputs' / name for name in ['fanout', 'pulses', 'input-and-output', 'multi-driver']}
cases['checks'] = out / 'checks/composed'
results = {}
for name, work in cases.items():
    def run(command, label):
        result = subprocess.run(list(map(str, command)), cwd=work, capture_output=True,
                                text=True, timeout=180)
        (work / (label + '.command.json')).write_text(json.dumps(list(map(str, command)), indent=2) + '\n')
        (work / (label + '.stdout')).write_text(result.stdout)
        (work / (label + '.stderr')).write_text(result.stderr)
        assert result.returncode == 0, (name, label, result.stdout, result.stderr)
        return result.stdout

    tb = (work / 'tb.v').read_text()
    if name != 'checks':
        tb = '\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
                       if line.startswith('always @') else line for line in tb.splitlines()) + '\n'
    (work / 'native-tb.v').write_text(tb)
    streams, waves = {}, {}
    for backend in ['generic', 'scalar', 'scalar-batch']:
        command = [compiler, '--gate-netlist', work / 'net.v', '--gate-top', 'dut',
                   '--liberty', work / 'cells.lib', '--gate-models', work / 'cells.v',
                   '--sdf-annotate', work / 'delay.sdf', work / 'native-tb.v', '--wave-support',
                   '--emit-only', '--emit-cpp', work / (backend + '.cpp'),
                   '--emit-ir', work / (backend + '.json')]
        if backend != 'generic':
            command.append('--gate-scalar-timing')
        if backend == 'scalar-batch':
            command.append('--gate-batch')
        run(command, backend + '-emit')
        code = (work / (backend + '.cpp')).read_text()
        assert ('#define DSIM_SCALAR_TIMING_ENABLED 1' in code) == (backend != 'generic')
        report = json.loads((work / (backend + '.json')).read_text())['gate_design']
        assert report.get('scalar_timing', False) == (backend != 'generic')
        assert report.get('batch_execution', False) == (backend == 'scalar-batch')
        run(['c++', '-std=c++17', '-O2', '-I' + config['DSIM_ZSTD_INCLUDE'],
             work / (backend + '.cpp'), config['DSIM_ZSTD_LIBRARY'], '-o', work / backend], backend + '-compile')
        streams[backend] = run([work / backend], backend + '-none')
        waves[backend] = {}
        for mode in ['ordered', 'settled']:
            for codec, fmt in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                dest = work / f'{backend}-{mode}-{codec}.{fmt}'
                dest.unlink(missing_ok=True)
                command = [work / backend, '--waveform', dest, '--wave-mode', mode,
                           '--wave-format', fmt, '--wave-block-events', 7]
                if fmt == 'dwf':
                    command += ['--wave-codec', codec]
                output = run(command, backend + '-' + mode + '-' + codec)
                assert output == streams[backend]
                waves[backend][mode, codec] = read(dest)
            assert waves[backend][mode, 'vcd'] == waves[backend][mode, 'raw'] == waves[backend][mode, 'zstd']
    assert streams['generic'] == streams['scalar'] == streams['scalar-batch'], name
    assert waves['generic'] == waves['scalar'] == waves['scalar-batch'], name
    results[name] = dict(status='PASS', trace=streams['scalar'].splitlines(),
                         full_ordered_settled_raw_zstd_equal=True)
    print('PASS generic/scalar SDF full streams', name, flush=True)

for arguments in [[], ['--sdf-check', 'missing.sdf'], ['-E'], ['--gate-check']]:
    r = subprocess.run([str(compiler), '--gate-scalar-timing', *arguments], capture_output=True, text=True)
    assert r.returncode != 0 and '--gate-scalar-timing requires SDF-annotated gate simulation code generation' in r.stderr
work = cases['checks']
(work / 'native.dsim.cpp').write_bytes((work / 'scalar.cpp').read_bytes())
replay_command = [sys.executable, str(ROOT / 'tests/sdf_runtime/checkpoint.py'),
                  str(compiler), str(work.parent), 'composed']
replay = subprocess.run(replay_command, capture_output=True, text=True, timeout=180)
(out / 'checkpoint.stdout').write_text(replay.stdout)
(out / 'checkpoint.stderr').write_text(replay.stderr)
assert replay.returncode == 0, (replay.stdout, replay.stderr)
(out / 'results.json').write_text(json.dumps(dict(status='PASS', cases=results,
    native_captures=90, checkpoint_captures=4, generated_checkpoint=True), indent=2) + '\n')
