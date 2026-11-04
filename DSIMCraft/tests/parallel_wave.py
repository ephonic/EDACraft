"""Decode every native codec against an independent four-state event model."""
from collections import defaultdict
from pathlib import Path
import json
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / 'waveform'))
from reader import declarations, read, timeline

mask = (1 << 257) - 1
X, Z = (mask, mask), (0, mask)


def bit(code):
    return [(0, 0), (1, 0), (1, 1), (0, 1)][code]


def resolve(a, b):
    if a == 3:
        return b
    if b == 3:
        return a
    return a if a == b and a != 2 else 2


def expected(scenario, window, scope):
    end = 6 if scenario == 'finish' else 0 if scenario == 'finish0' else 20
    committed = True
    if scenario == 'failure':
        end = 3 // window * window - 1
        committed = end >= 0
        end = max(end, 0)
    selected = [p for p in range(4) if not scope or scope == 'top.p' + str(p)]
    initial = [v for _ in selected for v in [X, bit(3)]]
    ranks = {(p, pin): rank * 2 + pin for rank, p in enumerate(selected) for pin in range(2)}
    changes = []
    for p in range(4):
        data, flag, drivers = X, 3, [3, 3]
        period = p % 3 + 1
        for pc in range(12):
            t = pc * period
            if not committed or t > end or (scenario.startswith('finish') and p > 1 and t == end):
                break

            def put(pin, value):
                if (p, pin) in ranks:
                    changes.append((t, p, len(changes), ranks[p, pin], value))

            first = [X, Z, ((1 << 256) | (pc + p), 0),
                     ((1 << 256) | pc, ((1 << 64) - 1) << 64)][pc % 4]
            if data != first:
                data = first
                put(0, data)
            for index, code in [(0, (pc + p) % 4), (1, 3 if pc % 3 else 1)]:
                drivers[index] = code
                updated = resolve(*drivers)
                if updated != flag:
                    flag = updated
                    put(1, bit(flag))
            if scenario.startswith('finish') and p == 1 and t == end:
                break  # finish in Active leaves this tick's NBA unapplied.
            nba = (pc + 16 * p, 0)
            if data != nba:
                data = nba
                put(0, data)
    changes.sort(key=lambda e: e[:3])
    return initial, [(t, ident, value) for t, _, _, ident, value in changes], end


def stream(initial, changes, end, mode):
    events = [(0, 'time', None)]
    now = 0

    def time(t):
        nonlocal now
        if now != t:
            events.append((t, 'time', None))
            now = t

    grouped = defaultdict(list)
    for t, ident, value in changes:
        grouped[t].append((ident, value))
    if mode == 'ordered':
        events += [(0, 'control', ['$dumpvars'])]
        events += [(0, 'value', (i, v)) for i, v in enumerate(initial)]
        events += [(0, 'control', ['$end'])]
        for t in sorted(grouped):
            time(t)
            events.extend((t, 'value', pair) for pair in grouped[t])
    else:
        state, last = list(initial), [None] * len(initial)
        for t in sorted({0, *grouped}):
            order = list(range(len(initial))) if t == 0 else []
            for ident, value in grouped[t]:
                state[ident] = value
                if ident not in order:
                    order.append(ident)
            time(t)
            if t == 0:
                events.append((0, 'control', ['$dumpvars']))
            for ident in order:
                if state[ident] != last[ident]:
                    events.append((t, 'value', (ident, state[ident])))
                    last[ident] = state[ident]
            if t == 0:
                events.append((0, 'control', ['$end']))
    time(end)
    return events


def main():
    binary, base = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='run-', dir=base))

    rows = []
    captures = 0
    for scenario in ['direct', 'normal', 'finish', 'finish0', 'failure', 'channels', 'filtered']:
        for mode in ['ordered', 'settled']:
            reference = None
            for workers, window in [(1, 1), (2, 3), (4, 32)]:
                current = None
                scope = 'top.p2' if scenario == 'filtered' else ''
                actual_scenario = 'normal' if scenario == 'filtered' else scenario
                for codec in ['vcd', 'raw', 'zstd']:
                    stem = f'{scenario}-{mode}-{workers}-{window}-{codec}'
                    path = out / (stem + ('.vcd' if codec == 'vcd' else '.dwf'))
                    command = [str(binary), actual_scenario, str(workers), str(window), str(path), mode, codec]
                    if scope:
                        command.append(scope)
                    result = subprocess.run(command, text=True, capture_output=True, timeout=60)
                    (out / (stem + '.command.json')).write_text(json.dumps(command) + '\n')
                    (out / (stem + '.stdout')).write_text(result.stdout)
                    (out / (stem + '.stderr')).write_text(result.stderr)
                    assert result.returncode == 0, (command, result.stderr)
                    capture = read(path)
                    meta, events = capture
                    assert ['$timescale', '1ps', '$end'] in meta['header']
                    decl = declarations(meta)
                    if scenario == 'channels':
                        assert len(decl) == 5
                        target = timeline(meta, events)[('top', 'dest')][2]
                        assert target == [(0, bit(3)), (4, bit(2)), (7, bit(1)), (12, bit(0)),
                                          (17, bit(2)), (27, bit(0)), (32, bit(1))], target
                        assert max(t for t, _, _ in events) == 40
                    else:
                        initial, changes, end = expected(actual_scenario, window, scope)
                        oracle = stream(initial, changes, end, mode)
                        assert events == oracle, (stem, next(((i, a, b) for i, (a, b) in enumerate(zip(events, oracle)) if a != b), (len(events), len(oracle))))
                        for p in ([2] if scope else range(4)):
                            prefix = ('top', 'p' + str(p))
                            assert decl[prefix + ('flag',)][0] == decl[prefix + ('escaped.alias[0]',)][0]
                            assert decl[prefix + ('data',)][1:] == (257, ['[256:0]'])
                    if current is None:
                        current = (result.stdout, capture)
                    assert current == (result.stdout, capture), stem
                    captures += 1
                comparable = timeline(*current[1]) if scenario == 'channels' else current[1]
                if scenario != 'failure':
                    if reference is None:
                        reference = comparable
                    assert reference == comparable, (scenario, mode, workers, window)
                rows.append(dict(scenario=scenario, mode=mode, workers=workers, window=window, status='PASS'))
            print('PASS global waveform independent oracle', scenario, mode, flush=True)

    # The output backend must protect an existing file even when attachment fails.
    protected = out / 'direct-ordered-1-1-vcd.vcd'
    before = protected.read_bytes()
    result = subprocess.run([str(binary), 'normal', '1', '1', str(protected), 'ordered', 'vcd'], capture_output=True, text=True)
    assert result.returncode != 0 and protected.read_bytes() == before
    command = [str(binary), 'attachment', '1', '1', str(out / 'partial-attachment.vcd'), 'ordered', 'vcd']
    result = subprocess.run(command, text=True, capture_output=True, timeout=60)
    (out / 'attachment.command.json').write_text(json.dumps(command) + '\n')
    (out / 'attachment.stdout').write_text(result.stdout)
    (out / 'attachment.stderr').write_text(result.stderr)
    assert result.returncode == 0 and result.stdout == 'PASS attachment cleanup\n', result.stderr
    (base / 'results.json').write_text(json.dumps(dict(status='PASS', directory=str(out), cases=rows,
        captures=captures, independent_oracle=True, shared_file_per_run=True, partial_attachment_cleanup=True), indent=2) + '\n')


if __name__ == "__main__":
    main()
