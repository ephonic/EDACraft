"""Replay actual dictionary code across pending MIPD/module-path events."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_waveforms import compare

parser = argparse.ArgumentParser()
parser.add_argument('compiler', type=Path); parser.add_argument('flow', type=Path)
parser.add_argument('--sanitize', action='store_true')
args = parser.parse_args(); compiler = args.compiler.resolve(); flow = args.flow.resolve()
native = json.loads((flow / 'results.json').read_text()); assert native['status'] == 'PASS'
config = {line.split('=', 1)[0].split(':', 1)[0]: line.split('=', 1)[1]
          for line in (compiler.parent / 'CMakeCache.txt').read_text().splitlines()
          if '=' in line and not line.startswith('//')}
report = dict(status='RUNNING', sanitizer=args.sanitize, captures=0, binaries=0, cases=[])
prefix = 'asan-' if args.sanitize else ''


def save():
    (flow / (prefix + 'checkpoint.json')).write_text(json.dumps(report, indent=2) + '\n')


def run(command, work, label):
    command = list(map(str, command))
    (work / (label + '.command.json')).write_text(json.dumps(command, indent=2) + '\n')
    r = subprocess.run(command, cwd=work, text=True, capture_output=True, timeout=240)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    assert r.returncode == 0, (label, r.returncode, r.stdout, r.stderr)
    assert not any(s in r.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
    return r.stdout, r.stderr


control = '''
s.run_until(101);
auto accepted=s.predict_until(125,[](Sim& probe){
 for(size_t i=0;i<probe.signals.size();++i){const auto& signal=probe.signals[i];if(!signal.net)probe.set(int(i),V::x(signal.value.w));}
 probe.run_until(102);
 for(size_t i=0;i<probe.signals.size();++i){const auto& signal=probe.signals[i];if(!signal.net)probe.set(int(i),V(0,0,signal.value.w));}
},[](const Sim&){return false;},[](Sim&){});
if(accepted||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing dictionary rollback");
if(!s.predict_until(150,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing dictionary commit");
s.run();
'''
try:
    save()
    for name in ['condition-edge', 'port-and-device', 'ff']:
        if name not in native['cases']:
            continue
        work = flow / name
        for backend in ['generic', 'jobs-wheel']:
            code = (work / (backend + '-dictionary.cpp')).read_text()
            assert code.count('\ns.run();\n') == 1
            expected = ((work / (backend + '-baseline-none.stdout')).read_text(),
                        (work / (backend + '-baseline-none.stderr')).read_text())
            for variant, body in [('boundary', '\ns.run_until(101);s.run_until(125);s.run_until(150);s.run();\n'), ('replay', control)]:
                label = prefix + backend + '-dictionary-' + variant
                (work / (label + '.cpp')).write_text(code.replace('\ns.run();\n', body))
                flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitize else ['-O2']
                run(['c++', '-std=c++17', *flags, '-I' + config['DSIM_ZSTD_INCLUDE'],
                     work / (label + '.cpp'), config['DSIM_ZSTD_LIBRARY'], '-o', work / label], work, label + '-compile')
                report['binaries'] += 1
                for mode in ['ordered', 'settled']:
                    stem = label + '-' + mode; wave = work / (stem + '.dwf'); wave.unlink(missing_ok=True)
                    assert run([work / label, '--waveform', wave, '--wave-mode', mode,
                                '--wave-codec', 'zstd', '--wave-block-events', '7'], work, stem) == expected
                    compare(work / (prefix + backend + '-dictionary-boundary-' + mode + '.dwf'), wave)
                    report['captures'] += 1
            report['cases'].append(name + '-' + backend)
            save()
    report['status'] = 'PASS'
finally:
    save()
