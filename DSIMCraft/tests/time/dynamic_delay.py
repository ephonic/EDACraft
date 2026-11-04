"""Runtime delays: sampling, four-state values, scales, parallelism and replay."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, declarations

def signal_streams(stream):
    meta, events = stream
    values = [[] for _ in meta['signals']]
    for tick, kind, payload in events:
        if kind == 'value': values[payload[0]].append((tick, payload[1]))
    return {name: (width, ranges, values[ident]) for name, (ident, width, ranges) in declarations(meta).items()}

compiler = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)

def run(args, work, label, success=True):
    p = subprocess.run(list(map(str, args)), cwd=work, text=True, capture_output=True, timeout=180)
    (work / (label + '.stdout')).write_text(p.stdout)
    (work / (label + '.stderr')).write_text(p.stderr)
    assert (p.returncode == 0) == success, (label, p.stdout, p.stderr)
    return p.stdout

expected = {
    'dynamic_delay': [
        'TRACE sampled t=5000 b=12 rhs=34 q=12 parts=a00b',
        'TRACE unknown t=7000', 'TRACE zero-nba t=8000 q=cc',
        'TRACE wide t=10000', 'TRACE wide-unknown t=10000'],
    'dynamic_scopes': ['TRACE fine t=7000 q=21', 'TRACE coarse t=30000 q=42'],
    'dynamic_parallel': [],
}
parallel = '''`timescale 1ps/1ps
module top;reg [7:0] delay,q;reg island;
initial begin delay=3;#1 delay=5;end
initial begin q=0;#0;#delay q=1;#delay q=2;end
initial begin island=0;repeat(7)begin #2 island=~island;end end
endmodule
'''
captures = 0
for name, trace in expected.items():
    work = out / name; work.mkdir(exist_ok=True)
    source = work / 'top.v'
    source.write_text(parallel if name == 'dynamic_parallel' else (ROOT / 'tests/time' / (name + '.v')).read_text())
    reference = {}
    for backend, flags in [('serial', []), ('wheel', ['--time-wheel']), ('parallel', ['--threads', '2'])]:
        cpp = work / (backend + '.cpp'); binary = work / backend
        run([compiler, source, '--wave-support', *flags, '--emit-cpp', cpp, '--emit-ir', work / (backend + '.json'), '-o', binary], work, backend + '-compile')
        assert '#define DSIM_DYNAMIC_DELAY_ENABLED 1' in cpp.read_text()
        assert run([binary], work, backend + '-none').splitlines() == trace
        for mode in ['ordered', 'settled']:
            for fmt in ['vcd', 'dwf']:
                stem = backend + '-' + mode + '-' + fmt; dest = work / (stem + '.' + fmt)
                dest.unlink(missing_ok=True)
                assert run([binary, '--waveform', dest, '--wave-format', fmt, '--wave-mode', mode], work, stem).splitlines() == trace
                stream = read(dest); captures += 1
                if backend == 'serial' and fmt == 'vcd': reference[mode] = stream
                if backend == 'parallel' and name == 'dynamic_parallel':
                    assert signal_streams(stream) == signal_streams(reference[mode]), (name, backend, mode, fmt)
                else:
                    assert stream == reference[mode], (name, backend, mode, fmt)
        if backend == 'parallel' and name == 'dynamic_parallel':
            stats = subprocess.run([str(binary), '--parallel-stats'], capture_output=True, text=True, check=True).stderr
            assert '"partitions":2' in stats, stats
    if name == 'dynamic_delay':
        # Restore the pending sampled RHS, NBA timers and the dynamic-delay PC.
        code = (work / 'serial.cpp').read_text()
        control = '''
s.run_until(1000);
bool accepted=s.predict_until(6000,[](Sim&){},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("dynamic delay rollback failed");
s.run();
'''
        assert code.count('\ns.run();\n') == 1
        replay = work / 'replay.cpp'; replay.write_text(code.replace('\ns.run();\n', control))
        cache = (compiler.parent / 'CMakeCache.txt').read_text().splitlines()
        config = {x.split('=', 1)[0].split(':', 1)[0]: x.split('=', 1)[1] for x in cache if '=' in x and not x.startswith('//')}
        run(['c++', '-std=c++17', '-O2', '-I' + config['DSIM_ZSTD_INCLUDE'], replay, config['DSIM_ZSTD_LIBRARY'], '-o', work / 'replay'], work, 'replay-compile')
        for fmt in ['vcd', 'dwf']:
            dest = work / ('replay.' + fmt)
            dest.unlink(missing_ok=True)
            assert run([work / 'replay', '--waveform', dest, '--wave-format', fmt, '--wave-mode', 'ordered'], work, 'replay-' + fmt).splitlines() == trace
            # run_until may add an empty timestamp at its explicit boundary;
            # every value event, timestamp and delta order must still match.
            def values(stream):
                time = 0; result = []
                for tick, kind, payload in stream[1]:
                    if kind == 'time': time = tick
                    else: result.append((time, kind, payload))
                return result
            assert values(read(dest)) == values(reference['ordered'])
            captures += 1
    print('PASS runtime delay', name, flush=True)

work = out / 'overflow'; work.mkdir(exist_ok=True)
(work / 'top.v').write_text('`timescale 1s/1fs\nmodule top;reg[63:0] d;initial begin d=100000;#d;end endmodule\n')
run([compiler, work / 'top.v', '-o', work / 'native'], work, 'compile')
run([work / 'native'], work, 'run', False)
assert 'delay exceeds simulation time range' in (work / 'run.stderr').read_text()
(out / 'results.json').write_text(json.dumps(dict(status='PASS', cases=list(expected), captures=captures, replay=True, runtime_overflow=True), indent=2) + '\n')
