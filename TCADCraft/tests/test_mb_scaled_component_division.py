from fractions import Fraction
from pathlib import Path
import copy
import json
import os
import random
import shutil
import subprocess

import pytest

from tcad.postprocess.boltzmann_product_range import _vector, _binary113
from tcad.postprocess.boltzmann_scaled_collision_tail import _value
from tcad.postprocess.boltzmann_scaled_arithmetic import scaled_value_fraction
from tcad.postprocess.boltzmann_scaled_component_division import audit_mb_scaled_component_division as audit

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def probe(tmp_path_factory):
    supplied = os.environ.get('TCAD_MB_SCALED_COMPONENT_DIVISION_PROBE')
    if supplied:
        return Path(supplied).resolve(strict=True)
    compiler = shutil.which('g++')
    if compiler is None:
        pytest.skip('standalone binary113 probe needs g++/libquadmath')
    path = tmp_path_factory.mktemp('component_division') / 'probe'
    subprocess.run([compiler, '-std=gnu++17', '-O2', '-I', str(ROOT / 'src'),
                    str(ROOT / 'tests/cpp/mb_scaled_component_division_probe.cpp'),
                    '-lquadmath', '-o', str(path)], check=True, capture_output=True, text=True, timeout=120)
    return path


@pytest.fixture
def run(probe):
    def call(atoms, divisor, accepted=True):
        before = copy.deepcopy((atoms, divisor))
        raw = '\n'.join([str(len(atoms)), *[token for group in [*atoms, divisor]
                                           for token in (str(len(group)), *group)]]) + '\n'
        result = subprocess.run([str(probe)], input=raw, capture_output=True, text=True, timeout=30)
        assert result.returncode == (0 if accepted else 2), result.stderr
        assert (atoms, divisor) == before
        if not accepted:
            assert not result.stdout
            return result.stderr
        wire = result.stdout.splitlines()
        return wire, audit(atoms, divisor, wire)
    return call


def aggregate(wire):
    n = int(wire[3])
    return scaled_value_fraction(wire[4:4+n])


@pytest.mark.parametrize('seed', range(24))
def test_random_signed_atoms_keep_their_own_rounding_and_remainders(run, seed):
    rng = random.Random(seed)
    values = [Fraction(rng.choice((-1, 1)) * rng.randrange(1, 1 << 113),
                       1 << rng.randrange(0, 30000)) for _ in range(5)]
    b = Fraction(rng.choice((-1, 1)) * rng.randrange(1, 1 << 130), 1 << 100)
    wire, report = run([_value(a) for a in values], _value(b))
    assert report['atoms_audited'] == 5
    expected = sum((_binary113(a/b) + _binary113((a-b*_binary113(a/b))/b)
                    for a in values), Fraction())
    assert aggregate(wire) == expected


@pytest.mark.parametrize('exponent', [1000, 14848, 15164, 30000])
def test_partition_preserves_tail_that_global_two_rounding_moves_to_remainder(run, exponent):
    tail = Fraction(1, 1 << exponent)
    wire, report = run([_value(Fraction(1)), _value(tail)], _value(Fraction(1)))
    assert aggregate(wire) == 1 + tail
    first = _binary113(1 + tail)
    assert first + _binary113(1 + tail - first) == 1 + tail
    # A third separated scale exceeds a global two-term quotient's coverage.
    tiny = tail * tail
    wire, report = run([_value(Fraction(1)), _value(tail), _value(tiny)], _value(Fraction(1)))
    assert aggregate(wire) == 1 + tail + tiny
    first = _binary113(1 + tail + tiny)
    assert first + _binary113(1 + tail + tiny - first) != aggregate(wire)
    assert report['aggregate_remainder_is_zero']


@pytest.mark.parametrize('a,b', [(1, 3), (-1, 3), (1, -3), (0, 3),
    ((1 << 113) + 1, 1 << 113), ((1 << 113) + 3, 1 << 113)],
    ids=['third', 'negative_numerator', 'negative_divisor', 'zero', 'even_tie', 'odd_tie'])
