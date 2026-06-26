"""L4 StructuralIR tests for EarphoneSRAM256K."""

from earphone.modules.sram256k.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"apb_frontend", "byte_write_mask", "mem_array", "read_data_register"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
