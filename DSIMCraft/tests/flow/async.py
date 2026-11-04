"""The six real tool flows expose async DWF controls without touching other modes."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from compare_waveforms import compare

compiler = Path(sys.argv[1]).resolve()
base = Path(sys.argv[2]).resolve(); base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))
original = json.loads((root / 'tests/flow/manifest.json').read_text())
report = dict(status='RUNNING', directory=str(out), cases=6, executions=0, identical_files=0, invalid_options=0)


def save():
    for path in [out / 'results.json', base / 'results.json']: path.write_text(json.dumps(report, indent=2) + '\n')


def absolute_cases():
    cases = json.loads(json.dumps(original['cases']))
    for case in cases:
        for key in ['sources', 'liberty', 'gate_models']:
            if key in case: case[key] = [str((root / 'tests/flow' / f).resolve()) for f in case[key]]
        for key in ['gate_netlist', 'sdf']:
            if key in case: case[key] = str((root / 'tests/flow' / case[key]).resolve())
    return cases


def flow(cases, label, success=True):
    manifest = out / (label + '.json'); manifest.write_text(json.dumps(dict(cases=cases), indent=2) + '\n')
    work = out / label
    command = [sys.executable, str(root / 'scripts/run_flow.py'), str(manifest), '--dsim', str(compiler), '--output', str(work)]
    (out / (label + '.command.json')).write_text(json.dumps(command) + '\n')
    r = subprocess.run(command, capture_output=True, text=True, timeout=600)
    (out / (label + '.stdout')).write_text(r.stdout); (out / (label + '.stderr')).write_text(r.stderr)
    assert (r.returncode == 0) == success, (label, r.stdout, r.stderr)
    results = list(work.glob('run-*/results.json')); assert len(results) == 1
    summary = json.loads(results[0].read_text()); assert summary['status'] == ('PASS' if success else 'FAIL')
    return results[0].parent, summary


try:
    save(); reference = None
    for jobs in [1, 4, 16]:
        cases = absolute_cases()
        for case in cases: case.update(wave_compression_jobs=jobs, wave_block_events=1)
        work, summary = flow(cases, 'jobs-' + str(jobs))
        assert len(summary['cases']) == 6
        for name, row in summary['cases'].items():
            assert row['status'] == 'PASS' and row['wave_controls'] == dict(wave_compression_jobs=jobs, wave_block_events=1)
            for mode in ['none', 'vcd', 'dwf']:
                command = row['stages']['native-' + mode]['command']
                for flag, value in [('--wave-compression-jobs', jobs), ('--wave-block-events', 1)]:
                    assert (flag in command) == (mode == 'dwf')
                    if mode == 'dwf': assert command[command.index(flag) + 1] == str(value)
            compare(work / name / 'native.vcd', work / name / 'native.dwf')
            if reference:
                before, previous = reference
                assert row['trace'] == previous['cases'][name]['trace']
                assert (work / name / 'native.dwf').read_bytes() == (before / name / 'native.dwf').read_bytes()
                report['identical_files'] += 1
            report['executions'] += 1
        if reference is None: reference = work, summary
        save()
    for key, values in [('wave_compression_jobs', [0, 17, True, 1.5, '4']),
                        ('wave_block_events', [0, 1000001, True, 1.5, '1'])]:
        for value in values:
            case = absolute_cases()[0]; case[key] = value
            work, summary = flow([case], 'invalid-' + str(report['invalid_options']), False)
            row = summary['cases'][case['name']]
            assert row['error'].startswith(key + ' must be an integer in ')
            assert not row.get('stages') and not (work / case['name'] / 'native').exists()
            report['invalid_options'] += 1
    assert report['executions'] == 18 and report['identical_files'] == 12 and report['invalid_options'] == 10
    report['status'] = 'PASS'
finally:
    save()
print('PASS six complete flows × three compression policies,12 byte identities,10 early option rejections')
