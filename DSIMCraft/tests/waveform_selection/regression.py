"""User-selected declarations and inclusive windows across native wave paths."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/waveform'))
from reader import read, declarations
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_waveforms import compare

compiler = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
cache = Path(sys.argv[3]) if len(sys.argv) > 3 else compiler.parent / 'CMakeCache.txt'
config = {s.split('=', 1)[0].split(':', 1)[0]: s.split('=', 1)[1]
          for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
report = dict(status='RUNNING', captures=0, byte_identical_pairs=0, rejected_options=0,
              rejected_manifests=0, cases={}, rollbacks=0, commits=0)
def save():
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
def run(command, work, label, ok=True):
    p = subprocess.run(list(map(str, command)), cwd=work, text=True, capture_output=True, timeout=180)
    (work / (label + '.stdout')).write_text(p.stdout)
    (work / (label + '.stderr')).write_text(p.stderr)
    assert p.returncode >= 0 and (p.returncode == 0) == ok, (label, p.returncode, p.stdout, p.stderr)
    return p.stdout, p.stderr
def model(command, work, name='sim'):
    exe = work / name
    run([compiler, *command, '--wave-support', '--emit-cpp', work / (name + '.cpp'), '-o', exe], work, name + '-compile')
    return exe
def streams(path):
    meta, events = read(path)
    values = [[] for _ in meta['signals']]
    for time, kind, payload in events:
        if kind == 'value':
            values[payload[0]].append((time, payload[1]))
    return meta, events, {key: (width, ranges, values[ident])
                          for key, (ident, width, ranges) in declarations(meta).items()}
def capture(exe, work, label, mode, fmt, flags):
    path = work / (label + '.' + fmt)
    stdout, stderr = run([exe, '--waveform', path, '--wave-mode', mode, '--wave-block-events', 3, *flags], work, label)
    report['captures'] += 1
    return path, stdout, stderr
def glob(pattern, name):
    return re.fullmatch(re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.'), name) is not None
def wanted(key, scopes=(), depth=0, include=(), exclude=()):
    hierarchy, full = key[:-1], '.'.join(key)
    roots = [tuple(s.split('.')) for s in scopes] if scopes else [hierarchy[:1]]
    return (any(hierarchy[:len(root)] == root and (not depth or len(hierarchy)-len(root) < depth) for root in roots)
            and (not include or any(glob(p, full) for p in include))
            and not any(glob(p, full) for p in exclude))
def projected(base_events, changes, start, end):
    times = [t for t, _, _ in base_events]
    if not times or max(times) < start or min(times) > end:
        return []
    result = []
    if min(times) < start:
        previous = [value for t, value in changes if t < start]
        assert previous, 'initial state missing from baseline'
        result.append((start, previous[-1]))
    return result + [(t, v) for t, v in changes if start <= t <= end]

try:
    save()
    spec = importlib.util.spec_from_file_location('sdf_cases', ROOT / 'tests/sdf_zero_input/cases.py')
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    cases.make(out / 'sdf-inputs')
    sdf = out / 'sdf-inputs/ic-zero-with-path'
    source = (sdf / 'tb.v').read_text().replace(',e(a,b,ze)', '')
    source = '\n'.join(s for s in source.splitlines() if not s.startswith(('initial begin $sdf_annotate', 'always @')))
    source = source.replace('$display("TRACE t=%0t d=%b e=%b",$time,d.u0.A,e.u0.A);', '')
    (sdf / 'native.v').write_text(source + '\n')
    fixtures = [
        ('hierarchy', [ROOT / 'tests/waveform_selection/hierarchy.sv'], (2, 6)),
        ('wheel', [ROOT / 'tests/waveform_selection/hierarchy.sv', '--time-wheel'], (2, 6)),
        ('dump', [ROOT / 'tests/waveform_selection/dump.sv'], (2, 4)),
        ('late', [ROOT / 'tests/waveform_selection/late.sv'], (2, 6)),
        ('parallel', [ROOT / 'tests/uvm_containers/parallel.sv', '--threads', 2], (1000, 3500)),
        ('sdf', ['--gate-netlist', sdf/'net.v', '--gate-top', 'dut', '--liberty', sdf/'cells.lib',
                 '--gate-models', sdf/'cells.v', '--sdf-annotate', sdf/'delay.sdf',
                 '--gate-scalar-timing', '--gate-sdf-jobs', '--gate-fold-zero-inputs', sdf/'native.v'], (11, 35))]
    for name, command, (start, end) in fixtures:
        work = out / name
        work.mkdir(exist_ok=True)
        exe = model(command, work)
        if name == 'parallel':
            _, stats = run([exe, '--parallel-stats'], work, 'partitions')
            assert '"partitions":2' in stats
        for mode in ['ordered', 'settled']:
            baseline, stdout, _ = capture(exe, work, mode + '-full', mode, 'vcd', [])
            meta, events, full = streams(baseline)
            intervals = [(start, end), (start+1, start+1), (0, 0), (0, 2**64-1), (999999, 1000000)]
            if name == 'late':
                intervals += [(0, 3)]  # $dumpvars starts after the requested end.
            for i, (first, last) in enumerate(intervals):
                flags = ['--wave-start', first, '--wave-end', last]
                paths = []
                for kind, fmt, extra in [('vcd', 'vcd', []), ('sync', 'dwf', []),
                                          ('async', 'dwf', ['--wave-async', '--wave-buffer-bytes', 4096])]:
                    p, text, _ = capture(exe, work, f'{mode}-window-{i}-{kind}', mode, fmt, flags + extra)
                    assert text == stdout
                    _, actual_events, actual = streams(p)
                    assert set(actual) == set(full)
                    assert all(first <= t <= last for t, _, _ in actual_events)
                    for key, (width, ranges, changes) in full.items():
                        assert actual[key] == (width, ranges, projected(events, changes, first, last)), (name, mode, first, last, key, actual[key])
                    controls = [(t, payload) for t, kind, payload in actual_events if kind == 'control']
                    expected = [(t, p) for t, k, p in events if k == 'control' and first <= t <= last]
                    if events and min(t for t, _, _ in events) < first <= max(t for t, _, _ in events):
                        expected = [(first, ['$dumpvars']), (first, ['$end'])] + expected
                    assert controls == expected, (name, first, last, controls, expected)
                    paths.append(p)
                compare(paths[0], paths[1]);compare(paths[1], paths[2])
                assert paths[1].read_bytes() == paths[2].read_bytes()
                report['byte_identical_pairs'] += 1
            if name in ('hierarchy', 'dump'):
                selections = [
                    dict(scopes=['top.u', 'top.v'], depth=1),
                    dict(scopes=['top.u', 'top.u.inner', 'top.v'], depth=1),
                    dict(include=['top.u.data', 'top.v.mem[1]', 'top.u.escaped.name[0]']),
                    dict(include=['top.?.*'], exclude=['*.inner.*', '*.alias_*', '*.mem[0]']),
                    dict(scopes=['top.u'], include=['*data', '*count']),
                    dict(depth=1),
                ] if name == 'hierarchy' else [dict(scopes=['top.u']), dict(include=['top.?.q'], exclude=['top.v.*'])]
                for i, select in enumerate(selections):
                    flags = []
                    for key, option in [('scopes', '--wave-scope'), ('include', '--wave-include'), ('exclude', '--wave-exclude')]:
                        for value in select.get(key, []): flags += [option, value]
                    if 'depth' in select: flags += ['--wave-depth', select['depth']]
                    expected = {key: value for key, value in full.items() if wanted(key, **select)}
                    assert expected
                    paths = []
                    for fmt, extra in [('vcd', []), ('dwf', ['--wave-async'])]:
                        path, text, _ = capture(exe, work, f'{mode}-selection-{i}-{fmt}', mode, fmt, flags+extra)
                        assert text == stdout
                        assert streams(path)[2] == expected, (mode, select, streams(path)[2].keys(), expected.keys())
                        paths.append(path)
                    compare(*paths)
                if name == 'hierarchy':
                    keys = {'.'.join(key) for key in full}
                    assert {'top.u.data', 'top.v.mem[1]', 'top.u.escaped.name[0]', 'top.u.inner.count'} <= keys, keys
        report['cases'][name] = 'PASS';save()
    for mode in ['ordered', 'settled']:
        assert streams(out/'hierarchy'/(mode+'-full.vcd'))[2] == streams(out/'wheel'/(mode+'-full.vcd'))[2]
    # Only committed changes may enter either selected output window.
    work = out/'hierarchy'
    code = (work/'sim.cpp').read_text();assert code.count('\ns.run();\n') == 1
    code = code.replace('\ns.run();\n', '''
s.run_until(1);
if(s.predict_until(4,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected prediction commit");
if(!s.predict_until(6,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("prediction not committed");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("transaction counts");
s.run();
''')
    (work/'replay.cpp').write_text(code)
    flags = ['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx', 'icpc') else []
    run([config['DSIM_MODEL_CXX'], '-std=c++17', '-O2', '-pthread', *flags, '-I'+str(ROOT/'include'),
         '-I'+config['DSIM_ZSTD_INCLUDE'], work/'replay.cpp', config['DSIM_ZSTD_LIBRARY'], '-o', work/'replay'], work, 'replay-compile')
    for mode in ['ordered', 'settled']:
        path, _, _ = capture(work/'replay', work, mode+'-replay', mode, 'dwf', ['--wave-start', 2, '--wave-end', 6, '--wave-async'])
        compare(path, work/(mode+'-window-0-async.dwf'))
    report['rollbacks'] += 1;report['commits'] += 1
    # Bad selection/configuration must fail before creating the requested file.
    invalid = [['--wave-scope', ''], ['--wave-include', ''], ['--wave-exclude', ''],
               ['--wave-scope', 'top.absent'], ['--wave-include', 'top.absent'], ['--wave-exclude', '*'],
               ['--wave-start', 5, '--wave-end', 4], ['--wave-start', -1], ['--wave-end', 'x'],
               ['--wave-start', 2**64], ['--wave-depth', 10001]]
    for flags in invalid:
        i = report['rejected_options'];path = out / f'bad-{i}.dwf'
        run([out/'hierarchy/sim', '--waveform', path, *flags], out, f'bad-{i}', False)
        assert not path.exists();report['rejected_options'] += 1
    # Real JSON flow applies selectors to both waveform formats, never the baseline.
    flow = dict(name='selection', sources=[str(ROOT/'tests/waveform_selection/hierarchy.sv')],
                wave_scopes=['top.u', 'top.v'], wave_include=['*data', '*mem[1]'],
                wave_exclude=['*alias*'], wave_depth=1, wave_start=2, wave_end=6,
                wave_async=True, wave_buffer_bytes=4096)
    manifest = out/'flow.json';manifest.write_text(json.dumps(dict(cases=[flow])))
    run([sys.executable, ROOT/'scripts/run_flow.py', manifest, '--dsim', compiler, '--output', out/'flow'], out, 'flow')
    flow_report = json.loads(next((out/'flow').glob('run-*/results.json')).read_text())
    row = flow_report['cases']['selection'];assert row['status'] == 'PASS'
    assert all(not str(a).startswith('--wave-') for a in row['stages']['native-none']['command'])
    actual = streams(Path(flow_report['directory'])/'selection/native.dwf')[2]
    assert {'.'.join(key) for key in actual} == {'top.u.data', 'top.u.mem[1]', 'top.v.data', 'top.v.mem[1]'}
    spec = importlib.util.spec_from_file_location('flow', ROOT/'scripts/run_flow.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for overrides in [dict(wave_scopes='top'), dict(wave_include=[]), dict(wave_exclude=[3]),
                      dict(wave_include=['']), dict(wave_start=True), dict(wave_end=-1),
                      dict(wave_depth=10001), dict(wave_start=4, wave_end=3), dict(wave_end=2**64)]:
        try: module.run_case(dict(flow, **overrides), ROOT, out, compiler, False, 1, {})
        except ValueError: report['rejected_manifests'] += 1
        else: raise AssertionError(overrides)
    report['cases']['json_flow'] = 'PASS'
    report['status'] = 'PASS'
finally:
    save()
print('PASS waveform selection:', report['captures'], 'captures,', report['byte_identical_pairs'], 'byte-identical pairs')
