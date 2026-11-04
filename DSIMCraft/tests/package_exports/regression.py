"""Package exports preserve declaration identity, lexical scope and shared storage."""
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
        if name in ['chains', 'shared']:
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
        print('PASS package exports', name, flush=True)

    # Adding an SV keyword must preserve legacy Verilog identifier mode.
    legacy = out / 'legacy.v'
    legacy.write_text('module top;integer export;initial begin export=7;'
                      'if(export!=7)$fatal(1,"legacy keyword");'
                      '$display("TRACE legacy export %0d",export);end endmodule\n')
    run([compiler, legacy, '--language', 'verilog', '-o', out / 'legacy'], out, 'legacy-compile')
    assert run([out / 'legacy'], out, 'legacy-run').strip() == 'TRACE legacy export 7'
    report['legacy_keyword'] = 'PASS'
    from negative_cases import negatives
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
print('PASS package exports:', report['captures'], 'captures,', report['rollbacks'],
      'rollbacks,', report['commits'], 'commits,', report['negative_cases'], 'rejections')
