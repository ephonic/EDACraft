"""Prepared models must execute the original constraints with strict identities."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('timing_cases', ROOT/'tests/timing_checks/cases.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
sys.path.insert(0, str(ROOT/'tests/waveform'))
from reader import read


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('generator', type=Path)
    p.add_argument('compiler', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('--vcs', action='store_true')
    a = p.parse_args()
    generator, compiler, out = a.generator.resolve(), a.compiler.resolve(), a.out.resolve()
    definitions = fixtures.make(out)
    names = ['setup', 'hold', 'recovery', 'removal', 'setuphold', 'recrem', 'width',
             'period', 'skew', 'condition', 'explicit-edge', 'fourstate', 'negative',
             'edge-overrides', 'setup-edge-overrides']
    expected = json.loads((ROOT/'tests/timing_checks/expected.json').read_text())
    results = {}

    def run(command, w, log, success=True):
        r = subprocess.run(list(map(str, command)), cwd=w, capture_output=True, text=True, timeout=240)
        (w/log).write_text(r.stdout+r.stderr)
        assert (r.returncode == 0) == success, (command, r.returncode, r.stdout, r.stderr)
        return r.stdout+r.stderr

    for name in names+['alias', 'alias-delta']:
        if name.startswith('alias'):
            w = out/name
            w.mkdir(exist_ok=True)
            for f in ['cells.lib', 'net.v', 'delay.sdf', 'tb.v', 'cells.v']:
                (w/f).write_bytes((out/'condition'/f).read_bytes())
            sdf = (w/'delay.sdf').read_text().replace('(COND E D)', '(COND ENABLE D)')
            (w/'delay.sdf').write_text(sdf)
            lib = (w/'cells.lib').read_text().replace('pin(D){direction:input;}',
                'pin(D){direction:input;timing(){related_pin:"C";sdf_cond:"ENABLE";when:"E";}}')
            (w/'cells.lib').write_text(lib)
            if name == 'alias-delta':
                (w/'tb.v').write_text('`timescale 1ps/1ps\nmodule top;reg C,D,E;wire Z;dut d(C,D,E,Z);\n'
                    '`ifdef VCS_REFERENCE\ninitial $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");\n`endif\n'
                    'initial begin C=0;D=0;E=0;#100;D=1;E=1;C=1;#10;C=0;D=0;E=0;'
                    '#10;D=1;E=1;#0;C=1;#10;C=0;D=0;E=1;#10;D=1;E=0;C=1;'
                    '#10;C=0;D=0;E=0;#10;E=1;D=1;#1;C=1;#10;$display("TRACE alias done");$finish;end endmodule\n')
        else:
            w = out/name
        # Start from deliberately incorrect placeholders; the SDF stays intact.
        base = (w/'cells.v').read_text()
        base = re.sub(r'specify\b.*?\bendspecify',
                      'specify (D=>Z)=0; $hold(posedge C,D,0); endspecify', base, flags=re.S)
        (w/'base.v').write_text(base)
        for f in ['prepared.v', 'coverage.json']:
            (w/f).unlink(missing_ok=True)
        command = [generator, '--models', w/'base.v', '--sdf', w/'delay.sdf',
                   '--liberty', w/'cells.lib', '-o', w/'prepared.v', '--report', w/'coverage.json']
        run(command, w, 'prepare.log')
        coverage = json.loads((w/'coverage.json').read_text())
        assert sum(m['entries'] for m in coverage['models']) == coverage['parsed']['entries']
        assert sum(d['occurrences'] for m in coverage['models'] for d in m['declarations']) == coverage['parsed']['entries']
        # Refuse reuse, aliases of an input, and partial writes after a failure.
        before = (w/'prepared.v').read_bytes()
        run(command, w, 'no-clobber.log', False)
        assert (w/'prepared.v').read_bytes() == before
        compile_command = [compiler, '--gate-netlist', w/'net.v', '--gate-top', 'dut',
                           '--liberty', w/'cells.lib', '--gate-models', w/'prepared.v',
                           '--sdf-annotate', w/'delay.sdf', w/'tb.v', '--wave-support',
                           '--emit-ir', w/'ir.json', '-o', w/'native']
        run(compile_command, w, 'native-compile.log')
        outputs = []
        for mode in ['none', 'vcd', 'dwf']:
            command = [w/'native']
            if mode != 'none':
                dest = w/('native.'+mode)
                dest.unlink(missing_ok=True)
                command += ['--waveform', dest, '--wave-format', mode, '--wave-block-events', '7']
            outputs.append(run(command, w, 'native-'+mode+'.log'))
        assert len(set(outputs)) == 1
        assert read(w/'native.vcd') == read(w/'native.dwf')
        native = [(k, int(t)) for k, t in re.findall(r'^TIMING kind=(\w+) time=(\d+)', outputs[0], re.M)]
        if name in expected:
            assert native == [tuple(x) for x in expected[name]], (name, native, expected[name])
        elif name == 'alias':
            assert native == [tuple(x) for x in expected['condition']]
            assert coverage['models'][0]['added_condition_aliases'] == {'ENABLE': 'E'}
        row = dict(status='PASS', violations=native, full_native_waves='PASS')
        if a.vcs:
            run(['vcs', '-full64', '-sverilog', '+define+VCS_REFERENCE', '-top', 'top',
                 w/'prepared.v', w/'net.v', w/'tb.v', '-o', w/'vcs'], w, 'vcs-compile.log')
            text = run([w/'vcs', '-no_save'], w, 'vcs-run.log')
            reference = []
            for match in re.finditer(r'Timing violation[^\n]*\n\s*\$(\w+)\((.*?)\);', text, re.S):
                events = re.findall(r':\s*(\d+)', match[2].split('limit')[0])
                assert events, match[0]
                reference.append((match[1].upper(), max(map(int, events))))
            assert len(reference) == text.count('Timing violation')
            assert reference == native, (name, native, reference)
            assert [s for s in outputs[0].splitlines() if s.startswith('TRACE ')] == [s for s in text.splitlines() if s.startswith('TRACE ')]
            annotation = (w/'annotation.log').read_text()
            errors, warnings = [int(re.search(r'Total '+label+r':\s*(\d+)', annotation)[1]) for label in ['errors', 'warnings']]
            assert (errors, warnings) == ((1, 0) if name == 'negative' else (0, 0)), (name, annotation)
            row.update(vcs='PASS', annotation_errors=errors, annotation_warnings=warnings)
        results[name] = row
        print('PASS prepared model', name, flush=True)

    # Explicitly reject unresolved conditions and logic aliases. No partial outputs.
    w = out/'alias'
    for suffix, lib in [('unresolved', ''), ('logic', (w/'cells.lib').read_text().replace('when:"E"', 'when:"E&D"'))]:
        if lib:
            (w/'bad.lib').write_text(lib)
        dest, report = w/(suffix+'.v'), w/(suffix+'.json')
        dest.unlink(missing_ok=True);report.unlink(missing_ok=True)
        command = [generator, '--models', w/'base.v', '--sdf', w/'delay.sdf', '-o', dest, '--report', report]
        if lib:command += ['--liberty', w/'bad.lib']
        text = run(command, w, suffix+'.log', False)
        assert 'condition alias' in text
        assert not dest.exists() and not report.exists()
    (out/'results.json').write_text(json.dumps(dict(status='PASS', cases=results), indent=2)+'\n')


if __name__ == '__main__':
    main()
