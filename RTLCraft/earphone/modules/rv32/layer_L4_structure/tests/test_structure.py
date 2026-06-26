"""L4 StructuralIR tests for EarphoneRV32."""

from earphone.modules.rv32.layer_L4_structure.src.structure import STRUCTURE


def test_structure_contract_contains_required_subblocks():
    names = {subblock.name for subblock in STRUCTURE.subblocks}
    assert {
        "pc_unit",
        "regfile",
        "decoder",
        "alu",
        "muldiv_unit",
        "load_store_unit",
    }.issubset(names)


def test_structure_contract_subblocks_have_interfaces():
    for subblock in STRUCTURE.subblocks:
        assert subblock.purpose
        assert subblock.interfaces

    regfile = next(subblock for subblock in STRUCTURE.subblocks if subblock.name == "regfile")
    assert {"rs1_addr", "rs2_addr", "rd_wdata"}.issubset(set(regfile.interfaces))
