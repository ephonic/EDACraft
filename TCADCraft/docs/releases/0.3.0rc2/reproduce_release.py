"""Build from sdist and validate a separately installed Linux release wheel."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import traceback
import xml.etree.ElementTree as ET
import zipfile

W = Path(sys.argv[1]).resolve()
S = W / 'input/TCADCraft'
A = W / 'artifacts'
A.mkdir()
env = os.environ.copy()
env.pop('PYTHONPATH', None)
env.update(TCAD_USE_PETSC='0', TCAD_USE_LAPACK='0', TCAD_CONSTANTS_PROFILE='si',
           TCAD_NATIVE_OPT='0', TCAD_EXPECT_CONSTANTS_PROFILE='si', TCAD_EXPECT_PRECISION='float128',
           OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUNBUFFERED='1')
env.pop('TCAD_FORCE_LONG_DOUBLE', None)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def run(name, command, cwd, timeout=1800):
    write(W / 'state.json', dict(status=name, utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    with (W / (name + '.log')).open('w') as log:
        result = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:result.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            import signal,time
            os.killpg(result.pid,signal.SIGTERM)
            try:result.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(result.pid,signal.SIGKILL);result.wait()
            raise

    assert result.returncode == 0, (name, result.returncode)


def verify_input_and_production():
    policy=json.loads((W/'build_policy.json').read_bytes())
    for n,h in policy['input_files'].items():assert sha(S/n)==h,n
    assert str(Path('/apps/EDAs/own/tcad/current').resolve())==policy['production_target']
    for n,h in policy['production_sha256'].items():assert sha(Path(n))==h,n
    return policy

try:
    policy=verify_input_and_production()
    run('metadata', [sys.executable, 'scripts/release_check.py'], S)
    run('sdist', [sys.executable, '-m', 'build', '--sdist', '--no-isolation', '--outdir', str(A)], S)
    sdist = next(A.glob('tcad-0.3.0rc2.tar.gz'))
    clean = W / 'clean_sdist'
    clean.mkdir()
    with tarfile.open(sdist) as archive:
        archive.extractall(clean, filter='data')
    clean_source = clean / 'tcad-0.3.0rc2'
    assert (clean_source / 'tcad_build_config.py').is_file()
    assert (clean_source / 'tests/data/sheet_phase2_linear_system.npz').is_file()
    assert (clean_source / 'tcad/solver/_sheet_ordering.py').is_file()
    assert (clean_source / 'docs/optimization/20261108-geometric-z-time512/reproduction/meshes.npz').is_file()
    assert (clean_source / 'docs/optimization/20261108-geometric-z-time512/reproduction/geometric_z113_n512.py').is_file()
    for n,h in policy['input_files'].items():
        if n.startswith(('tcad/','src/','tests/','benchmarks/')) or n in ('setup.py','pyproject.toml','MANIFEST.in','tcad_build_config.py'):
            assert sha(clean_source/n)==h,('sdist identity',n)

    run('wheel_from_sdist', [sys.executable, '-m', 'build', '--wheel', '--no-isolation', '--outdir', str(A)], clean_source, 3600)
    wheel = next(A.glob('tcad-0.3.0rc2-*.whl'))
    with zipfile.ZipFile(wheel) as package:
        assert any(n.startswith('tcad/core/_bindings.') and n.endswith('.so') for n in package.namelist())
        for n,h in policy['input_files'].items():
            if n.startswith('tcad/') and Path(n).suffix in ('.py','.pyx','.pxd','.json','.cpp','.h'):
                assert hashlib.sha256(package.read(n)).hexdigest()==h,('wheel source identity',n)
        assert not any(n.startswith(('quad-si/', 'quad-legacy-charge/', 'long-double-')) for n in package.namelist())
    run('venv', [sys.executable, '-m', 'venv', '--system-site-packages', str(W / 'venv')], W)
    py = str(W / 'venv/bin/python')
    run('wheel_install', [py, '-m', 'pip', 'install', '--no-deps', str(wheel)], W)
    neutral = W / 'installed_checks'
    neutral.mkdir()
    (neutral / 'installed_identity.py').write_text('''from pathlib import Path
import importlib.metadata,json,sys
import tcad
from tcad.core import native_precision,native_constants,_bindings
assert tcad.__version__=='0.3.0rc2'
assert importlib.metadata.version('tcad')=='0.3.0rc2'
assert Path(tcad.__file__).is_relative_to(Path(sys.prefix))
assert native_precision()['backend']=='float128' and native_precision()['mantissa_bits']==113
assert native_constants()['profile']=='si'
print(json.dumps(dict(version=tcad.__version__,package=tcad.__file__,binary=_bindings.__file__,precision=native_precision(),constants=native_constants()),indent=2))
''')
    run('installed_identity', [py, 'installed_identity.py'], neutral)
    identity = json.loads((W / 'installed_identity.log').read_text())
    binary = Path(identity['binary'])
    readme = (S / 'README.md').read_text()
    python_blocks = re.findall(r'```python\n(.*?)```', readme, re.S)
    assert len(python_blocks) == 2
    (neutral / 'readme_smoke.py').write_text('\n'.join(python_blocks) + '\n')
    run('readme_graphene_smoke', [py, 'readme_smoke.py'], neutral)
    mos2 = python_blocks[1].replace('from tcad.material import graphene_sheet', 'from tcad.material import mos2_sheet')
    mos2 = mos2.replace('graphene_sheet(),', 'mos2_sheet(reference_eV=-0.9),')
    mos2 = mos2.replace('contact_resistance_ohm_m=0.003,', 'thermionic_barrier_n_eV=0.12,')
    (neutral / 'mos2_smoke.py').write_text(mos2 + '\n')
    run('mos2_smoke', [py, 'mos2_smoke.py'], neutral)
    assert "linear_ordering='GEOMETRIC_ND'" in python_blocks[1]

    shutil.copytree(S / 'tests', neutral / 'tests')
    shutil.copytree(S / 'benchmarks', neutral / 'benchmarks')
    for name in ('pytest.ini', 'conftest.py', 'tcad_build_config.py'):
        shutil.copy2(S / name, neutral / name)
    tests = sorted('tests/' + p.name for p in (neutral / 'tests').glob('test_sheet*.py'))
    tests += ['tests/test_constants_profile.py', 'tests/test_precision_backend.py']
    run('installed_targeted_pytest', [py, '-m', 'pytest', '-q', *tests, '--junitxml=' + str(A / 'targeted_tests.xml')], neutral, 1800)
    suites = ET.parse(A / 'targeted_tests.xml').getroot()
    suites = [suites] if suites.tag == 'testsuite' else list(suites)
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['failures'] == counts['errors'] == counts['skipped'] == 0
    assert counts['tests'] > 1055
    ldd = subprocess.check_output(['ldd', str(binary)], text=True)
    assert 'not found' not in ldd
    compatibility = dict(python=platform.python_version(), implementation='CPython', architecture=platform.machine(),
                         platform=platform.platform(), libc=platform.libc_ver(), wheel_tag=wheel.name,
                         precision=identity['precision'], constants=identity['constants'],
                         binary_sha256=sha(binary), shared_library_dependencies=ldd.splitlines(),
                         manylinux_certified=False, numpy_build_version=__import__('numpy').__version__,
                         install_scope='Linux x86_64 CPython 3.13; tested host runtime only; dependencies installed separately')
    write(A / 'compatibility.json', compatibility)
    report = dict(version='0.3.0rc2', status='passed_clean_sdist_wheel_install_and_targeted_checks',
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  wheel_built_from_sdist=True, installation_verified_outside_source_tree=True,
                  readme_graphene_example_passed=True, mos2_variant_passed=True,
                  test_scope=tests, junit=counts, full_suite_rerun=False,
                  build_flags={k: env[k] for k in ('TCAD_USE_PETSC','TCAD_USE_LAPACK','TCAD_CONSTANTS_PROFILE','TCAD_NATIVE_OPT')},
                  artifacts={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in (sdist, wheel)},
                  input_tar_sha256=sha(W / 'source_input.tar.gz'), binary_sha256=sha(binary),
                  legacy_charge_binary_built=False, commercial_runs=0, experimental_acceptance=False,
                  physical_device_qualification=False)
    verify_input_and_production()
    report.update(input_policy_sha256=sha(W/'build_policy.json'),input_source_files_verified=len(policy['input_files']),
                  all_packaged_numerical_sources_verified=True,production_unchanged=True,
                  numerical_development_commit=policy['numerical_development_commit'],new_complete_device_pulses=0,
                  numerical_evidence_inherited=True)
    write(A / 'RELEASE_VERIFICATION.json', report)
    with tarfile.open(W / 'release_artifacts.tar.gz', 'w:gz') as archive:
        for p in sorted(A.iterdir()):
            archive.add(p, arcname=p.name)
    write(W / 'result.json', dict(status=report['status'], artifacts_archive_bytes=(W / 'release_artifacts.tar.gz').stat().st_size,
                                artifacts_archive_sha256=sha(W / 'release_artifacts.tar.gz'), junit=counts))
    write(W / 'state.json', dict(status='completed_release_verification'))
except BaseException:
    write(W / 'failure.json', dict(status='failed_preserved', traceback=traceback.format_exc()))
    raise
