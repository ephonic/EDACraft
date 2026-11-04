#!/usr/bin/env python3
"""Train and build a generated simulation model with GCC profile feedback."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args):
    source = args.source.expanduser().resolve(strict=True)
    run_dir = args.run_dir.expanduser().resolve(strict=True)
    # A fresh work directory keeps profile identity independent of prior builds.
    work = args.work.expanduser().absolute()
    located = shutil.which(args.cxx)
    if located is None:
        raise RuntimeError(f'compiler not found: {args.cxx}')
    args.cxx = str(Path(located).resolve())
    macros = subprocess.run([args.cxx, '-dM', '-E', '-x', 'c++', '-'], input='',
                            text=True, capture_output=True, timeout=30)
    if macros.returncode or '__GNUC__' not in macros.stdout or '__clang__' in macros.stdout:
        raise RuntimeError('--cxx must select GCC; this workflow uses GCC profile data')
    work.mkdir(parents=True, exist_ok=False)
    source_copy = work / 'model.cpp'
    shutil.copy2(source, source_copy)
    binary = work / 'simv'
    profiles = work / 'profiles'
    profiles.mkdir()
    report = {'status': 'BUILDING', 'input': str(source), 'input_sha256': digest(source_copy),
              'run_dir': str(run_dir), 'binary': str(binary), 'compiler': args.cxx,
              'compiler_version': subprocess.check_output([args.cxx, '--version'], text=True),
              'flags': ['-std=c++17', '-O2', '-pthread', *args.cxx_flag],
              'training_args': args.train_arg, 'verify': args.verify, 'commands': {}}

    def save():
        (work / 'pgo.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(command, label, cwd):
        report['commands'][label] = list(map(str, command))
        save()
        p = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=args.timeout)
        (work / (label + '.stdout')).write_text(p.stdout)
        (work / (label + '.stderr')).write_text(p.stderr)
        if p.returncode:
            raise RuntimeError(f'{label} failed ({p.returncode}); see {work / (label + ".stderr")}')
        return p.stdout

    try:
        flags = [args.cxx, *report['flags'], str(source_copy), '-o', str(binary)]
        run([*flags, '-fprofile-generate=' + str(profiles)], 'compile-training', work)
        report['training_binary_sha256'] = digest(binary)
        report['status'] = 'TRAINING'
        training = run([str(binary), *args.train_arg], 'training', run_dir)
        report['profiles'] = {str(p.relative_to(work)): digest(p) for p in sorted(profiles.rglob('*.gcda'))}
        if not report['profiles']:
            raise RuntimeError('training produced no GCC profile data')
        report['status'] = 'BUILDING_OPTIMIZED'
        run([*flags, '-fprofile-use=' + str(profiles), '-Werror=missing-profile',
             '-Werror=coverage-mismatch'], 'compile-optimized', work)
        report['binary_sha256'] = digest(binary)
        if args.verify:
            report['status'] = 'VERIFYING'
            optimized = run([str(binary), *args.train_arg], 'verify', run_dir)
            if training != optimized:
                raise RuntimeError('optimized stdout differs from training; see training.stdout and verify.stdout')
        report['status'] = 'PASS'
        save()
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        save()
        raise
    print(binary)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='C++ produced by dsim --emit-only --emit-cpp')
    parser.add_argument('--work', type=Path, required=True, help='new directory for the model, profiles and executable')
    parser.add_argument('--run-dir', type=Path, default=Path.cwd(), help='working directory for training inputs')
    parser.add_argument('--cxx', default='g++', help='GCC C++ compiler executable')
    parser.add_argument('--cxx-flag', action='append', default=[], help='extra literal compiler argument; use --cxx-flag=-FLAG')
    parser.add_argument('--train-arg', action='append', default=[], help='literal simulation argument; use --train-arg=--OPTION')
    parser.add_argument('--verify', action='store_true', help='rerun optimized model and compare complete stdout')
    parser.add_argument('--timeout', type=float, default=1800, help='seconds allowed per build/run')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        build(args)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
