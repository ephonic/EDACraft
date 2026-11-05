"""Independent bounded integer replay of canonical-atom two-round division.

No native calls or cached producer results. Exponents stay explicit while
rounding, avoiding repeated Fraction gcds with a very wide dyadic divisor.
"""
from fractions import Fraction
from functools import lru_cache
from .boltzmann_scaled_collision_trace import _wire


def _normal(n,e):
    if not n:return (0,0)
    low=(abs(n)&-abs(n)).bit_length()-1;n>>=low;e+=low
    if abs(e)>65536 or abs(n).bit_length()>65536:
        raise ValueError('independent dyadic span/exponent budget exceeded')
    return n,e


def _dyad(x):
    d=x.denominator
    if d&(d-1):raise ValueError('dyadic quotient operands required')
    return _normal(x.numerator,1-d.bit_length())


def _add(a,b,direction=1):
    n,e=a;m,f=b
    if not n:return _normal(direction*m,f)
    if not m:return a
    low=min(e,f)
    # Match the bounded aligned integer workspace before cancellation.
    if max(abs(n).bit_length()+e-low,abs(m).bit_length()+f-low)>65536:
        raise ValueError('independent dyadic addition span budget exceeded')
    return _normal((n<<(e-low))+direction*(m<<(f-low)),low)


def _mul(a,b):
    n,e=a;m,f=b
    return _normal(n*m,e+f)


def _round(a,b):
    n,e=a;d,f=b
    if not d:raise ValueError('trace division by zero')
    if not n:return (0,0)
    sign=1 if (n>0)==(d>0) else -1;n=abs(n);d=abs(d)
    k=n.bit_length()-d.bit_length()
    if (n<d<<k) if k>=0 else (n<<(-k)<d):k-=1
    shift=112-k
    numerator,denominator=(n<<shift,d) if shift>=0 else (n,d<<(-shift))
    q,r=divmod(numerator,denominator)
    if 2*r>denominator or (2*r==denominator and q&1):q+=1
    return _normal(sign*q,e-f+k-112)


def _fraction(a):
    n,e=a
    return Fraction(n<<e) if e>=0 else Fraction(n,1<<(-e))


@lru_cache(maxsize=64)
def quotient(a,b):
    """Same canonical atoms, RN113 twice per atom, exact total remainder."""
    divisor=_dyad(b)
    if not divisor[0]:raise ValueError('trace division by zero')
    _dyad(a);raw=_wire(a);result=(0,0);rest=(0,0)
    for c,e in zip(raw[3::2],raw[4::2]):
        atom=(int(c,16),int(e));head=_round(atom,divisor)
        residual=_add(atom,_mul(divisor,head),-1)
        tail=_round(residual,divisor);part=_add(head,tail)
        result=_add(result,part)
        rest=_add(rest,_add(atom,_mul(divisor,part),-1))
    return _fraction(result),_fraction(rest)
