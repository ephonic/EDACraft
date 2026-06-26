"""L4 StructuralIR tests for EarphoneFFT256."""

from earphone.modules.fft256.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"input_adapter", "fft256_core", "output_adapter"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
