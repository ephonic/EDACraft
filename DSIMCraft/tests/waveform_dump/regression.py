"""Actual testbench dump calls, two codecs, ordered capture and optional VCS."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from cases import make

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'scripts'))
from run_flow import physical_bits
from reader import read
from compare_waveforms import compare

p = argparse.ArgumentParser()
p.add_argument('compiler', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--vendor', type=Path)
a = p.parse_args(); compiler = a.compiler.resolve()
a.output.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='actual-', dir=a.output.resolve()))
digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
report = dict(status='RUNNING', directory=str(out), compiler_sha256=digest(compiler), cases={},
              runtime_sha256=digest(root / 'include/dsim/runtime.hpp'),
              waveform_sha256=digest(root / 'include/dsim/waveform.hpp'),
              captures=0, full_codec_comparisons=0, vendor_physical_comparisons=0,
              vendor_ordered_equivalence=False, performance_claim=False)

def run(cmd, work, label, good=True):
    cmd = list(map(str, cmd)); (work / (label + '.command.json')).write_text(json.dumps(cmd) + '\n')
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=120)
    (work / (label + '.stdout')).write_text(r.stdout); (work / (label + '.stderr')).write_text(r.stderr)
    (work / (label + '.exit')).write_text(str(r.returncode) + '\n')
    assert (r.returncode == 0) == good, (label, r.returncode, r.stdout, r.stderr)
    return r

def same(left, right):
    compare(left, right)
    report['full_codec_comparisons'] += 1

try:
    fixtures = make(out / 'inputs')
    for name, fixture in fixtures.items():
        w = out / name; w.mkdir(); source = out / 'inputs' / name / 'top.v'
        exe = w / 'simv'; cpp = w / 'model.cpp'
        run([compiler, source, '--emit-cpp', cpp, '-o', exe], w, 'compile')
        text = cpp.read_text()
        assert '#define DSIM_DUMP_TASKS_ENABLED 1\n' in text
        assert '#define DSIM_REPLICATION_ENABLED 1\n' in text
        row = dict(status='RUNNING', source_sha256=digest(source), cpp_sha256=digest(cpp), runs={})
        report['cases'][name] = row
        waves = {}
        for label, flags in [
            ('default', []),
            ('raw', ['--waveform', 'capture.dwf', '--wave-format', 'dwf', '--wave-codec', 'raw']),
            ('zstd', ['--waveform', 'capture.dwf', '--wave-format', 'dwf', '--wave-compression-jobs', '4']),
            ('ordered-vcd', ['--waveform', 'capture.vcd', '--wave-format', 'vcd', '--wave-mode', 'ordered']),
            ('ordered-dwf', ['--waveform', 'capture.dwf', '--wave-format', 'dwf', '--wave-mode', 'ordered',
                             '--wave-compression-jobs', '2'])]:
            work = w / label; work.mkdir()
            result = run([exe, *flags], work, 'run')
            files = [f for f in work.iterdir() if f.suffix in {'.vcd', '.dwf', '.dump'}]
            expected = 0 if name == 'file-only' else 1
            assert len(files) == expected, (name, label, files)
            row['runs'][label] = dict(stdout=result.stdout, wave_sha256={f.name:digest(f) for f in files})
            if files:
                wave = files[0]; meta, events = read(wave)
                waves[label] = wave; report['captures'] += 1
                row['runs'][label]['controls'] = [(t, v) for t, k, v in events if k == 'control']
                if label == 'default':
                    assert wave.name == ('verilog.dump' if name == 'default-file' else 'vcs.vcd')
        if waves:
            same(waves['default'], waves['raw']); same(waves['default'], waves['zstd'])
            same(waves['ordered-vcd'], waves['ordered-dwf'])
            if a.vendor:
                vendor = a.vendor.resolve() / name / 'run-0' / ('verilog.dump' if name == 'default-file' else 'vcs.vcd')
                assert source.read_bytes() == (a.vendor / name / 'top.v').read_bytes()
                native, reference = physical_bits(waves['default']), physical_bits(vendor)
                assert native == reference, (name, [(k, native.get(k), reference.get(k)) for k in set(native)|set(reference) if native.get(k)!=reference.get(k)])
                native_controls = [(t, v) for t, k, v in read(waves['default'])[1] if k == 'control']
                reference_controls = [(t, v) for t, k, v in read(vendor)[1] if k == 'control']
                assert native_controls == reference_controls, (name, native_controls, reference_controls)
                report['vendor_physical_comparisons'] += len(native)
        row['status'] = 'PASS'; print('PASS dump', name, flush=True)
    assert report['captures'] == 75 and report['full_codec_comparisons'] == 45
    from extras import exercise
    exercise(compiler, out, run, same, report)
    report['total_complete_captures'] = sum(1 for f in out.rglob('*') if f.suffix in {'.vcd','.dwf','.dump'} and f.parent.name!='protected')
    assert report['total_complete_captures'] == 148
    assert report['full_codec_comparisons'] == 107
    report['status'] = 'PASS'
except BaseException as error:
    report.update(status='FAIL', error=repr(error)); raise
finally:
    for f in [out / 'results.json', a.output / 'results.json']:
        f.write_text(json.dumps(report, indent=2) + '\n')
print('PASS testbench dumps,148 captures,107 complete comparisons including54 transactional captures')
