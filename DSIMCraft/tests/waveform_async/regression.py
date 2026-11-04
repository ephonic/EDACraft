"""Independent wide values, bounded queues, worker errors and real compiled flows."""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
sys.path.insert(0, str(root / 'tests/waveform'))
from compare_waveforms import compare
from reader import read, dwf

p = argparse.ArgumentParser()
for name in ['compiler', 'writer', 'normal_kernel', 'failure_kernel', 'parallel_generic', 'parallel_compact', 'output']: p.add_argument(name, type=Path)
a = p.parse_args()
for name in ['compiler', 'writer', 'normal_kernel', 'failure_kernel', 'parallel_generic', 'parallel_compact']: setattr(a, name, getattr(a, name).resolve())
base = a.output.resolve(); base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))
report = dict(status='RUNNING', directory=str(out), byte_identical_files=0, complete_captures=0, cases={}, invalid_options=0)


def save():
    for f in [out / 'results.json', base / 'results.json']: f.write_text(json.dumps(report, indent=2) + '\n')


def run(command, label, input=None, success=True):
    command = list(map(str, command)); (out / (label + '.command.json')).write_text(json.dumps(command) + '\n')
    r = subprocess.run(command, cwd=out, input=input, text=True, capture_output=True, timeout=240)
    (out / (label + '.stdout')).write_text(r.stdout); (out / (label + '.stderr')).write_text(r.stderr)
    assert (r.returncode == 0) == success, (label, r.returncode, r.stdout, r.stderr)
    assert not any(s in r.stderr for s in ['AddressSanitizer', 'runtime error:', 'DEADLYSIGNAL'])
    return r.stdout, r.stderr


def capture(exe, label, mode, jobs, block=17, input=None, vcd=False):
    path = out / (label + ('.vcd' if vcd else '.dwf'))
    result = run([exe, '--waveform', path, '--wave-mode', mode, '--wave-format', 'vcd' if vcd else 'dwf',
                  '--wave-codec', 'zstd', '--wave-block-events', block, '--wave-compression-jobs', jobs], label, input)
    report['complete_captures'] += 1
    return path, result


def equal(left, right):
    compare(left, right); assert left.read_bytes() == right.read_bytes()
    report['byte_identical_files'] += 1


