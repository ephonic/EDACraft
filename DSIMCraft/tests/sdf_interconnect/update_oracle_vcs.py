"""Run the additional update study without modifying the frozen base runner."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from update_cases import make

out = Path(sys.argv[1]).resolve()
assert not (out / 'results.json').exists()
cases = make(out)
results = dict(status='RUNNING', cases={}, note='Fresh VCS MIPD update reference only; no native support or performance claim.')


def save():
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


save()
try:
    for name in cases:
        w = out / name
        command = ['vcs', '-full64', '-sverilog', '+define+VCS_REFERENCE', 'cells.v', 'net.v', 'tb.v', '-o', 'simv']
        with (w / 'compile.log').open('w') as log:
            run = subprocess.run(command, cwd=w, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        assert run.returncode == 0, name
        traces = []
        for i in range(3):
            with (w / f'run-{i}.log').open('w') as log:
                run = subprocess.run([str(w / 'simv'), '-no_save'], cwd=w, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            log = (w / f'run-{i}.log').read_text()
            assert run.returncode == 0 and 'Done' in log, (name, i)
            traces.append([line for line in log.splitlines() if line.startswith('TRACE ')])
            (w / 'vcs.vcd').rename(w / f'{i}-vcs.vcd')
            annotation = w / 'annotation.log'
            if annotation.exists():
                annotation.rename(w / f'{i}-annotation.log')
        assert traces[0] and traces.count(traces[0]) == 3, name
        results['cases'][name] = dict(trace=traces[0], command=command, binary_sha256=hashlib.sha256((w / 'simv').read_bytes()).hexdigest())
        save()
        print('PASS fresh VCS MIPD ordered update', name, flush=True)
    results['status'] = 'PASS'
    save()
except Exception as error:
    results['status'] = 'FAIL'
    results['error'] = str(error)
    save()
    raise
