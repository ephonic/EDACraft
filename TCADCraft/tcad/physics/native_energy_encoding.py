"""Lossless native input literals for decimal binary128 energy coordinates.

Only encoding is performed here. EOS, fluxes and solves remain native. Exact
hexadecimal literals avoid decimal midpoint differences between libquadmath
versions, especially at the lower subnormal boundary.
"""
from decimal import Decimal,InvalidOperation
import re
from tcad.postprocess.native_energy_identity import _binary128_key

_DECIMAL=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',re.ASCII)


def native_energy_literal(value):
    if not isinstance(value,str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError('finite native-range decimal energy coordinate required')
    try:
        decimal=Decimal(value);integer,exponent=_binary128_key(decimal)
    except (InvalidOperation,ValueError,TypeError) as error:
        raise ValueError('finite native-range decimal energy coordinate required') from error
    if not integer:
        if decimal:raise ValueError('nonzero energy coordinate underflows to zero')
        return '-0' if decimal.is_signed() else '0'
    return ('-' if integer<0 else '')+f'0x{abs(integer):x}p{exponent:+d}'
