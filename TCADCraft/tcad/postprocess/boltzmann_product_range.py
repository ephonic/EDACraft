"""Exact integer witness for a binary113 expansion product; no physical step.

All sums and products use rational integers. The diagnostic can distinguish
pairwise range rejection followed by exact cancellation from a product whose
least significant bit cannot be stored by ANY sum of supported components.
It neither truncates tails nor changes the solver's admitted range.
"""
from decimal import Decimal,InvalidOperation
from fractions import Fraction


def _binary113(value):
    if not value:return Fraction(0)
    sign=-1 if value<0 else 1;n=abs(value.numerator);d=value.denominator
    e=n.bit_length()-d.bit_length()
    if (n<d<<e) if e>=0 else (n<<(-e)<d):e-=1
    shift=112-e;a,b=(n<<shift,d) if shift>=0 else (n,d<<(-shift))
    h,r=divmod(a,b)
    if 2*r>b or (2*r==b and h%2):h+=1
    return Fraction(sign*h,1<<shift) if shift>=0 else Fraction(sign*h<<(-shift))


LOW=_binary113(Fraction(1,10**4000));HIGH=_binary113(Fraction(10**4000))
# Every admitted binary113 component is an integer multiple of this quantum.
GRID_EXPONENT2=LOW.numerator.bit_length()-LOW.denominator.bit_length()-112


def _supported(x):return not x or LOW<=abs(x)<=HIGH


def _vector(raw):
    if not isinstance(raw,(list,tuple)) or len(raw)>4096:raise ValueError('bounded decimal product vector required')
    out=[]
    for text in raw:
        if type(text) is not str or not 1<=len(text)<=256:raise ValueError('short decimal strings required')
        try:d=Decimal(text)
        except InvalidOperation as exc:raise ValueError('finite decimal component required') from exc
        if not d.is_finite() or (d and not Decimal('1e-4000')<=d.copy_abs()<=Decimal('1e4000')):
            raise ValueError('input component outside supported decimal range')
        value=_binary113(Fraction(d))
        if not _supported(value):raise ValueError('input component outside supported binary range')
        out.append(value)
    return out


def _dyadic(x,compact=False):
    if not x:return dict(coefficient='0',exponent2=0,significand_bits=0)
    n=x.numerator;d=x.denominator
    if d&(d-1):raise ValueError('exact dyadic required')
    zeros=(abs(n)&-abs(n)).bit_length()-1;n>>=zeros
    result=dict(exponent2=zeros-(d.bit_length()-1),significand_bits=abs(n).bit_length())
    result['coefficient_hex' if compact else 'coefficient']=hex(n) if compact else str(n)
    return result


def audit_mb_product_range(left,right):
    """Inspect a multiplication in the native expansion DAG, without native calls.

    Inputs are the saved binary113 decimal vectors passed to a multiplication.
    A grid obstruction proves that exact cancellation/canonicalization cannot
    make its result fit the current component representation. Other failed
    products may require a different accumulation order; that is not a solver
    acceptance. The diagnostic does not certify a complete physical trajectory.
    """
    a=_vector(left);b=_vector(right)
    if len(a)*len(b)>65536:raise ValueError('product pair budget exceeded')
    exact=sum(a,Fraction(0))*sum(b,Fraction(0));first=None;pairs=0
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            if not x or not y:continue
            pairs+=1;h=_binary113(x*y);l=_binary113(x*y-h)
            # A binary113 product has at most 226 significant bits. Neither
            # this exact FMA residual nor its exponent is rounded to binary64.
            if h+l!=x*y:raise ArithmeticError('exact binary113 product decomposition failed')
            if first is None and not (_supported(h) and _supported(l)):
                first=dict(left_index=i,right_index=j,high=_dyadic(h),low=_dyadic(l),
                    high_supported=_supported(h),low_supported=_supported(l))
    chunks=[];remaining=exact
    while remaining:
        if len(chunks)>=4096:raise ValueError('canonical diagnostic component budget exceeded')
        h=_binary113(remaining);chunks.append(h);remaining-=h
    tail=_dyadic(exact,compact=True)
    blocked=bool(exact and tail['exponent2']<GRID_EXPONENT2)
    supported=all(_supported(x) for x in chunks)
    compensated=[]
    if not blocked and not supported:
        for x in reversed(chunks):
            if _supported(x):compensated.append(x);continue
            # Construct a lossless, deliberately noncanonical pair. This is
            # diagnostic evidence only: the solver/auditors require strong
            # expansions and cannot consume this replacement unchanged.
            sign=-1 if x<0 else 1;high=LOW+abs(x)
            if _binary113(high)!=high or not _supported(high):
                compensated=None;break
            compensated.extend((sign*high,-sign*LOW))
        if compensated is not None and (len(compensated)>4096 or sum(compensated,Fraction(0))!=exact):
            compensated=None
    represented=supported or bool(compensated)
    return dict(scope='exact_binary113_expansion_product_range_witness',precision_bits=113,
        input_component_counts=[len(a),len(b)],nonzero_pairs=pairs,
        first_rejected_pair=first,exact_product=tail,exact_product_zero=not exact,
        canonical_expansion=[_dyadic(x) for x in reversed(chunks)],
        compensated_supported_expansion=[_dyadic(x) for x in compensated] if compensated else None,
        canonical_components_supported=supported,minimum_component_quantum_exponent2=GRID_EXPONENT2,
        exact_product_below_supported_grid=blocked,
        tail_bits_below_supported_grid=max(0,GRID_EXPONENT2-tail['exponent2']) if exact else 0,
        cancellation_can_remove_range_obstruction=False if blocked else None,
        exact_supported_expansion_exists=False if blocked else True if represented else None,
        native_physics_used=False,physical_time_advanced=False,complete_device_energy=False,physical_validated=False)
