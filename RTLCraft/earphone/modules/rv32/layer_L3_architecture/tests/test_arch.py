"""L3 ArchitectureIR tests for EarphoneRV32."""

from earphone.modules.rv32.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneRV32"
    assert ARCH.isa == "RV32IM"
    assert ARCH.reset_pc == 0x1000
    assert ARCH.imem_width == 32
    assert ARCH.dmem_width == 32


def test_architecture_contract_contains_required_pipeline_and_units():
    assert {"IF", "ID", "EX", "MEM", "WB"}.issubset(set(ARCH.stages))
    assert "iterative" in ARCH.multiplier
    assert "iterative" in ARCH.divider
    assert ARCH.branch_predictor == "static not-taken"
