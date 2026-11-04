#!/usr/bin/env python3
"""Compare a fresh full native regression against saved VCS references.

Use after compiler changes that preserve existing fixtures, so the final native
build is checked without attributing earlier timing measurements to it.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('regression', ROOT/'tests/regression.py')
regression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regression)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native-results', type=Path, required=True)
    ap.add_argument('--reference', type=Path, action='append', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    native = json.loads(args.native_results.read_text())
    references = {}
    for path in args.reference:
        data = json.loads(path.read_text())
        if 'failure' in data:
            raise RuntimeError(f'Failed reference run: {path}: {data["failure"]}')
        for case, record in data['cases'].items():
            if case in references and references[case]['trace'] != record['trace']:
                raise RuntimeError(f'Conflicting VCS references for {case}')
            references[case] = record
    verified = {}
    for case, expected in regression.CASES.items():
        reference = references[case]
        sha = hashlib.sha256((ROOT/'tests/cases'/f'{case}.v').read_bytes()).hexdigest()
        if reference['status'] != 'PASS' or reference['sha256'] != sha:
            raise RuntimeError(f'{case}: reference failed or input changed')
        if native[case]['status'] != 'PASS' or native[case]['trace'] != reference['trace'] or reference['trace'] != expected:
            raise RuntimeError(f'{case}: native/VCS/expected trace mismatch')
        verified[case] = {'status': 'PASS', 'sha256': sha, 'trace': native[case]['trace']}
    files = [ROOT/'CMakeLists.txt']
    for directory in ('cmake', 'parsers', 'src', 'include', 'tests', 'scripts'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    report = {'note': 'Final native regression checked against saved same-input VCS traces. Earlier timing measurements remain separate.',
              'implementation_sha256': manifest, 'cases': verified}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f'PASS final native/VCS recheck: {len(verified)} cases')


if __name__ == '__main__':
    main()
