"""Compile original primitive group syntax, compare truth, full code and waves."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
from cases import KINDS, make

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from compare_waveforms import compare
p = argparse.ArgumentParser(); p.add_argument('compiler', type=Path); p.add_argument('output', type=Path)
p.add_argument('--baseline', type=Path); a = p.parse_args()
compiler = a.compiler.resolve(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=True)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(status='RUNNING', compiler_sha256=digest(compiler), cases={}, captures=0, entire_cpp_identities=0,
              prior_named_cpp_identities=0, independent_truth_patterns=0)


def run(cmd, work, label, success=True):
    cmd = list(map(str, cmd)); (work / (label + '.command.json')).write_text(json.dumps(cmd) + '\n')
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=240)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    assert (r.returncode == 0) == success, (label, r.returncode, r.stdout, r.stderr)
    if not success: assert r.returncode > 0 and 'dsim:' in r.stderr
    return r.stdout, r.stderr


try:
    for delayed in [False, True]:
        for kind in KINDS:
            name = kind + ('-delay' if delayed else '-zero'); work = out / name; work.mkdir(exist_ok=True)
            row = dict(status='RUNNING', variants={}); report['cases'][name] = row
            for variant in ['named', 'unnamed', 'mixed']:
                code, expected = make(kind, variant, delayed)
                source = work / (variant + '.v'); source.write_text(code)
                cpp = work / (variant + '.cpp')
                run([compiler, source, '--wave-support', '--emit-cpp', cpp, '-o', work / variant], work, variant + '-compile')
                if variant != 'named':
                    assert cpp.read_bytes() == (work / 'named.cpp').read_bytes(); report['entire_cpp_identities'] += 1
                elif a.baseline:
                    previous = work / 'previous.cpp'
                    run([a.baseline.resolve(), source, '--wave-support', '--emit-only', '--emit-cpp', previous], work, 'previous')
                    assert cpp.read_bytes() == previous.read_bytes(); report['prior_named_cpp_identities'] += 1
                observed = run([work / variant], work, variant + '-none')
                assert observed[0].splitlines() == expected, (name, variant, observed[0], expected)
                report['independent_truth_patterns'] += len(expected)
                for mode in ['ordered', 'settled']:
                    for codec, suffix in [('vcd', 'vcd'), ('raw', 'dwf'), ('zstd', 'dwf')]:
                        label = variant + '-' + mode + '-' + codec; wave = work / (label + '.' + suffix)
                        wave.unlink(missing_ok=True)
                        cmd = [work / variant, '--waveform', wave, '--wave-format', suffix, '--wave-mode', mode,
                               '--wave-block-events', '7']
                        if suffix == 'dwf': cmd += ['--wave-codec', codec]
                        if codec == 'zstd': cmd += ['--wave-compression-jobs', '4']
                        assert run(cmd, work, label) == observed
                        compare(work / ('named-' + mode + '-vcd.vcd'), wave); report['captures'] += 1
                row['variants'][variant] = dict(status='PASS', source_sha256=digest(source), cpp_sha256=digest(cpp),
                                               binary_sha256=digest(work / variant))
            row['status'] = 'PASS'; print('PASS primitive group', name, flush=True)
    rejected = {
        'empty': 'buf();', 'single-port': 'buf(q);', 'missing-group': 'buf;',
        'trailing-comma': 'and(q,a,b),;', 'missing-terminal': 'and(q,a,);',
        'array-width': 'buf g[1:0](q,{a,b,a});', 'third-logic-delay': 'and #(1,2,3)(q,a,b);',
        'too-many-tristate': 'bufif1(q,a,b,a);', 'negative-delay': 'buf #(-1)(q,a);',
        'weak-strength': 'buf (weak1,weak0)(q,a);',
    }
    for name, declaration in rejected.items():
        work = out / ('reject-' + name); work.mkdir(exist_ok=True)
        source = work / 'top.v'; source.write_text('module top;reg a,b;wire q;' + declaration + 'endmodule\n')
        cpp = work / 'model.cpp'
        cpp.unlink(missing_ok=True)
        run([compiler, source, '--emit-only', '--emit-cpp', cpp], work, 'compile', success=False)
        assert not cpp.exists()
    report.update(status='PASS', rejected=list(rejected))
finally:
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
