"""Recover actual native compressed captures and reject complete damaged blocks."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

from reader import ROOT, dwf, read

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('compiler', type=Path)
p.add_argument('out', type=Path)
a = p.parse_args()
compiler, base = a.compiler.resolve(), a.out.resolve()
base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base))


def run(command, work, log, success=True):
    r = subprocess.run(list(map(str, command)), cwd=work, text=True,
                       capture_output=True, timeout=180)
    (work / (log + '.stdout')).write_text(r.stdout)
    (work / (log + '.stderr')).write_text(r.stderr)
    assert (r.returncode == 0) == success, (command, r.stdout, r.stderr)
    return r


records = []
attempts = 0


def recover_cuts(path, label, kind='native'):
    global attempts
    original = path.read_bytes()
    with path.open('rb') as src:
        r = dwf.Reader(src)
        blocks = [r.block(i)[1] for i in range(len(r.index))]
        meta, index, index_offset = r.meta, r.index, r.index_offset
    cuts = {len(original), index_offset, len(original) - 1, len(original) - 16,
            index_offset + 4, index_offset + dwf.RECORD.size + 1}
    for row in index:
        # In a record header, in its payload and immediately after it.
        cuts.update([row[2] + 3, row[2] + dwf.RECORD.size - 1,
                     row[3] - 1, row[3]])
    for number, cut in enumerate(sorted(c for c in cuts if 0 <= c <= len(original))):
        broken = path.parent / f'{label}-{number}.broken'
        recovered = path.parent / f'{label}-{number}.recovered.dwf'
        broken.write_bytes(original[:cut])
        expected = [event for row, events in zip(index, blocks) if row[3] <= cut for event in events]
        report = dwf.recover(broken, recovered)
        attempts += 1
        assert report['events_recovered'] == len(expected)
        assert report['blocks_recovered'] == sum(row[3] <= cut for row in index)
        assert recovered.read_bytes()[:report['copied_prefix_bytes']] == original[:report['copied_prefix_bytes']]
        with recovered.open('rb') as src:
            rr = dwf.Reader(src)
            assert rr.meta == meta and list(rr.events()) == expected
            # Keep every event at an equal-time block boundary in a window.
            for start in sorted({0, report['last_complete_time']}):
                before = [None] * len(meta['signals'])
                for t, event_kind, payload in expected:
                    if t < start and event_kind == 'value':
                        before[payload[0]] = payload[1]
                assert rr.window(start, start) == (before, [e for e in expected if e[0] == start])
        assert broken.read_bytes() == original[:cut]
    records.append(dict(name=label, kind=kind, status='PASS', blocks=len(index), events=sum(map(len, blocks)),
                        cuts=len(cuts), bytes=len(original)))


# Native captures include wide four-state RTL delay and SDF/check state.
spec = importlib.util.spec_from_file_location('checks', ROOT / 'tests/timing_checks/cases.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.make(out / 'checks')
cases = {'rtl': [compiler, ROOT / 'tests/time/intra_assignment.v'],
         'sdf': [compiler, '--gate-netlist', out / 'checks/composed/net.v', '--gate-top', 'dut',
                 '--liberty', out / 'checks/composed/cells.lib', '--gate-models', out / 'checks/composed/cells.v',
                 '--sdf-annotate', out / 'checks/composed/delay.sdf', out / 'checks/composed/tb.v']}
for name, command in cases.items():
    w = out / name
    w.mkdir()
    run(command + ['--wave-support', '-o', w / 'native'], w, 'compile')
    for mode in ['ordered', 'settled']:
        reference = w / (mode + '.vcd')
        run([w / 'native', '--waveform', reference, '--wave-format', 'vcd', '--wave-mode', mode], w, mode + '-vcd')
        for codec in ['raw', 'zstd']:
            path = w / f'{mode}-{codec}.dwf'
            run([w / 'native', '--waveform', path, '--wave-mode', mode,
                 '--wave-codec', codec, '--wave-block-events', 7], w, mode + '-' + codec)
            assert read(path) == read(reference)
            recover_cuts(path, name + '-' + mode + '-' + codec)
    print('PASS native recovery full ordered/settled events and windows', name, flush=True)

# A native Zstd index whose frame is damaged can be rebuilt from good blocks.
path = out / 'rtl/ordered-zstd.dwf'
with path.open('rb') as src:
    original_reader = dwf.Reader(src)
    expected_events = list(original_reader.events())
    index_offset = original_reader.index_offset
bad = bytearray(path.read_bytes())
assert dwf.RECORD.unpack(bad[index_offset:index_offset + dwf.RECORD.size])[1] == 2
bad[index_offset + dwf.RECORD.size] ^= 1
(out / 'zstd-index.bad').write_bytes(bad)
report = dwf.recover(out / 'zstd-index.bad', out / 'zstd-index.dwf')
assert not report['original_finalization_valid']
with (out / 'zstd-index.dwf').open('rb') as src:
    assert list(dwf.Reader(src).events()) == expected_events

# Controls and empty/equal-time records are part of the retained prefix too.
proto_meta = {'schema': 'dsim.wave.prototype.v1', 'signals': [{'code': '!', 'width': 1}],
              'header': [['$var', 'wire', '1', '!', 'q', '$end'], ['$enddefinitions', '$end']]}
proto_events = [(0, 'time', None), (0, 'control', ['$dumpvars']),
                (0, 'value', (0, (1, 1))), (0, 'control', ['$end']),
                (0, 'time', None), (0, 'value', (0, (0, 0))),
                (0, 'value', (0, (1, 0))), (0, 'value', (0, (0, 0))),
                (4, 'time', None), (4, 'control', ['$dumpoff']),
                (4, 'value', (0, (1, 1))), (4, 'control', ['$end']),
                (5, 'time', None), (5, 'control', ['$comment', 'retained', '$end'])]
for codec in ['raw', 'zlib', 'zstd']:
    path = out / ('controls-' + codec + '.dwf')
    with path.open('wb') as dest:
        writer = dwf.Writer(dest, proto_meta, codec, 2)
        for event in proto_events:
            writer.append(event)
        writer.close()
    with path.open('rb') as src:
        assert list(dwf.Reader(src).events()) == proto_events
    recover_cuts(path, 'controls-' + codec, kind='prototype-controls')

# A complete record with bad CRC/semantics must fail, not be skipped as a tail.
w = out / 'invalid'
w.mkdir()
meta = {'schema': 'dsim.wave.prototype.v1', 'signals': [{'code': '!', 'width': 1}],
        'header': [['$enddefinitions', '$end']]}
data = io.BytesIO()
writer = dwf.Writer(data, meta, 'raw', 2)
for event in [(0, 'time', None), (0, 'value', (0, (0, 0))),
              (3, 'time', None), (3, 'value', (0, (1, 0)))]:
    writer.append(event)
writer.close()
original = data.getvalue()
r = dwf.Reader(io.BytesIO(original))
for label, offset in [('metadata-crc', len(dwf.MAGIC) + dwf.RECORD.size),
                      ('block-crc', r.index[1][2] + dwf.RECORD.size)]:
    bad = bytearray(original)
    bad[offset] ^= 1
    src, dest = w / (label + '.bad'), w / (label + '.dwf')
    src.write_bytes(bad)
    try:
        dwf.recover(src, dest)
        raise AssertionError('corrupt complete record accepted')
    except ValueError:
        assert not dest.exists()
# Recompute the CRC after introducing a wrong checkpoint, to test semantics.
bad = bytearray(original)
offset = r.index[1][2]
tag, codec, raw_len, stored_len, _ = dwf.RECORD.unpack(bad[offset:offset + dwf.RECORD.size])
bad[offset + dwf.RECORD.size] = 1
raw = bytes(bad[offset + dwf.RECORD.size:offset + dwf.RECORD.size + stored_len])
bad[offset:offset + dwf.RECORD.size] = dwf.RECORD.pack(tag, codec, raw_len, stored_len, zlib.crc32(raw))
(w / 'checkpoint.bad').write_bytes(bad)
run([sys.executable, ROOT / 'experiments/waveform/dwf.py', 'recover', w / 'checkpoint.bad',
     w / 'checkpoint.dwf'], w, 'checkpoint', False)
assert not (w / 'checkpoint.dwf').exists()
# An invalid final index is replaceable; all data events remain verified.
bad = bytearray(original)
bad[r.index_offset + dwf.RECORD.size] ^= 1
(w / 'index.bad').write_bytes(bad)
report = run([sys.executable, ROOT / 'experiments/waveform/dwf.py', 'recover',
              w / 'index.bad', w / 'index.dwf'], w, 'index')
assert not json.loads(report.stdout)['original_finalization_valid']
with (w / 'index.dwf').open('rb') as src:
    assert list(dwf.Reader(src).events()) == list(dwf.Reader(io.BytesIO(original)).events())
for number, invalid in enumerate([1, {}, ['bad-row'], [[True, 0, 0, 0, 0]]]):
    malformed = io.BytesIO(original[:r.index_offset])
    malformed.seek(0, 2)
    offset = dwf.write_record(malformed, b'INDX', dwf.json_bytes(invalid), 'raw')
    malformed.write(dwf.FOOTER.pack(offset, dwf.END))
    source, dest = w / f'index-shape-{number}.bad', w / f'index-shape-{number}.dwf'
    source.write_bytes(malformed.getvalue())
    assert not dwf.recover(source, dest)['original_finalization_valid']
    with dest.open('rb') as src:
        assert list(dwf.Reader(src).events()) == list(dwf.Reader(io.BytesIO(original)).events())
run([sys.executable, ROOT / 'experiments/waveform/dwf.py', 'recover', w / 'index.bad', w / 'index.dwf'],
    w, 'no-clobber', False)
assert (w / 'index.bad').read_bytes() == bad

# Both Python backends obey the same single-frame and decompression bounds.
backend_names = []
for name, backend in [('selected', dwf.zstd), ('system', dwf._system_zstd())]:
    if backend is None:
        continue
    payload = b'compressed waveform' * 100
    packed = backend.compress(payload, level=3)
    assert backend.ZstdDecompressor().decompress(packed, max_length=len(payload) + 1) == payload
    backend_names.append(name)
selected = dwf.zstd
try:
    dwf.zstd = dwf._system_zstd()
    assert dwf.zstd is not None
    recover_cuts(out / 'rtl/ordered-zstd.dwf', 'system-native-zstd', kind='system-backend')
finally:
    dwf.zstd = selected
report = dict(status='PASS', run_directory=str(out),
              native_cases=[r for r in records if r['kind'] == 'native'],
              other_cases=[r for r in records if r['kind'] != 'native'],
              recovery_attempts=attempts, codec_backends=backend_names,
              complete_corruption_rejected=True, index_repair=True, no_clobber=True)
(base / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS recovery checks', attempts, 'backend checks', backend_names, flush=True)
