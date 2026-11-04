"""Rollback real generated zero-input programs, including source-pin aliases."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from compare_waveforms import compare
p = argparse.ArgumentParser()
p.add_argument('compiler', type=Path); p.add_argument('flow', type=Path)
p.add_argument('--sanitize', action='store_true')
a = p.parse_args(); report = json.loads((a.flow / 'results.json').read_text())
assert report['status'] == 'PASS'
work = Path(report['directory'])
config = {line.split('=', 1)[0].split(':', 1)[0]: line.split('=', 1)[1]
          for line in (a.compiler.resolve().parent / 'CMakeCache.txt').read_text().splitlines()
          if '=' in line and not line.startswith('//')}
captures = 0
for name in ['ic-zero', 'ic-zero-with-path', 'ic-positive']:
    for backend in ['generic', 'dictionary-wheel']:
        w = work / name; code = (w / (backend + '.cpp')).read_text()
        assert code.count('\ns.run();\n') == 1
        replay = '''
s.run_until(11);
auto accepted=s.predict_until(15,[](Sim&){},[](const Sim&){return true;},[](Sim&){});
if(!accepted)throw std::runtime_error("missing zero-input commit");
auto rolled=s.predict_until(35,[](Sim& probe){
 for(size_t id=0;id<probe.signals.size();++id){const auto& sig=probe.signals[id];if(!sig.net)probe.set(int(id),V::x(sig.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(rolled||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing zero-input rollback");
s.run();
'''
        boundary = '\ns.run_until(11);s.run_until(15);s.run_until(35);s.run();\n'
        for variant, body in [('boundary', boundary), ('replay', replay)]:
            stem = backend + '-' + variant + ('-san' if a.sanitize else '')
            cpp = w / (stem + '.cpp'); cpp.write_text(code.replace('\ns.run();\n', body))
            command = ['c++', '-std=c++17', '-O1' if a.sanitize else '-O2', '-I' + config['DSIM_ZSTD_INCLUDE'], cpp,
                       config['DSIM_ZSTD_LIBRARY'], '-o', w / stem]
            if a.sanitize: command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            r = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=240)
            (w / (stem + '-compile.log')).write_text(r.stdout + r.stderr); assert r.returncode == 0, r.stderr
            for mode in ['ordered', 'settled']:
                wave = w / (stem + '-' + mode + '.dwf')
                r = subprocess.run([str(w / stem), '--waveform', str(wave), '--wave-mode', mode,
                                    '--wave-codec', 'zstd', '--wave-block-events', '7'], capture_output=True, text=True, timeout=60)
                (w / (stem + '-' + mode + '.stdout')).write_text(r.stdout)
                (w / (stem + '-' + mode + '.stderr')).write_text(r.stderr)
                assert r.returncode == 0, r.stderr
                assert not any(s in r.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
                if variant == 'replay':
                    baseline = backend + '-boundary' + ('-san' if a.sanitize else '')
                    compare(w / (baseline + '-' + mode + '.dwf'), wave)
                    assert r.stdout == (w / (baseline + '-' + mode + '.stdout')).read_text()
                    assert r.stderr == (w / (baseline + '-' + mode + '.stderr')).read_text()
                captures += 1
        print('PASS zero-input transaction', name, backend, flush=True)
(a.flow / ('checkpoint-san.json' if a.sanitize else 'checkpoint.json')).write_text(
    json.dumps(dict(status='PASS', cases=3, backends=2, captures=captures, sanitizer=a.sanitize), indent=2) + '\n')