def test_two_rounding_ties_and_signs(run, a, b):
    # Tie numerators span 114 bits: split into original binary113 atoms.
    atoms = [_value(Fraction(a))] if abs(a).bit_length() <= 113 else [_value(Fraction(a-1)), _value(Fraction(1))]
    run(atoms, _value(Fraction(b)))


def test_exact_cancellation_does_not_discard_nonzero_individual_residuals(run):
    wire, report = run([_value(Fraction(1)), _value(Fraction(-1))], _value(Fraction(3)))
    assert aggregate(wire) == 0
    assert report['aggregate_remainder_is_zero']
    assert report['nonzero_atom_remainders'] == 2


@pytest.mark.parametrize('index', range(5))
def test_all_original_witness_atoms_can_be_divided_without_old_scalar_tail_guard(run, index):
    case = json.loads((ROOT / 'tests/data/mb_product_range_witness.json').read_text())['cases'][index]
    atoms = [_value(a) for a in _vector(case['right'])]
    wire, report = run(atoms, _value(Fraction(1000)))
    assert report['atoms_audited'] == len(case['right'])
    assert not report['physical_time_advanced']


@pytest.mark.parametrize('mode,cell', [(m,c) for m in ('closed','contact','mixed') for c in (0,1)])
def test_original_six_cell_lattice_normalization_matches_legacy_component_division(run, mode, cell):
    path = ROOT / 'docs/validation/mb_affine_range_witness_20261024/captured' / mode / f'cell{cell}.txt'
    tokens = path.read_text().split(); endpoint = tokens[1:1+int(tokens[0])]
    frame = endpoint[1:1+int(endpoint[0])]
    atoms, divisor = [_value(a) for a in _vector(frame[9:])], _value(_vector([frame[3]])[0])
    wire, report = run(atoms, divisor)
    assert report['original_atom_partition_preserved']
    b = scaled_value_fraction(divisor)
    legacy = sum((_binary113(a/b) + _binary113(_binary113(a-b*_binary113(a/b))/b)
                  for a in _vector(frame[9:])), Fraction())
    assert aggregate(wire) == legacy


@pytest.mark.parametrize('kind', ['version','precision','provenance','rounding','truncated','extra'])
def test_independent_auditor_rejects_tampered_evidence(run, kind):
    atoms, divisor = [_value(Fraction(1))], _value(Fraction(3))
    wire, _ = run(atoms, divisor)
    bad = wire.copy()
    if kind == 'version': bad[0] = 'mb_scaled_component_division_v2'
    elif kind == 'precision': bad[1] = '64'
    elif kind == 'provenance': bad[2] = '0'
    elif kind == 'rounding':
        i = next(i for i,s in enumerate(bad) if s.startswith('0x'))
        bad[i] = '0x1' if bad[i] != '0x1' else '0x3'
    elif kind == 'truncated': bad.pop()
    else: bad.append('0')
    with pytest.raises(ValueError): audit(atoms, divisor, bad)


@pytest.mark.parametrize('atoms,divisor', [([], _value(Fraction())),
    ([_value(Fraction(1) + Fraction(1, 1 << 1000))], _value(Fraction(1))),
    ([['mb_scaled_value_v1','113','1','0x2','0']], _value(Fraction(1)))])
def test_native_and_auditor_reject_invalid_inputs(run, atoms, divisor):
    run(atoms, divisor, accepted=False)
    with pytest.raises(ValueError): audit(atoms, divisor, [])


def test_cumulative_evidence_budget_rejects_before_producing_partial_packet(run):
    error = run([_value(Fraction(1))] * 1400, _value(Fraction(3)), accepted=False)
    assert 'evidence budget' in error


def test_empty_atom_partition_is_explicit_zero(run):
    wire, report = run([], _value(Fraction(3)))
    assert aggregate(wire) == 0 and report['atoms_audited'] == 0
