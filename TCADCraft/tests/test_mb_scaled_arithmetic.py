from fractions import Fraction
from pathlib import Path
import copy
import json
import os
import random
import shutil
import subprocess

import pytest

from tcad.postprocess.boltzmann_product_range import _vector
from tcad.postprocess.boltzmann_scaled_arithmetic import (
    audit_mb_scaled_arithmetic as audit, scaled_value_fraction as value,
    split_mb_scaled_arithmetic as split,
)
from tcad.postprocess.boltzmann_scaled_collision_tail import (
    _value, audit_mb_scaled_collision_tail as audit_tail,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def probes(tmp_path_factory):
    folder = tmp_path_factory.mktemp('scaled_arithmetic')
    result = {}
    for kind in ('arithmetic', 'collision_tail'):
        supplied = os.environ.get('TCAD_MB_SCALED_' + ('ARITHMETIC' if kind == 'arithmetic' else 'TAIL') + '_PROBE')
        if supplied:
            binary = Path(supplied).resolve(strict=True)
        else:
            compiler = shutil.which('g++')
            if compiler is None:
                pytest.skip('standalone native binary113 test needs g++/libquadmath')
            binary = folder / kind
            subprocess.run([compiler, '-std=gnu++17', '-O2', '-I', str(ROOT / 'src'),
                            str(ROOT / f'tests/cpp/mb_scaled_{kind}_probe.cpp'),
                            '-lquadmath', '-o', str(binary)],
                           capture_output=True, text=True, check=True, timeout=120)
        result[kind] = binary
    return result


@pytest.fixture
def run(probes):
    def call(op, a, b, accepted=True):
        raw = '\n'.join([f'{op} {len(a)} {len(b)}', *a, *b]) + '\n'
        result = subprocess.run([str(probes['arithmetic'])], input=raw,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == (0 if accepted else 2), result.stderr
        if not accepted:
            assert not result.stdout
            return result.stderr
        wire = result.stdout.splitlines()
        audit(op, a, b, wire)
        return split(wire)
    return call


@pytest.mark.parametrize('operation', ['add', 'subtract', 'multiply', 'divide'])
@pytest.mark.parametrize('seed', range(12))
def test_scaled_arithmetic_random_integer_replay(run, seed, operation):
    rng = random.Random(seed)
    a = Fraction(rng.choice([-1, 1]) * rng.randrange(1, 1 << 240), 1 << rng.randrange(0, 20000))
    b = Fraction(rng.choice([-1, 1]) * rng.randrange(1, 1 << 170), 1 << rng.randrange(0, 20000))
    run(operation, _value(a), _value(b))


@pytest.mark.parametrize('numerator,denominator', [(1, 3), (-1, 3), (1, -3), (0, 3),
    ((1 << 113) + 1, 1 << 113), ((1 << 113) + 3, 1 << 113),
    ((1 << 114) - 1, 1 << 113), (1, 1 << 20000), (1 << 20000, 3)],
    ids=['third', 'negative_numerator', 'negative_denominator', 'zero',
         'even_tie', 'odd_tie', 'carry_tie', 'tiny', 'huge_third'])
def test_division_ties_sign_zero_and_explicit_exponent(run, numerator, denominator):
    a, b = _value(Fraction(numerator)), _value(Fraction(denominator))
    q, remainder = run('divide', a, b)
    product, _ = run('multiply', b, q)
    reconstructed, _ = run('add', product, remainder)
    assert value(reconstructed) == numerator
    if abs(denominator) == 3 and numerator:
        assert value(remainder) != 0


@pytest.mark.parametrize('seed', range(8))
def test_exact_cancellation_below_old_grid_survives_division_recomposition(run, seed):
    small = Fraction(seed + 1, 1 << 30000)
    a, b = _value(1 + small), _value(Fraction(-1))
    tail, _ = run('add', a, b)
    assert value(tail) == small
    q, remainder = run('divide', tail, _value(Fraction(3)))
    product, _ = run('multiply', q, _value(Fraction(3)))
    restored, _ = run('add', product, remainder)
    assert value(restored) == small


@pytest.mark.parametrize('index', range(5))
def test_original_failed_products_can_feed_subtraction_and_division(run, index):
    case = json.loads((ROOT / 'tests/data/mb_product_range_witness.json').read_text())['cases'][index]
    left, _ = run('import', case['left'], [])
    right, _ = run('import', case['right'], [])
    product, _ = run('multiply', left, right)
    expected = sum(_vector(case['left']), Fraction()) * sum(_vector(case['right']), Fraction())
    assert value(product) == expected
    delta, _ = run('subtract', left, product)
    q, rest = run('divide', delta, _value(Fraction(1000)))
    back, _ = run('multiply', q, _value(Fraction(1000)))
    back, _ = run('add', back, rest)
    assert value(back) == value(left) - expected


@pytest.mark.parametrize('raw', [[], ['0'], ['1e-4000', '-1e-4000', '2'], ['1e4000'], ['-1e-4000']])
def test_original_decimal_import(run, raw):
    out, rest = run('import', raw, [])
    assert value(out) == sum(_vector(raw), Fraction()) and value(rest) == 0


@pytest.mark.parametrize('bad', [[], ['mb_scaled_value_v2', '113', '0'],
    ['mb_scaled_value_v1', '64', '0'], ['mb_scaled_value_v1', '113', '00'],
    ['mb_scaled_value_v1', '113', '1', '0x2', '0'],
    ['mb_scaled_value_v1', '113', '1', '0x01', '0'],
    ['mb_scaled_value_v1', '113', '1', '0x1', '-0'],
    ['mb_scaled_value_v1', '113', '1', '0x1', '65537'],
    ['mb_scaled_value_v1', '113', '2', '0x1', '0', '-0x1', '2'],
    ['mb_scaled_value_v1', '113', '2', '0x3', '0', '0x1', '1'],
    ['mb_scaled_value_v1', '113', '2', '0x1', '-40000', '0x1', '40000']])
def test_malformed_scaled_values_rejected_by_native_and_auditor(run, bad):
    run('add', bad, _value(Fraction(1)), accepted=False)
    with pytest.raises(ValueError): value(bad)


def test_zero_divisor_and_original_import_limits(run):
    run('divide', _value(Fraction(1)), _value(Fraction()), accepted=False)
    run('import', ['1'] * 4097, [], accepted=False)
    run('import', ['1e-4001'], [], accepted=False)
    run('unknown', _value(Fraction()), _value(Fraction()), accepted=False)


def test_pair_budget_is_checked_before_integer_multiply(run):
    a = ['mb_scaled_value_v1', '113', '257'] + [x for i in range(257) for x in ('0x1', str(2*i))]
    b = ['mb_scaled_value_v1', '113', '256'] + [x for i in range(256) for x in ('0x1', str(2*i))]
    run('multiply', a, b, accepted=False)


def tail_input(index):
    case = json.loads((ROOT / 'tests/data/mb_product_range_witness.json').read_text())['cases'][index]
    folder = ROOT / 'docs/validation/mb_affine_range_witness_20261024/captured' / case['mode']
    tokens = (folder / f'cell{case["cell"]}.txt').read_text().split()
    n = int(tokens[0]); endpoint = tokens[1:1+n]
    record = json.loads((ROOT / case['diagnostic_record']).read_text())
    command = next(x.split()[1:] for x in record['stderr'].splitlines() if x.startswith('COLLISION_COMMAND '))
    return endpoint, command, case['left'], case['right']


@pytest.fixture
def tail(probes):
    def call(args, accepted=True):
        raw = '\n'.join(x for group in args for x in (str(len(group)), *group)) + '\n'
        result = subprocess.run([str(probes['collision_tail'])], input=raw,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == (0 if accepted else 2), result.stderr
        if not accepted:
            assert not result.stdout
            return
        return result.stdout.splitlines()
    return call


@pytest.mark.parametrize('index', range(5))
def test_original_collision_tail_reaches_all_fourteen_operations(tail, index):
    args = tail_input(index)
    old = copy.deepcopy(args)
    wire = tail(args)
    report = audit_tail(*args, wire)
    assert report['exact_native_operations_audited'] == 14
    assert report['evidence_components'] <= 4096
    assert report['fixed_tau_lineage_energy_gate_passed']
    assert not report['state_committed'] and not report['full_collision_audited']
    assert args == old
    bad = wire.copy(); bad[-2] = '0x3' if bad[-2] != '0x3' else '0x5'
    with pytest.raises(ValueError): audit_tail(*args, bad)


def test_tail_rejects_capacity_substitution_and_nonpositive_tau(tail):
    args = list(tail_input(0))
    args[2] = ['1']
    tail(args, accepted=False)
    args = list(tail_input(0)); args[1] = args[1].copy(); args[1][1] = '-1'
    tail(args, accepted=False)
