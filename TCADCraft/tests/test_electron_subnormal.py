"""Independent subnormal probability checks, including block/squaring boundaries."""
from decimal import Decimal, localcontext
import math
import numpy as np
import pytest
from tcad.physics.electron_counting import BirthDeathChain


UNIT = math.ulp(0.)


def weak_chain(rate, birth=True):
    # An unoccupied state contributes a unit rate to uniformization. Its
    # presence must not erase the actual weak transition from the initial state.
    chain = BirthDeathChain(2, lambda n: (rate if birth else 1.) if n == 0 else 0.,
                           lambda n: (1. if birth else rate) if n == 2 else 0.)
    chain.initialize(count=0 if birth else 2)
    return chain


def weak_reference(rate, duration, birth=True):
    with localcontext() as ctx:
        ctx.prec = 800
        survival = (-Decimal.from_float(rate) * Decimal.from_float(duration)).exp()
        result = np.array([float(survival), float(1 - survival), 0.])
    return result if birth else result[::-1]


def assert_rounded_probability(got, expected):
    # A one-ULP budget at the final float64 boundary, plus a relative budget
    # for tails that grow back into the normal range over very long holds.
    assert abs(got - expected) <= max(math.ulp(expected), 3e-13 * expected)
    if expected > 0.:
        assert got > 0.


@pytest.mark.parametrize('birth', [False, True])
@pytest.mark.parametrize('units', [1, 7])
@pytest.mark.parametrize('duration', [.01, .3, 1., 2., 40., 100., 4096., 4097., 1e4, 1e200])
def test_absorbing_initial_subnormal_is_invariant(birth, units, duration):
    chain = BirthDeathChain(2, lambda n: float(birth and n == 0),
                           lambda n: float(not birth and n == 2))
    initial = np.array([1., 0., units * UNIT])
    if not birth:
        initial = initial[::-1]
    chain.initialize(p0=initial)
    result = chain.advance(duration)
    assert result[-1 if birth else 0] == units * UNIT
    assert math.fsum(result) == pytest.approx(1., abs=2e-15)


@pytest.mark.parametrize('birth', [False, True])
@pytest.mark.parametrize('units', [1, 3, 31])
@pytest.mark.parametrize('duration', [.1, 1., 40., 80., 4096., 4097., 1e4, 1e200])
def test_subnormal_rate_transfer_against_decimal(birth, units, duration):
    chain = weak_chain(units * UNIT, birth)
    expected = weak_reference(units * UNIT, duration, birth)
    for got, want in zip(chain.advance(duration), expected):
        assert_rounded_probability(got, want)


@pytest.mark.parametrize('birth', [False, True])
@pytest.mark.parametrize('units', [1, 7, 31])
@pytest.mark.parametrize('duration', [.1, 1., 2., 40., 80., 1e4])
def test_initial_subnormal_decay_against_decimal(birth, units, duration):
    chain = BirthDeathChain(2, lambda n: float(birth and n == 0),
                           lambda n: float(not birth and n == 2))
    initial = np.array([units * UNIT, 0., 1.])
    if not birth:
        initial = initial[::-1]
    chain.initialize(p0=initial)
    with localcontext() as ctx:
        ctx.prec = 800
        mass = Decimal.from_float(units * UNIT)
        survival = mass * (-Decimal.from_float(duration)).exp()
        expected = np.array([float(survival), float(mass - survival), 1.])
    if not birth:
        expected = expected[::-1]
    for got, want in zip(chain.advance(duration), expected):
        assert_rounded_probability(got, want)


@pytest.mark.parametrize('birth', [False, True])
@pytest.mark.parametrize('duration', [1., 40., 4097., 1e4])
def test_subnormal_generated_probability_reaches_decoder(birth, duration):
    from tcad.physics.storage_readout import decode_distributions
    chain = weak_chain(8 * UNIT, birth)
    probability = chain.advance(duration)
    stable = np.array([0., 0., 1.]) if birth else np.array([1., 0., 0.])
    distributions = np.array([probability, stable]) if birth else np.array([stable, probability])
    result = decode_distributions(distributions, [1. if birth else 2.])
    with localcontext() as ctx:
        ctx.prec = 800
        expected = float((1 - (-Decimal.from_float(8 * UNIT)
                              * Decimal.from_float(duration)).exp()) / 2)
    assert_rounded_probability(result.bit_error_rate, expected)
    assert_rounded_probability(result.symbol_error_rate, expected)
