"""Exact independent decimal codec identity, including tiny signed energies."""
from decimal import Decimal,localcontext
import pytest
from tcad.postprocess.native_energy_identity import same_native_energy,_binary128_key


@pytest.mark.parametrize('source,recorded',[
 ('-8026.28955375010513795253075386426644','-8.026289553750105137952530753864266444e+03'),
 ('-8029.82219966466223559642401141900336','-8.029822199664662235596424011419003364e+03'),
 ('-8031.72153929605156519322406438732287','-8.031721539296051565193224064387322869e+03'),
 ('12118.1462202291381768937128526886227','1.211814622022913817689371285268862266e+04'),
 ('12130.0130637673850286795129704842111','1.213001306376738502867951297048421111e+04')])
def test_native_general_and_scientific_formats_share_exact_binary128_identity(source,recorded):
    assert source!=recorded and Decimal(source)!=Decimal(recorded)
    assert same_native_energy(recorded,source)


@pytest.mark.parametrize('value',['0','-0','1','-1','1e-120','-1e-320','1e-4930'])
def test_equivalent_decimal_spelling_keeps_all_energy_scales(value):
    assert same_native_energy(str(Decimal(value).normalize()),value)


@pytest.mark.parametrize('a,b',[('0','1e-120'),('0','-1e-4930'),('1e-120','-1e-120'),
 ('1.0000000000000000000000000000001e-120','1e-120'),('NaN','1'),('Infinity','1'),
 ('1e-6000','1e-6000'),('1e6000','1e6000')])
def test_erasure_sign_changes_representable_changes_and_invalid_values_reject(a,b):
    assert not same_native_energy(a,b)


def test_exact_binary_midpoints_use_nearest_even_and_adjacent_values_remain_distinct():
    with localcontext() as context:
        context.prec=200
        ulp=Decimal(2)**-112;half=ulp/2
        assert same_native_energy('1',str(1+half))
        assert not same_native_energy('1',str(1+ulp))
        assert same_native_energy(str(1+2*ulp),str(1+ulp+half))
        assert _binary128_key('2')==(1,1)
