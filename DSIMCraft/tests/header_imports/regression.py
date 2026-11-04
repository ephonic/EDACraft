"""Header import ordering, cloned lexical scopes and named module port types."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fixtures = Path(__file__).resolve().parent
compiler = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
cache_path = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else compiler.parent / 'CMakeCache.txt'
cache = {x.split('=', 1)[0].split(':', 1)[0]: x.split('=', 1)[1]
         for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, declarations


def run(cmd, work, label, ok=True):
    p = subprocess.run(list(map(str, cmd)), cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(p.stdout)
    (work / (label + '.stderr')).write_text(p.stderr)
    assert p.returncode == (0 if ok else 1), (label, p.returncode, p.stdout, p.stderr)
    return p.stdout


def stream(path):
    meta, events = read(path)
    values = [[] for _ in meta['signals']]
    for t, kind, payload in events:
        if kind == 'value':
            values[payload[0]].append((t, payload[1]))
    return {key: (width, ranges, values[ident])
            for key, (ident, width, ranges) in declarations(meta).items()}


expected = json.loads((fixtures / 'expected.json').read_text())
report = dict(status='RUNNING', models={}, captures=0, rollbacks=0, commits=0)
try:
    for name, wanted in expected.items():
        work = out / name
        work.mkdir(exist_ok=True)
        reference = None
        for backend, flags in [('serial', []), ('wheel', ['--time-wheel']), ('parallel', ['--threads', '2'])]:
            run([compiler, fixtures / (name + '.sv'), *flags, '--wave-support',
                 '--emit-cpp', work / (backend + '.cpp'), '--emit-ir', work / (backend + '.json'),
                 '-o', work / backend], work, backend + '-compile')
            wave = work / (backend + '.vcd')
            wave.unlink(missing_ok=True)
            text = run([work / backend, '--waveform', wave, '--wave-format', 'vcd',
                        '--wave-mode', 'ordered'], work, backend + '-run')
            assert [line for line in text.splitlines() if line.startswith('TRACE')] == wanted, (name, text)
            current = stream(wave)
            assert current, (name, 'missing wave signals')
            if reference is None:
                reference = current
            else:
                assert current == reference, (name, backend, 'complete ordered stream')
            report['captures'] += 1
        if name in ['ports', 'clones', 'interfaces', 'shared']:
            code = (work / 'serial.cpp').read_text()
            assert code.count('\ns.run();\n') == 1
            for mode, accept in [('rollback', 'false'), ('commit', 'true')]:
                replay = code.replace('\ns.run();\n', '''
s.run_until(500);
bool accepted=s.predict_until(1500,[](Sim&){},[](const Sim&){return ACCEPT;},[](Sim&){});
if(accepted!=ACCEPT)throw std::runtime_error("prediction result");
if(s.prediction_stats.ATTEMPTS!=1)throw std::runtime_error("prediction counter");
s.run();
'''.replace('ACCEPT', accept).replace('ATTEMPTS', 'commits' if accept == 'true' else 'rollbacks'))
                source = work / (mode + '.cpp')
                source.write_text(replay)
                run(['c++', '-std=c++17', '-O2', '-pthread',
                     '-I' + cache['DSIM_ZSTD_INCLUDE'], source, cache['DSIM_ZSTD_LIBRARY'],
                     '-o', work / mode], work, mode + '-compile')
                wave = work / (mode + '.vcd')
                wave.unlink(missing_ok=True)
                text = run([work / mode, '--waveform', wave, '--wave-format', 'vcd',
                            '--wave-mode', 'ordered'], work, mode + '-run')
                assert text == (work / 'serial-run.stdout').read_text(), (name, mode, 'output replay')
                assert stream(wave) == reference, (name, mode, 'ordered wave replay')
                report['captures'] += 1
                report['commits' if accept == 'true' else 'rollbacks'] += 1
        report['models'][name] = dict(status='PASS', trace=wanted,
            source_sha256=hashlib.sha256((fixtures / (name + '.sv')).read_bytes()).hexdigest())
        print('PASS header imports', name, flush=True)

    p = 'package p;parameter int N=3;typedef logic[2:0] T;endpackage '
    q = 'package q;parameter int N=5;endpackage '
    negatives = {
        'missing_package': ('module top import absent::*; ;endmodule', 'unknown or not yet declared package'),
        'missing_member': (p + 'module top import p::missing; ;endmodule', 'package member not found'),
        'explicit_conflict': (p + q + 'module top import p::N,q::N; ;endmodule', 'conflicting explicit'),
        'parameter_conflict': (p + 'module top import p::N; #(parameter N=7)();endmodule', 'redefined'),
        'port_conflict': (p + 'module top import p::N; (input logic N);endmodule', 'redefined'),
        'local_conflict': (p + 'module top import p::N; ;integer N;endmodule', 'redefined'),
        'ambiguous_parameter': (p + q + 'module top import p::*; import q::*; #(parameter W=N)();endmodule', 'ambiguous wildcard'),
        'ambiguous_port': (p + q + 'module top import p::*; import q::*; (input logic[N-1:0] x);endmodule', 'ambiguous wildcard'),
        'used_wildcard_conflict': (p + 'module top import p::*; #(parameter W=N)();integer N;endmodule', 'redefined'),
        'parent_isolation': (p + 'module child import p::*; ;endmodule module top;child u();integer x;initial x=N;endmodule', 'not visible'),
        'sibling_isolation': (p + 'module a import p::*; ;endmodule module b;integer x;initial x=N;endmodule module top;a x();b y();endmodule', 'not visible'),
        'body_too_late': (p + 'module top #(parameter W=N)();import p::*;endmodule', 'not visible'),
        'missing_port_type': ('module top(input absent x);endmodule', 'unknown integral type absent'),
        'value_as_type': (p + 'module top import p::*; (input N x);endmodule', 'unknown integral type N'),
        'interface_parameter': (p + q + 'interface bus import p::N; #(parameter N=7)();endinterface module top;bus x();endmodule', 'redefined'),
    }
    for name, (text, diagnostic) in negatives.items():
        source = out / (name + '.sv')
        source.write_text(text + '\n')
        dest = out / (name + '.cpp')
        dest.unlink(missing_ok=True)
        run([compiler, source, '--emit-only', '--emit-cpp', dest], out, name, False)
        assert diagnostic in (out / (name + '.stderr')).read_text(), (name, (out / (name + '.stderr')).read_text())
        assert not dest.exists(), name
    report.update(status='PASS', negative_cases=len(negatives))
finally:
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS header imports:', report['captures'], 'captures,', report['rollbacks'],
      'rollbacks,', report['commits'], 'commits,', report['negative_cases'], 'rejections')
