"""L4 StructuralIR tests for EarphoneSIMD16."""

from earphone.modules.simd16.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {"int16_lane_array", "fp16_pipeline", "predicate_mask", "result_mux"}.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces
