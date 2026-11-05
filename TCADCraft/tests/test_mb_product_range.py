from decimal import Decimal,localcontext
from fractions import Fraction
import builtins,json
import pytest
from tcad.postprocess.boltzmann_product_range import audit_mb_product_range as audit


def unpack(row):
    n=int(row.get('coefficient',row.get('coefficient_hex','0')),0) if 'coefficient_hex' in row else int(row['coefficient'])
    e=row['exponent2'];return Fraction(n<<e) if e>=0 else Fraction(n,1<<(-e))


@pytest.mark.parametrize('sign',[1,-1])
def test_exact_product_cannot_fit_any_supported_expansion(sign):
    # Powers of two make the expected low bit independent of a rounder.
    with localcontext() as c:
        c.prec=15000
        a=str(Decimal(sign)*Decimal(2)**-8000);b=str(Decimal(2)**-8000)
    # Short hexadecimal-free scientific decimal inputs round to those powers.
    with localcontext() as c:
        c.prec=40;a=format(Decimal(a),'.38E');b=format(Decimal(b),'.38E')
    r=audit([a],[b])
    assert r['exact_product']['exponent2']==-16000 and r['exact_product_below_supported_grid']
    assert not r['exact_supported_expansion_exists'] and r['cancellation_can_remove_range_obstruction'] is False
    assert unpack(r['exact_product'])==Fraction(sign,1<<16000)
    assert sum(map(unpack,r['canonical_expansion']),Fraction(0))==unpack(r['exact_product'])


def test_pairwise_range_failure_can_cancel_exactly():
    r=audit(['1e-3000','-1e-3000'],['1e-3000'])
    assert r['first_rejected_pair'] is not None
    assert r['exact_product_zero'] and r['exact_supported_expansion_exists']
    assert not r['exact_product_below_supported_grid'] and r['canonical_expansion']==[]


def test_cancellation_preserves_a_finite_tail():
    r=audit(['1e-3000','-1e-3000','1'],['2'])
    assert unpack(r['exact_product'])==2 and r['exact_supported_expansion_exists']


@pytest.mark.parametrize('left,right,expected',[([],['1'],0),(['0'],['1'],0),(['1.5'],['-2'],-3),(['1','2'],['3','4'],21)])
def test_known_products(left,right,expected):
    old=(left.copy(),right.copy());r=audit(left,right)
    assert unpack(r['exact_product'])==expected and (left,right)==old
    assert not r['native_physics_used'] and not r['physical_time_advanced'] and not r['physical_validated']
    json.dumps(r,allow_nan=False)


def test_binary113_low_bit_is_retained_after_large_cancellation():
    with localcontext() as c:
        c.prec=200;t=format(Decimal(2)**-112,'.115E')
    r=audit(['1',t],['1','-'+t])
    assert unpack(r['exact_product'])==1-Fraction(1,1<<224)
    assert len(r['canonical_expansion'])>=2 and r['exact_supported_expansion_exists']


def test_decimal_context_and_binary64_cannot_change_witness(monkeypatch):
    expected=audit(['1e-3000'],['1e-2000'])
    def forbidden(*a,**k):raise AssertionError('binary64/native import forbidden')
    original_import=builtins.__import__
    def guarded(name,*a,**k):
        if name.startswith(('tcad.core','tcad.solver','numpy')):return forbidden()
        return original_import(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',guarded)
    with localcontext() as c:
        c.prec=2;c.Emin=-99;c.Emax=99
        assert audit(['1e-3000'],['1e-2000'])==expected


@pytest.mark.parametrize('raw',[None,'1',[1],[True],['nan'],['Infinity'],['1e-4001'],['1e4001'],['1e-999999999'],['1e999999999'],['x'],['1'*257],['1']*4097])
def test_invalid_component_vectors_fail_before_large_integer_conversion(raw):
    with pytest.raises(ValueError):audit(raw,['1'])


def test_pair_budget_is_enforced():
    with pytest.raises(ValueError,match='pair budget'):audit(['1']*257,['1']*256)

@pytest.mark.parametrize('index',range(5))
def test_original_second_spatial_native_failures_have_exact_grid_obstruction(index):
    from pathlib import Path
    from tcad.postprocess.boltzmann_product_range import _vector,_dyadic,_binary113
    case=json.loads((Path(__file__).parent/'data/mb_product_range_witness.json').read_text())['cases'][index]
    r=audit(case['left'],case['right'])
    assert r==case['witness'] and r['exact_product']['exponent2']==case['expected_tail_exponent2']
    assert not r['canonical_components_supported']
    if case['mode']=='contact':
        assert not r['exact_product_below_supported_grid'] and r['exact_supported_expansion_exists'] is True
        assert sum(map(unpack,r['compensated_supported_expansion']),Fraction(0))==unpack(r['exact_product'])
    else:assert r['exact_product_below_supported_grid'] and r['exact_supported_expansion_exists'] is False
    first=r['first_rejected_pair'];a,b,h,l=case['native_first_pair']
    assert _vector([a])[0]==_vector(case['left'])[first['left_index']]
    assert _vector([b])[0]==_vector(case['right'])[first['right_index']]
    # Native decimal exports are rounded back to binary113. Output h/l may
    # lie outside the solver range, so the input-range parser is not used.
    assert _dyadic(_binary113(Fraction(Decimal(h))))==first['high']
    assert _dyadic(_binary113(Fraction(Decimal(l))))==first['low']
    assert sum(map(unpack,r['canonical_expansion']),Fraction(0))==unpack(r['exact_product'])
