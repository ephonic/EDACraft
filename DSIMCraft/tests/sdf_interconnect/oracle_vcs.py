"""Collect fresh executable VCS evidence before implementing wire-delay semantics."""
from pathlib import Path
import hashlib, json, subprocess, sys
from cases import make
if len(sys.argv) == 3 and sys.argv[2] == '--extra-only':
    from extra_cases import make

out = Path(sys.argv[1]).resolve(); assert not (out / 'results.json').exists()
cases = make(out); results = dict(status='RUNNING', cases={}, note='VCS oracle study only; no native INTERCONNECT support claim.')
def save(): (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
save()
try:
    for name in cases:
        w = out / name
        cmd = ['vcs', '-full64', '-sverilog', '+define+VCS_REFERENCE', 'cells.v', 'net.v', 'tb.v', '-o', 'simv']
        with (w / 'compile.log').open('w') as log:
            p = subprocess.run(cmd, cwd=w, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        assert p.returncode == 0, name
        traces = []
        for i in range(3):
            with (w / f'run-{i}.log').open('w') as log:
                p = subprocess.run([str(w / 'simv'), '-no_save'], cwd=w, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            text = (w / f'run-{i}.log').read_text()
            assert p.returncode == 0 and 'Done' in text, (name, i)
            traces.append([s for s in text.splitlines() if s.startswith('TRACE ')])
            (w / 'vcs.vcd').rename(w / f'{i}-vcs.vcd')
            if (w / 'annotation.log').exists(): (w / 'annotation.log').rename(w / f'{i}-annotation.log')
        assert traces[0] and traces.count(traces[0]) == 3, name
        results['cases'][name] = dict(trace=traces[0], command=cmd, binary_sha256=hashlib.sha256((w / 'simv').read_bytes()).hexdigest())
        save(); print('PASS fresh VCS INTERCONNECT', name, flush=True)
    results['status'] = 'PASS'; save()
except Exception as e:
    results['status'] = 'FAIL'; results['error'] = str(e); save(); raise
