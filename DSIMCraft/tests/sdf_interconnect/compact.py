"""Compare actual compiled receiver storage backends, including ordered waves."""
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
compact = 'int target=s.compact_net();s.set(target,V::z(1));s.set(target,V::x(1));'
generic = 'int target=s.signal(1,true);s.set(target,V::x(1));'
cases = {name: out / 'inputs' / name for name in
         ['fanout', 'pulses', 'input-and-output', 'multi-driver']}
cases['checks'] = out / 'checks/composed'
results = {}
for name, w in cases.items():
    def run(command, label):
        result = subprocess.run(list(map(str, command)), cwd=w, capture_output=True,
                                text=True, timeout=180)
        (w / (label + '.stdout')).write_text(result.stdout)
        (w / (label + '.stderr')).write_text(result.stderr)
        assert result.returncode == 0, (name, label, result.stdout, result.stderr)
        return result.stdout

    tb = (w / 'tb.v').read_text()
    if name != 'checks':
        tb = '\n'.join('always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);'
                       if line.startswith('always @') else line for line in tb.splitlines()) + '\n'
    (w / 'native-tb.v').write_text(tb)
    run([compiler, '--gate-netlist', w / 'net.v', '--gate-top', 'dut',
         '--liberty', w / 'cells.lib', '--gate-models', w / 'cells.v',
         '--sdf-annotate', w / 'delay.sdf', w / 'native-tb.v', '--wave-support',
         '--emit-only', '--emit-cpp', w / 'compact.cpp'], 'emit')
    code = (w / 'compact.cpp').read_text()
    if code.count(compact) == 1:
        generic_code, compact_code = code.replace(compact, generic), code
    else:
        assert code.count(generic) == 1
        generic_code, compact_code = code, code.replace(generic, compact)
    (w / 'generic.cpp').write_text(generic_code)
    (w / 'compact.cpp').write_text(compact_code)
    streams, waves = {}, {}
    for backend in ['generic', 'compact']:
        run(['c++', '-std=c++17', '-O2', '-I' + config['DSIM_ZSTD_INCLUDE'],
             w / (backend + '.cpp'), config['DSIM_ZSTD_LIBRARY'], '-o', w / backend],
            backend + '-compile')
        streams[backend] = run([w / backend], backend + '-none')
        waves[backend] = {}
        for mode, fmt in [('ordered', 'vcd'), ('ordered', 'dwf'), ('settled', 'dwf')]:
            dest = w / f'{backend}-{mode}.{fmt}'
            dest.unlink(missing_ok=True)
            stdout = run([w / backend, '--waveform', dest, '--wave-mode', mode,
                          '--wave-format', fmt, '--wave-block-events', 7], backend + '-' + mode + '-' + fmt)
            assert stdout == streams[backend]
            waves[backend][mode, fmt] = read(dest)
        assert waves[backend]['ordered', 'vcd'] == waves[backend]['ordered', 'dwf']
    assert streams['generic'] == streams['compact'], name
    assert waves['generic'] == waves['compact'], name
    results[name] = dict(status='PASS', full_ordered_and_settled_waves=True,
                         trace=streams['compact'].splitlines())
    print('PASS generic/compact receiver full streams', name, flush=True)
(out / 'results.json').write_text(json.dumps(dict(status='PASS', cases=results), indent=2) + '\n')