try:
    save()
    # The existing writer test validates its scalar stream against independent
    # Python integers; use that same input for both policies and many tiny blocks.
    run([sys.executable, root / 'tests/waveform/writer.py', a.writer, out / 'reference'], 'writer-oracle')
    source = (out / 'reference/events.txt').read_text()
    for mode in ['ordered', 'settled']:
        vcd, reference = capture(a.writer, 'writer-' + mode + '-vcd', mode, 1, input=source, vcd=True)
        for block in [1, 17, 16384]:
            sync, observed = capture(a.writer, f'writer-{mode}-{block}-sync', mode, 1, block, source)
            assert observed == reference; compare(vcd, sync)
            for jobs in [2, 4, 16]:
                wave, observed = capture(a.writer, f'writer-{mode}-{block}-{jobs}', mode, jobs, block, source)
                assert observed == reference; equal(sync, wave)
    report['cases']['scalar_aliases_tiny_blocks'] = 'PASS'; save()
    run([a.normal_kernel, out / 'budget'], 'budget')
    run([a.failure_kernel, out / 'worker-failure'], 'worker-failure')
    # Independent1024-bit four-state oracle, with explicit per-word PRNG order.
    mask64 = (1 << 64) - 1; mask = (1 << 1024) - 1; rng = 1017
    def next_word():
        global rng
        rng ^= (rng << 13) & mask64; rng ^= rng >> 7; rng ^= (rng << 17) & mask64
        return rng
    expected = []
    for t in range(80):
        expected.append((t, 'time', None))
        for ident in range(64):
            av = bv = 0
            for k in range(16): av |= next_word() << (64 * k); bv |= next_word() << (64 * k)
            expected.append((t, 'value', (ident, (mask, mask) if t % 5 == 0 else (av, bv))))
    assert read(out / 'budget/wide-1.dwf')[1] == expected
    for jobs in [2, 4, 16]: equal(out / 'budget/wide-1.dwf', out / f'budget/wide-{jobs}.dwf')
    for name in ['worker-failure/worker-failure', 'budget/budget-failure']:
        result = dwf.recover(out / (name + '.dwf'), out / (name + '-recovered.dwf'))
        assert result['blocks_recovered'] == result['events_recovered'] == 0
    wide = out / 'budget/wide-4.dwf'
    with wide.open('rb') as f:
        decoder = dwf.Reader(f); index = decoder.index; prefix = [e for i in range(3) for e in decoder.block(i)[1]]
    raw = wide.read_bytes(); partial = out / 'partial.dwf'; partial.write_bytes(raw[:index[3][3] - 1])
    recovered = out / 'recovered.dwf'; result = dwf.recover(partial, recovered)
    assert result['blocks_recovered'] == 3 and read(recovered)[1] == prefix
    corrupt = bytearray(raw); corrupt[index[3][2] + dwf.RECORD.size] ^= 1
    damaged = out / 'corrupt.dwf'; damaged.write_bytes(corrupt)
    try:
        read(damaged)
    except (ValueError, RuntimeError): pass
    else: raise AssertionError('corrupt complete record accepted')
    report['cases']['wide_budget_error_recovery'] = 'PASS'; save()

    tb = out / 'top.v'
    tb.write_text('`timescale 1ps/1ps\nmodule top;reg [256:0] a;wire [256:0] y;assign y=~a;'
                  "initial begin a=0;#1;a=257'h10000000000000000000000000000000000000000000000000000000000000005;"
                  "#0;a=257'h7;#3;a=257'bx;#1;a=257'bz;#3;$finish;end endmodule\n")
    fixtures = [('rtl', [tb], (1, 4, 6))]
    spec = importlib.util.spec_from_file_location('zero_input_cases', root / 'tests/sdf_zero_input/cases.py')
    generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)
    generator.make(out / 'sdf-inputs'); src = out / 'sdf-inputs/ic-zero-with-path'
    native = (src / 'tb.v').read_text().replace(',e(a,b,ze)', '')
    native = '\n'.join(line for line in native.splitlines() if not line.startswith(('initial begin $sdf_annotate', 'always @')))
    native = native.replace('$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);', '')
    (src / 'native-tb.v').write_text(native + '\n')
    fixtures.append(('sdf', ['--gate-netlist', src / 'net.v', '--gate-top', 'dut', '--liberty', src / 'cells.lib',
                            '--gate-models', src / 'cells.v', '--sdf-annotate', src / 'delay.sdf', '--gate-scalar-timing',
                            '--gate-sdf-jobs', '--gate-fold-zero-inputs', src / 'native-tb.v'], (11, 35, 75)))
    config = {line.split('=', 1)[0].split(':', 1)[0]: line.split('=', 1)[1] for line in
              (a.compiler.parent / 'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith('//')}
    for name, arguments, horizons in fixtures:
        exe = out / name; cpp = out / (name + '.cpp')
        run([a.compiler, *arguments, '--wave-support', '--emit-cpp', cpp, '-o', exe], name + '-compile')
        code = cpp.read_text(); assert code.count('\ns.run();\n') == 1
        first, wrong, accepted = horizons
        boundary = f'\ns.run_until({first});s.run_until({wrong});s.run_until({accepted});s.run();\n'
        replay = f'''
s.run_until({first});
auto rolled=s.predict_until({wrong},[](Sim& probe){{
 for(size_t i=0;i<probe.signals.size();++i){{const auto& sig=probe.signals[i];if(!sig.net)probe.set(int(i),V::x(sig.value.w));}}
}},[](const Sim&){{return false;}},[](Sim&){{}});
if(rolled||s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
if(!s.predict_until({accepted},[](Sim&){{}},[](const Sim&){{return true;}},[](Sim&){{}}))throw std::runtime_error("missing commit");
s.run();
'''
        for variant, body in [('boundary', boundary), ('replay', replay)]:
            generated = out / (name + '-' + variant + '.cpp'); generated.write_text(code.replace('\ns.run();\n', body))
            run(['c++', '-std=c++17', '-O2', '-pthread', '-I' + config['DSIM_ZSTD_INCLUDE'], generated,
                 config['DSIM_ZSTD_LIBRARY'], '-o', out / (name + '-' + variant)], name + '-' + variant + '-compile')
        for variant in ['', '-boundary', '-replay']:
            for mode in ['ordered', 'settled']:
                label = name + variant + '-' + mode
                vcd, reference = capture(out / (name + variant), label + '-vcd', mode, 1, vcd=True)
                sync, observed = capture(out / (name + variant), label + '-sync', mode, 1)
                assert observed == reference; compare(vcd, sync)
                for jobs in [2, 4]:
                    wave, observed = capture(out / (name + variant), label + '-' + str(jobs), mode, jobs)
                    assert observed == reference; equal(sync, wave)
                if variant == '-replay': equal(out / (name + '-boundary-' + mode + '-4.dwf'), out / (label + '-4.dwf'))
        report['cases'][name + '_compiled_transactions'] = 'PASS'; save()
    for backend in ['generic', 'compact']:
        for scenario in ['channels', 'direct', 'finish', 'finish0', 'failure']:
            for mode in ['ordered', 'settled']:
                stem = 'parallel-' + backend + '-' + scenario + '-' + mode
                exe = getattr(a, 'parallel_' + backend)
                for jobs in [1, 4]:
                    dest = out / (stem + '-' + str(jobs) + '.dwf')
                    result = run([exe, scenario, 4, 4, dest, mode, 'zstd', 'top', jobs], stem + '-' + str(jobs))
                    if jobs == 1: reference = result
                    else: assert result == reference; equal(out / (stem + '-1.dwf'), dest)
                    report['complete_captures'] += 1
    report['cases']['parallel_global_commits'] = 'PASS'
    for flags in [['--wave-compression-jobs', '0'], ['--wave-compression-jobs', '17'], ['--wave-compression-jobs', 'x'],
                  ['--wave-compression-jobs', '2', '--wave-codec', 'raw'], ['--wave-compression-jobs', '2', '--wave-format', 'vcd']]:
        dest = out / ('invalid-' + str(report['invalid_options']) + '.dwf')
        run([a.writer, '--waveform', dest, *flags], 'invalid-' + str(report['invalid_options']), source, False)
        assert not dest.exists(); report['invalid_options'] += 1
    report['status'] = 'PASS'
finally:
    save()
