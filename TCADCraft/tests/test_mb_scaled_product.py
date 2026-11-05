"""Compile the actual standalone native primitive; replay without native math."""
from pathlib import Path
import json
import os
import random
import shutil
import subprocess

import pytest

from tcad.postprocess.boltzmann_scaled_product import audit_mb_scaled_product as audit

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def scaled_probe(tmp_path_factory):
    supplied = os.environ.get('TCAD_MB_SCALED_PROBE')
    if supplied:
        binary = Path(supplied).resolve(strict=True)
    else:
        compiler = shutil.which('g++')
        if compiler is None:
            pytest.skip('standalone binary113 test needs g++ and libquadmath')
        binary = tmp_path_factory.mktemp('mb_scaled') / 'probe'
        subprocess.run([compiler, '-std=gnu++17', '-O2', '-Wall', '-Wextra',
                        '-I', str(ROOT / 'src'),
                        str(ROOT / 'tests/cpp/mb_scaled_product_probe.cpp'),
                        '-lquadmath', '-o', str(binary)], check=True,
                       capture_output=True, text=True, timeout=60)

    def run(left, right, accepted=True):
        text = '\n'.join([f'{len(left)} {len(right)}', *left, *right]) + '\n'
        result = subprocess.run([str(binary)], input=text, capture_output=True,
                                text=True, timeout=10)
        if not accepted:
            assert result.returncode == 2 and not result.stdout
            return result.stderr
        assert result.returncode == 0, result.stderr
        return result.stdout.splitlines()
    return run


@pytest.mark.parametrize('index', range(5))
def test_original_five_failed_products_preserve_every_bit(scaled_probe, index):
    case = json.loads((ROOT / 'tests/data/mb_product_range_witness.json').read_text())['cases'][index]
    wire = scaled_probe(case['left'], case['right'])
    result = audit(case['left'], case['right'], wire)
    assert result['minimum_exponent2'] == case['expected_tail_exponent2']
    assert result['exact_integer_replay'] and not result['state_committed']
    assert not result['physical_time_advanced'] and not result['physical_validated']
    assert result['output_component_count'] <= 4096
    # The native sum is independent of input ordering, including compensation.
    assert scaled_probe(case['left'][::-1], case['right'][::-1]) == wire


@pytest.mark.parametrize('left,right', [([], ['1']), (['0'], ['1e4000']),
    (['1e-4000'], ['1e-4000']), (['1e4000'], ['1e4000']),
    (['1e-3000', '-1e-3000'], ['1e-3000']),
    (['1e4000', '1e-4000', '-1e4000'], ['-1e-4000']),
    (['1', '2', '-1'], ['-3', '-4']),
    (['1.0000000000000000000000000000000002', '-1'], ['1e-4000'])])
def test_extreme_products_and_cancellation(scaled_probe, left, right):
    wire = scaled_probe(left, right)
    assert audit(left, right, wire)['exact_integer_replay']


@pytest.mark.parametrize('seed', range(24))
def test_integer_replay_spans_sign_exponent_and_cancellation(scaled_probe, seed):
    rng = random.Random(seed)
    def vector():
        a = [f'{rng.choice([-1, 1]) * rng.randrange(1, 10**30)}e{rng.randrange(-3950, 3950)}'
             for _ in range(rng.randrange(1, 20))]
        return a + [a[0], a[0][1:] if a[0][0] == '-' else '-' + a[0]]
    a, b = vector(), vector()
    assert audit(a, b, scaled_probe(a, b))['exact_integer_replay']


@pytest.mark.parametrize('bad', ['nan', 'Infinity', '0x1p0', '1_0', '1e-4001',
    '1e4001', '1.00000000000000000000000000000000000000001e4000',
    '9.99999999999999999999999999999999999999999e-4001', '1e999999999',
    '1' * 257, '.', '1e', '--1'])
def test_native_rejects_bad_or_rounded_in_inputs(scaled_probe, bad):
    scaled_probe([bad], ['1'], accepted=False)


def test_original_pair_and_vector_budgets(scaled_probe):
    scaled_probe(['1'] * 257, ['1'] * 256, accepted=False)
    scaled_probe(['1'] * 4097, ['1'], accepted=False)
    assert audit(['1'] * 256, ['1'] * 256,
                 scaled_probe(['1'] * 256, ['1'] * 256))['nonzero_pairs'] == 65536


@pytest.mark.parametrize('mutation', ['tail', 'exponent', 'sign', 'count', 'pairs',
                                     'version', 'overlap', 'huge', 'even'])
def test_independent_replay_rejects_tampered_wire(scaled_probe, mutation):
    a, b = ['1', '1e-1000'], ['1']
    wire = scaled_probe(a, b)
    if mutation == 'tail': wire[-2] = '0x1' if wire[-2] != '0x1' else '0x3'
    elif mutation == 'exponent': wire[-1] = str(int(wire[-1]) + 1)
    elif mutation == 'sign': wire[6] = '-' + wire[6]
    elif mutation == 'count': wire[5] = str(int(wire[5]) + 1)
    elif mutation == 'pairs': wire[4] = '0'
    elif mutation == 'version': wire[0] = 'mb_scaled_product_v2'
    elif mutation == 'overlap': wire[9] = wire[7]
    elif mutation == 'huge': wire[-1] = '9' * 64
    elif mutation == 'even': wire[6] = '0x2'
    with pytest.raises(ValueError): audit(a, b, wire)


def test_auditor_does_not_call_native_or_depend_on_decimal_precision(scaled_probe, monkeypatch):
    from decimal import localcontext
    a, b = ['1e-4000'], ['-1e-4000']
    wire = scaled_probe(a, b)
    expected = audit(a, b, wire)
    def forbidden(*args, **kwargs): raise AssertionError('producer replay forbidden')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    with localcontext() as c:
        c.prec = 2
        assert audit(a, b, wire) == expected
