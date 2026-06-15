"""L4 StructuralIR tests for EarphoneI2C."""

from earphone.modules.i2c.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"apb_register_bank", "byte_controller_fsm", "open_drain_pad_ctrl"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
