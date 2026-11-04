"""Keep wildcard module identities separate from strict topology/type checks."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from cases import make

compiler = Path(sys.argv[1]).resolve(); base = Path(sys.argv[2]).resolve()
base.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='run-', dir=base)); make(out / 'inputs')
fixture = out / 'inputs/identical-iopath'
common = ['--gate-netlist', fixture / 'net.v', '--gate-top', 'dut', '--liberty', fixture / 'cells.lib', '--sdf-tick', '100fs']
records = {}


def run(label, sdf, models=False, ok=True):
    command = list(map(str, [compiler, '--sdf-bind-check', sdf, *common,
        *(['--gate-models', fixture / 'cells.v'] if models else [])]))
    result = subprocess.run(command, text=True, capture_output=True, timeout=90)
    (out / (label + '.command.json')).write_text(json.dumps(command) + '\n')
    (out / (label + '.stdout')).write_text(result.stdout); (out / (label + '.stderr')).write_text(result.stderr)
    assert (result.returncode == 0) == ok, (label, result.stdout, result.stderr)
    records[label] = dict(returncode=result.returncode)
    return json.loads(result.stdout) if ok else result.stderr


raw = run('topology', fixture / 'delay.sdf')
assert raw['target_cells'] == raw['bound_entries'] == 2 and raw['wildcard_alias_targets'] == 0
annotated = run('annotated', fixture / 'delay.sdf', True)
assert annotated['binding']['target_cells'] == annotated['distinct_paths'] == 3
assert annotated['binding']['wildcard_alias_targets'] == 1
leaf = out / 'leaf.sdf'; leaf.write_text((fixture / 'delay.sdf').read_text().replace('(INSTANCE *)', '(INSTANCE fast)'))
explicit = run('explicit', leaf, True)
assert explicit['binding']['target_cells'] == explicit['distinct_paths'] == 1
assert explicit['binding']['wildcard_alias_targets'] == 0
wrong = out / 'wrong.sdf'; wrong.write_text(leaf.read_text().replace('CELLTYPE "D"', 'CELLTYPE "S"'))
assert 'CELLTYPE mismatch' in run('explicit-mismatch', wrong, True, False)
unknown = out / 'unknown.sdf'; unknown.write_text((fixture / 'delay.sdf').read_text().replace('CELLTYPE "D"', 'CELLTYPE "ABSENT"'))
assert 'wildcard matched no CELLTYPE' in run('absent-type', unknown, True, False)
report = dict(status='PASS', checks=records, directory=str(out))
for p in [out / 'results.json', base / 'results.json']: p.write_text(json.dumps(report, indent=2) + '\n')
print('PASS strict topology, proved wildcard targets, explicit scope and type failures')
