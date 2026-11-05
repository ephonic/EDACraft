"""Exact IEEE binary128 identity of independently parsed decimal encodings.

Native energy coordinates use binary128 (113 significand bits). Their 36g
state and 36e local-record formats both round-trip, while projecting them to
the host's 64-bit-significand long double can disagree at a midpoint. Integer
rational rounding avoids that second projection and introduces no tolerance.
"""
from decimal import Decimal,InvalidOperation


def _binary128_key(value):
    value=Decimal(value)
    if not value.is_finite():raise ValueError('finite energy encoding required')
    if not value:return 0,0
    # Bound the decimal exponent before constructing potentially enormous
    # integers. The two edge decades still use exact rational rounding below.
    if value.adjusted()>4932:raise ValueError('binary128 energy overflow')
    if value.adjusted()<-4966:return 0,0
    numerator,denominator=value.copy_abs().as_integer_ratio()
    exponent=numerator.bit_length()-denominator.bit_length()
    if (numerator < denominator<<exponent) if exponent>=0 else (numerator<<(-exponent) < denominator):
        exponent-=1
    if exponent>16383:raise ValueError('binary128 energy overflow')
    quantum=max(exponent-112,-16494)
    if quantum>=0:denominator<<=quantum
    else:numerator<<=-quantum
    integer,remainder=divmod(numerator,denominator)
    if 2*remainder>denominator or (2*remainder==denominator and integer&1):integer+=1
    if not integer:return 0,0
    zeros=(integer&-integer).bit_length()-1
    integer>>=zeros;quantum+=zeros
    if integer.bit_length()-1+quantum>16383:raise ValueError('binary128 energy overflow')
    return -integer if value.is_signed() else integer,quantum


def same_native_energy(recorded,source):
    """Same nearest-even binary128 value, preserving nonzero/zero distinction."""
    try:
        a,b=Decimal(recorded),Decimal(source)
        if not a.is_finite() or not b.is_finite() or bool(a)!=bool(b):return False
        ka,kb=_binary128_key(a),_binary128_key(b)
        # Nonzero values outside the representable range must not silently
        # certify an erased authoritative coordinate.
        return ka==kb and (not a or ka!=(0,0))
    except (ValueError,InvalidOperation,TypeError):return False
