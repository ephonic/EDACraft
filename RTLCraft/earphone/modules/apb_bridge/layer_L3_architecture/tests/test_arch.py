"""L3 ArchitectureIR tests for EarphoneAPBBridge."""

from earphone.modules.apb_bridge.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneAPBBridge"
    assert ARCH.slot_count == 8
    assert ARCH.slave_region_size_bytes == 4 * 1024 * 1024


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert "decode" in ARCH.stages
    assert "pready" in ARCH.timing.lower()
    assert len(ARCH.invariants) >= 3
