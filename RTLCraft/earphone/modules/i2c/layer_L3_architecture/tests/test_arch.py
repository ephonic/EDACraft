"""L3 ArchitectureIR tests for EarphoneI2C."""

from earphone.modules.i2c.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneI2C"
    assert ARCH.apb_addr_width == 12
    assert ARCH.transaction_data_width == 8


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert {"idle", "start", "byte", "ack", "data", "stop", "finish"}.issubset(set(ARCH.states))
    assert "apb" in ARCH.host_protocol.lower()
    assert len(ARCH.invariants) >= 3
