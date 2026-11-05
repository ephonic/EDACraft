"""Native capacity boundaries with independent exact arithmetic checks."""
from fractions import Fraction
from pathlib import Path
import json
import random
import pytest
from tcad.core import _capacity_mb as native
from tcad.postprocess.boltzmann_capacity_arithmetic import audit_mb_capacity_arithmetic as audit,split_mb_capacity_arithmetic
from tcad.postprocess.boltzmann_capacity_endpoint_collision import audit_mb_capacity_endpoint_collision as audit_collision
from tcad.postprocess.boltzmann_recomputed_endpoint_collision import _wire
from tcad.postprocess.boltzmann_dyadic_codec import scaled_value_fraction
from tcad.postprocess.boltzmann_recomputed_endpoint_powerlaw import split_mb_recomputed_endpoint_powerlaw

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'docs/validation/mb_recomputed_endpoint_20261024/captured'


def operation(op,a,b):
    left,right=_wire(Fraction(a)),_wire(Fraction(b))
    raw=native.arithmetic([op],left,right)
    assert audit(op,left,right,raw)['exact_integer_identity']
    return raw


def control(mode,cell):
    r=json.loads((PARENT/f'control_{mode}.json').read_text())['report']
    c=r['collisions'][cell]
    packet=c['root_packet']
    # The selected constitutive tau values are part of the saved root header.
    fixed=[c['command'][14],packet[4],packet[5],*c['command'][15:]]
    return r['transported_states'][cell]['endpoint'],fixed


@pytest.mark.parametrize('width',[65520,65521,65534,65535,65536])
@pytest.mark.parametrize('sign',[-1,1])
def test_full_width_shift_read_add_and_cancellation(width,sign):
    x=sign*((1<<(width-1))+1)
    operation('add',x,0)
    operation('subtract',x,x)
    operation('add',x,-sign)


@pytest.mark.parametrize('target',[65535,65536])
@pytest.mark.parametrize('sign',[-1,1])
def test_product_fits_even_when_limb_sum_exceeds_capacity(target,sign):
    a=(1<<163)+1
    b=(1<<(target-164))+1
    assert (a*b).bit_length()==target
    assert ((a.bit_length()+15)//16+(b.bit_length()+15)//16)==4097
    operation('multiply',sign*a,b)


@pytest.mark.parametrize('op,a,b',[
    ('add',(1<<65536)-1,1),
    ('subtract',-((1<<65536)-1),1),
    ('multiply',(1<<163)+1,(1<<(65537-164))+1),
    ('multiply',(1<<32768)-1,(1<<32769)-1),
],ids=['carry','negative_carry','product','dense_product'])
def test_true_overflow_is_rejected(op,a,b):
    with pytest.raises(ValueError,match='budget exceeded'):
        native.arithmetic([op],_wire(Fraction(a)),_wire(Fraction(b)))


def test_product_pair_budget_is_preserved():
    a=(1<<(113*260))-1
    with pytest.raises(ValueError,match='pair budget exceeded'):
        native.arithmetic(['multiply'],_wire(Fraction(a)),_wire(Fraction(a)))


@pytest.mark.parametrize('seed',range(12))
def test_random_signed_dyadics_and_two_round_division(seed):
    rng=random.Random(seed)
    a=Fraction(rng.getrandbits(500+seed*83)*rng.choice((-1,1)),1<<rng.randrange(100))
    b=Fraction((rng.getrandbits(350+seed*31)|1)*rng.choice((-1,1)),1<<rng.randrange(100))
    for op in ('add','subtract','multiply','divide'):operation(op,a,b)


@pytest.mark.parametrize('numerator',[1,3,5,7,2**114+1,-(2**114+3)])
def test_quotient_ties_and_exact_remainder(numerator):
    operation('divide',numerator,3 if abs(numerator)<10 else 2**113)


@pytest.mark.parametrize('damage',['version','precision','operation','count','extra','truncated','value','remainder'])
def test_saved_proof_tampering_is_rejected(damage):
    a,b=_wire(Fraction(7)),_wire(Fraction(3))
    raw=native.arithmetic(['divide'],a,b)
    if damage=='version':raw[0]='old'
    elif damage=='precision':raw[1]='64'
    elif damage=='operation':raw[2]='add'
    elif damage=='count':raw[3]='8195'
    elif damage=='extra':raw.append('0')
    elif damage=='truncated':raw.pop()
    elif damage=='value':raw[7]='0x1'
    else:raw[-1]='0'
    with pytest.raises(ValueError):audit('divide',a,b,raw)


@pytest.mark.parametrize('damage',['nul','long','type','op_type','op_count','short','overlap','exponent','zero_divisor'])
def test_native_argument_and_wire_validation(damage):
    op=['add'];a=_wire(Fraction(7));b=_wire(Fraction(3))
    if damage=='nul':a[3]='0x1\0'
    elif damage=='long':a[3]='1'*65
    elif damage=='type':a[3]=1
    elif damage=='op_type':op='add'
    elif damage=='op_count':op=[]
    elif damage=='short':a.pop()
    elif damage=='overlap':a=['mb_scaled_value_v1','113','2','0x1','0','0x1','0']
    elif damage=='exponent':a[-1]='65537'
    else:op=['divide'];b=_wire(Fraction())
    with pytest.raises(ValueError):native.arithmetic(op,a,b)


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
@pytest.mark.parametrize('cell',[0,1])
def test_saved_control_fixed_collision_has_complete_independent_energy_gate(mode,cell):
    endpoint,command=control(mode,cell)
    raw=native.collision(endpoint,command)
    check=audit_collision(endpoint,command,raw)
    assert check['status']=='complete' and check['full_fixed_tau_energy_gate_passed']


@pytest.mark.parametrize('cell,last',[(0,'lineage0.17'),(1,'lineage0.13')])
def test_original_mixed_reaches_true_boundary_without_partial_output(cell,last):
    c=json.loads((PARENT/'original_mixed.json').read_text())['cells'][cell]
    endpoint=c['args'][0];before=list(endpoint)
    with pytest.raises(ValueError,match=last):native.collision(endpoint,c['fixed_reference_tau_command'])
    assert endpoint==before


def test_saved_arithmetic_replay_calls_no_native(monkeypatch):
    a,b=_wire(Fraction(7)),_wire(Fraction(3));raw=native.arithmetic(['divide'],a,b)
    def deny(*args):raise AssertionError('producer called')
    monkeypatch.setattr(native,'arithmetic',deny)
    assert audit('divide',a,b,raw)['exact_integer_identity']
