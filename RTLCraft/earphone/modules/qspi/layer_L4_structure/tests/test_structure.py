"""L4 StructuralIR tests for EarphoneQSPI."""

from earphone.modules.qspi.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"host_request_frontend", "phase_fsm", "qspi_pad_control"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
