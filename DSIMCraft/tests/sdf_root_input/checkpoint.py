"""Commit and roll back generated models while corrected input delays are pending."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from compare_waveforms import compare
p = argparse.ArgumentParser(); p.add_argument('compiler', type=Path); p.add_argument('flow', type=Path)
p.add_argument('--sanitize', action='store_true'); a = p.parse_args()
report = json.loads((a.flow / 'results.json').read_text()); assert report['status'] == 'PASS'
work = Path(report['directory'])
cache = {line.split('=', 1)[0].split(':', 1)[0]:line.split('=', 1)[1] for line in
         (a.compiler.resolve().parent / 'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
pairs = [('root-reg', 'generic'), ('root-increment', 'dictionary-wheel')] if a.sanitize else [
    (name, backend) for name in ['root-reg', 'root-increment', 'internal-reg', 'root-three']
    for backend in ['generic', 'dictionary-wheel']]
rows = []; captures = 0
for name, backend in pairs:
    directory = work / name; original = (directory / (backend + '.cpp')).read_text()
    assert original.count('\ns.run();\n') == 1
    boundary = '\ns.run_until(41);s.run_until(45);s.run_until(75);s.run();\n'
    replay = '''
s.run_until(41);
if(!s.predict_until(45,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing input-delay commit");
auto rolled=s.predict_until(75,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i){const auto& sig=probe.signals[i];if(!sig.net)probe.set(int(i),V::x(sig.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(rolled||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing input-delay rollback");
s.run();
'''
    suffix = '-san' if a.sanitize else ''
    for variant, body in [('boundary', boundary), ('replay', replay)]:
        stem = backend + '-' + variant + suffix; cpp = directory / (stem + '.cpp')
        cpp.write_text(original.replace('\ns.run();\n', body))
        cmd = ['c++', '-std=c++17', '-pthread', '-O1' if a.sanitize else '-O2', '-I' + cache['DSIM_ZSTD_INCLUDE'],
               cpp, cache['DSIM_ZSTD_LIBRARY'], '-o', directory / stem]
        if a.sanitize: cmd += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        cmd = list(map(str, cmd)); (directory / (stem + '-compile.command.json')).write_text(json.dumps(cmd) + '\n')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        (directory / (stem + '-compile.stdout')).write_text(result.stdout)
        (directory / (stem + '-compile.stderr')).write_text(result.stderr); assert result.returncode == 0, result.stderr
        for mode in ['ordered', 'settled']:
            label = stem + '-' + mode; wave = directory / (label + '.dwf')
            cmd = list(map(str, [directory / stem, '--waveform', wave, '--wave-mode', mode,
                '--wave-block-events', 7, '--wave-compression-jobs', 4]))
            (directory / (label + '.command.json')).write_text(json.dumps(cmd) + '\n')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            (directory / (label + '.stdout')).write_text(result.stdout); (directory / (label + '.stderr')).write_text(result.stderr)
            assert result.returncode == 0, result.stderr
            assert not any(s in result.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
            assert result.stdout == (directory / (backend + '-none.stdout')).read_text()
            if variant == 'replay':
                before = directory / (backend + '-boundary' + suffix + '-' + mode + '.dwf')
                compare(before, wave); assert before.read_bytes() == wave.read_bytes()
                assert result.stderr == (directory / (backend + '-boundary' + suffix + '-' + mode + '.stderr')).read_text()
            captures += 1
    rows.append(dict(case=name, backend=backend, cpp_sha256=hashlib.sha256((directory / (backend + '.cpp')).read_bytes()).hexdigest()))
    print('PASS root input transaction', name, backend, 'sanitizer=' + str(a.sanitize), flush=True)
(a.flow / ('checkpoint-san.json' if a.sanitize else 'checkpoint.json')).write_text(json.dumps(
    dict(status='PASS', configurations=rows, captures=captures, sanitizer=a.sanitize, compression_jobs=4), indent=2) + '\n')
