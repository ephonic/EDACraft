from fractions import Fraction
import random
import pytest
from tcad.postprocess.boltzmann_dyadic_quotient import quotient
from tcad.postprocess.boltzmann_scaled_collision_trace import _divide,_atoms


@pytest.mark.parametrize('seed',range(12))
def test_integer_two_round_quotient_matches_fraction_reference(seed):
    rng=random.Random(900+seed);width=(113,240,1000,4096)[seed%4]
    a=Fraction(rng.getrandbits(width)*(-1 if seed&1 else 1),1<<(width+3))
    b=Fraction(rng.getrandbits(width//2)|1,1<<(width//2+5))
    q,r=quotient(a,b)
    from tcad.postprocess.boltzmann_dyadic_codec import scaled_value_fraction as fast
    from tcad.postprocess.boltzmann_scaled_arithmetic import scaled_value_fraction as reference
    from tcad.postprocess.boltzmann_scaled_collision_trace import _wire
    assert fast(_wire(a))==reference(_wire(a))==a
    assert (q,r)==_divide(_atoms(a),b)
    assert a==b*q+r
    assert abs(r)<=sum(map(abs,_atoms(a)),Fraction())/(1<<226)


def test_integer_two_round_quotient_preserves_sparse_remote_tail_and_sign():
    a=Fraction(3,4)+Fraction(7,1<<60000);b=Fraction(11,8)
    assert quotient(a,b)==_divide(_atoms(a),b)
    q,r=quotient(a,b);n,s=quotient(-a,b)
    assert (n,s)==(-q,-r) and r


def test_integer_quotient_rejects_non_dyadic_divisor_zero_and_resource_overflow():
    for a,b in [(Fraction(1),Fraction(0)),(Fraction(1),Fraction(1,3)),(Fraction(1,1<<65537),Fraction(3))]:
        with pytest.raises(ValueError):quotient(a,b)
