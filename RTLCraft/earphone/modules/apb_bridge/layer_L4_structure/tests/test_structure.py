"""L4 StructuralIR tests for EarphoneAPBBridge."""

from earphone.modules.apb_bridge.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"region_decode", "request_fanout", "response_mux"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
