"""Actual compiler batches: exact ordered waves/stdout and generated rollback."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read
gate_spec = importlib.util.spec_from_file_location('gate_fixtures', Path(__file__).with_name('regression.py'))
gates = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(gates)

parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path)
parser.add_argument('out', type=Path)
args = parser.parse_args()
compiler, out = args.compiler.resolve(), args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
cache = dict(line.split('=', 1) for line in (compiler.parent / 'CMakeCache.txt').read_text().splitlines()
             if '=' in line and not line.startswith('//'))
zstd_include = next(v for k, v in cache.items() if k.startswith('DSIM_ZSTD_INCLUDE:'))
zstd_library = next(v for k, v in cache.items() if k.startswith('DSIM_ZSTD_LIBRARY:'))

def run(command, work, label):
    p = subprocess.run(list(map(str, command)), cwd=work, text=True, capture_output=True, timeout=180)
    (work / (label + '.stdout')).write_text(p.stdout)
    (work / (label + '.stderr')).write_text(p.stderr)
    assert p.returncode == 0, (label, p.stdout, p.stderr)
    return p.stdout

cases = {name: gates.command(compiler, name) for name in
         ['four_state', 'hierarchy', 'connections', 'wide_atomic', 'seq_feedback', 'seq_regions']}
spec = importlib.util.spec_from_file_location('check_fixtures', ROOT / 'tests/timing_checks/cases.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
fixtures.make(out / 'timing-inputs')
w = out / 'timing-inputs/composed'
cases['sdf-checks'] = [compiler, '--gate-netlist', w / 'net.v', '--gate-top', 'dut', '--liberty', w / 'cells.lib',
                       '--gate-models', w / 'cells.v', '--sdf-annotate', w / 'delay.sdf', w / 'tb.v']
base = ROOT / 'tests/flow/sdf'
cases['sdf-paths'] = [compiler, '--gate-netlist', base / 'net.v', '--gate-top', 'dut', '--liberty', base / 'cells.lib',
                      '--gate-models', base / 'cells.v', '--sdf-annotate', base / 'delay.sdf', base / 'native-tb.v']
results = {}
for name, command in cases.items():
    work = out / name
    work.mkdir(exist_ok=True)
    traces, waves = {}, {}
    for variant in ['baseline', 'batch']:
        binary = work / variant
        run(command + (['--gate-batch'] if variant == 'batch' else []) +
            ['--wave-support', '--emit-ir', work / (variant + '.json'), '-o', binary], work, variant + '-compile')
        ir = json.loads((work / (variant + '.json')).read_text())['gate_design']
        assert ir.get('batch_execution', False) == (variant == 'batch')
        traces[variant] = run([binary], work, variant + '-none')
        waves[variant] = {}
        for fmt, mode in [('vcd', 'ordered'), ('dwf', 'ordered'), ('dwf', 'settled')]:
            wave = work / (variant + '-' + mode + '.' + fmt)
            wave.unlink(missing_ok=True)
            trace = run([binary, '--waveform', wave, '--wave-format', fmt, '--wave-mode', mode,
                         '--wave-block-events', 7], work, variant + '-' + mode + '-' + fmt)
            assert trace == traces[variant]
            waves[variant][(fmt, mode)] = read(wave)
        assert waves[variant][('vcd', 'ordered')] == waves[variant][('dwf', 'ordered')]
    assert traces['baseline'] == traces['batch'], name
    assert waves['baseline'] == waves['batch'], name
    if name in ['seq_feedback', 'sdf-checks']:
        code = (work / 'batch.dsim.cpp').read_text()
        assert code.count('\ns.run();\n') == 1
        control = '''
s.run_until(1);
if(!s.finished) {
 bool ok=s.predict_until(100,[](Sim& probe){
  for(size_t i=0;i<probe.signals.size();++i)if(!probe.signals[i].net)probe.set(int(i),V::x(probe.signals[i].value.w));
 },[](const Sim&){return false;},[](Sim&){});
 if(ok||s.prediction_stats.rollbacks!=1)throw std::runtime_error("batch rollback failed");
}
s.run();
'''
        replay = work / 'replay.cpp'
        # Match an existing waveform timestamp. A bounded run records its
        # boundary even if no signal changed; adding tick 1 to the SDF case
        # would compare different run protocols rather than rollback effects.
        if name == 'sdf-checks':
            control = control.replace('s.run_until(1);', 's.run_until(3);')
        replay.write_text(code.replace('\ns.run();\n', control))
        run(['c++', '-std=c++17', '-O2', '-I' + zstd_include, replay, zstd_library, '-o', work / 'replay'], work, 'replay-compile')
        for mode in ['ordered', 'settled']:
            wave = work / ('replay-' + mode + '.dwf')
            wave.unlink(missing_ok=True)
            trace = run([work / 'replay', '--waveform', wave, '--wave-mode', mode, '--wave-block-events', 7], work, 'replay-' + mode)
            assert trace == traces['baseline'] and read(wave) == waves['baseline'][('dwf', mode)]
    results[name] = dict(status='PASS', trace=traces['baseline'].splitlines(), rollback=name in ['seq_feedback', 'sdf-checks'])
    print('PASS compiled FIFO batch ordered/settled waves and stdout', name, flush=True)

# Profile one actual generated program to prove batches contain multiple events.
work = out / 'hierarchy'
code = (work / 'batch.dsim.cpp').read_text()
code = code.replace('\ns.run();\n', '\ns.run();\nstd::cerr<<"BATCH "<<s.batch_stats.entries<<" "<<s.batch_stats.events<<"\\n";\n')
(work / 'profile.cpp').write_text(code)
run(['c++', '-std=c++17', '-O2', '-DDSIM_BATCH_PROFILE', '-I' + zstd_include, work / 'profile.cpp', zstd_library,
     '-o', work / 'profile'], work, 'profile-compile')
run([work / 'profile'], work, 'profile-run')
_, entries, events = (work / 'profile-run.stderr').read_text().strip().split()
assert int(events) > int(entries) > 0
(out / 'results.json').write_text(json.dumps(dict(status='PASS', cases=results, profile=dict(entries=int(entries), events=int(events))), indent=2) + '\n')
